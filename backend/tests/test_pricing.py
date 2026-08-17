import asyncio
import json
from decimal import Decimal
from pathlib import Path

import pytest
import httpx

import distance
import main
from distance import DistanceResult
from pricing import PricingConfig, calculate_visit_pricing, classify_customer_segment


TEST_CONFIG = PricingConfig(
    home_small_cents=5_000,
    home_several_cents=10_000,
    home_major_cents=15_000,
    business_assessment_cents=30_000,
    included_distance_miles=Decimal("5"),
    distance_rate_cents=250,
)


@pytest.mark.parametrize(
    ("distance", "expected_cents"),
    [(3, 5_000), (10, 6_250), (20, 8_750)],
)
def test_home_small_distance_pricing(distance, expected_cents):
    result = calculate_visit_pricing("home", "homeowner", "small", distance, config=TEST_CONFIG)
    assert result["fee_cents"] == expected_cents
    assert result["distance_miles"] == float(distance)


def test_home_whole_home_nearby_is_at_least_150():
    result = calculate_visit_pricing("home", "homeowner", "major", 3, config=TEST_CONFIG)
    assert result["fee_cents"] >= 15_000
    assert result["label"] == "On-Site Project Consultation"


@pytest.mark.parametrize(
    ("customer_type", "expected"),
    [
        ("individual landlord", "business"),
        ("property-management company", "enterprise"),
        ("leasing company", "enterprise"),
    ],
)
def test_customer_classification(customer_type, expected):
    assert classify_customer_segment(customer_type, "home") == expected


def test_enterprise_requires_approved_amount():
    pending = calculate_visit_pricing("enterprise", "property-management company", None, None, config=TEST_CONFIG)
    assert pending["fee_cents"] is None
    assert pending["requires_manual_review"] is True
    approved = calculate_visit_pricing(
        "enterprise",
        "property-management company",
        None,
        None,
        approved_amount_cents=42_500,
        config=TEST_CONFIG,
    )
    assert approved["fee_cents"] == 42_500


def test_old_record_without_segment_fields_still_loads(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    data_dir = tmp_path / "data"
    uploads = data_dir / "uploads"
    uploads.mkdir(parents=True)
    old_record = {
        "id": "old-project",
        "project_code": "LDX-OLD123",
        "name": "Legacy Customer",
        "phone": "2165550100",
        "service_category": "General repair",
    }
    (data_dir / "appointment-requests.jsonl").write_text(json.dumps(old_record) + "\n", encoding="utf-8")
    monkeypatch.setattr(main, "UPLOAD_DIR", uploads)
    monkeypatch.setattr(main, "PAYMENTS_FILE", data_dir / "payments.jsonl")

    loaded = main.find_project("ldx-old123", "(216) 555-0100")
    assert loaded == old_record
    public = main.public_project_record(loaded)
    assert public["customer_segment"] is None
    assert public["visit_fee_cents"] is None


def test_appointment_uses_provider_distance_and_persists_pricing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    data_dir = tmp_path / "data"
    uploads = data_dir / "uploads"
    uploads.mkdir(parents=True)
    monkeypatch.setattr(main, "UPLOAD_DIR", uploads)

    class TenMileProvider:
        async def route_distance(self, project_address: str) -> DistanceResult:
            assert project_address == "123 Main Street, Cleveland, OH"
            return DistanceResult(10, "test_router", "test route")

    monkeypatch.setattr(distance, "distance_provider", TenMileProvider())

    async def scenario():
        transport = httpx.ASGITransport(app=main.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.post(
                "/api/appointments/request",
                json={
                    "name": "Home Owner",
                    "phone": "2165550100",
                    "address": "123 Main Street, Cleveland, OH",
                    "preferred_date": "2026-08-20",
                    "preferred_time": "Morning · 9 AM–12 PM",
                    "project_summary": "Install one shelf.",
                    "service_category": "LODEX Home · Handyman & Property Maintenance",
                    "customer_segment": "home",
                    "customer_type": "homeowner",
                    "project_size_class": "small",
                    "distance_miles": 1,
                    "assumptions_confirmed": True,
                },
            )

    response = asyncio.run(scenario())
    assert response.status_code == 200
    confirmation = response.json()["confirmation"]
    assert confirmation["distance_miles"] == 10
    assert confirmation["visit_fee_cents"] == 6_250
    assert confirmation["visit_fee_label"] == "Diagnostic Visit"
    record = json.loads((data_dir / "appointment-requests.jsonl").read_text(encoding="utf-8"))
    assert record["distance_provider"] == "test_router"
    assert record["pricing_rule"] == "home_small_distance_adjusted"
