import asyncio
import hashlib
import hmac
import json
import time
from pathlib import Path

import httpx
import pytest

import main


@pytest.fixture
def payment_app(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    data_dir = tmp_path / "data"
    uploads_dir = data_dir / "uploads"
    uploads_dir.mkdir(parents=True)
    monkeypatch.setattr(main, "UPLOAD_DIR", uploads_dir)
    monkeypatch.setattr(main, "PAYMENTS_FILE", data_dir / "payments.jsonl")
    monkeypatch.setattr(main, "STRIPE_SECRET_KEY", "sk_test_example")
    monkeypatch.setattr(main, "STRIPE_WEBHOOK_SECRET", "whsec_example")
    monkeypatch.setattr(main, "STRIPE_CURRENCY", "usd")
    monkeypatch.setattr(main, "STRIPE_DEPOSIT_AMOUNT_CENTS", 5000)
    return data_dir


async def _api_request(method: str, path: str, **kwargs) -> httpx.Response:
    transport = httpx.ASGITransport(app=main.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        return await client.request(method, path, **kwargs)


def api_request(method: str, path: str, **kwargs) -> httpx.Response:
    return asyncio.run(_api_request(method, path, **kwargs))


def write_project(data_dir: Path, *, project_code: str = "LDX-ABC123") -> None:
    record = {
        "id": "project-1",
        "project_code": project_code,
        "phone": "(216) 555-0100",
        "email": "customer@example.com",
        "service_category": "General repair",
    }
    (data_dir / "appointment-requests.jsonl").write_text(
        json.dumps(record) + "\n", encoding="utf-8"
    )


def read_records(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def signed_headers(payload: bytes, secret: str = "whsec_example") -> dict[str, str]:
    timestamp = int(time.time())
    digest = hmac.new(
        secret.encode("utf-8"),
        f"{timestamp}.".encode("utf-8") + payload,
        hashlib.sha256,
    ).hexdigest()
    return {"Stripe-Signature": f"t={timestamp},v1={digest}"}


def test_stripe_checkout_sends_form_mapping(monkeypatch: pytest.MonkeyPatch):
    captured: dict[str, object] = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"id": "cs_test_mapping", "url": "https://checkout.stripe.test/mapping"}

    class FakeAsyncClient:
        def __init__(self, **kwargs):
            captured["client_kwargs"] = kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url, *, data, headers):
            captured["url"] = url
            captured["data"] = data
            captured["headers"] = headers
            return FakeResponse()

    monkeypatch.setattr(main, "STRIPE_SECRET_KEY", "sk_test_example")
    monkeypatch.setattr(main, "STRIPE_DEPOSIT_AMOUNT_CENTS", 5000)
    monkeypatch.setattr(main.httpx, "AsyncClient", FakeAsyncClient)

    session = asyncio.run(
        main.stripe_checkout_session([("mode", "payment")], "lodex-test-idempotency")
    )

    assert session["id"] == "cs_test_mapping"
    assert captured["data"] == {"mode": "payment"}
    assert captured["headers"]["Authorization"] == "Bearer sk_test_example"


def test_checkout_uses_server_amount_and_records_session(
    payment_app, monkeypatch: pytest.MonkeyPatch
):
    data_dir = payment_app
    write_project(data_dir)
    captured: dict[str, object] = {}

    async def fake_checkout(fields, idempotency_key):
        captured["fields"] = fields
        captured["idempotency_key"] = idempotency_key
        return {"id": "cs_test_123", "url": "https://checkout.stripe.test/cs_test_123"}

    monkeypatch.setattr(main, "stripe_checkout_session", fake_checkout)

    response = api_request(
        "POST",
        "/api/payments/checkout",
        json={
            "project_code": "ldx-abc123",
            "phone": "216.555.0100",
            "amount_cents": 1,
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": "checkout_created",
        "project_code": "LDX-ABC123",
        "checkout_url": "https://checkout.stripe.test/cs_test_123",
        "amount_cents": 5000,
        "currency": "usd",
    }
    fields = dict(captured["fields"])
    assert fields["line_items[0][price_data][unit_amount]"] == "5000"
    assert fields["line_items[0][price_data][currency]"] == "usd"
    assert fields["customer_email"] == "customer@example.com"
    assert str(captured["idempotency_key"]).startswith("lodex-deposit-LDX-ABC123-")

    records = read_records(data_dir / "payments.jsonl")
    assert records[0]["status"] == "checkout_created"
    assert records[0]["session_id"] == "cs_test_123"


def test_checkout_rejects_unmatched_project(payment_app, monkeypatch: pytest.MonkeyPatch):
    _ = payment_app
    called = False

    async def fake_checkout(fields, idempotency_key):
        nonlocal called
        called = True
        return {"id": "unused", "url": "https://unused.test"}

    monkeypatch.setattr(main, "stripe_checkout_session", fake_checkout)
    response = api_request(
        "POST",
        "/api/payments/checkout",
        json={"project_code": "LDX-NOTFOUND", "phone": "2165550100"},
    )

    assert response.status_code == 404
    assert called is False


def test_webhook_records_paid_event_and_is_idempotent(payment_app):
    data_dir = payment_app
    event = {
        "id": "evt_test_paid",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_123",
                "payment_status": "paid",
                "payment_intent": "pi_test_123",
                "amount_total": 5000,
                "currency": "usd",
                "metadata": {"project_code": "LDX-ABC123", "project_id": "project-1"},
            }
        },
    }
    payload = json.dumps(event).encode("utf-8")

    response = api_request(
        "POST",
        "/api/payments/webhook", content=payload, headers=signed_headers(payload)
    )
    duplicate = api_request(
        "POST",
        "/api/payments/webhook", content=payload, headers=signed_headers(payload)
    )

    assert response.status_code == 200
    assert response.json() == {"received": True, "handled": True}
    assert duplicate.status_code == 200
    assert duplicate.json() == {"received": True, "handled": True, "duplicate": True}
    records = read_records(data_dir / "payments.jsonl")
    assert len(records) == 1
    assert records[0]["status"] == "paid"
    assert records[0]["event_id"] == "evt_test_paid"


def test_webhook_rejects_bad_signature_and_ignores_unknown_events(payment_app):
    data_dir = payment_app
    payload = json.dumps(
        {
            "id": "evt_test_unknown",
            "type": "payment_method.attached",
            "data": {"object": {"id": "pm_test_123"}},
        }
    ).encode("utf-8")

    invalid = api_request(
        "POST",
        "/api/payments/webhook",
        content=payload,
        headers={"Stripe-Signature": "t=1,v1=invalid"},
    )
    ignored = api_request(
        "POST",
        "/api/payments/webhook", content=payload, headers=signed_headers(payload)
    )

    assert invalid.status_code == 400
    assert ignored.status_code == 200
    assert ignored.json() == {"received": True, "handled": False}
    assert read_records(data_dir / "payments.jsonl") == []
