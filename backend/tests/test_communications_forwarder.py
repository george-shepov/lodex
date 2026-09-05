from communications_forwarder import build_tenant_payload


def test_appointment_maps_to_lodex_sales_conversation() -> None:
    payload = build_tenant_payload(
        "appointments",
        {
            "id": "project-id",
            "project_code": "LDX-ABC123",
            "name": "Sarah Miller",
            "phone": "+1 216 555 0101",
            "email": "sarah@example.com",
            "address": "123 Main St",
            "preferred_date": "2026-09-03",
            "preferred_time": "afternoon",
            "project_summary": "Replace the exterior door\nCustomer has photos.",
            "service_category": "Door installation",
        },
    )

    assert payload["tenant"] == "lodex"
    assert payload["queue"] == "sales"
    assert payload["project_id"] == "LDX-ABC123"
    assert payload["assigned_agent"] == "lodex-sales"
    assert payload["contact"]["emails"] == ["sarah@example.com"]
    assert payload["event"]["intent"] == "appointment_request"
    assert payload["event"]["metadata"]["project_code"] == "LDX-ABC123"


def test_support_maps_to_high_priority_support_conversation() -> None:
    payload = build_tenant_payload(
        "support",
        {
            "id": "support-id",
            "project_code": "LDX-ABC123",
            "room_code": "LDX-ABC123",
            "name": "Sarah Miller",
            "phone": "2165550101",
            "message": "The customer needs help with the existing project.",
        },
    )

    assert payload["tenant"] == "lodex"
    assert payload["queue"] == "support"
    assert payload["project_id"] == "LDX-ABC123"
    assert payload["assigned_agent"] == "lodex-support"
    assert payload["event"]["kind"] == "handoff"
    assert payload["event"]["intent"] == "support_request"
    assert payload["event"]["escalation_score"] == 85
    assert payload["event"]["metadata"]["project_code"] == "LDX-ABC123"
