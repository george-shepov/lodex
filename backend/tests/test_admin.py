import asyncio
import json
from pathlib import Path

import httpx
import pytest

import main


@pytest.fixture
def admin_app(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    data_dir = tmp_path / "data"
    uploads_dir = data_dir / "uploads"
    uploads_dir.mkdir(parents=True)
    monkeypatch.setattr(main, "UPLOAD_DIR", uploads_dir)
    monkeypatch.setattr(main, "SUPPORT_REQUESTS_FILE", data_dir / "support-requests.jsonl")
    monkeypatch.setattr(main, "VISITOR_EVENTS_FILE", data_dir / "visitor-events.jsonl")
    monkeypatch.setattr(main, "PROJECT_EVENTS_FILE", data_dir / "project-events.jsonl")
    monkeypatch.setattr(main, "PAYMENTS_FILE", data_dir / "payments.jsonl")
    monkeypatch.setattr(main, "LODEX_ADMIN_TOKEN", "owner-token-for-tests")
    main.admin_sessions.clear()
    main.active_visitors.clear()
    return data_dir


def run(coro):
    return asyncio.run(coro)


async def submit_project(client: httpx.AsyncClient) -> httpx.Response:
    return await client.post(
        "/api/appointments/request",
        json={
            "name": "Jordan Customer",
            "phone": "440-555-0100",
            "email": "jordan@example.com",
            "address": "123 Main Street, Cleveland, OH",
            "preferred_date": "2026-08-20",
            "preferred_time": "Morning · 9 AM–12 PM",
            "project_summary": "Mount a television above the living-room fireplace and hide the cable.",
            "service_category": "White-Glove Delivery & Installation",
            "uploads": [{"upload_id": "upload-1", "filename": "fireplace.jpg", "media_type": "image/jpeg"}],
            "conversation": [
                {"role": "user", "text": "I need a TV mounted."},
                {"role": "assistant", "text": "What is the wall material?", "kind": "required"},
            ],
            "assumptions_confirmed": True,
            "intake_ready": True,
        },
    )


def test_customer_receives_complete_confirmation(admin_app):
    async def scenario():
        transport = httpx.ASGITransport(app=main.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await submit_project(client)
            assert response.status_code == 200
            body = response.json()
            assert body["project_code"].startswith("LDX-")
            assert body["confirmation"]["address"] == "123 Main Street, Cleveland, OH"
            assert body["confirmation"]["project_summary"].startswith("Mount a television")
            assert body["confirmation"]["uploads"][0]["filename"] == "fireplace.jpg"

    run(scenario())


def test_admin_session_protects_inbox_and_returns_full_messages(admin_app):
    async def scenario():
        transport = httpx.ASGITransport(app=main.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            assert (await client.get("/api/admin/overview")).status_code == 401
            await submit_project(client)
            login = await client.post("/api/admin/login", json={"token": "owner-token-for-tests"})
            assert login.status_code == 200
            overview = (await client.get("/api/admin/overview")).json()
            project = overview["project_requests"][0]
            assert project["name"] == "Jordan Customer"
            assert len(project["conversation"]) == 2
            assert project["project_summary"].startswith("Mount a television")

    run(scenario())


def test_presence_is_anonymous_and_support_room_is_visible_to_admin(admin_app):
    async def scenario():
        transport = httpx.ASGITransport(app=main.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            heartbeat = await client.post(
                "/api/presence/heartbeat",
                json={"visitor_id": "lv_1234567890123456", "path": "/services/handyman-maintenance", "page_title": "LODEX"},
            )
            assert heartbeat.status_code == 200
            support = await client.post(
                "/api/support/call",
                json={"visitor_id": "lv_1234567890123456", "name": "Jordan", "phone": "4405550100", "message": "Please look at this leak."},
            )
            assert support.status_code == 200
            assert support.json()["room_code"].startswith("LDX-LIVE-")
            await client.post("/api/admin/login", json={"token": "owner-token-for-tests"})
            overview = (await client.get("/api/admin/overview")).json()
            assert overview["active_count"] == 1
            assert overview["visitors_today"] == 1
            assert overview["support_requests"][0]["message"] == "Please look at this leak."

        record = json.loads((admin_app / "visitor-events.jsonl").read_text(encoding="utf-8"))
        assert "ip" not in record
        assert "user_agent" not in record

    run(scenario())
