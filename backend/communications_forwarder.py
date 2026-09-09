from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any

import httpx


DATA_DIR = Path(os.getenv("LODEX_DATA_DIR", "/app/data"))
STATE_FILE = Path(
    os.getenv(
        "COMMUNICATIONS_FORWARDER_STATE_FILE",
        str(DATA_DIR / ".communications-forwarder-state.json"),
    )
)
HUB_URL = os.getenv("COMMUNICATIONS_HUB_URL", "http://communications-hub:8080").rstrip("/")
HUB_TOKEN = os.getenv("COMMUNICATIONS_HUB_TOKEN", "").strip()
try:
    POLL_SECONDS = max(1.0, float(os.getenv("COMMUNICATIONS_FORWARDER_POLL_SECONDS", "3") or 3))
except ValueError:
    POLL_SECONDS = 3.0

SOURCES: dict[str, Path] = {
    "appointments": DATA_DIR / "appointment-requests.jsonl",
    "support": DATA_DIR / "support-requests.jsonl",
}


def _string(value: Any) -> str:
    return str(value or "").strip()


def _metadata(values: dict[str, Any]) -> dict[str, str]:
    return {
        key: _string(value)
        for key, value in values.items()
        if value is not None and _string(value)
    }


def build_tenant_payload(source: str, record: dict[str, Any]) -> dict[str, Any]:
    if source == "appointments":
        project_id = _string(record.get("project_code") or record.get("id")) or None
        summary = _string(record.get("project_summary"))
        service = _string(record.get("service_category")) or "New project"
        subject = service if not summary else summary.splitlines()[0][:500]
        return {
            "tenant": "lodex",
            "contact": {
                "display_name": _string(record.get("name")),
                "phone_numbers": [_string(record.get("phone"))] if _string(record.get("phone")) else [],
                "emails": [_string(record.get("email"))] if _string(record.get("email")) else [],
                "external_ids": {},
            },
            "queue": "sales",
            "subject": subject,
            "project_id": project_id,
            "assigned_agent": "lodex-sales",
            "event": {
                "kind": "message",
                "channel": "web",
                "direction": "inbound",
                "text": summary or service,
                "intent": "appointment_request",
                "escalation_score": 55,
                "actions": ["review_project", "confirm_visit"],
                "metadata": _metadata(
                    {
                        "source": "lodex.appointment_request",
                        "source_id": record.get("id"),
                        "project_code": record.get("project_code"),
                        "preferred_date": record.get("preferred_date"),
                        "preferred_time": record.get("preferred_time"),
                        "address": record.get("address"),
                        "service_category": record.get("service_category"),
                    }
                ),
            },
        }

    if source == "support":
        project_code = _string(record.get("project_code"))
        record_id = _string(record.get("id"))
        project_id = project_code or (f"support:{record_id}" if record_id else None)
        message = _string(record.get("message")) or "Customer requested support."
        return {
            "tenant": "lodex",
            "contact": {
                "display_name": _string(record.get("name")),
                "phone_numbers": [_string(record.get("phone"))] if _string(record.get("phone")) else [],
                "emails": [],
                "external_ids": {},
            },
            "queue": "support",
            "subject": f"Support — {project_code}" if project_code else "LODEX support request",
            "project_id": project_id,
            "assigned_agent": "lodex-support",
            "event": {
                "kind": "handoff",
                "channel": "web",
                "direction": "inbound",
                "text": message,
                "intent": "support_request",
                "escalation_score": 85 if project_code else 70,
                "actions": ["review_support_request", "contact_customer"],
                "metadata": _metadata(
                    {
                        "source": "lodex.support_request",
                        "source_id": record.get("id"),
                        "project_code": project_code,
                        "room_code": record.get("room_code"),
                    }
                ),
            },
        }

    raise ValueError(f"Unsupported LODEX outbox source: {source}")


def load_state() -> dict[str, int]:
    if not STATE_FILE.exists():
        return {}
    try:
        payload = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    state: dict[str, int] = {}
    for key, value in payload.items():
        if isinstance(value, int) and value >= 0:
            state[str(key)] = value
    return state


def save_state(state: dict[str, int]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(
        prefix=f".{STATE_FILE.name}.",
        suffix=".tmp",
        dir=STATE_FILE.parent,
        text=True,
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as output:
            json.dump(state, output, sort_keys=True)
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())
        os.replace(temp_name, STATE_FILE)
    finally:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass


def post_payload(client: httpx.Client, payload: dict[str, Any]) -> None:
    response = client.post(
        f"{HUB_URL}/api/tenant/conversations",
        json=payload,
        headers={"X-Communications-Token": HUB_TOKEN},
    )
    response.raise_for_status()


def process_source(
    client: httpx.Client,
    source: str,
    path: Path,
    state: dict[str, int],
) -> int:
    if not path.exists():
        return 0

    offset = state.get(source, 0)
    size = path.stat().st_size
    if offset > size:
        offset = 0
        state[source] = 0
        save_state(state)

    processed = 0
    with path.open("rb") as stream:
        stream.seek(offset)
        while True:
            line_start = stream.tell()
            line = stream.readline()
            if not line:
                break
            next_offset = stream.tell()
            try:
                record = json.loads(line.decode("utf-8"))
                if not isinstance(record, dict):
                    raise ValueError("JSONL record must be an object")
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
                print(
                    f"LODEX communications forwarder skipping malformed {source} record "
                    f"at offset {line_start}: {type(error).__name__}"
                )
                state[source] = next_offset
                save_state(state)
                continue

            payload = build_tenant_payload(source, record)
            post_payload(client, payload)
            state[source] = next_offset
            save_state(state)
            processed += 1
    return processed


def run_once(client: httpx.Client, state: dict[str, int]) -> int:
    processed = 0
    for source, path in SOURCES.items():
        processed += process_source(client, source, path, state)
    return processed


def main() -> None:
    print(f"LODEX communications forwarder hub={HUB_URL}")
    while True:
        if not HUB_TOKEN:
            print("LODEX communications forwarder disabled: COMMUNICATIONS_HUB_TOKEN is not configured.")
            time.sleep(max(POLL_SECONDS, 30.0))
            continue

        state = load_state()
        try:
            with httpx.Client(timeout=5.0) as client:
                processed = run_once(client, state)
            if processed:
                print(f"LODEX communications forwarder delivered {processed} record(s).")
        except httpx.HTTPError as error:
            print(f"LODEX communications forwarder HTTP retry: {type(error).__name__}: {error}")
        except Exception as error:
            print(f"LODEX communications forwarder retry: {type(error).__name__}: {error}")
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
