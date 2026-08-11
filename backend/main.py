import json
import hashlib
import hmac
import os
import re
import shutil
import subprocess
import time
import uuid
import base64
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Any

import httpx
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

BUSINESS_NAME = os.getenv("BUSINESS_NAME", "LODEX Construction Maintenance and Repair")
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "data/uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
MAX_UPLOAD_BYTES = 40 * 1024 * 1024
ALLOWED_TYPES = {
    "image/jpeg", "image/png", "image/webp", "image/heic",
    "video/mp4", "video/quicktime", "video/webm",
}
STRIPE_API_VERSION = "2026-02-25.clover"
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "").strip()
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "").strip()
STRIPE_CURRENCY = os.getenv("STRIPE_CURRENCY", "usd").strip().lower()
try:
    STRIPE_DEPOSIT_AMOUNT_CENTS = int(os.getenv("LODEX_DEPOSIT_AMOUNT_CENTS", "0") or 0)
except ValueError:
    STRIPE_DEPOSIT_AMOUNT_CENTS = 0
PAYMENTS_FILE = UPLOAD_DIR.parent / "payments.jsonl"

app = FastAPI(title="LODEX Intake API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")],
    allow_methods=["*"],
    allow_headers=["*"],
)
virtual_rooms: dict[str, set[WebSocket]] = {}


class IntakeChat(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    project_summary: str = ""
    media_notes: str = ""
    service_category: str = Field(default="", max_length=120)


class AppointmentRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    phone: str = Field(min_length=7, max_length=40)
    email: str | None = Field(default=None, max_length=254)
    address: str = Field(min_length=5, max_length=300)
    preferred_date: str
    preferred_time: str
    project_summary: str = Field(min_length=5, max_length=6000)
    service_category: str = Field(default="General inquiry", max_length=120)
    uploads: list[dict] = Field(default_factory=list)
    assumptions_confirmed: bool


class FeedbackRequest(BaseModel):
    project_code: str = Field(min_length=3, max_length=40)
    phone: str = Field(default="", max_length=40)
    rating: int = Field(ge=1, le=5)
    recommend: bool | None = None
    comments: str = Field(default="", max_length=2000)


class CheckoutRequest(BaseModel):
    project_code: str = Field(min_length=6, max_length=20)
    phone: str = Field(min_length=7, max_length=40)


def client() -> AsyncOpenAI:
    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(503, "AI analysis is not configured yet. You can still submit an appointment request.")
    return AsyncOpenAI()


def sanitize_filename(filename: str | None) -> str:
    name = Path(filename or "upload").name
    return re.sub(r"[^a-zA-Z0-9._-]", "_", name)[:120]


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line:
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            records.append(value)
    return records


def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as output:
        output.write(json.dumps(record) + "\n")


def normalize_phone(value: str) -> str:
    return re.sub(r"\D", "", value)


def find_project(project_code: str, phone: str) -> dict[str, Any] | None:
    requested_code = project_code.strip().upper()
    requested_phone = normalize_phone(phone)
    records = load_jsonl(UPLOAD_DIR.parent / "appointment-requests.jsonl")
    for record in reversed(records):
        if (
            str(record.get("project_code", "")).upper() == requested_code
            and normalize_phone(str(record.get("phone", ""))) == requested_phone
        ):
            return record
    return None


def latest_payment(project_code: str) -> dict[str, Any] | None:
    for record in reversed(load_jsonl(PAYMENTS_FILE)):
        if str(record.get("project_code", "")).upper() == project_code.strip().upper():
            return record
    return None


def stripe_is_configured() -> bool:
    return bool(STRIPE_SECRET_KEY and STRIPE_DEPOSIT_AMOUNT_CENTS > 0)


async def stripe_checkout_session(fields: list[tuple[str, str]], idempotency_key: str) -> dict[str, Any]:
    if not stripe_is_configured():
        raise HTTPException(503, "Stripe deposits are not configured yet.")
    headers = {
        "Authorization": f"Bearer {STRIPE_SECRET_KEY}",
        "Idempotency-Key": idempotency_key,
        "Stripe-Version": STRIPE_API_VERSION,
    }
    try:
        async with httpx.AsyncClient(timeout=25.0) as client:
            response = await client.post(
                "https://api.stripe.com/v1/checkout/sessions",
                data=dict(fields),
                headers=headers,
            )
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError) as error:
        print(f"LODEX Stripe Checkout unavailable: {type(error).__name__}")
        raise HTTPException(502, "Stripe could not create the payment session.") from error
    if not isinstance(payload, dict) or not payload.get("id") or not payload.get("url"):
        raise HTTPException(502, "Stripe returned an invalid payment session.")
    return payload


