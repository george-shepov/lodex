import asyncio
import json
import hashlib
import hmac
import os
import re
import secrets
import shutil
import subprocess
import time
import uuid
import base64
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Any, Literal

import httpx
from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

import distance
from pricing import (
    calculate_visit_pricing,
    classify_customer_segment,
    normalize_project_size,
    segment_from_project,
)

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
APPOINTMENTS_FILE = UPLOAD_DIR.parent / "appointment-requests.jsonl"
SUPPORT_REQUESTS_FILE = UPLOAD_DIR.parent / "support-requests.jsonl"
VISITOR_EVENTS_FILE = UPLOAD_DIR.parent / "visitor-events.jsonl"
PROJECT_EVENTS_FILE = UPLOAD_DIR.parent / "project-events.jsonl"
LODEX_ADMIN_TOKEN = os.getenv("LODEX_ADMIN_TOKEN", "").strip()
ADMIN_SESSION_COOKIE = "lodex_admin_session"
ADMIN_SESSION_TTL_SECONDS = 8 * 60 * 60
ACTIVE_VISITOR_SECONDS = 75

app = FastAPI(title="LODEX Intake API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")],
    allow_methods=["*"],
    allow_headers=["*"],
)
virtual_rooms: dict[str, set[WebSocket]] = {}
admin_event_sockets: set[WebSocket] = set()
admin_sessions: dict[str, float] = {}
active_visitors: dict[str, dict[str, Any]] = {}


class ConversationTurn(BaseModel):
    role: Literal["assistant", "user"]
    text: str = Field(min_length=1, max_length=4000)
    kind: Literal["required", "extra", "answer", "handoff"] | None = None


