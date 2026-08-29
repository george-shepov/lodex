"""Fixed-precision pricing for sellable LODEX concepts."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any


def _cents(value: Decimal) -> int:
    return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def current_offer_price_cents(offer: dict[str, Any]) -> int:
    sale_price = offer.get("sale_price_cents")
    if isinstance(sale_price, int):
        return sale_price
    regular_price = offer.get("regular_price_cents")
    if not isinstance(regular_price, int):
        raise ValueError("Offer does not have a valid price.")
    return regular_price


def markup_cents(acquisition_cents: int, policy: dict[str, Any]) -> int:
    method = str(policy.get("method") or "").upper()
    try:
        value = Decimal(str(policy.get("value") or "0"))
    except Exception as error:
        raise ValueError("Markup policy value must be numeric.") from error
    if not value.is_finite() or value < 0:
        raise ValueError("Markup policy value must be non-negative and finite.")
    if method == "PERCENT":
        amount = _cents(Decimal(acquisition_cents) * value / Decimal("100"))
    elif method == "FIXED":
        amount = _cents(value)
    else:
        raise ValueError(f"Unsupported markup method: {method or 'missing'}")
    minimum = policy.get("minimum_margin_amount_cents")
    if isinstance(minimum, int):
        amount = max(amount, minimum)
    return amount


def _policy_for_component(
    concept: dict[str, Any],
    component: dict[str, Any],
    retailer: dict[str, Any],
    policies: list[dict[str, Any]],
) -> dict[str, Any]:
    active = [policy for policy in policies if policy.get("active", True)]
    candidates = (
        ("COMPONENT", {str(component.get("id")), str(component.get("name"))}),
        ("CONCEPT", {str(concept.get("id")), str(concept.get("slug"))}),
        ("RETAILER", {str(retailer.get("id")), str(retailer.get("key"))}),
        ("CATEGORY", {str(concept.get("category"))}),
        ("GLOBAL", {"", "*", "GLOBAL"}),
    )
    for scope, keys in candidates:
        match = next(
            (
                policy
                for policy in reversed(active)
                if policy.get("scope") == scope and str(policy.get("scope_key") or "") in keys
            ),
            None,
        )
        if match:
            return match
    default_id = concept.get("default_markup_policy_id")
    default = next((policy for policy in active if policy.get("id") == default_id), None)
    if default:
        return default
    raise ValueError("Concept does not have an active markup policy.")


def calculate_concept_pricing(
    concept: dict[str, Any],
    components: list[dict[str, Any]],
    offers: dict[str, dict[str, Any]],
    products: dict[str, dict[str, Any]],
    retailers: dict[str, dict[str, Any]],
    policies: list[dict[str, Any]],
) -> dict[str, Any]:
    lines: list[dict[str, Any]] = []
    acquisition_subtotal = 0
    procurement_markup = 0
    source_times: list[str] = []
    stale = False
    now = datetime.now(timezone.utc)

    for component in sorted(components, key=lambda item: int(item.get("sort_order") or 0)):
        offer = offers.get(str(component.get("preferred_offer_id") or ""))
        if not offer:
            if component.get("required", True):
                raise ValueError(f"Required component {component.get('name')} has no offer.")
            continue
        product = products.get(str(offer.get("product_id") or ""))
        retailer = retailers.get(str((product or {}).get("retailer_id") or ""), {})
        if not product:
            raise ValueError(f"Offer for {component.get('name')} has no product.")
        quantity = Decimal(str(component.get("quantity") or "1"))
        if not quantity.is_finite() or quantity <= 0:
            raise ValueError("Component quantity must be positive and finite.")
        unit_price = current_offer_price_cents(offer)
        acquisition = _cents(Decimal(unit_price) * quantity)
        policy = _policy_for_component(concept, component, retailer, policies)
        markup = markup_cents(acquisition, policy)
        acquisition_subtotal += acquisition
        procurement_markup += markup
        source_time = str(offer.get("source_timestamp") or offer.get("fetched_at") or "")
        if source_time:
            source_times.append(source_time)
        expires_at = str(offer.get("expires_at") or "")
        if expires_at:
            try:
                stale = stale or datetime.fromisoformat(expires_at.replace("Z", "+00:00")) <= now
            except ValueError:
                stale = True
        lines.append(
            {
                "component_id": component.get("id"),
                "component_name": component.get("name"),
                "group": component.get("group"),
                "quantity": str(quantity),
                "unit": component.get("unit"),
                "selection_mode": component.get("selection_mode"),
                "requirement_spec_json": component.get("requirement_spec_json", {}),
                "offer_id": offer.get("id"),
                "product_id": product.get("id"),
                "product_name": product.get("name"),
                "brand": product.get("brand"),
                "retailer_name": retailer.get("name"),
                "availability_status": offer.get("availability_status", "UNKNOWN"),
                "source_provider": offer.get("source_provider", "manual"),
                "source_timestamp": source_time,
                "expires_at": expires_at or None,
                "acquisition_unit_price_cents": unit_price,
                "acquisition_total_cents": acquisition,
                "markup_policy_id": policy.get("id"),
                "markup_cents": markup,
                "customer_line_total_cents": acquisition + markup,
            }
        )

    labor = int(concept.get("base_labor_estimate_cents") or 0)
    overhead = int(concept.get("base_project_overhead_cents") or 0)
    total = acquisition_subtotal + procurement_markup + labor + overhead
    return {
        "currency": "USD",
        "acquisition_subtotal_cents": acquisition_subtotal,
        "procurement_markup_cents": procurement_markup,
        "labor_cents": labor,
        "project_overhead_cents": overhead,
        "total_cents": total,
        "availability_as_of": min(source_times) if source_times else None,
        "stale": stale,
        "lines": lines,
    }