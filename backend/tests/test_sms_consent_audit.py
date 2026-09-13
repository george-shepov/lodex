import asyncio
import json
from pathlib import Path

import httpx
import pytest

import main
import sms_consent_audit


@pytest.fixture
def consent_app(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    data_dir = tmp_path / "data"
    uploads_dir = data_dir / "uploads"
    uploads_dir.mkdir(parents=True)
    monkeypatch.setattr(main, "UPLOAD_DIR", uploads_dir)
    return data_dir


def run(coro):
    return asyncio.run(coro)


def test_affirmative_sms_consent_is_persisted_with_server_timestamp(consent_app):
    async def scenario():
        transport = httpx.ASGITransport(app=main.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.post(
                "/api/sms/consent",
                headers={"Origin": "https://lodex.work"},
                json={
                    "phone": "(216) 247-4724",
                    "consent": True,
                    "source_form": "schedule-card",
                    "source_path": "/",
                    "consent_text": sms_consent_audit.SMS_CONSENT_TEXT,
                    "consent_version": sms_consent_audit.SMS_CONSENT_COPY_VERSION,
                },
            )
            assert response.status_code == 200
            assert response.json()["recorded"] is True

        records = [
            json.loads(line)
            for line in (consent_app / "sms-consent-events.jsonl").read_text(encoding="utf-8").splitlines()
            if line
        ]
        assert len(records) == 1
        record = records[0]
        assert record["phone_normalized"] == "2162474724"
        assert record["consent"] is True
        assert record["source_form"] == "schedule-card"
        assert record["source_path"] == "/"
        assert record["consent_text"] == sms_consent_audit.SMS_CONSENT_TEXT
        assert record["displayed_text_matches_current"] is True
        assert record["privacy_policy_url"] == "https://lodex.work/privacy"
        assert record["terms_and_conditions_url"] == "https://lodex.work/terms"
        assert record["consent_version"] == sms_consent_audit.SMS_CONSENT_COPY_VERSION
        assert record["recorded_at"].endswith("+00:00")
        assert len(record["consent_text_sha256"]) == 64
        assert record["request_origin"] == "https://lodex.work"

    run(scenario())


def test_false_sms_consent_does_not_create_opt_in_record(consent_app):
    async def scenario():
        transport = httpx.ASGITransport(app=main.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.post(
                "/api/sms/consent",
                json={
                    "phone": "2162474724",
                    "consent": False,
                    "source_form": "schedule-card",
                    "source_path": "/",
                    "consent_text": sms_consent_audit.SMS_CONSENT_TEXT,
                },
            )
            assert response.status_code == 200
            assert response.json() == {"ok": True, "recorded": False}

        assert not (consent_app / "sms-consent-events.jsonl").exists()

    run(scenario())