class IntakeChat(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    project_summary: str = ""
    media_notes: str = ""
    service_category: str = Field(default="", max_length=120)
    customer_segment: Literal["home", "business", "enterprise"] | None = None
    customer_type: str | None = Field(default=None, max_length=120)
    project_size_class: Literal["small", "several", "major"] | None = None
    conversation: list[ConversationTurn] = Field(default_factory=list, max_length=24)


class AppointmentRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    phone: str = Field(min_length=7, max_length=40)
    email: str | None = Field(default=None, max_length=254)
    address: str = Field(min_length=5, max_length=300)
    preferred_date: str
    preferred_time: str
    project_summary: str = Field(min_length=5, max_length=6000)
    service_category: str = Field(default="General inquiry", max_length=120)
    customer_segment: Literal["home", "business", "enterprise"] | None = None
    customer_type: str | None = Field(default=None, max_length=120)
    project_size_class: Literal["small", "several", "major"] | None = None
    uploads: list[dict] = Field(default_factory=list)
    conversation: list[ConversationTurn] = Field(default_factory=list, max_length=24)
    assumptions_confirmed: bool
    intake_ready: bool = False


class FeedbackRequest(BaseModel):
    project_code: str = Field(min_length=3, max_length=40)
    phone: str = Field(default="", max_length=40)
    rating: int = Field(ge=1, le=5)
    recommend: bool | None = None
    comments: str = Field(default="", max_length=2000)


class CheckoutRequest(BaseModel):
    project_code: str = Field(min_length=6, max_length=20)
    phone: str = Field(min_length=7, max_length=40)


class AdminLoginRequest(BaseModel):
    token: str = Field(min_length=16, max_length=500)


class PresenceHeartbeat(BaseModel):
    visitor_id: str = Field(pattern=r"^[a-zA-Z0-9_-]{12,100}$")
    path: str = Field(default="/", max_length=500)
    page_title: str = Field(default="", max_length=200)


class SupportCallRequest(BaseModel):
    visitor_id: str = Field(pattern=r"^[a-zA-Z0-9_-]{12,100}$")
    name: str = Field(default="", max_length=120)
    phone: str = Field(default="", max_length=40)
    project_code: str = Field(default="", max_length=40)
    message: str = Field(default="", max_length=1000)


class ProjectStatusUpdate(BaseModel):
    status: Literal["requested", "contacted", "scheduled", "in_progress", "completed", "cancelled"]
    note: str = Field(default="", max_length=1000)


def client() -> AsyncOpenAI:
    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(503, "AI analysis is not configured yet. You can still submit an appointment request.")
    return AsyncOpenAI()


ModelTier = Literal["luna", "terra", "sol"]
MODEL_TIER_RANK: dict[ModelTier, int] = {"luna": 0, "terra": 1, "sol": 2}
MODEL_DEFAULTS: dict[ModelTier, tuple[str, str]] = {
    "luna": ("gpt-5.6-luna", "medium"),
    "terra": ("gpt-5.6-terra", "high"),
    "sol": ("gpt-5.6-sol", "xhigh"),
}
VALID_REASONING_EFFORTS = {"none", "low", "medium", "high", "xhigh", "max"}
SOL_SCOPE_CUES = (
    "load-bearing", "load bearing", "structural crack", "foundation failure",
    "electrical panel", "breaker panel", "exposed wiring", "gas line", "gas leak",
    "asbestos", "lead paint", "unstable structure", "collapse", "fire-damaged structure",
)


def model_route(tier: ModelTier) -> dict[str, str]:
    default_model, default_effort = MODEL_DEFAULTS[tier]
    model = os.getenv(f"OPENAI_MODEL_{tier.upper()}", default_model).strip() or default_model
    effort = os.getenv(f"OPENAI_REASONING_{tier.upper()}", default_effort).strip().lower()
    if effort not in VALID_REASONING_EFFORTS:
        effort = default_effort
    return {"tier": tier, "model": model, "reasoning_effort": effort}


def choose_model_tier(text: str, *, profile_key: str = "", task: str = "qualification") -> ModelTier:
    normalized = text.lower()
    if any(cue in normalized for cue in SOL_SCOPE_CUES):
        return "sol"
    service_domains = sum(
        bool(re.search(pattern, normalized))
        for pattern in (
            r"\b(?:furnish(?:e[ds]?|ing(?:s)?)?|sourc(?:e[ds]?|ing)?|shopping)\b",
            r"\b(?:landscap(?:e[ds]?|ing)?|yards?)\b",
            r"\b(?:renovat(?:e[ds]?|ing|ions?)|remodel(?:s|ed|ing)?|repair(?:s|ed|ing)?)\b",
            r"\b(?:clean(?:s|ed|ing)?|restor(?:e[ds]?|ing|ations?)|pressure wash(?:es|ed|ing)?)\b",
            r"\b(?:deliver(?:s|ed|ing|y|ies)?|assembl(?:e[ds]?|ing|y|ies)|install(?:s|ed|ing|ations?)?)\b",
        )
    )
    if (
        profile_key == "property_strategy"
        or len(normalized) > 2500
        or service_domains >= 3
        or (task == "vision" and any(term in normalized for term in ("restoration", "fire damage", "structural")))
    ):
        return "terra"
    return "luna"


def public_route(route: dict[str, str]) -> dict[str, str]:
    return {
        "tier": route["tier"],
        "model": route["model"],
        "reasoning_effort": route["reasoning_effort"],
    }


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


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_now() -> str:
    return utc_now().isoformat()


def purge_admin_sessions() -> None:
    now = time.time()
    for session_id, expires_at in list(admin_sessions.items()):
        if expires_at <= now:
            admin_sessions.pop(session_id, None)


def create_admin_session() -> str:
    purge_admin_sessions()
    session_id = secrets.token_urlsafe(32)
    admin_sessions[session_id] = time.time() + ADMIN_SESSION_TTL_SECONDS
    return session_id


def valid_admin_session(session_id: str | None) -> bool:
    purge_admin_sessions()
    if not session_id:
        return False
    expires_at = admin_sessions.get(session_id, 0)
    if expires_at <= time.time():
        admin_sessions.pop(session_id, None)
        return False
    admin_sessions[session_id] = time.time() + ADMIN_SESSION_TTL_SECONDS
    return True


def require_admin(request: Request) -> None:
    if not LODEX_ADMIN_TOKEN:
        raise HTTPException(503, "LODEX administrator access is not configured.")
    if not valid_admin_session(request.cookies.get(ADMIN_SESSION_COOKIE)):
        raise HTTPException(401, "Administrator authentication is required.")


def admin_cookie_options() -> dict[str, Any]:
    origin = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173").lower()
    return {
        "key": ADMIN_SESSION_COOKIE,
        "max_age": ADMIN_SESSION_TTL_SECONDS,
        "httponly": True,
        "secure": origin.startswith("https://"),
        "samesite": "lax",
        "path": "/",
    }


def verify_admin_token(token: str) -> None:
    if not LODEX_ADMIN_TOKEN:
        raise HTTPException(503, "LODEX administrator access is not configured.")
    if not secrets.compare_digest(token, LODEX_ADMIN_TOKEN):
        raise HTTPException(401, "The administrator token is not valid.")


def project_event_statuses() -> dict[str, dict[str, Any]]:
    statuses: dict[str, dict[str, Any]] = {}
    for event in load_jsonl(PROJECT_EVENTS_FILE):
        code = str(event.get("project_code", "")).upper()
        if code:
            statuses[code] = event
    return statuses


def recent_active_visitors() -> list[dict[str, Any]]:
    cutoff = time.time() - ACTIVE_VISITOR_SECONDS
    for visitor_id, visitor in list(active_visitors.items()):
        if float(visitor.get("last_seen_epoch", 0)) < cutoff:
            active_visitors.pop(visitor_id, None)
    return sorted(active_visitors.values(), key=lambda item: item["last_seen_epoch"], reverse=True)


async def broadcast_admin_event(event_type: str, payload: dict[str, Any]) -> None:
    message = {"type": event_type, "at": iso_now(), "payload": payload}
    for socket in list(admin_event_sockets):
        try:
            await socket.send_json(message)
        except Exception:
            admin_event_sockets.discard(socket)


def public_project_record(record: dict[str, Any]) -> dict[str, Any]:
    code = str(record.get("project_code", "")).upper()
    status_event = project_event_statuses().get(code, {})
    return {
        "id": record.get("id"),
        "project_code": code,
        "name": record.get("name", ""),
        "phone": record.get("phone", ""),
        "email": record.get("email", ""),
        "address": record.get("address", ""),
        "preferred_date": record.get("preferred_date", ""),
        "preferred_time": record.get("preferred_time", ""),
        "project_summary": record.get("project_summary", ""),
        "service_category": record.get("service_category", "General inquiry"),
        "customer_segment": record.get("customer_segment"),
        "customer_type": record.get("customer_type"),
        "project_size_class": record.get("project_size_class"),
        "distance_miles": record.get("distance_miles"),
        "visit_fee_cents": record.get("visit_fee_cents"),
        "visit_fee_label": record.get("visit_fee_label"),
        "pricing_rule": record.get("pricing_rule"),
        "uploads": record.get("uploads", []),
        "conversation": record.get("conversation", []),
        "assumptions_confirmed": bool(record.get("assumptions_confirmed")),
        "intake_ready": bool(record.get("intake_ready")),
        "created_at": record.get("created_at"),
        "status": status_event.get("status", record.get("status", "requested")),
        "status_note": status_event.get("note", ""),
        "payment_status": (latest_payment(code) or {}).get("status", "not_started"),
    }


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


def checkout_pricing_for_project(project: dict[str, Any]) -> dict[str, Any]:
    """Resolve checkout only from server-persisted or configured project data."""
    segment = segment_from_project(project)
    approved_fee = project.get("admin_approved_visit_fee_cents")
    if segment == "enterprise":
        return calculate_visit_pricing(
            segment,
            str(project.get("customer_type") or ""),
            str(project.get("project_size_class") or ""),
            project.get("distance_miles"),
            approved_amount_cents=approved_fee if isinstance(approved_fee, int) else None,
        )

    stored_fee = project.get("visit_fee_cents")
    if isinstance(stored_fee, int) and stored_fee > 0:
        return {
            "fee_cents": stored_fee,
            "label": str(project.get("visit_fee_label") or "Project Assessment"),
            "distance_miles": project.get("distance_miles"),
            "pricing_rule": str(project.get("pricing_rule") or "persisted_project_pricing"),
            "requires_manual_review": False,
        }

    if isinstance(approved_fee, int) and approved_fee > 0:
        return calculate_visit_pricing(
            segment,
            str(project.get("customer_type") or ""),
            str(project.get("project_size_class") or ""),
            project.get("distance_miles"),
            approved_amount_cents=approved_fee,
        )

    has_new_pricing_fields = any(
        key in project
        for key in ("customer_segment", "customer_type", "project_size_class", "pricing_rule")
    )
    if has_new_pricing_fields:
        return calculate_visit_pricing(
            segment,
            str(project.get("customer_type") or ""),
            str(project.get("project_size_class") or ""),
            project.get("distance_miles"),
        )

    # Existing records predate segment and route pricing. Preserve their former
    # server-configured checkout without pretending a distance was calculated.
    legacy_fee = STRIPE_DEPOSIT_AMOUNT_CENTS if STRIPE_DEPOSIT_AMOUNT_CENTS > 0 else None
    return {
        "fee_cents": legacy_fee,
        "label": "Project Deposit",
        "distance_miles": None,
        "pricing_rule": "legacy_server_configured_deposit",
        "requires_manual_review": legacy_fee is None,
    }


def stripe_is_configured() -> bool:
    return bool(STRIPE_SECRET_KEY)


STREET_ADDRESS_PATTERN = re.compile(
    r"\b\d{1,6}\s+[a-z0-9.'-]+(?:\s+[a-z0-9.'-]+){0,5}\s+"
    r"(?:street|st|avenue|ave|road|rd|drive|dr|lane|ln|boulevard|blvd|court|ct|"
    r"circle|cir|parkway|pkwy|place|pl|way)\b",
    re.IGNORECASE,
)

FRUSTRATION_CUES = (
    "stop confirming",
    "stop asking",
    "already told",
    "i said what i said",
    "patience is running low",
    "not reading another",
    "why are you keep",
    "why do you keep",
    "same question",
    "asking me the same",
    "asked me already",
    "how many times",
    "just do it",
    "go already",
    "wrap it up",
)

ACTION_CUES = (
    "let's get rolling",
    "lets get rolling",
    "get started",
    "start now",
    "start asap",
    "move forward",
    "go ahead",
    "proceed",
    "you get it all",
    "whatever you can find",
)

QUALIFICATION_PROFILES: dict[str, dict[str, Any]] = {
    "property_strategy": {
        "label": "Property decision & refresh",
        "requirements": {
            "decision_goal": {
                "label": "Decision being compared",
                "description": "The customer has identified the paths being compared, such as sell, private rental, or short-term rental.",
                "question": "Which outcomes are you comparing for the property—selling, private rental, short-term rental, or another option?",
                "patterns": (r"\bairbnb\b", r"\bshort.?term rental\b", r"\bprivate(?:ly)? rent", r"\bsell(?:ing)?\b"),
            },
            "property_scope": {
                "label": "Property areas in scope",
                "description": "The rooms, exterior areas, or whole-property scope are known.",
                "question": "Which parts of the property should be included in the comparison and refresh plan?",
                "patterns": (r"\bwhole (?:house|property)\b", r"\bentire (?:house|property)\b", r"\bbedrooms?\b", r"\blandscap", r"\bkitchen\b", r"\bbath"),
            },
            "current_state": {
                "label": "Current condition and usable assets",
                "description": "What already exists and the property's current condition are sufficiently described for a first visit.",
                "question": "What is already usable, and what condition is the property in now?",
                "patterns": (r"\bneeds? (?:attention|work|refresh|repair)", r"\bexisting\b", r"\bi have\b", r"\balready have\b", r"\bunfurnished\b", r"\bempty\b"),
            },
            "primary_priority": {
                "label": "Financial or practical priority",
                "description": "The main decision rule is known, such as minimum spend, fastest readiness, durability, or maximum sale value.",
                "question": "What should drive the plan most—minimum spend, fastest readiness, durability, or highest resale value?",
                "patterns": (r"\bmin(?:imum)? (?:spend|possible|cost)", r"\bcheap", r"\blow(?:est)? (?:price|cost|budget)", r"\bmax(?:imum)? (?:value|return)", r"\basap\b", r"\bdurab"),
            },
            "timing": {
                "label": "Target timing",
                "description": "The desired start, deadline, or urgency is known.",
                "question": "When do you want the property ready or the work started?",
                "patterns": (r"\basap\b", r"\bimmediately\b", r"\bthis (?:week|month)\b", r"\bby\s+[a-z0-9]", r"\bno rush\b", r"\bflexible timing\b"),
            },
        },
        "extras": ("occupancy during work", "photos or measurements", "must-keep items"),
    },
    "renovation": {
        "label": "Renovation or larger improvement",
        "requirements": {
            "desired_outcome": {"label": "Desired outcome", "description": "What the customer wants changed or improved is clear.", "question": "What should be different when this project is finished?", "patterns": (r"\bremodel", r"\brenovat", r"\brefresh", r"\bupdate", r"\breplace", r"\bbuild")},
            "areas": {"label": "Rooms or areas", "description": "The rooms or physical areas in scope are known.", "question": "Which rooms or areas are included?", "patterns": (r"\bkitchen\b", r"\bbath", r"\bbedroom", r"\bbasement\b", r"\bwhole (?:house|property)\b", r"\bexterior\b", r"\boffice\b")},
            "current_condition": {"label": "Current condition", "description": "The existing condition, damage, or starting point is described enough for a visit.", "question": "What is there now, and what condition is it in?", "patterns": (r"\bcurrently\b", r"\bexisting\b", r"\bdamag", r"\bold\b", r"\bunfinished\b", r"\bneeds? (?:work|attention|repair)")},
            "priority_constraint": {"label": "Main priority or constraint", "description": "The primary budget, quality, preservation, occupancy, or schedule constraint is known.", "question": "What matters most here—budget, speed, durability, matching existing finishes, or something else?", "patterns": (r"\bbudget\b", r"\bcheap", r"\basap\b", r"\bdurab", r"\bmatch", r"\bpreserv", r"\bminimum spend")},
            "timing": {"label": "Target timing", "description": "The desired start or deadline is known.", "question": "When would you like the work started or completed?", "patterns": (r"\basap\b", r"\bimmediately\b", r"\bthis (?:week|month)\b", r"\bby\s+[a-z0-9]", r"\bno rush\b", r"\bflexible timing\b")},
        },
        "extras": ("occupancy and access", "known measurements", "materials already selected"),
    },
    "maintenance": {
        "label": "Repair or property maintenance",
        "requirements": {
            "issue": {"label": "Problem or task", "description": "The repair, maintenance task, or punch-list outcome is identified.", "question": "What is not working or what needs to be repaired?", "patterns": (r"\brepair", r"\bfix", r"\bbroken\b", r"\bleak", r"\binstall", r"\breplace", r"\bmaintenance\b")},
            "location_quantity": {"label": "Location and quantity", "description": "Where the issue is and how many items or areas are involved are known or reasonably bounded.", "question": "Where is the issue, and is it one item or several?", "patterns": (r"\b(?:one|two|three|four|\d+)\b", r"\bkitchen\b", r"\bbath", r"\bbedroom", r"\bgarage\b", r"\boutside\b", r"\bwhole (?:house|property)\b")},
            "desired_result": {"label": "Desired result", "description": "The customer has described what a successful fix looks like.", "question": "What result do you want when the repair is complete?", "patterns": (r"\bso (?:it|they)\b", r"\bwant\b", r"\bneed (?:it|them|this) to\b", r"\bworking\b", r"\bfinished\b")},
            "access_safety": {"label": "Access or safety constraints", "description": "Known access, height, utility, hazard, tenant, or scheduling constraints are stated, delegated for onsite review, or explicitly unknown.", "question": "Are there any access, height, utility, tenant, or safety constraints we should plan around?", "patterns": (r"\baccess\b", r"\bladder\b", r"\bheight\b", r"\bpower\b", r"\bwater\b", r"\btenant\b", r"\bnot sure\b", r"\bcheck (?:it )?onsite\b")},
        },
        "extras": ("photos", "model or material details", "preferred timing"),
    },
    "delivery_installation": {
        "label": "Delivery and installation",
        "requirements": {
            "items": {"label": "Items involved", "description": "The item type, quantity, or order is identified.", "question": "What items need to be picked up, delivered, assembled, or installed?", "patterns": (r"\bfurniture\b", r"\bbed", r"\bappliance", r"\btv\b", r"\bequipment\b", r"\bdesk\b", r"\bcabinet")},
            "origin_destination": {"label": "Pickup and destination", "description": "The pickup source and destination or a delegated sourcing plan are known enough to coordinate.", "question": "Where are the items coming from, and where do they need to go?", "patterns": (r"\bpick.?up\b", r"\bstore\b", r"\bmarketplace\b", r"\bfacebook\b", r"\bdeliver", r"\bonsite\b", r"\bat the house\b")},
            "setup_scope": {"label": "Assembly or installation scope", "description": "The expected assembly, installation, placement, testing, or debris removal is known.", "question": "Should we assemble, install, place, test, or remove packaging after delivery?", "patterns": (r"\bassembl", r"\binstall", r"\bplace", r"\btest", r"\bpackag", r"\bdebris")},
            "access": {"label": "Delivery access", "description": "Stairs, elevators, doorways, parking, floor, or other delivery access is described or delegated for onsite review.", "question": "What should we know about stairs, doors, parking, elevators, or other delivery access?", "patterns": (r"\bstairs?\b", r"\belevator\b", r"\bdoor", r"\bparking\b", r"\b(?:first|1st|ground) floor\b", r"\bnot sure\b", r"\bcheck (?:it )?onsite\b")},
            "timing": {"label": "Delivery timing", "description": "The requested timing or flexibility is known.", "question": "When do the items need to be delivered and ready?", "patterns": (r"\basap\b", r"\bimmediately\b", r"\bthis (?:week|month)\b", r"\bby\s+[a-z0-9]", r"\bno rush\b", r"\bflexible timing\b")},
        },
        "extras": ("largest-item measurements", "fragile or high-value handling", "packaging disposal"),
    },
    "sourcing": {
        "label": "Shopping, sourcing, and setup",
        "requirements": {
            "items_outcome": {"label": "Items or outcome needed", "description": "The products, furnishings, materials, or end result to source are identified.", "question": "What should we find or furnish first?", "patterns": (r"\bfurnish", r"\bfurniture\b", r"\bbed", r"\bchair", r"\btable", r"\blamp", r"\bmaterials?\b", r"\bfixture")},
            "quantity_spaces": {"label": "Quantity or spaces", "description": "The number of items, rooms, or areas to cover is known or flexible by instruction.", "question": "How many rooms, areas, or items should the sourcing plan cover?", "patterns": (r"\b(?:one|two|three|four|five|six|\d+)\b", r"\bwhole (?:house|property)\b", r"\bentire (?:house|property)\b")},
            "spending_rule": {"label": "Spending rule", "description": "A budget, maximum, minimum-spend direction, or value rule is known.", "question": "What spending rule should guide us—a firm cap, minimum possible, or best long-term value?", "patterns": (r"\bbudget\b", r"\bcheap", r"\binexpensive\b", r"\bfree\b", r"\blow(?:est)? (?:price|cost)", r"\bminimum (?:spend|possible)", r"\bwon't break the bank")},
            "acceptance_flexibility": {"label": "Quality and flexibility", "description": "New versus used, appearance, quality floor, substitutions, or delegated choice is known.", "question": "What is acceptable on condition and style—new, used, free if decent, matching, or simply best available?", "patterns": (r"\bused\b", r"\bnew\b", r"\bfree\b", r"\bdecent\b", r"\bgood quality\b", r"\bwhatever\b", r"\bdo not limit\b", r"\buse your judgment\b")},
            "fulfillment": {"label": "Timing, delivery, and setup", "description": "Urgency plus delivery, assembly, or installation expectations are known.", "question": "When should this be ready, and should LODEX handle delivery and setup?", "patterns": (r"\basap\b", r"\bimmediately\b", r"\bassembl", r"\bdeliver", r"\binstall", r"\bonsite\b", r"\bready\b")},
        },
        "extras": ("measurements", "must-match colors or finishes", "items to avoid"),
    },
    "cleaning_restoration": {
        "label": "Cleaning and surface restoration",
        "requirements": {
            "surface_item": {"label": "Surface or item", "description": "The material, object, or area to clean or restore is identified.", "question": "What surface or item needs cleaning or restoration?", "patterns": (r"\bmetal\b", r"\bconcrete\b", r"\bstone\b", r"\bbrick\b", r"\bsiding\b", r"\bdeck\b", r"\bdriveway\b", r"\bhouse exterior\b")},
            "condition": {"label": "Contamination or condition", "description": "The dirt, coating, corrosion, residue, staining, or damage is described.", "question": "What needs to come off or be improved—dirt, paint, rust, residue, staining, or something else?", "patterns": (r"\bdirt", r"\bpaint\b", r"\brust\b", r"\bresidue\b", r"\bstain", r"\bmold\b", r"\bmildew\b", r"\bfire damage\b")},
            "area_quantity": {"label": "Area or quantity", "description": "The approximate size, count, or bounded area is known, shown in media, or delegated to onsite measurement.", "question": "Roughly how large is the area, or how many items are involved?", "patterns": (r"\b(?:one|two|three|four|\d+)\b", r"\bsq(?:uare)?\.?\s*f", r"\bwhole\b", r"\bentire\b", r"\bphoto", r"\bvideo", r"\bmeasure onsite\b")},
            "desired_finish": {"label": "Desired finish", "description": "The target result and anything that must be preserved are known.", "question": "What should the finished surface look like, and is there any finish or detail we must preserve?", "patterns": (r"\bremove\b", r"\bclean\b", r"\brestore\b", r"\bpreserv", r"\bwithout (?:damage|removing)", r"\blike new\b")},
            "site_constraints": {"label": "Site constraints", "description": "Known water, power, drainage, access, occupied-area, or safety constraints are stated, unknown, or delegated for onsite review.", "question": "Are water, power, drainage, access, or occupied-area constraints known, or should we verify them onsite?", "patterns": (r"\bwater\b", r"\bpower\b", r"\bdrain", r"\baccess\b", r"\boccupied\b", r"\bnot sure\b", r"\bverify (?:it )?onsite\b", r"\bcheck (?:it )?onsite\b")},
        },
        "extras": ("photos or video", "prior cleaning attempts", "preferred timing"),
    },
    "business": {
        "label": "LODEX Business project",
        "requirements": {
            "site_and_scope": {
                "label": "Property or business scope",
                "description": "The property/business type and requested outcome are known, including turnover, make-ready, furnishing, renovation, repairs, or maintenance where relevant.",
                "question": "What type of property or business is this, and what outcome do you need?",
                "patterns": (r"\brental\b", r"\bairbnb\b", r"\bvrbo\b", r"\bstore\b", r"\bshop\b", r"\brestaurant\b", r"\boffice\b", r"\bturnover\b", r"\bmake.?ready\b", r"\brenovat", r"\brepair", r"\bmaintenan"),
            },
            "operations_access": {
                "label": "Operations, access, and scheduling",
                "description": "Tenant/customer continuity plus access and scheduling constraints are stated, unknown, or delegated for coordination.",
                "question": "Will tenants or customers be onsite, and are there access or scheduling restrictions we should plan around?",
                "patterns": (r"\btenant", r"\bcustomer", r"\boccupied\b", r"\bvacant\b", r"\baccess\b", r"\bhours\b", r"\bafter.?hours\b", r"\bkey", r"\blockbox\b", r"\bnot sure\b", r"\bcoordinate\b"),
            },
            "work_pattern": {
                "label": "Location count and work pattern",
                "description": "Whether this is one location or recurring work and the desired timing are known.",
                "question": "Is this one location or recurring work, and when do you need it ready?",
                "patterns": (r"\bone location\b", r"\bsingle (?:site|property|location)\b", r"\brecurring\b", r"\bongoing\b", r"\bportfolio\b", r"\basap\b", r"\bby\s+[a-z0-9]", r"\bthis (?:week|month)\b", r"\bflexible\b"),
            },
            "sourcing_relationship": {
                "label": "Sourcing and relationship",
                "description": "Purchasing/sourcing responsibility and one-time versus ongoing maintenance preference are known or flexible.",
                "question": "Should LODEX purchase or source anything, and is this a one-time project or an ongoing maintenance relationship?",
                "patterns": (r"\bsourc", r"\bpurchas", r"\bprocure", r"\bmaterial", r"\bappliance", r"\bfurnish", r"\bone.?time\b", r"\bongoing\b", r"\brecurring\b", r"\bmaintenance\b", r"\buse your judgment\b"),
            },
        },
        "extras": ("tenant repair coordination", "inspection or turnover deadline"),
    },
    "enterprise": {
        "label": "LODEX Enterprise scope",
        "requirements": {
            "portfolio_coverage": {
                "label": "Locations, units, and coverage",
                "description": "The approximate number of locations or units and geographic coverage are known.",
                "question": "Approximately how many locations or units are involved, and what geographic area should the work cover?",
                "patterns": (r"\b\d+\s+(?:units?|locations?|sites?|properties?)\b", r"\bportfolio\b", r"\bmultiple locations\b", r"\bstatewide\b", r"\bcounty\b", r"\bregional\b", r"\bcleveland\b", r"\bohio\b"),
            },
            "rollout_work": {
                "label": "Rollout or maintenance need",
                "description": "The desired rollout timing and whether this is recurring maintenance or a defined project rollout are known.",
                "question": "What needs to roll out, on what timing, and is this a project program or recurring maintenance?",
                "patterns": (r"\brollout\b", r"\bprogram\b", r"\brecurring\b", r"\bmaintenance\b", r"\brenovat", r"\bfurnish", r"\bturnover\b", r"\bby\s+[a-z0-9]", r"\bquarter\b", r"\bphase"),
            },
            "contacts_approval": {
                "label": "Contacts and approvals",
                "description": "The facilities/property contact and approval or procurement process are described or delegated for follow-up.",
                "question": "Who coordinates facilities or property access, and what approval or procurement process should we follow?",
                "patterns": (r"\bfacilit", r"\bproperty contact\b", r"\bmanager\b", r"\bprocure", r"\bapprov", r"\bdecision maker\b", r"\bcoordinator\b", r"\bfollow.?up\b"),
            },
            "standards_vendor": {
                "label": "Standards and vendor requirements",
                "description": "Standardized finish/material needs plus COI, vendor onboarding, and PO requirements are known or explicitly not required.",
                "question": "Are standardized finishes or materials required, and do you have COI, vendor-onboarding, or PO requirements?",
                "patterns": (r"\bstandard", r"\bfinish", r"\bmaterial", r"\bcoi\b", r"\bcertificate of insurance\b", r"\bvendor", r"\bpurchase order\b", r"\bpo\b", r"\bnot required\b", r"\bnone\b"),
            },
        },
        "extras": ("site prioritization", "reporting and photo-documentation format"),
    },
    "general": {
        "label": "General property project",
        "requirements": {
            "desired_outcome": {"label": "Desired outcome", "description": "What the customer wants LODEX to accomplish is clear.", "question": "What would you like LODEX to accomplish?", "patterns": (r"\bneed\b", r"\bwant\b", r"\bhelp (?:with|me)", r"\bfix\b", r"\bbuild\b", r"\bclean\b", r"\bfurnish\b")},
            "scope": {"label": "Items or areas in scope", "description": "The affected items, rooms, areas, or quantity are reasonably bounded.", "question": "Which items, rooms, or areas are involved?", "patterns": (r"\b(?:one|two|three|four|\d+)\b", r"\broom", r"\bhouse\b", r"\bproperty\b", r"\bitem", r"\bexterior\b")},
            "priority": {"label": "Main priority", "description": "The leading budget, speed, quality, or preservation priority is known.", "question": "What matters most—cost, speed, durability, appearance, or something else?", "patterns": (r"\b(?:cost|budget)\b", r"\bcheap", r"\b(?:speed|asap)\b", r"\bquick", r"\bdurab", r"\bappearance\b", r"\bpreserv")},
            "timing": {"label": "Target timing", "description": "The desired start, deadline, or flexibility is known.", "question": "When would you like to start?", "patterns": (r"\basap\b", r"\bimmediately\b", r"\bthis (?:week|month)\b", r"\bby\s+[a-z0-9]", r"\bno rush\b", r"\bflexible timing\b")},
        },
        "extras": ("photos or measurements", "site access", "materials or products already chosen"),
    },
}


def conversation_text(payload: IntakeChat, role: str | None = None) -> str:
    turns = [turn.text for turn in payload.conversation if role is None or turn.role == role]
    if not turns and role in (None, "user"):
        turns = [line for line in payload.project_summary.splitlines() if line.strip()]
    return "\n".join(turns)


def captured_address(payload: IntakeChat) -> str:
    match = STREET_ADDRESS_PATTERN.search(conversation_text(payload, "user"))
    return match.group(0).strip(" ,.") if match else ""


def qualification_profile(payload: IntakeChat) -> tuple[str, dict[str, Any]]:
    if payload.customer_segment or payload.customer_type:
        classification_text = f"{payload.customer_type or ''}\n{conversation_text(payload, 'user')}"
        segment = classify_customer_segment(classification_text, payload.customer_segment)
        if segment in {"business", "enterprise"}:
            return segment, QUALIFICATION_PROFILES[segment]
    user_text = conversation_text(payload, "user").lower()
    decision_terms = sum(
        bool(re.search(pattern, user_text))
        for pattern in (r"\bairbnb\b", r"\bshort.?term rental\b", r"\bprivate(?:ly)? rent", r"\bsell(?:ing)?\b")
    )
    if decision_terms >= 2:
        return "property_strategy", QUALIFICATION_PROFILES["property_strategy"]
    category = payload.service_category.lower()
    if "renovation" in category or "contracting" in category:
        key = "renovation"
    elif "maintenance" in category or "handyman" in category:
        key = "maintenance"
    elif "delivery" in category or "installation" in category:
        key = "delivery_installation"
    elif "sourcing" in category or "shopping" in category or "procurement" in category:
        key = "sourcing"
    elif "cleaning" in category or "restoration" in category:
        key = "cleaning_restoration"
    else:
        key = "general"
    return key, QUALIFICATION_PROFILES[key]


def fallback_requirement_coverage(payload: IntakeChat, profile: dict[str, Any]) -> set[str]:
    haystack = f"{conversation_text(payload, 'user')}\n{payload.media_notes}".lower()
    covered: set[str] = set()
    for requirement_id, requirement in profile["requirements"].items():
        if any(re.search(pattern, haystack, re.IGNORECASE) for pattern in requirement["patterns"]):
            covered.add(requirement_id)
    covered.update(contextual_constraint_coverage(payload, profile))
    return covered


def contextual_constraint_coverage(payload: IntakeChat, profile: dict[str, Any]) -> set[str]:
    """Treat a direct "none" answer as meaningful only for constraint questions."""
    constraint_requirements = {"access", "access_safety", "site_constraints"}
    questions = {
        re.sub(r"\W+", " ", requirement["question"].lower()).strip(): requirement_id
        for requirement_id, requirement in profile["requirements"].items()
        if requirement_id in constraint_requirements
    }
    covered: set[str] = set()
    for previous, current in zip(payload.conversation, payload.conversation[1:]):
        if previous.role != "assistant" or previous.kind != "required" or current.role != "user":
            continue
        normalized_question = re.sub(r"\W+", " ", previous.text.lower()).strip()
        requirement_id = questions.get(normalized_question)
        if requirement_id and re.match(
            r"^\s*(?:no(?:ne|pe)?|nothing|n\s*/?\s*a|not applicable)\b",
            current.text,
            re.IGNORECASE,
        ):
            covered.add(requirement_id)
    return covered


def customer_asked_question(message: str) -> bool:
    text = message.strip().lower()
    return "?" in text or bool(
        re.match(r"^(?:how|what|why|when|where|who|can|could|do|does|did|is|are|will|would|should)\b", text)
    )


def customer_declines_more_detail(payload: IntakeChat) -> bool:
    """Stop an open-ended/optional follow-up without misreading a specific answer."""
    message = payload.message
    if re.fullmatch(
        r"\s*(?:that['’]?s\s+all|no\s+more(?:\s+details?)?|nothing\s+else)[\s.!?]*",
        message,
        re.IGNORECASE,
    ):
        return True
    if not re.fullmatch(
        r"\s*(?:i\s*(?:do\s*n['’]?t|don['’]?t)\s*know|idk|not\s+sure|nothing)[\s.!?]*",
        message,
        re.IGNORECASE,
    ):
        return False
    previous = payload.conversation[-2] if len(payload.conversation) >= 2 else None
    previous_text = previous.text.lower() if previous and previous.role == "assistant" else ""
    return bool(
        previous
        and previous.role == "assistant"
        and (
            previous.kind == "extra"
            or "important detail" in previous_text
            or "anything else" in previous_text
        )
    )


def extra_questions_asked(payload: IntakeChat) -> int:
    return sum(1 for turn in payload.conversation if turn.role == "assistant" and turn.kind == "extra")


def qualification_status(
    profile_key: str,
    profile: dict[str, Any],
    covered: set[str],
) -> dict[str, Any]:
    requirements = profile["requirements"]
    total = len(requirements)
    progress = round(100 * len(covered) / total) if total else 100
    return {
        "profile": profile_key,
        "label": profile["label"],
        "progress": progress,
        "qualified": len(covered) == total,
        "requirements": [
            {
                "id": requirement_id,
                "label": requirement["label"],
                "covered": requirement_id in covered,
            }
            for requirement_id, requirement in requirements.items()
        ],
    }


def handoff_fallback() -> str:
    return (
        "I have enough to qualify the project and get it moving. Choose a preferred visit "
        "window below, and LODEX will carry the captured details into the onsite plan."
    )


async def ai_qualification_decision(
    payload: IntakeChat,
    profile_key: str,
    profile: dict[str, Any],
    extra_count: int,
) -> tuple[dict[str, Any] | None, dict[str, str]]:
    routing_text = f"{conversation_text(payload, 'user')}\n{payload.service_category}\n{payload.media_notes}"
    route = model_route(choose_model_tier(routing_text, profile_key=profile_key))
    if not os.getenv("OPENAI_API_KEY"):
        return None, public_route(route)
    requirements = profile["requirements"]
    requirement_guide = {
        requirement_id: {
            "label": requirement["label"],
            "covered_when": requirement["description"],
        }
        for requirement_id, requirement in requirements.items()
    }
    transcript = "\n".join(
        f"{turn.role.upper()}{f' [{turn.kind}]' if turn.kind else ''}: {turn.text}"
        for turn in payload.conversation
    ) or f"USER: {payload.project_summary or payload.message}"
    system = f"""You are the qualification lead for {BUSINESS_NAME}. Use judgment, not a rigid interview.
The active playbook is {profile['label']}. Decide which required facts are genuinely covered by the full conversation.
A fact is covered when it is explicit, reasonably inferable, intentionally delegated to LODEX, explicitly flexible, explicitly unknown but suitable for onsite verification, or supported by media notes. Do not reconfirm a covered fact.
If required facts are missing, ask exactly one concise question that can cover the most important missing fact, preferably combining tightly related missing facts naturally. Required questions have no numeric limit.
For a required_question, set target_requirement to the single still-missing requirement the question addresses. Never target a requirement included in covered_required. For every other response kind, set target_requirement to "none".
Only after every required fact is covered may you ask an extra question. Ask an extra only when it materially improves visit preparation, selection, safety, or estimating. Never ask more than two extras total.
If the customer's latest message asks a side question, answer it directly. A customer question never consumes the extra-question budget and must not be ignored merely to end intake.
When qualified and no worthwhile extra remains, or the customer clearly says to proceed, produce a decisive handoff with no question and direct them to choose a visit window.
Report your confidence honestly. Recommend Terra when the decision needs stronger ambiguity resolution or cross-service judgment. Recommend Sol only for genuinely difficult, safety-sensitive, structurally sensitive, or high-consequence judgment.
Never ask for name, phone, email, street address, or appointment time in chat; the visit form collects those. Never ask the customer to confirm a recap. Never invent a final price."""
    prompt_payload = {
        "requirements": requirement_guide,
        "suggested_extra_topics": profile["extras"],
        "extra_questions_already_asked": extra_count,
        "selected_service": payload.service_category or None,
        "media_notes": payload.media_notes or None,
        "latest_customer_message": payload.message,
        "conversation": transcript,
    }
    schema = {
        "type": "object",
        "properties": {
            "covered_required": {
                "type": "array",
                "items": {"type": "string", "enum": list(requirements)},
                "uniqueItems": True,
            },
            "response_kind": {
                "type": "string",
                "enum": ["required_question", "extra_question", "customer_answer", "handoff"],
            },
            "target_requirement": {
                "type": "string",
                "enum": ["none", *requirements],
            },
            "reply": {"type": "string"},
            "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
            "recommended_tier": {"type": "string", "enum": ["luna", "terra", "sol"]},
        },
        "required": ["covered_required", "response_kind", "target_requirement", "reply", "confidence", "recommended_tier"],
        "additionalProperties": False,
    }
    deadline = time.monotonic() + 18
    for escalation_attempt in range(3):
        prompt_payload["current_model_tier"] = route["tier"]
        prompt = json.dumps(prompt_payload, ensure_ascii=False)
        try:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return None, public_route(route)
            print(
                f"LODEX qualification route={route['tier']} "
                f"model={route['model']} effort={route['reasoning_effort']}"
            )
            response = await asyncio.wait_for(
                client().responses.create(
                model=route["model"],
                reasoning={"effort": route["reasoning_effort"]},
                input=[{"role": "system", "content": system}, {"role": "user", "content": prompt}],
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "lodex_qualification_decision",
                        "strict": True,
                        "schema": schema,
                    }
                },
                ),
                timeout=max(0.1, remaining),
            )
            decision = json.loads(response.output_text)
            if not isinstance(decision, dict):
                return None, public_route(route)
            recommended = str(decision.get("recommended_tier", route["tier"]))
            if (
                escalation_attempt < 2
                and recommended in MODEL_TIER_RANK
                and MODEL_TIER_RANK[recommended] > MODEL_TIER_RANK[route["tier"]]
            ):
                route = model_route(recommended)  # type: ignore[arg-type]
                continue
            return decision, public_route(route)
        except Exception as error:
            print(f"LODEX qualification AI unavailable: {type(error).__name__}: {error}")
            return None, public_route(route)
    return None, public_route(route)


