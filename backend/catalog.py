"""Sellable concept catalog using LODEX's append-only JSONL persistence."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal, Protocol
from urllib.parse import urlparse

from fastapi import Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator

import main
from catalog_pricing import calculate_concept_pricing

app = main.app


def _path(name: str) -> Path:
    return main.UPLOAD_DIR.parent / f"catalog-{name}.jsonl"


def _snapshots(name: str) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for record in main.load_jsonl(_path(name)):
        record_id = str(record.get("id") or "")
        if record_id:
            records[record_id] = record
    return records


def _append(name: str, record: dict[str, Any]) -> None:
    main.append_jsonl(_path(name), {"schema_version": 1} | record)


def _id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime | None = None) -> str:
    return (value or _now()).isoformat()


def _validate_url(value: str) -> str:
    if not value:
        return value
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("URL must use http or https.")
    return value


class ManualOfferInput(BaseModel):
    retailer_key: str = Field(min_length=1, max_length=80, pattern=r"^[a-z0-9-]+$")
    retailer_name: str = Field(min_length=1, max_length=160)
    retailer_homepage_url: str = Field(default="", max_length=1200)
    retailer_terms_notes: str = Field(default="Manual catalog entry; verify permitted use before publishing.", max_length=2000)
    retailer_product_id: str = Field(min_length=1, max_length=240)
    brand: str = Field(default="", max_length=160)
    product_name: str = Field(min_length=1, max_length=300)
    product_description: str = Field(default="", max_length=3000)
    product_url: str = Field(default="", max_length=1200)
    image_url: str = Field(default="", max_length=1200)
    product_category: str = Field(default="", max_length=160)
    attributes_json: dict[str, Any] = Field(default_factory=dict)
    sku: str = Field(default="", max_length=240)
    currency: str = Field(default="USD", pattern=r"^[A-Z]{3}$")
    regular_price_cents: int = Field(ge=0, le=1_000_000_000)
    sale_price_cents: int | None = Field(default=None, ge=0, le=1_000_000_000)
    availability_status: Literal["IN_STOCK", "LOW_STOCK", "OUT_OF_STOCK", "UNKNOWN"] = "UNKNOWN"
    available_quantity: int | None = Field(default=None, ge=0)
    location_scope: str = Field(default="", max_length=240)
    fulfillment_json: dict[str, Any] = Field(default_factory=dict)
    source_timestamp: str | None = None
    expires_at: str | None = None
    raw_source_ref: str = Field(default="manual-entry", max_length=500)

    @field_validator("retailer_homepage_url", "product_url", "image_url")
    @classmethod
    def validate_remote_url(cls, value: str) -> str:
        return _validate_url(value)


class ComponentInput(BaseModel):
    group: str = Field(min_length=1, max_length=120)
    name: str = Field(min_length=1, max_length=240)
    description: str = Field(default="", max_length=2000)
    quantity: str = Field(default="1", pattern=r"^\d+(?:\.\d{1,3})?$")
    unit: str = Field(default="each", max_length=40)
    required: bool = True
    selection_mode: Literal["FIXED", "SUBSTITUTE_ALLOWED", "CUSTOMER_CHOICE"] = "SUBSTITUTE_ALLOWED"
    requirement_spec_json: dict[str, Any] = Field(default_factory=dict)
    sort_order: int = Field(default=0, ge=0, le=10_000)
    offer: ManualOfferInput


class MarkupPolicyInput(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    scope: Literal["GLOBAL", "CATEGORY", "RETAILER", "CONCEPT", "COMPONENT"] = "CONCEPT"
    scope_key: str = Field(default="", max_length=240)
    method: Literal["PERCENT", "FIXED"]
    value: str = Field(pattern=r"^\d+(?:\.\d{1,4})?$")
    minimum_margin_amount_cents: int = Field(default=0, ge=0, le=1_000_000_000)
    active: bool = True


class ConceptCreate(BaseModel):
    slug: str = Field(min_length=2, max_length=160, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    name: str = Field(min_length=2, max_length=240)
    category: str = Field(min_length=2, max_length=160)
    summary: str = Field(min_length=2, max_length=500)
    description: str = Field(default="", max_length=5000)
    status: Literal["CONCEPT", "BUILT_PROJECT", "RETIRED"] = "CONCEPT"
    publication_status: Literal["DRAFT", "PUBLISHED", "ARCHIVED"] = "DRAFT"
    width: str | None = Field(default=None, max_length=40)
    length: str | None = Field(default=None, max_length=40)
    height: str | None = Field(default=None, max_length=40)
    dimension_unit: str = Field(default="ft", max_length=20)
    hero_media: dict[str, str] = Field(default_factory=dict)
    source_design_provenance: dict[str, Any] = Field(default_factory=dict)
    intended_use: str = Field(default="", max_length=1000)
    included_features: list[str] = Field(default_factory=list, max_length=50)
    configurable_options: list[str] = Field(default_factory=list, max_length=50)
    commercial_modes: list[Literal["DESIGN_ONLY", "BUILD_ONLY", "TURNKEY"]] = Field(default_factory=lambda: ["TURNKEY"])
    base_labor_estimate_cents: int = Field(default=0, ge=0, le=1_000_000_000)
    base_project_overhead_cents: int = Field(default=0, ge=0, le=1_000_000_000)
    lead_time_min_days: int = Field(default=1, ge=1, le=3650)
    lead_time_max_days: int = Field(default=30, ge=1, le=3650)
    price_validity_hours: int = Field(default=72, ge=1, le=720)
    substitution_policy: str = Field(default="Equivalent products may be substituted with approval when availability or pricing changes.", max_length=2000)
    markup_policy: MarkupPolicyInput
    components: list[ComponentInput] = Field(min_length=1, max_length=100)


class OfferPatch(BaseModel):
    regular_price_cents: int | None = Field(default=None, ge=0, le=1_000_000_000)
    sale_price_cents: int | None = Field(default=None, ge=0, le=1_000_000_000)
    availability_status: Literal["IN_STOCK", "LOW_STOCK", "OUT_OF_STOCK", "UNKNOWN"] | None = None
    available_quantity: int | None = Field(default=None, ge=0)
    source_timestamp: str | None = None
    expires_at: str | None = None


class QuoteRequest(BaseModel):
    lead_id: str | None = Field(default=None, max_length=120)


class ProviderContext(BaseModel):
    postal_code: str | None = Field(default=None, max_length=20)
    location: str | None = Field(default=None, max_length=200)


class RetailCatalogProvider(Protocol):
    retailer_key: str

    def search_products(self, query: str, context: ProviderContext) -> list[dict[str, Any]]: ...
    def get_product(self, external_id: str, context: ProviderContext) -> dict[str, Any] | None: ...
    def get_offers(self, external_id: str, context: ProviderContext) -> list[dict[str, Any]]: ...
    def health_check(self) -> dict[str, Any]: ...


class ManualCatalogProvider:
    retailer_key = "manual"

    def search_products(self, query: str, context: ProviderContext) -> list[dict[str, Any]]:
        del context
        needle = query.casefold().strip()
        return [
            product
            for product in _snapshots("products").values()
            if not needle or needle in f"{product.get('brand', '')} {product.get('name', '')}".casefold()
        ]

    def get_product(self, external_id: str, context: ProviderContext) -> dict[str, Any] | None:
        del context
        return next(
            (product for product in _snapshots("products").values() if product.get("retailer_product_id") == external_id),
            None,
        )

    def get_offers(self, external_id: str, context: ProviderContext) -> list[dict[str, Any]]:
        product = self.get_product(external_id, context)
        if not product:
            return []
        return [offer for offer in _snapshots("offers").values() if offer.get("product_id") == product.get("id")]

    def health_check(self) -> dict[str, Any]:
        return {"ok": True, "provider": self.retailer_key, "checked_at": _iso()}


manual_provider = ManualCatalogProvider()


def _concept_components(concept_id: str) -> list[dict[str, Any]]:
    return [item for item in _snapshots("components").values() if item.get("concept_id") == concept_id]


def _pricing(concept: dict[str, Any]) -> dict[str, Any]:
    return calculate_concept_pricing(
        concept,
        _concept_components(str(concept["id"])),
        _snapshots("offers"),
        _snapshots("products"),
        _snapshots("retailers"),
        list(_snapshots("markup-policies").values()),
    )


def _public_concept(concept: dict[str, Any], *, include_detail: bool = True) -> dict[str, Any]:
    pricing = _pricing(concept)
    valid_until = _iso(_now() + timedelta(hours=int(concept.get("price_validity_hours") or 72)))
    public_lines = [
        {
            "group": line["group"],
            "name": line["component_name"],
            "quantity": line["quantity"],
            "unit": line["unit"],
            "selection_mode": line["selection_mode"],
            "product": {
                "name": line["product_name"],
                "brand": line["brand"],
                "availability_status": line["availability_status"],
                "source_provider": line["source_provider"],
                "source_timestamp": line["source_timestamp"],
            },
        }
        for line in pricing["lines"]
    ]
    result = {
        "id": concept["id"],
        "slug": concept["slug"],
        "name": concept["name"],
        "category": concept["category"],
        "summary": concept["summary"],
        "status": concept["status"],
        "status_label": "Built Project" if concept["status"] == "BUILT_PROJECT" else "Concept Design",
        "hero_media": concept.get("hero_media", {}),
        "dimensions": {
            "width": concept.get("width"),
            "length": concept.get("length"),
            "height": concept.get("height"),
            "unit": concept.get("dimension_unit"),
        },
        "lead_time": {
            "min_days": concept.get("lead_time_min_days"),
            "max_days": concept.get("lead_time_max_days"),
        },
        "commercial_modes": concept.get("commercial_modes", []),
        "price": {
            "currency": pricing["currency"],
            "turnkey_price_cents": pricing["total_cents"],
            "type": "PRELIMINARY",
            "valid_until": valid_until,
            "availability_as_of": pricing["availability_as_of"],
            "stale": pricing["stale"],
        },
        "availability_caveat": "Product availability and preliminary pricing can change until a quote is locked.",
        "substitution_policy": concept.get("substitution_policy"),
    }
    if include_detail:
        result |= {
            "description": concept.get("description"),
            "intended_use": concept.get("intended_use"),
            "included_features": concept.get("included_features", []),
            "configurable_options": concept.get("configurable_options", []),
            "component_groups": public_lines,
            "published_at": concept.get("published_at"),
        }
    return result


def _admin_concept(concept: dict[str, Any]) -> dict[str, Any]:
    return {
        "concept": concept,
        "components": _concept_components(str(concept["id"])),
        "pricing": _pricing(concept),
    }


def _find_published(slug: str) -> dict[str, Any]:
    concept = next(
        (
            item
            for item in _snapshots("concepts").values()
            if item.get("slug") == slug and item.get("publication_status") == "PUBLISHED" and item.get("status") != "RETIRED"
        ),
        None,
    )
    if not concept:
        raise HTTPException(404, "Published concept not found.")
    return concept


@app.post("/api/admin/concepts", dependencies=[Depends(main.require_admin)])
async def create_concept(payload: ConceptCreate):
    concepts = _snapshots("concepts")
    if any(item.get("slug") == payload.slug for item in concepts.values()):
        raise HTTPException(409, "Concept slug already exists.")
    now = _iso()
    concept_id = _id("CON")
    policy_id = _id("MRK")
    policy = payload.markup_policy.model_dump() | {
        "id": policy_id,
        "scope_key": payload.markup_policy.scope_key or concept_id,
        "created_at": now,
        "updated_at": now,
    }
    _append("markup-policies", policy)
    component_records: list[dict[str, Any]] = []
    for item in payload.components:
        offer_input = item.offer
        retailers = _snapshots("retailers")
        retailer = next((record for record in retailers.values() if record.get("key") == offer_input.retailer_key), None)
        if not retailer:
            retailer = {
                "id": _id("RTL"),
                "key": offer_input.retailer_key,
                "name": offer_input.retailer_name,
                "homepage_url": offer_input.retailer_homepage_url,
                "integration_type": "MANUAL",
                "active": True,
                "terms_notes": offer_input.retailer_terms_notes,
                "last_sync_at": now,
            }
            _append("retailers", retailer)
        product = {
            "id": _id("PRD"),
            "retailer_id": retailer["id"],
            "retailer_product_id": offer_input.retailer_product_id,
            "brand": offer_input.brand,
            "name": offer_input.product_name,
            "description": offer_input.product_description,
            "product_url": offer_input.product_url,
            "image_url": offer_input.image_url,
            "category": offer_input.product_category,
            "attributes_json": offer_input.attributes_json,
            "active": True,
            "created_at": now,
            "updated_at": now,
        }
        _append("products", product)
        source_timestamp = offer_input.source_timestamp or now
        offer = {
            "id": _id("OFF"),
            "product_id": product["id"],
            "sku": offer_input.sku,
            "currency": offer_input.currency,
            "regular_price_cents": offer_input.regular_price_cents,
            "sale_price_cents": offer_input.sale_price_cents,
            "availability_status": offer_input.availability_status,
            "available_quantity": offer_input.available_quantity,
            "location_scope": offer_input.location_scope,
            "fulfillment_json": offer_input.fulfillment_json,
            "source_provider": "manual",
            "source_timestamp": source_timestamp,
            "fetched_at": now,
            "expires_at": offer_input.expires_at or _iso(_now() + timedelta(hours=payload.price_validity_hours)),
            "raw_source_ref": offer_input.raw_source_ref,
            "active": True,
        }
        _append("offers", offer)
        component = item.model_dump(exclude={"offer"}) | {
            "id": _id("CMP"),
            "concept_id": concept_id,
            "preferred_offer_id": offer["id"],
            "approved_alternative_offer_ids": [],
        }
        _append("components", component)
        component_records.append(component)
    concept = payload.model_dump(exclude={"components", "markup_policy"}) | {
        "id": concept_id,
        "default_markup_policy_id": policy_id,
        "created_at": now,
        "updated_at": now,
        "published_at": now if payload.publication_status == "PUBLISHED" else None,
    }
    _append("concepts", concept)
    return _admin_concept(concept)


@app.get("/api/admin/concepts", dependencies=[Depends(main.require_admin)])
async def admin_concepts():
    return {"concepts": [_admin_concept(item) for item in _snapshots("concepts").values()]}


@app.get("/api/admin/concepts/{concept_id}", dependencies=[Depends(main.require_admin)])
async def admin_concept(concept_id: str):
    concept = _snapshots("concepts").get(concept_id)
    if not concept:
        raise HTTPException(404, "Concept not found.")
    return _admin_concept(concept)


@app.patch("/api/admin/catalog/offers/{offer_id}", dependencies=[Depends(main.require_admin)])
async def update_offer(offer_id: str, payload: OfferPatch):
    offer = _snapshots("offers").get(offer_id)
    if not offer:
        raise HTTPException(404, "Offer not found.")
    changes = payload.model_dump(exclude_unset=True)
    if "source_timestamp" not in changes:
        changes["source_timestamp"] = _iso()
    updated = offer | changes | {"fetched_at": _iso()}
    _append("offers", updated)
    return updated


@app.get("/api/admin/retail/search", dependencies=[Depends(main.require_admin)])
async def search_manual_catalog(q: str = Query(default="", max_length=200), postal_code: str | None = Query(default=None, max_length=20)):
    return {
        "provider": manual_provider.health_check(),
        "products": manual_provider.search_products(q, ProviderContext(postal_code=postal_code)),
    }


@app.get("/api/concepts")
async def public_concepts():
    concepts = [
        _public_concept(item, include_detail=False)
        for item in _snapshots("concepts").values()
        if item.get("publication_status") == "PUBLISHED" and item.get("status") != "RETIRED"
    ]
    return {"concepts": concepts}


@app.get("/api/concepts/{slug}")
async def public_concept(slug: str):
    return _public_concept(_find_published(slug))


@app.post("/api/concepts/{concept_id}/quote-request")
async def create_quote_snapshot(concept_id: str, payload: QuoteRequest):
    concept = _snapshots("concepts").get(concept_id)
    if not concept or concept.get("publication_status") != "PUBLISHED" or concept.get("status") == "RETIRED":
        raise HTTPException(404, "Published concept not found.")
    pricing = _pricing(concept)
    created_at = _now()
    quote = {
        "id": _id("QTE"),
        "concept_id": concept_id,
        "lead_id": payload.lead_id,
        "currency": pricing["currency"],
        "retail_subtotal_cents": pricing["acquisition_subtotal_cents"],
        "procurement_markup_cents": pricing["procurement_markup_cents"],
        "labor_cents": pricing["labor_cents"],
        "freight_delivery_cents": 0,
        "assembly_install_cents": 0,
        "project_management_cents": pricing["project_overhead_cents"],
        "contingency_cents": 0,
        "tax_if_applicable_cents": 0,
        "total_cents": pricing["total_cents"],
        "valid_until": _iso(created_at + timedelta(hours=int(concept.get("price_validity_hours") or 72))),
        "substitution_policy": concept.get("substitution_policy"),
        "component_snapshot_json": pricing["lines"],
        "pricing_snapshot_json": {key: value for key, value in pricing.items() if key != "lines"},
        "created_at": _iso(created_at),
    }
    _append("quote-snapshots", quote)
    return {
        "quote_id": quote["id"],
        "concept_id": concept_id,
        "currency": quote["currency"],
        "total_cents": quote["total_cents"],
        "valid_until": quote["valid_until"],
        "substitution_policy": quote["substitution_policy"],
        "price_type": "QUOTE_LOCKED",
    }


@app.get("/api/admin/quotes/{quote_id}", dependencies=[Depends(main.require_admin)])
async def admin_quote_snapshot(quote_id: str):
    quote = _snapshots("quote-snapshots").get(quote_id)
    if not quote:
        raise HTTPException(404, "Quote not found.")
    return quote