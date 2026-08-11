import asyncio
from pathlib import Path

import httpx
import pytest

import main


async def _api_request(method: str, path: str, **kwargs) -> httpx.Response:
    transport = httpx.ASGITransport(app=main.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        return await client.request(method, path, **kwargs)


def api_request(method: str, path: str, **kwargs) -> httpx.Response:
    return asyncio.run(_api_request(method, path, **kwargs))


@pytest.fixture(autouse=True)
def no_ai_key(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)


def test_qualified_property_lead_moves_to_visit_without_another_question():
    conversation = [
        {"role": "user", "text": "How much to minimally furnish a four bedroom house for Airbnb?"},
        {"role": "assistant", "text": "Do you need sourcing and setup, and where is the house?"},
        {"role": "user", "text": "5160 Stevenson St. I need to spend the minimum possible."},
        {"role": "assistant", "text": "Do you need the whole house or only certain rooms?"},
        {"role": "user", "text": "The whole property. I need to compare Airbnb, private rent, or selling after a refresh and landscaping."},
        {"role": "user", "text": "All of the above."},
    ]

    response = api_request(
        "POST",
        "/api/intake/chat",
        json={
            "message": "All of the above.",
            "project_summary": "\n".join(turn["text"] for turn in conversation if turn["role"] == "user"),
            "service_category": "Shopping, Sourcing & Procurement",
            "conversation": conversation,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ready_to_schedule"] is True
    assert "?" not in body["reply"]
    assert body["captured_address"].lower().startswith("5160 stevenson st")


def test_customer_frustration_forces_handoff_instead_of_confirmation_loop():
    conversation = [
        {"role": "user", "text": "I need inexpensive used beds, tables, chairs, and lamps for three rooms."},
        {"role": "assistant", "text": "Would you prefer used or new items?"},
        {"role": "user", "text": "I said what I said. Stop confirming the same thing and just do it."},
    ]

    response = api_request(
        "POST",
        "/api/intake/chat",
        json={
            "message": conversation[-1]["text"],
            "project_summary": "\n".join(turn["text"] for turn in conversation if turn["role"] == "user"),
            "conversation": conversation,
        },
    )

    body = response.json()
    assert body["ready_to_schedule"] is True
    assert "?" not in body["reply"]
    assert "confirm" not in body["reply"].lower()


def test_two_prior_questions_are_the_discovery_limit():
    conversation = [
        {"role": "user", "text": "I need help furnishing three bedrooms on a very low budget."},
        {"role": "assistant", "text": "Which rooms need furniture?"},
        {"role": "user", "text": "Three bedrooms."},
        {"role": "assistant", "text": "What items matter most?"},
        {"role": "user", "text": "Beds first, then cheap tables, chairs, and lights."},
    ]

    payload = main.IntakeChat(
        message=conversation[-1]["text"],
        project_summary="\n".join(turn["text"] for turn in conversation if turn["role"] == "user"),
        conversation=conversation,
    )

    assert main.intake_should_handoff(payload) is True


def test_first_vague_message_can_still_receive_one_forward_question():
    response = api_request(
        "POST",
        "/api/intake/chat",
        json={
            "message": "I need some help with my house.",
            "project_summary": "I need some help with my house.",
            "conversation": [{"role": "user", "text": "I need some help with my house."}],
        },
    )

    body = response.json()
    assert body["ready_to_schedule"] is False
    assert "repeat" in body["reply"].lower()


def test_intake_ready_project_reports_complete_progress(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    uploads_dir = tmp_path / "data" / "uploads"
    uploads_dir.mkdir(parents=True)
    monkeypatch.setattr(main, "UPLOAD_DIR", uploads_dir)
    record = {
        "id": "project-1",
        "project_code": "LDX-READY1",
        "phone": "4406018001",
        "project_summary": "Furnish three bedrooms affordably",
        "service_category": "Shopping, Sourcing & Procurement",
        "assumptions_confirmed": False,
        "intake_ready": True,
    }
    (uploads_dir.parent / "appointment-requests.jsonl").write_text(
        __import__("json").dumps(record) + "\n", encoding="utf-8"
    )

    response = api_request(
        "GET", "/api/projects/lookup?code=LDX-READY1&phone=4406018001"
    )

    assert response.status_code == 200
    assert response.json()["progress"] == 100
    assert response.json()["scope_confirmed"] is False