async def qualification_decision(payload: IntakeChat) -> dict[str, Any]:
    profile_key, profile = qualification_profile(payload)
    requirements = profile["requirements"]
    extra_count = extra_questions_asked(payload)
    decision, route = await ai_qualification_decision(payload, profile_key, profile, extra_count)
    covered = fallback_requirement_coverage(payload, profile)
    if decision:
        covered.update(
            requirement_id
            for requirement_id in decision.get("covered_required", [])
            if requirement_id in requirements
        )
    missing = [requirement_id for requirement_id in requirements if requirement_id not in covered]
    status = qualification_status(profile_key, profile, covered)
    response_meta = {
        "qualification": status,
        "ai_route": route,
        "degraded": decision is None,
    }
    reply = str((decision or {}).get("reply", "")).strip()
    response_kind = str((decision or {}).get("response_kind", ""))
    target_requirement = str((decision or {}).get("target_requirement", "none"))
    latest_text = payload.message.lower()
    wants_action = any(cue in latest_text for cue in ACTION_CUES)
    is_frustrated = any(cue in latest_text for cue in FRUSTRATION_CUES)
    declines_more_detail = customer_declines_more_detail(payload)
    latest_question = customer_asked_question(payload.message)

    if wants_action or is_frustrated or declines_more_detail:
        if response_kind != "handoff" or not reply or "?" in reply:
            reply = handoff_fallback()
        return {
            "reply": reply,
            "ready_to_schedule": True,
            "question_kind": "handoff",
        } | response_meta

    if missing:
        next_requirement = requirements[missing[0]]
        if (
            response_kind != "required_question"
            or target_requirement not in missing
            or "?" not in reply
        ):
            reply = next_requirement["question"]
        return {
            "reply": reply,
            "ready_to_schedule": False,
            "question_kind": "required",
        } | response_meta

    if latest_question:
        if response_kind != "customer_answer" or not reply:
            reply = "That project question is worth answering directly. LODEX can address it without making you repeat the qualified scope."
        return {
            "reply": reply,
            "ready_to_schedule": False,
            "question_kind": "answer",
        } | response_meta

    if extra_count < 2 and response_kind == "extra_question" and "?" in reply:
        return {
            "reply": reply,
            "ready_to_schedule": False,
            "question_kind": "extra",
        } | response_meta

    if response_kind != "handoff" or not reply or "?" in reply:
        reply = handoff_fallback()
    return {
        "reply": reply,
        "ready_to_schedule": True,
        "question_kind": "handoff",
    } | response_meta


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
    route = model_route(
        choose_model_tier(f"{description}\n{service_category}", task="vision")
    )
    print(
        f"LODEX vision route={route['tier']} "
        f"model={route['model']} effort={route['reasoning_effort']}"
    )
    result = await client().responses.create(
        model=route["model"],
        reasoning={"effort": route["reasoning_effort"]},
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
    return {
        "ok": True,
        "ai_configured": bool(os.getenv("OPENAI_API_KEY")),
        "admin_configured": bool(LODEX_ADMIN_TOKEN),
        "model_router": {
            tier: public_route(model_route(tier))
            for tier in ("luna", "terra", "sol")
        },
    }


@app.post("/api/admin/login")
async def admin_login(request: AdminLoginRequest):
    verify_admin_token(request.token)
    session_id = create_admin_session()
    response = JSONResponse({"authenticated": True, "expires_in": ADMIN_SESSION_TTL_SECONDS})
    response.set_cookie(value=session_id, **admin_cookie_options())
    return response


@app.post("/api/admin/bootstrap", include_in_schema=False)
async def admin_bootstrap(token: Annotated[str, Form()]):
    """Exchange the Operations Center token for a LODEX-only session cookie.

    The token travels in a TLS-protected POST body, never in a URL, query string,
    fragment, referrer, or persisted browser storage on the LODEX origin.
    """
    verify_admin_token(token)
    session_id = create_admin_session()
    response = RedirectResponse(url="/admin", status_code=303)
    response.set_cookie(value=session_id, **admin_cookie_options())
    return response


@app.get("/api/admin/session", dependencies=[Depends(require_admin)])
async def admin_session():
    return {"authenticated": True}


@app.delete("/api/admin/session", dependencies=[Depends(require_admin)])
async def admin_logout(request: Request):
    session_id = request.cookies.get(ADMIN_SESSION_COOKIE)
    if session_id:
        admin_sessions.pop(session_id, None)
    response = JSONResponse({"authenticated": False})
    response.delete_cookie(ADMIN_SESSION_COOKIE, path="/")
    return response


@app.post("/api/presence/heartbeat")
async def presence_heartbeat(request: PresenceHeartbeat):
    now = time.time()
    existing = active_visitors.get(request.visitor_id)
    is_new_visit = not existing or float(existing.get("last_seen_epoch", 0)) < now - ACTIVE_VISITOR_SECONDS
    first_seen = iso_now() if is_new_visit else str(existing.get("first_seen"))
    visitor = {
        "visitor_id": request.visitor_id,
        "path": request.path,
        "page_title": request.page_title,
        "first_seen": first_seen,
        "last_seen": iso_now(),
        "last_seen_epoch": now,
    }
    active_visitors[request.visitor_id] = visitor
    if is_new_visit:
        append_jsonl(VISITOR_EVENTS_FILE, {
            "visitor_id": request.visitor_id,
            "path": request.path,
            "page_title": request.page_title,
            "created_at": visitor["first_seen"],
        })
        await broadcast_admin_event("visitor.entered", {
            "visitor_id": request.visitor_id,
            "path": request.path,
            "page_title": request.page_title,
        })
    return {"ok": True, "active": len(recent_active_visitors())}


@app.post("/api/support/call")
async def request_support_call(request: SupportCallRequest):
    project_code = request.project_code.strip().upper()
    room_code = project_code or f"LDX-LIVE-{uuid.uuid4().hex[:6].upper()}"
    record = request.model_dump() | {
        "id": uuid.uuid4().hex,
        "room_code": room_code,
        "status": "waiting",
        "created_at": iso_now(),
    }
    append_jsonl(SUPPORT_REQUESTS_FILE, record)
    await broadcast_admin_event("support.requested", {
        "id": record["id"],
        "room_code": room_code,
        "name": record["name"],
        "phone": record["phone"],
        "message": record["message"],
    })
    return {
        "accepted": True,
        "room_code": room_code,
        "message": "LODEX has been alerted. Keep this page open and join the video room when you are ready.",
    }


@app.get("/api/admin/overview", dependencies=[Depends(require_admin)])
async def admin_overview():
    requests = [public_project_record(record) for record in reversed(load_jsonl(UPLOAD_DIR.parent / "appointment-requests.jsonl"))]
    support_requests = list(reversed(load_jsonl(SUPPORT_REQUESTS_FILE)))
    today = utc_now().date().isoformat()
    visitors_today = {
        str(record.get("visitor_id", ""))
        for record in load_jsonl(VISITOR_EVENTS_FILE)
        if str(record.get("created_at", "")).startswith(today)
    }
    active = recent_active_visitors()
    return {
        "active_visitors": [
            {key: value for key, value in visitor.items() if key != "last_seen_epoch"}
            for visitor in active
        ],
        "active_count": len(active),
        "visitors_today": len(visitors_today),
        "project_requests": requests[:100],
        "support_requests": support_requests[:100],
        "counts": {
            "projects": len(requests),
            "waiting_support": sum(item.get("status") == "waiting" for item in support_requests),
            "paid": sum(item.get("payment_status") == "paid" for item in requests),
        },
    }


@app.patch("/api/admin/projects/{project_code}", dependencies=[Depends(require_admin)])
async def update_project_status(project_code: str, request: ProjectStatusUpdate):
    requested_code = project_code.strip().upper()
    if not any(str(item.get("project_code", "")).upper() == requested_code for item in load_jsonl(UPLOAD_DIR.parent / "appointment-requests.jsonl")):
        raise HTTPException(404, "Project request not found.")
    event = request.model_dump() | {"project_code": requested_code, "created_at": iso_now()}
    append_jsonl(PROJECT_EVENTS_FILE, event)
    await broadcast_admin_event("project.updated", event)
    return event


@app.websocket("/api/admin/events")
async def admin_events(websocket: WebSocket):
    if not LODEX_ADMIN_TOKEN or not valid_admin_session(websocket.cookies.get(ADMIN_SESSION_COOKIE)):
        await websocket.close(code=1008)
        return
    await websocket.accept()
    admin_event_sockets.add(websocket)
    await websocket.send_json({"type": "admin.connected", "at": iso_now(), "payload": {}})
    try:
        while True:
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=30)
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "admin.ping", "at": iso_now(), "payload": {}})
    except WebSocketDisconnect:
        pass
    finally:
        admin_event_sockets.discard(websocket)


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
    decision = await qualification_decision(payload)
    return decision | {
        "captured_address": captured_address(payload),
    }


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
                "status": project_event_statuses().get(requested_code, {}).get("status", "Meet-and-greet requested"),
                "title": title,
                "service_category": record.get("service_category", "General inquiry"),
                "customer_segment": record.get("customer_segment"),
                "customer_type": record.get("customer_type"),
                "project_size_class": record.get("project_size_class"),
                "distance_miles": record.get("distance_miles"),
                "visit_fee_cents": record.get("visit_fee_cents"),
                "visit_fee_label": record.get("visit_fee_label"),
                "pricing_rule": record.get("pricing_rule"),
                "next_step": "LODEX will confirm the requested visit window and review any remaining details with you.",
                "progress": 100 if record.get("assumptions_confirmed") or record.get("intake_ready") else 72,
                "scope_confirmed": bool(record.get("assumptions_confirmed")),
                "requested_date": record.get("preferred_date"),
                "requested_time": record.get("preferred_time"),
                "address": record.get("address"),
                "project_summary": record.get("project_summary", ""),
                "uploads": record.get("uploads", []),
                "payment_status": (latest_payment(record["project_code"]) or {}).get("status", "not_started"),
                "past_projects": past_projects[:8],
            }
    raise HTTPException(404, "We could not match that project code and phone number.")


