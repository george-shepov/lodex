import asyncio
from pathlib import Path

import httpx
import pytest

import admin_media
import main
from catalog_pricing import markup_cents


@pytest.fixture(name="catalog_app")
def catalog_fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    uploads = tmp_path / "data" / "uploads"
    uploads.mkdir(parents=True)
    monkeypatch.setattr(main, "UPLOAD_DIR", uploads)
    monkeypatch.setattr(main, "LODEX_ADMIN_TOKEN", "owner-token-for-tests")
    main.admin_sessions.clear()
    return tmp_path / "data"


def run(coro):
    return asyncio.run(coro)


def concept_payload():
    common_offer = {
        "retailer_key": "manual-catalog",
        "retailer_name": "Approved Manual Catalog",
        "retailer_homepage_url": "https://catalog.example.test",
        "retailer_terms_notes": "Test fixture supplied by an administrator.",
        "currency": "USD",
        "availability_status": "IN_STOCK",
        "source_timestamp": "2026-08-29T12:00:00+00:00",
        "expires_at": "2026-09-01T12:00:00+00:00",
    }
    return {
        "slug": "cedar-focus-office",
        "name": "Cedar Focus Office",
        "category": "Backyard Offices",
        "summary": "A compact insulated backyard office concept.",
        "description": "A quiet one-person workspace with durable exterior materials.",
        "status": "CONCEPT",
        "publication_status": "PUBLISHED",
        "width": "10",
        "length": "12",
        "height": "9",
        "dimension_unit": "ft",
        "hero_media": {"url": "/inspiration/realistic/office.webp", "alt": "Cedar backyard office concept rendering"},
        "intended_use": "Remote workers who need a separate year-round workspace.",
        "included_features": ["Insulated shell", "Dedicated task lighting"],
        "configurable_options": ["Desk finish", "Exterior stain"],
        "commercial_modes": ["DESIGN_ONLY", "BUILD_ONLY", "TURNKEY"],
        "base_labor_estimate_cents": 500_000,
        "base_project_overhead_cents": 100_000,
        "lead_time_min_days": 30,
        "lead_time_max_days": 60,
        "price_validity_hours": 72,
        "markup_policy": {
            "name": "Backyard office procurement",
            "scope": "CONCEPT",
            "method": "PERCENT",
            "value": "25",
            "minimum_margin_amount_cents": 0,
        },
        "components": [
            {
                "group": "furniture",
                "name": "Work desk",
                "quantity": "1",
                "unit": "each",
                "selection_mode": "SUBSTITUTE_ALLOWED",
                "requirement_spec_json": {"type": "desk", "minWidthIn": 60, "finish": ["oak", "walnut"]},
                "sort_order": 10,
                "offer": common_offer | {
                    "retailer_product_id": "desk-001",
                    "brand": "Fixture Brand",
                    "product_name": "Sixty Inch Oak Desk",
                    "product_url": "https://catalog.example.test/desk-001",
                    "product_category": "desk",
                    "sku": "DESK-001",
                    "regular_price_cents": 80_000,
                },
            },
            {
                "group": "electrical / lighting",
                "name": "Task light",
                "quantity": "2",
                "unit": "each",
                "selection_mode": "SUBSTITUTE_ALLOWED",
                "requirement_spec_json": {"type": "task-light", "finish": ["black", "brass"]},
                "sort_order": 20,
                "offer": common_offer | {
                    "retailer_product_id": "light-001",
                    "brand": "Fixture Brand",
                    "product_name": "Adjustable Task Light",
                    "product_url": "https://catalog.example.test/light-001",
                    "product_category": "lighting",
                    "sku": "LIGHT-001",
                    "regular_price_cents": 10_000,
                },
            },
        ],
    }


def test_catalog_markup_is_fixed_precision_and_honors_minimum():
    assert markup_cents(9_999, {"method": "PERCENT", "value": "12.5"}) == 1_250
    assert markup_cents(9_999, {"method": "FIXED", "value": "1750"}) == 1_750
    assert markup_cents(
        1_000,
        {"method": "PERCENT", "value": "5", "minimum_margin_amount_cents": 900},
    ) == 900


def test_catalog_rejects_invalid_lead_time_and_currency(catalog_app):
    _ = catalog_app

    async def scenario():
        transport = httpx.ASGITransport(app=admin_media.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            assert (await client.post("/api/admin/login", json={"token": "owner-token-for-tests"})).status_code == 200

            invalid_lead_time = concept_payload() | {
                "lead_time_min_days": 60,
                "lead_time_max_days": 30,
            }
            lead_time_response = await client.post("/api/admin/concepts", json=invalid_lead_time)
            assert lead_time_response.status_code == 422
            assert "lead_time_min_days must not exceed lead_time_max_days" in lead_time_response.text

            invalid_currency = concept_payload()
            invalid_currency["components"][0]["offer"]["currency"] = "EUR"
            currency_response = await client.post("/api/admin/concepts", json=invalid_currency)
            assert currency_response.status_code == 422
            currency_error = currency_response.json()["detail"][0]
            assert currency_error["loc"][-1] == "currency"
            assert currency_error["ctx"]["expected"] == "'USD'"

    run(scenario())


def test_concept_public_boundary_and_quote_snapshot_are_immutable(catalog_app):
    _ = catalog_app

    async def scenario():
        transport = httpx.ASGITransport(app=admin_media.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            assert (await client.post("/api/admin/concepts", json=concept_payload())).status_code == 401
            assert (await client.post("/api/admin/login", json={"token": "owner-token-for-tests"})).status_code == 200

            created_response = await client.post("/api/admin/concepts", json=concept_payload())
            assert created_response.status_code == 200, created_response.text
            admin = created_response.json()
            concept_id = admin["concept"]["id"]
            assert len(admin["components"]) == 2
            assert admin["pricing"]["acquisition_subtotal_cents"] == 100_000
            assert admin["pricing"]["procurement_markup_cents"] == 25_000
            assert admin["pricing"]["total_cents"] == 725_000

            public_response = await client.get("/api/concepts/cedar-focus-office")
            assert public_response.status_code == 200
            public = public_response.json()
            assert public["status_label"] == "Concept Design"
            assert public["price"]["turnkey_price_cents"] == 725_000
            assert len(public["component_groups"]) == 2
            serialized_public = public_response.text.lower()
            assert "acquisition" not in serialized_public
            assert "markup" not in serialized_public
            assert "margin" not in serialized_public
            assert "source_design_provenance" not in serialized_public

            quote_response = await client.post(f"/api/concepts/{concept_id}/quote-request", json={"lead_id": "LEAD-123"})
            assert quote_response.status_code == 200
            quote = quote_response.json()
            assert quote["total_cents"] == 725_000

            desk_offer_id = admin["components"][0]["preferred_offer_id"]
            updated = await client.patch(
                f"/api/admin/catalog/offers/{desk_offer_id}",
                json={"regular_price_cents": 120_000, "source_timestamp": "2026-08-30T12:00:00+00:00"},
            )
            assert updated.status_code == 200
            current_public = (await client.get("/api/concepts/cedar-focus-office")).json()
            assert current_public["price"]["turnkey_price_cents"] == 775_000

            frozen = (await client.get(f"/api/admin/quotes/{quote['quote_id']}")).json()
            assert frozen["total_cents"] == 725_000
            assert frozen["component_snapshot_json"][0]["acquisition_unit_price_cents"] == 80_000

    run(scenario())