def verify_stripe_signature(payload: bytes, signature: str) -> bool:
    if not STRIPE_WEBHOOK_SECRET or not signature:
        return False
    values: dict[str, list[str]] = {}
    for item in signature.split(","):
        key, separator, value = item.partition("=")
        if separator:
            values.setdefault(key, []).append(value)
    timestamps = values.get("t", [])
    signatures = values.get("v1", [])
    if not timestamps or not signatures:
        return False
    try:
        timestamp = int(timestamps[0])
    except ValueError:
        return False
    if abs(time.time() - timestamp) > 300:
        return False
    signed_payload = f"{timestamp}.".encode("utf-8") + payload
    expected = hmac.new(
        STRIPE_WEBHOOK_SECRET.encode("utf-8"), signed_payload, hashlib.sha256
    ).hexdigest()
    return any(hmac.compare_digest(expected, candidate) for candidate in signatures)


async def analyze_image(path: Path, media_type: str, description: str, service_category: str = "") -> str:
    """Return observable details and follow-up questions; never a price."""
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    prompt = f"""This is a customer-uploaded image for {BUSINESS_NAME}. The selected service is: {service_category or '(not selected)'}. Customer description: {description or '(none)'}.
Describe only visible, relevant job details. Separate what you can see from what must be confirmed. Ask no more than two questions needed to scope the requested visit. For cleaning or restoration, identify the surface and any visible uncertainty but do not prescribe a method without confirmation. Never state a price, never claim licensing or insurance, and never assume hidden damage or dimensions."""
    result = await client().responses.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
        input=[{"role": "user", "content": [
            {"type": "input_text", "text": prompt},
            {"type": "input_image", "image_url": f"data:{media_type};base64,{encoded}"},
        ]}],
    )
    return result.output_text


