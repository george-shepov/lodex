"""Durable audit trail for customer SMS/MMS consent.

The browser displays an optional, unchecked consent box next to phone inputs.
When a customer affirmatively checks it, the frontend posts the exact displayed
copy and its source context here. The server supplies the authoritative UTC
timestamp and canonical policy URLs before appending an immutable JSONL event.
"""

from __future__ import annotations

import hashlib
import re
import uuid

from fastapi import Request
from pydantic import BaseModel, Field

import main


SMS_CONSENT_COPY_VERSION = "2026-09-13-v1"
SMS_CONSENT_TEXT = (
    "I agree to receive service-related SMS/MMS messages from LODEX at the mobile number provided. "
    "Message frequency varies. Message and data rates may apply. Reply STOP to opt out or HELP for assistance. "
    "Consent is not a condition of purchase."
)
PRIVACY_POLICY_URL = "https://lodex.work/privacy"
TERMS_AND_CONDITIONS_URL = "https://lodex.work/terms"


class SmsConsentAuditRequest(BaseModel):
    phone: str = Field(min_length=7, max_length=40)
    consent: bool = True
    source_form: str = Field(default="phone_form", max_length=120)
    source_path: str = Field(default="/", max_length=500)
    consent_text: str = Field(min_length=20, max_length=1000)
    consent_version: str = Field(default=SMS_CONSENT_COPY_VERSION, max_length=80)


def _normalized_phone(phone: str) -> str:
    return re.sub(r"\D", "", phone)


def _consent_events_file():
    # Resolve from UPLOAD_DIR at call time so tests and deployments that
    # relocate the data directory automatically keep the audit beside it.
    return main.UPLOAD_DIR.parent / "sms-consent-events.jsonl"


@main.app.post("/api/sms/consent", include_in_schema=False)
async def record_sms_consent(payload: SmsConsentAuditRequest, request: Request):
    """Append an affirmative SMS-consent event without blocking other forms."""
    if not payload.consent:
        return {"ok": True, "recorded": False}

    normalized_phone = _normalized_phone(payload.phone)
    if len(normalized_phone) < 7:
        return {"ok": True, "recorded": False}

    displayed_text = payload.consent_text.strip()
    record = {
        "id": uuid.uuid4().hex,
        "phone": payload.phone.strip(),
        "phone_normalized": normalized_phone,
        "consent": True,
        "source_form": payload.source_form.strip() or "phone_form",
        "source_path": payload.source_path.strip() or "/",
        "consent_text": displayed_text,
        "consent_text_sha256": hashlib.sha256(displayed_text.encode("utf-8")).hexdigest(),
        "consent_version": payload.consent_version.strip() or SMS_CONSENT_COPY_VERSION,
        "displayed_text_matches_current": displayed_text == SMS_CONSENT_TEXT,
        "privacy_policy_url": PRIVACY_POLICY_URL,
        "terms_and_conditions_url": TERMS_AND_CONDITIONS_URL,
        "recorded_at": main.iso_now(),
        "request_origin": (request.headers.get("origin") or "").strip()[:500],
    }
    main.append_jsonl(_consent_events_file(), record)
    return {"ok": True, "recorded": True, "id": record["id"]}
