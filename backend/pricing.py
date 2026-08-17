"""Server-side customer classification and visit pricing for LODEX."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Literal


CustomerSegment = Literal["home", "business", "enterprise"]
ProjectSizeClass = Literal["small", "several", "major"]


@dataclass(frozen=True)
class PricingConfig:
    home_small_cents: int = 5_000
    home_several_cents: int = 10_000
    home_major_cents: int = 15_000
    business_assessment_cents: int = 30_000
    included_distance_miles: Decimal = Decimal("5")
    distance_rate_cents: int = 250

    @classmethod
    def from_env(cls) -> "PricingConfig":
        return cls(
            home_small_cents=_env_cents("LODEX_HOME_SMALL_VISIT_CENTS", 5_000),
            home_several_cents=_env_cents("LODEX_HOME_SEVERAL_VISIT_CENTS", 10_000),
            home_major_cents=_env_cents("LODEX_HOME_MAJOR_VISIT_CENTS", 15_000),
            business_assessment_cents=_env_cents("LODEX_BUSINESS_ASSESSMENT_CENTS", 30_000),
            included_distance_miles=_env_decimal("LODEX_INCLUDED_DISTANCE_MILES", "5"),
            distance_rate_cents=_env_cents("LODEX_DISTANCE_RATE_CENTS_PER_MILE", 250),
        )


def _env_cents(name: str, fallback: int) -> int:
    try:
        value = int(os.getenv(name, str(fallback)) or fallback)
    except ValueError:
        return fallback
    return value if value >= 0 else fallback


def _env_decimal(name: str, fallback: str) -> Decimal:
    try:
        value = Decimal(os.getenv(name, fallback) or fallback)
    except Exception:
        return Decimal(fallback)
    return value if value >= 0 else Decimal(fallback)


ENTERPRISE_CUES = (
    r"\bproperty[ -]?management compan(?:y|ies)\b",
    r"\bleasing compan(?:y|ies)\b",
    r"\bhousing authorit(?:y|ies)\b",
    r"\bmunicipalit(?:y|ies)\b",
    r"\bfacilities? department\b",
    r"\bgovernment\b",
    r"\bpublic[ -]?sector\b",
    r"\bcorporate housing\b",
    r"\bworkforce housing\b",
    r"\binstitutional\b",
    r"\bschools?\b",
    r"\bpublic facilit(?:y|ies)\b",
    r"\bprime contractor\b",
    r"\bportfolio\b",
    r"\bmulti[ -]?location\b",
    r"\bmulti[ -]?site\b",
    r"\bdeveloper\b",
    r"\bfranchise\b",
)
BUSINESS_CUES = (
    r"\blandlord\b",
    r"\bairbnb\b",
    r"\bvrbo\b",
    r"\bshort[ -]?term rental\b",
    r"\brental property\b",
    r"\breal[ -]?estate investor\b",
    r"\bshop\b",
    r"\brestaurant\b",
    r"\boffice\b",
    r"\bsmall business\b",
)


def classify_customer_segment(
    customer_type: str | None = None,
    declared_segment: str | None = None,
) -> CustomerSegment:
    """Classify known customer types while retaining an explicit valid selection."""
    text = str(customer_type or "").strip().lower()
    if any(re.search(pattern, text) for pattern in ENTERPRISE_CUES):
        return "enterprise"
    if any(re.search(pattern, text) for pattern in BUSINESS_CUES):
        return "business"
    if declared_segment in {"home", "business", "enterprise"}:
        return declared_segment  # type: ignore[return-value]
    if text in {"enterprise", "corporate", "institution"}:
        return "enterprise"
    if text in {"business", "commercial", "rental_owner"}:
        return "business"
    if text in {"home", "homeowner", "owner_occupied", "owner-occupied"}:
        return "home"
    return "home"


def segment_from_project(project: dict) -> CustomerSegment:
    explicit = str(project.get("customer_segment") or "").strip().lower()
    customer_type = str(project.get("customer_type") or "").strip()
    if customer_type or explicit:
        return classify_customer_segment(customer_type, explicit)
    category = str(project.get("service_category") or "").strip().lower()
    if category.startswith("lodex enterprise"):
        return "enterprise"
    if category.startswith("lodex business"):
        return "business"
    return "home"


def normalize_project_size(value: str | None) -> ProjectSizeClass:
    text = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    aliases: dict[str, ProjectSizeClass] = {
        "small": "small",
        "small_repair": "small",
        "small_repair_/_installation": "small",
        "installation": "small",
        "several": "several",
        "several_repairs": "several",
        "several_repairs_or_improvements": "several",
        "major": "major",
        "major_renovation": "major",
        "whole_home": "major",
        "major_renovation_/_whole_home_project": "major",
    }
    return aliases.get(text, "small")


def _money_cents(value: Decimal) -> int:
    return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def calculate_visit_pricing(
    segment: str,
    customer_type: str | None = None,
    project_size: str | None = None,
    distance_miles: float | Decimal | None = None,
    *,
    approved_amount_cents: int | None = None,
    config: PricingConfig | None = None,
) -> dict:
    """Return authoritative visit pricing; unknown Home distance requires review."""
    active = config or PricingConfig.from_env()
    canonical_segment = classify_customer_segment(customer_type, segment)

    if canonical_segment == "enterprise":
        approved = approved_amount_cents if approved_amount_cents and approved_amount_cents > 0 else None
        return {
            "fee_cents": approved,
            "label": "Custom assessment",
            "distance_miles": None,
            "pricing_rule": "enterprise_admin_approved" if approved else "enterprise_custom_assessment",
            "requires_manual_review": approved is None,
        }

    if canonical_segment == "business":
        return {
            "fee_cents": active.business_assessment_cents,
            "label": "Business Project Assessment",
            "distance_miles": None,
            "pricing_rule": "business_standard_assessment",
            "requires_manual_review": False,
        }

    size = normalize_project_size(project_size)
    labels = {
        "small": "Initial Project Deposit",
        "several": "Project Assessment & Diagnostic Visit",
        "major": "On-Site Project Consultation",
    }
    base_amounts = {
        "small": active.home_small_cents,
        "several": active.home_several_cents,
        "major": active.home_major_cents,
    }
    if distance_miles is None:
        return {
            "fee_cents": None,
            "label": labels[size],
            "distance_miles": None,
            "pricing_rule": f"home_{size}_distance_pending",
            "requires_manual_review": True,
        }

    distance = Decimal(str(distance_miles))
    if not distance.is_finite() or distance < 0:
        raise ValueError("distance_miles must be a non-negative finite number")
    surcharge_miles = max(Decimal("0"), distance - active.included_distance_miles)
    surcharge_cents = _money_cents(surcharge_miles * active.distance_rate_cents)
    fee_cents = max(base_amounts[size], base_amounts[size] + surcharge_cents)
    distance_adjusted = surcharge_cents > 0
    label = "Diagnostic Visit" if size == "small" and distance_adjusted else labels[size]
    return {
        "fee_cents": fee_cents,
        "label": label,
        "distance_miles": float(distance),
        "pricing_rule": f"home_{size}_{'distance_adjusted' if distance_adjusted else 'nearby'}",
        "requires_manual_review": False,
    }