@app.post("/api/appointments/request")
async def request_appointment(request: AppointmentRequest):
    project_id = uuid.uuid4().hex
    project_code = f"LDX-{project_id[:6].upper()}"
    classification_text = f"{request.customer_type or ''}\n{request.project_summary}\n{request.service_category}"
    segment = classify_customer_segment(classification_text, request.customer_segment)
    project_size = normalize_project_size(request.project_size_class) if segment == "home" else None
    distance_result = None
    distance_miles = None
    if segment == "home":
        distance_result = await distance.distance_provider.route_distance(request.address)
        distance_miles = distance_result.miles
    pricing = calculate_visit_pricing(
        segment,
        classification_text,
        project_size,
        distance_miles,
    )
    record = request.model_dump() | {
        "id": project_id,
        "project_code": project_code,
        "status": "requested",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "note": "Requested time is not a final booking until LODEX confirms it.",
        "customer_segment": segment,
        "customer_type": request.customer_type or segment,
        "project_size_class": project_size,
        "distance_miles": pricing["distance_miles"],
        "distance_provider": distance_result.provider if distance_result else None,
        "visit_fee_cents": pricing["fee_cents"],
        "visit_fee_label": pricing["label"],
        "pricing_rule": pricing["pricing_rule"],
        "pricing_requires_manual_review": pricing["requires_manual_review"],
    }
    append_jsonl(UPLOAD_DIR.parent / "appointment-requests.jsonl", record)
    await broadcast_admin_event("project.created", {
        "project_code": record["project_code"],
        "name": record["name"],
        "phone": record["phone"],
        "service_category": record["service_category"],
        "customer_segment": record["customer_segment"],
        "visit_fee_cents": record["visit_fee_cents"],
        "visit_fee_label": record["visit_fee_label"],
        "preferred_date": record["preferred_date"],
        "preferred_time": record["preferred_time"],
    })
    return {
        "id": record["id"],
        "project_code": record["project_code"],
        "message": "Meet-and-greet requested. We will confirm the time and final scope before any final price is set.",
        "confirmation": {
            "name": record["name"],
            "phone": record["phone"],
            "email": record.get("email") or "",
            "address": record["address"],
            "preferred_date": record["preferred_date"],
            "preferred_time": record["preferred_time"],
            "project_summary": record["project_summary"],
            "service_category": record["service_category"],
            "customer_segment": record["customer_segment"],
            "customer_type": record["customer_type"],
            "project_size_class": record["project_size_class"],
            "distance_miles": record["distance_miles"],
            "visit_fee_cents": record["visit_fee_cents"],
            "visit_fee_label": record["visit_fee_label"],
            "pricing_rule": record["pricing_rule"],
            "pricing_requires_manual_review": record["pricing_requires_manual_review"],
            "uploads": record["uploads"],
        },
    }


