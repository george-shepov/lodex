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
    metadata = payload["event"]["metadata"]
    assert metadata["project_code"] == "LDX-ABC123"
    assert metadata["sms_template_catalog_version"] == "lodex-a2p-service-2026-09-13-v1"
    assert metadata["suggested_sms_template_id"] == "service_photo_request"
    assert metadata["suggested_sms_draft"] == (
        "LODEX: Hi Sarah, thanks for contacting us about Door installation. "
        "Could you send a few photos of the area so we can better understand the work? "
        "Reply STOP to opt out or HELP for assistance."
    )


def test_existing_uploads_do_not_generate_photo_request_draft() -> None:
    payload = build_tenant_payload(
        "appointments",
        {
            "id": "project-id",
            "project_code": "LDX-ABC123",
            "name": "Sarah Miller",
            "phone": "+1 216 555 0101",
            "project_summary": "Replace the exterior door",
            "service_category": "Door installation",
            "uploads": [{"upload_id": "photo-1", "filename": "door.jpg"}],
        },
    )

    metadata = payload["event"]["metadata"]
    assert metadata["sms_template_catalog_version"] == "lodex-a2p-service-2026-09-13-v1"
    assert "suggested_sms_template_id" not in metadata
    assert "suggested_sms_draft" not in metadata


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
    metadata = payload["event"]["metadata"]
    assert metadata["project_code"] == "LDX-ABC123"
    assert metadata["sms_template_catalog_version"] == "lodex-a2p-service-2026-09-13-v1"
