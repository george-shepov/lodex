import pytest

from communications_templates import (
    SMS_TEMPLATE_CATALOG_VERSION,
    SMS_TEMPLATES,
    campaign_sample_messages,
    render_sms_template,
)


def test_campaign_catalog_preserves_all_five_registered_samples() -> None:
    assert SMS_TEMPLATE_CATALOG_VERSION == "lodex-a2p-service-2026-09-13-v1"
    assert list(SMS_TEMPLATES) == [
        "service_photo_request",
        "estimate_ready",
        "appointment_confirmation",
        "arrival_update",
        "work_complete",
    ]
    samples = campaign_sample_messages()
    assert len(samples) == 5
    assert all(message.startswith("LODEX:") for message in samples)
    assert all("Reply STOP to opt out" in message for message in samples)
    assert "HELP for assistance" in samples[0]
    assert SMS_TEMPLATES["work_complete"].requires_media is True


def test_render_appointment_confirmation_uses_runtime_values() -> None:
    message = render_sms_template(
        "appointment_confirmation",
        {
            "Service": "door installation",
            "Date": "September 18",
            "Time": "2:00 PM",
            "Service Address": "123 Main St",
        },
    )
    assert message == (
        "LODEX: Your door installation appointment is confirmed for September 18 at 2:00 PM at 123 Main St. "
        "Please reply if you need to reschedule. Reply STOP to opt out."
    )
    assert "[" not in message


def test_renderer_rejects_missing_variables() -> None:
    with pytest.raises(ValueError, match="Amount"):
        render_sms_template(
            "estimate_ready",
            {
                "First Name": "Alex",
                "Project Description": "deck repair",
            },
        )
