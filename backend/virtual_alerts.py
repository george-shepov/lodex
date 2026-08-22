"""Operator alerts for customer virtual-room joins.

A customer can enter a virtual room from several places in the UI.  Some of
those paths historically opened the WebSocket directly without first creating
an /api/support/call record, so the owner dashboard had nothing to display.
This ASGI middleware makes the room connection itself authoritative: every
customer room join creates (or reuses) a waiting support request and emits the
same admin event as the explicit support form.
"""

import time
import uuid
from http.cookies import SimpleCookie
from urllib.parse import unquote

import main


RECENT_ALERT_SECONDS = 120


def _admin_session_from_scope(scope) -> str | None:
    headers = dict(scope.get("headers") or [])
    raw_cookie = headers.get(b"cookie", b"").decode("latin-1", errors="ignore")
    if not raw_cookie:
        return None
    cookie = SimpleCookie()
    try:
        cookie.load(raw_cookie)
    except Exception:
        return None
    morsel = cookie.get(main.ADMIN_SESSION_COOKIE)
    return morsel.value if morsel else None


def _recent_request(room_code: str) -> bool:
    now = time.time()
    for record in reversed(main.load_jsonl(main.SUPPORT_REQUESTS_FILE)):
        if str(record.get("room_code", "")).upper() != room_code:
            continue
        created_at = str(record.get("created_at") or "")
        try:
            created = main.datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            age = now - created.timestamp()
            return age <= RECENT_ALERT_SECONDS
        except (TypeError, ValueError):
            return True
    return False


async def _alert_operator(room_code: str) -> None:
    if _recent_request(room_code):
        return
    record = {
        "id": uuid.uuid4().hex,
        "visitor_id": "virtual-room",
        "room_code": room_code,
        "name": "Virtual visitor",
        "phone": "",
        "project_code": room_code if room_code.startswith("LDX-") else "",
        "message": "Customer entered the live video room and is waiting for LODEX.",
        "status": "waiting",
        "created_at": main.iso_now(),
        "source": "virtual_room",
    }
    main.append_jsonl(main.SUPPORT_REQUESTS_FILE, record)
    await main.broadcast_admin_event(
        "support.requested",
        {
            "id": record["id"],
            "room_code": room_code,
            "name": record["name"],
            "phone": "",
            "message": record["message"],
        },
    )


class VirtualRoomAlertMiddleware:
    """Alert the operator when a non-admin WebSocket enters a virtual room."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope.get("type") == "websocket":
            path = str(scope.get("path") or "")
            prefix = "/api/virtual/rooms/"
            if path.startswith(prefix):
                session_id = _admin_session_from_scope(scope)
                is_admin = main.valid_admin_session(session_id)
                if not is_admin:
                    room_code = unquote(path[len(prefix):]).strip().upper()
                    if room_code:
                        await _alert_operator(room_code)
        await self.app(scope, receive, send)
