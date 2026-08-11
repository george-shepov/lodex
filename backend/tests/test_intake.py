import asyncio
import json
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


def install_fake_ai(monkeypatch: pytest.MonkeyPatch, decision: dict):
    captured = {}

    class FakeResponse:
        output_text = json.dumps(decision)

    class FakeResponses:
        async def create(self, **kwargs):
            captured.update(kwargs)
            return FakeResponse()

    class FakeClient:
        responses = FakeResponses()

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(main, "client", lambda: FakeClient())
    return captured


def test_qualified_property_lead_moves_to_visit_after_required_facts_are_covered():
    conversation = [
        {"role": "user", "text": "How much to minimally furnish a four bedroom house for Airbnb?"},
        {"role": "assistant", "text": "Do you need sourcing and setup, and where is the house?"},
        {"role": "user", "text": "5160 Stevenson St. I need to spend the minimum possible."},
        {"role": "assistant", "text": "Which parts of the property are in scope?", "kind": "required"},
        {"role": "user", "text": "The entire property needs attention. I need to compare Airbnb, private rent, or selling after a refresh and landscaping."},
        {"role": "user", "text": "ASAP. Use what is already good and keep new spending as low as possible."},
    ]

    response = api_request(
        "POST",
        "/api/intake/chat",
        json={
            "message": conversation[-1]["text"],
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
    assert body["qualification"]["profile"] == "property_strategy"
    assert body["qualification"]["progress"] == 100


def test_frustration_does_not_skip_a_required_fulfillment_fact():
    conversation = [
        {"role": "user", "text": "I need inexpensive used beds, tables, chairs, and lamps for three rooms. Free if decent."},
        {"role": "assistant", "text": "When should it be ready, and should we handle delivery and setup?", "kind": "required"},
        {"role": "user", "text": "I said what I said. Stop confirming the same thing and just do it."},
    ]

    response = api_request(
        "POST",
        "/api/intake/chat",
        json={
            "message": conversation[-1]["text"],
            "project_summary": "\n".join(turn["text"] for turn in conversation if turn["role"] == "user"),
            "service_category": "Shopping, Sourcing & Procurement",
            "conversation": conversation,
        },
    )

    body = response.json()
    assert body["ready_to_schedule"] is False
    assert body["question_kind"] == "required"
    assert "?" in body["reply"]
    assert body["qualification"]["progress"] == 80


def test_required_questions_are_not_cut_off_after_two_turns():
    conversation = [
        {"role": "user", "text": "I need rust cleaned from a metal gate."},
        {"role": "assistant", "text": "How large is the affected area?", "kind": "required"},
        {"role": "user", "text": "The whole gate."},
        {"role": "assistant", "text": "What finish should be preserved?", "kind": "required"},
        {"role": "user", "text": "I do not know yet."},
    ]

    response = api_request(
        "POST",
        "/api/intake/chat",
        json={
            "message": conversation[-1]["text"],
            "project_summary": "\n".join(turn["text"] for turn in conversation if turn["role"] == "user"),
            "service_category": "Cleaning & Surface Restoration",
            "conversation": conversation,
        },
    )

    body = response.json()
    assert body["ready_to_schedule"] is False
    assert body["question_kind"] == "required"
    assert "?" in body["reply"]
    assert body["qualification"]["progress"] < 100


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
    assert body["question_kind"] == "required"
    assert body["qualification"]["progress"] == 50


def test_qualified_lead_can_receive_two_useful_extra_questions(monkeypatch: pytest.MonkeyPatch):
    all_required = ["items_outcome", "quantity_spaces", "spending_rule", "acceptance_flexibility", "fulfillment"]
    captured = install_fake_ai(
        monkeypatch,
        {
            "covered_required": all_required,
            "response_kind": "extra_question",
            "reply": "Are there any colors or finishes you want us to avoid?",
        },
    )
    base = "Furnish three bedrooms with beds, tables, chairs, and lamps. Minimum possible spend, used or free if decent, ASAP, delivered and assembled onsite."
    conversation = [{"role": "user", "text": base}]

    first = api_request(
        "POST",
        "/api/intake/chat",
        json={"message": base, "project_summary": base, "service_category": "Shopping, Sourcing & Procurement", "conversation": conversation},
    ).json()

    assert first["qualification"]["qualified"] is True
    assert first["ready_to_schedule"] is False
    assert first["question_kind"] == "extra"
    assert captured["text"]["format"]["type"] == "json_schema"

    conversation.extend([
        {"role": "assistant", "text": first["reply"], "kind": "extra"},
        {"role": "user", "text": "Avoid bright colors."},
    ])
    second = api_request(
        "POST",
        "/api/intake/chat",
        json={"message": "Avoid bright colors.", "project_summary": f"{base}\nAvoid bright colors.", "service_category": "Shopping, Sourcing & Procurement", "conversation": conversation},
    ).json()
    assert second["ready_to_schedule"] is False
    assert second["question_kind"] == "extra"

    conversation.extend([
        {"role": "assistant", "text": second["reply"], "kind": "extra"},
        {"role": "user", "text": "No particle board if solid wood is free."},
    ])
    third = api_request(
        "POST",
        "/api/intake/chat",
        json={"message": conversation[-1]["text"], "project_summary": base, "service_category": "Shopping, Sourcing & Procurement", "conversation": conversation},
    ).json()
    assert third["ready_to_schedule"] is True
    assert third["question_kind"] == "handoff"
    assert "?" not in third["reply"]


def test_customer_side_question_is_answered_without_consuming_extra_budget(monkeypatch: pytest.MonkeyPatch):
    all_required = ["items_outcome", "quantity_spaces", "spending_rule", "acceptance_flexibility", "fulfillment"]
    install_fake_ai(
        monkeypatch,
        {
            "covered_required": all_required,
            "response_kind": "customer_answer",
            "reply": "Yes. LODEX can use card-based deposits when a deposit is requested for the project.",
        },
    )
    base = "Furnish three bedrooms with beds and lamps. Minimum spend, used is fine, ASAP, delivered and assembled onsite."
    conversation = [
        {"role": "user", "text": base},
        {"role": "assistant", "text": "Any finish preference?", "kind": "extra"},
        {"role": "user", "text": "Neutral."},
        {"role": "assistant", "text": "Anything we should avoid?", "kind": "extra"},
        {"role": "user", "text": "Do you accept credit cards?"},
    ]
    body = api_request(
        "POST",
        "/api/intake/chat",
        json={"message": conversation[-1]["text"], "project_summary": base, "service_category": "Shopping, Sourcing & Procurement", "conversation": conversation},
    ).json()

    assert body["qualification"]["qualified"] is True
    assert body["ready_to_schedule"] is False
    assert body["question_kind"] == "answer"
    assert "card" in body["reply"].lower()


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