@app.post("/api/payments/checkout")
async def create_deposit_checkout(request: CheckoutRequest):
    """Create Checkout from persisted server pricing, never a browser amount."""
    project = find_project(request.project_code, request.phone)
    if project is None:
        raise HTTPException(404, "We could not match that project code and phone number.")
    if not stripe_is_configured():
        raise HTTPException(503, "Stripe deposits are not configured yet.")

    pricing = checkout_pricing_for_project(project)
    amount_cents = pricing.get("fee_cents")
    if not isinstance(amount_cents, int) or amount_cents <= 0:
        segment = segment_from_project(project)
        if segment == "enterprise":
            raise HTTPException(
                409,
                "LODEX Enterprise uses a custom assessment. We will review the scope and confirm the appropriate visit or project setup before payment.",
            )
        raise HTTPException(
            409,
            "LODEX needs to confirm route distance and the combined assessment amount before checkout.",
        )

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
        ("line_items[0][price_data][unit_amount]", str(amount_cents)),
        ("line_items[0][price_data][product_data][name]", f"LODEX {pricing['label']} — {service_category}"),
        ("line_items[0][quantity]", "1"),
        ("metadata[project_code]", project_code),
        ("metadata[project_id]", str(project.get("id", ""))),
        ("metadata[customer_segment]", segment_from_project(project)),
        ("metadata[pricing_rule]", str(pricing["pricing_rule"])[:500]),
    ]
    email = str(project.get("email") or "").strip()
    if email:
        fields.append(("customer_email", email))

    session = await stripe_checkout_session(fields, f"lodex-assessment-{project_code}-{uuid.uuid4().hex}")
    append_jsonl(PAYMENTS_FILE, {
        "project_code": project_code,
        "project_id": project.get("id"),
        "session_id": session["id"],
        "status": "checkout_created",
        "customer_segment": segment_from_project(project),
        "visit_fee_label": pricing["label"],
        "pricing_rule": pricing["pricing_rule"],
        "amount_cents": amount_cents,
        "currency": STRIPE_CURRENCY,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return {
        "status": "checkout_created",
        "project_code": project_code,
        "checkout_url": session["url"],
        "visit_fee_label": pricing["label"],
        "pricing_rule": pricing["pricing_rule"],
        "amount_cents": amount_cents,
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
