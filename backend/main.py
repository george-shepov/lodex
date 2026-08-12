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
from typing import Annotated, Any, Literal

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


class ConversationTurn(BaseModel):
    role: Literal["assistant", "user"]
    text: str = Field(min_length=1, max_length=4000)
    kind: Literal["required", "extra", "answer", "handoff"] | None = None


class IntakeChat(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    project_summary: str = ""
    media_notes: str = ""
    service_category: str = Field(default="", max_length=120)
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
    uploads: list[dict] = Field(default_factory=list)
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
            "access": {"label": "Delivery access", "description": "Stairs, elevators, doorways, parking, floor, or other delivery access is described or delegated for onsite review.", "question": "What should we know about stairs, doors, parking, elevators, or other delivery access?", "patterns": (r"\bstairs?\b", r"\belevator\b", r"\bdoor", r"\bparking\b", r"\bground floor\b", r"\bnot sure\b", r"\bcheck (?:it )?onsite\b")},
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
    "general": {
        "label": "General property project",
        "requirements": {
            "desired_outcome": {"label": "Desired outcome", "description": "What the customer wants LODEX to accomplish is clear.", "question": "What would you like LODEX to accomplish?", "patterns": (r"\bneed\b", r"\bwant\b", r"\bhelp (?:with|me)", r"\bfix\b", r"\bbuild\b", r"\bclean\b", r"\bfurnish\b")},
            "scope": {"label": "Items or areas in scope", "description": "The affected items, rooms, areas, or quantity are reasonably bounded.", "question": "Which items, rooms, or areas are involved?", "patterns": (r"\b(?:one|two|three|four|\d+)\b", r"\broom", r"\bhouse\b", r"\bproperty\b", r"\bitem", r"\bexterior\b")},
            "priority": {"label": "Main priority", "description": "The leading budget, speed, quality, or preservation priority is known.", "question": "What matters most—cost, speed, durability, appearance, or something else?", "patterns": (r"\bbudget\b", r"\bcheap", r"\basap\b", r"\bquick", r"\bdurab", r"\bappearance\b", r"\bpreserv")},
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
    return covered


def customer_asked_question(message: str) -> bool:
    text = message.strip().lower()
    return "?" in text or bool(
        re.match(r"^(?:how|what|why|when|where|who|can|could|do|does|did|is|are|will|would|should)\b", text)
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
            "reply": {"type": "string"},
            "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
            "recommended_tier": {"type": "string", "enum": ["luna", "terra", "sol"]},
        },
        "required": ["covered_required", "response_kind", "reply", "confidence", "recommended_tier"],
        "additionalProperties": False,
    }
    for escalation_attempt in range(3):
        prompt_payload["current_model_tier"] = route["tier"]
        prompt = json.dumps(prompt_payload, ensure_ascii=False)
        try:
            print(
                f"LODEX qualification route={route['tier']} "
                f"model={route['model']} effort={route['reasoning_effort']}"
            )
            response = await client().responses.create(
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
    latest_text = payload.message.lower()
    wants_action = any(cue in latest_text for cue in ACTION_CUES)
    is_frustrated = any(cue in latest_text for cue in FRUSTRATION_CUES)
    latest_question = customer_asked_question(payload.message)

    if missing:
        next_requirement = requirements[missing[0]]
        if response_kind != "required_question" or "?" not in reply:
            reply = next_requirement["question"]
        return {
            "reply": reply,
            "ready_to_schedule": False,
            "question_kind": "required",
        } | response_meta

    if wants_action or is_frustrated:
        if response_kind != "handoff" or not reply or "?" in reply:
            reply = handoff_fallback()
        return {
            "reply": reply,
            "ready_to_schedule": True,
            "question_kind": "handoff",
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
        "model_router": {
            tier: public_route(model_route(tier))
            for tier in ("luna", "terra", "sol")
        },
    }


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
                "status": "Meet-and-greet requested",
                "title": title,
                "service_category": record.get("service_category", "General inquiry"),
                "next_step": "LODEX will confirm the requested visit window and review any remaining details with you.",
                "progress": 100 if record.get("assumptions_confirmed") or record.get("intake_ready") else 72,
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