def first_video_frame(video_path: Path) -> Path | None:
    frame = video_path.with_name(f"{video_path.stem}-frame.jpg")
    try:
        subprocess.run(["ffmpeg", "-y", "-ss", "00:00:02", "-i", str(video_path), "-frames:v", "1", "-q:v", "3", str(frame)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
        return frame if frame.exists() else None
    except (FileNotFoundError, subprocess.SubprocessError):
        return None


@app.get("/api/health")
async def health():
    return {"ok": True, "ai_configured": bool(os.getenv("OPENAI_API_KEY"))}


@app.websocket("/api/virtual/rooms/{room_id}")
async def virtual_room(websocket: WebSocket, room_id: str):
    await websocket.accept()
    peers = virtual_rooms.setdefault(room_id, set())
    if len(peers) >= 2:
        await websocket.send_json({"type": "room-full"})
        await websocket.close(code=1008)
        return
    peers.add(websocket)
    await websocket.send_json({"type": "joined", "participants": len(peers)})
    for peer in list(peers):
        if peer is not websocket:
            await peer.send_json({"type": "peer-joined"})
    try:
        while True:
            message = await websocket.receive_json()
            for peer in list(peers):
                if peer is not websocket:
                    await peer.send_json(message)
    except WebSocketDisconnect:
        peers.discard(websocket)
        if not peers:
            virtual_rooms.pop(room_id, None)


@app.post("/api/intake/upload")
async def upload_media(
    file: Annotated[UploadFile, File(...)],
    description: Annotated[str, Form()] = "",
    service_category: Annotated[str, Form()] = "",
):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(415, "Please upload a JPG, PNG, WebP, HEIC, MP4, MOV, or WebM file.")
    upload_id = uuid.uuid4().hex
    suffix = Path(sanitize_filename(file.filename)).suffix
    target = UPLOAD_DIR / f"{upload_id}{suffix}"
    size = 0
    with target.open("wb") as output:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > MAX_UPLOAD_BYTES:
                output.close()
                target.unlink(missing_ok=True)
                raise HTTPException(413, "That file is over the 40 MB intake limit.")
            output.write(chunk)

    analysis = "Upload saved. What should we focus on?"
    analyzed_type = file.content_type
    analysis_target = target
    if file.content_type.startswith("video/"):
        frame = first_video_frame(target)
        if frame:
            analysis_target, analyzed_type = frame, "image/jpeg"
        else:
            analysis = "Video received. What should we check?"
    if analyzed_type.startswith("image/") and os.getenv("OPENAI_API_KEY"):
        try:
            analysis = await analyze_image(analysis_target, analyzed_type, description, service_category)
        except Exception:
            analysis = "Upload received. What result do you want?"
    record = {"upload_id": upload_id, "filename": sanitize_filename(file.filename), "media_type": file.content_type, "description": description, "service_category": service_category, "stored_path": str(target), "analysis": analysis}
    with (UPLOAD_DIR.parent / "uploads.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")
    return {
        "upload_id": upload_id,
        "filename": sanitize_filename(file.filename),
        "media_type": file.content_type,
        "description": description,
        "analysis": analysis,
        "message": "Uploaded.",
    }


@app.post("/api/intake/chat")
async def intake_chat(payload: IntakeChat):
    if not os.getenv("OPENAI_API_KEY"):
        return {"reply": "What outcome do you want, and where is the work?"}
    system = f"""You are the intake assistant for {BUSINESS_NAME}, a Northeast Ohio property-project service.
Clarify renovation, repair, maintenance, delivery/installation, sourcing, cleaning, or surface-restoration work before a meet-and-greet.
Default to ONE or TWO short sentences and about 45 words maximum. Never repeat, paraphrase, or recap what the customer just said; the UI already shows the project scope and progress percentage.
Ask exactly ONE next question unless two tightly connected facts are genuinely needed. Never ask more than TWO questions in one reply.
At a useful milestone, give at most one short acknowledgment and immediately ask the next high-value question. Do not turn the conversation into a questionnaire.
Never state or imply a final price. Do not invent details from photos or videos. Clearly label uncertainty when it matters.
Prioritize only the next missing detail among scope, location/area, material/item, dimensions/quantity, access/safety, desired result, timing, or an in-person confirmation.
For cleaning/restoration, ask only the next needed fact about surface, condition, target result, water/power access, or finishes that must be preserved. Do not promise a method before review.
Only when enough information exists for scope confirmation may you use a very compact checklist, no more than 60 words total, then ask the customer to confirm it and proceed to the meet-and-greet."""
    prompt = f"Selected service: {payload.service_category or '(not selected)'}\nProject summary so far: {payload.project_summary or '(none)'}\nMedia notes: {payload.media_notes or '(none)'}\nCustomer says: {payload.message}"
    try:
        response = await client().responses.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
            input=[{"role": "system", "content": system}, {"role": "user", "content": prompt}],
        )
        return {"reply": response.output_text, "degraded": False}
    except Exception as error:
        print(f"LODEX chat AI unavailable: {type(error).__name__}: {error}")
        return {"reply": "What outcome do you want, and where is the work?", "degraded": True}


@app.post("/api/feedback")
async def submit_feedback(feedback: FeedbackRequest):
    record = feedback.model_dump() | {"created_at": datetime.now(timezone.utc).isoformat()}
    with (UPLOAD_DIR.parent / "feedback.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")
    return {"ok": True, "message": "Thank you. Your feedback was saved."}


@app.get("/api/projects/lookup")
async def lookup_project(code: str, phone: str):
    requested_code = code.strip().upper()
    requested_phone = re.sub(r"\D", "", phone)
    request_file = UPLOAD_DIR.parent / "appointment-requests.jsonl"
    if not request_file.exists():
        raise HTTPException(404, "No project request was found yet.")
    records = [json.loads(line) for line in request_file.read_text(encoding="utf-8").splitlines() if line]
    for record in reversed(records):
        stored_phone = re.sub(r"\D", "", str(record.get("phone", "")))
        if record.get("project_code", "").upper() == requested_code and stored_phone == requested_phone:
            summary = (record.get("project_summary") or "").strip()
            title = summary.splitlines()[0][:72] if summary else "Home project"
            past_projects = []
            for previous in reversed(records):
                previous_phone = re.sub(r"\D", "", str(previous.get("phone", "")))
                if previous_phone == requested_phone and previous.get("project_code", "").upper() != requested_code:
                    previous_summary = (previous.get("project_summary") or "").strip()
                    past_projects.append({
                        "project_code": previous.get("project_code"),
                        "title": previous_summary.splitlines()[0][:72] if previous_summary else "Home project",
                        "status": previous.get("status", "requested"),
                    })
            return {
                "project_code": record["project_code"],
                "status": "Meet-and-greet requested",
                "title": title,
                "service_category": record.get("service_category", "General inquiry"),
                "next_step": "LODEX will confirm the requested visit window and review any remaining details with you.",
                "progress": 100 if record.get("assumptions_confirmed") else 72,
                "scope_confirmed": bool(record.get("assumptions_confirmed")),
                "requested_date": record.get("preferred_date"),
                "requested_time": record.get("preferred_time"),
                "payment_status": (latest_payment(record["project_code"]) or {}).get("status", "not_started"),
                "past_projects": past_projects[:8],
            }
    raise HTTPException(404, "We could not match that project code and phone number.")


@app.post("/api/appointments/request")
async def request_appointment(request: AppointmentRequest):
    project_id = uuid.uuid4().hex
    project_code = f"LDX-{project_id[:6].upper()}"
    record = request.model_dump() | {
        "id": project_id,
        "project_code": project_code,
        "status": "requested",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "note": "Requested time is not a final booking until LODEX confirms it.",
    }
    with (UPLOAD_DIR.parent / "appointment-requests.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")
    return {
        "id": record["id"],
        "project_code": record["project_code"],
        "message": "Meet-and-greet requested. We will confirm the time and final scope before any final price is set.",
    }


@app.post("/api/payments/checkout")
async def create_deposit_checkout(request: CheckoutRequest):
    """Create a Stripe-hosted Checkout Session for a configured LODEX deposit.

    The amount is server-configured; it is never accepted from the browser.
    The project code and phone number must match an existing intake request.
    """
    project = find_project(request.project_code, request.phone)
    if project is None:
        raise HTTPException(404, "We could not match that project code and phone number.")
    if not stripe_is_configured():
        raise HTTPException(503, "Stripe deposits are not configured yet.")

    project_code = str(project["project_code"]).upper()
    existing_payment = latest_payment(project_code)
    if existing_payment and existing_payment.get("status") == "paid":
        return {"status": "paid", "project_code": project_code}

    origin = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173").rstrip("/")
    success_url = os.getenv(
        "STRIPE_CHECKOUT_SUCCESS_URL",
        f"{origin}/?payment=success&project_code={project_code}&session_id={{CHECKOUT_SESSION_ID}}",
    )
    cancel_url = os.getenv(
        "STRIPE_CHECKOUT_CANCEL_URL",
        f"{origin}/?payment=cancelled&project_code={project_code}",
    )
    service_category = str(project.get("service_category") or "LODEX project")[:120]
    fields = [
        ("mode", "payment"),
        ("success_url", success_url),
        ("cancel_url", cancel_url),
        ("line_items[0][price_data][currency]", STRIPE_CURRENCY),
        ("line_items[0][price_data][unit_amount]", str(STRIPE_DEPOSIT_AMOUNT_CENTS)),
        ("line_items[0][price_data][product_data][name]", f"LODEX project deposit — {service_category}"),
        ("line_items[0][quantity]", "1"),
        ("metadata[project_code]", project_code),
        ("metadata[project_id]", str(project.get("id", ""))),
    ]
    email = str(project.get("email") or "").strip()
    if email:
        fields.append(("customer_email", email))

    session = await stripe_checkout_session(fields, f"lodex-deposit-{project_code}-{uuid.uuid4().hex}")
    append_jsonl(PAYMENTS_FILE, {
        "project_code": project_code,
        "project_id": project.get("id"),
        "session_id": session["id"],
        "status": "checkout_created",
        "amount_cents": STRIPE_DEPOSIT_AMOUNT_CENTS,
        "currency": STRIPE_CURRENCY,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return {
        "status": "checkout_created",
        "project_code": project_code,
        "checkout_url": session["url"],
        "amount_cents": STRIPE_DEPOSIT_AMOUNT_CENTS,
        "currency": STRIPE_CURRENCY,
    }


@app.post("/api/payments/webhook")
async def stripe_webhook(request: Request):
    """Verify and record Stripe Checkout payment events."""
    payload = await request.body()
    signature = request.headers.get("Stripe-Signature", "")
    if not verify_stripe_signature(payload, signature):
        raise HTTPException(400, "Invalid Stripe webhook signature.")
    try:
        event = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise HTTPException(400, "Invalid Stripe webhook payload.") from error

    event_id = str(event.get("id") or "")
    event_type = str(event.get("type") or "")
    data = event.get("data", {}).get("object", {})
    if not event_id or not isinstance(data, dict):
        return {"received": True, "handled": False}
    if any(record.get("event_id") == event_id for record in load_jsonl(PAYMENTS_FILE)):
        return {"received": True, "handled": True, "duplicate": True}

    if event_type == "checkout.session.completed":
        status = "paid" if data.get("payment_status") == "paid" else "checkout_completed"
    else:
        status = {
            "checkout.session.async_payment_succeeded": "paid",
            "checkout.session.async_payment_failed": "payment_failed",
            "checkout.session.expired": "expired",
        }.get(event_type)
    if status:
        metadata = data.get("metadata") or {}
        append_jsonl(PAYMENTS_FILE, {
            "event_id": event_id,
            "event_type": event_type,
            "project_code": str(metadata.get("project_code") or "").upper(),
            "project_id": metadata.get("project_id"),
            "session_id": data.get("id"),
            "payment_intent_id": data.get("payment_intent"),
            "status": status,
            "amount_total": data.get("amount_total"),
            "currency": data.get("currency"),
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
    return {"received": True, "handled": bool(status)}
