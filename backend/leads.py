from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal

from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field

import main

app = main.app
LEADS_FILE = main.UPLOAD_DIR.parent / "leads.jsonl"
FOLLOW_UP_DAYS = (1, 3, 7, 14)
ACTIVE_STATUSES = {"new", "contacted", "waiting", "quoted", "follow_up"}


class LeadCreate(BaseModel):
    source: str = Field(default="yelp", max_length=40)
    external_id: str = Field(default="", max_length=200)
    name: str = Field(min_length=1, max_length=160)
    service: str = Field(default="General inquiry", max_length=160)
    summary: str = Field(default="", max_length=5000)
    reply_to: str = Field(default="", max_length=320)
    source_url: str = Field(default="", max_length=1200)
    status: Literal["new", "contacted", "waiting", "quoted", "follow_up", "scheduled", "won", "lost", "cold"] = "new"
    quoted_amount_cents: int | None = Field(default=None, ge=0, le=100_000_000)
    created_at: str | None = None
    last_contact_at: str | None = None
    next_follow_up_at: str | None = None
    follow_up_count: int = Field(default=0, ge=0, le=100)
    notes: str = Field(default="", max_length=5000)


class LeadPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    service: str | None = Field(default=None, max_length=160)
    summary: str | None = Field(default=None, max_length=5000)
    reply_to: str | None = Field(default=None, max_length=320)
    source_url: str | None = Field(default=None, max_length=1200)
    status: Literal["new", "contacted", "waiting", "quoted", "follow_up", "scheduled", "won", "lost", "cold"] | None = None
    quoted_amount_cents: int | None = Field(default=None, ge=0, le=100_000_000)
    last_contact_at: str | None = None
    next_follow_up_at: str | None = None
    notes: str | None = Field(default=None, max_length=5000)


class LeadImport(BaseModel):
    leads: list[LeadCreate] = Field(max_length=500)


def now() -> datetime:
    return datetime.now(timezone.utc)


def iso(value: datetime) -> str:
    return value.isoformat()


def parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except ValueError:
        return None


def lead_snapshots() -> dict[str, dict]:
    snapshots: dict[str, dict] = {}
    for record in main.load_jsonl(LEADS_FILE):
        lead_id = str(record.get("id") or "")
        if lead_id:
            snapshots[lead_id] = record
    return snapshots


def find_by_external(source: str, external_id: str) -> dict | None:
    if not external_id:
        return None
    for lead in lead_snapshots().values():
        if lead.get("source") == source and lead.get("external_id") == external_id:
            return lead
    return None


def due_state(lead: dict) -> str:
    if lead.get("status") not in ACTIVE_STATUSES:
        return "closed"
    next_at = parse_dt(str(lead.get("next_follow_up_at") or ""))
    if not next_at:
        return "unscheduled"
    delta = next_at - now()
    if delta.total_seconds() <= 0:
        return "due"
    if delta <= timedelta(hours=24):
        return "soon"
    return "later"


def public_lead(lead: dict) -> dict:
    item = dict(lead)
    item["due_state"] = due_state(item)
    return item


def next_follow_up(count: int, base: datetime | None = None) -> str | None:
    if count >= len(FOLLOW_UP_DAYS):
        return None
    base = base or now()
    return iso(base + timedelta(days=FOLLOW_UP_DAYS[count]))


def create_record(payload: LeadCreate) -> tuple[dict, bool]:
    existing = find_by_external(payload.source, payload.external_id)
    if existing:
        return existing, False

    created = parse_dt(payload.created_at) or now()
    lead_id = f"LEAD-{uuid.uuid4().hex[:10].upper()}"
    record = payload.model_dump() | {
        "id": lead_id,
        "created_at": iso(created),
        "updated_at": iso(now()),
    }
    if record["status"] in ACTIVE_STATUSES and not record.get("next_follow_up_at"):
        base = parse_dt(record.get("last_contact_at")) or created
        record["next_follow_up_at"] = next_follow_up(int(record.get("follow_up_count") or 0), base)
    main.append_jsonl(LEADS_FILE, record)
    return record, True


@app.get("/api/admin/leads", dependencies=[Depends(main.require_admin)])
async def list_leads():
    leads = [public_lead(item) for item in lead_snapshots().values()]
    leads.sort(
        key=lambda item: (
            0 if item.get("due_state") == "due" else 1,
            str(item.get("next_follow_up_at") or "9999"),
            str(item.get("created_at") or ""),
        )
    )
    return {
        "leads": leads,
        "counts": {
            "total": len(leads),
            "due": sum(item.get("due_state") == "due" for item in leads),
            "open": sum(item.get("status") in ACTIVE_STATUSES for item in leads),
            "quoted": sum(item.get("status") == "quoted" for item in leads),
            "won": sum(item.get("status") == "won" for item in leads),
        },
        "follow_up_days": list(FOLLOW_UP_DAYS),
    }


@app.post("/api/admin/leads", dependencies=[Depends(main.require_admin)])
async def create_lead(payload: LeadCreate):
    record, created = create_record(payload)
    return {"lead": public_lead(record), "created": created}


@app.post("/api/admin/leads/import", dependencies=[Depends(main.require_admin)])
async def import_leads(payload: LeadImport):
    imported = 0
    duplicates = 0
    for item in payload.leads:
        _, created = create_record(item)
        if created:
            imported += 1
        else:
            duplicates += 1
    return {"imported": imported, "duplicates": duplicates, "total": len(payload.leads)}


@app.patch("/api/admin/leads/{lead_id}", dependencies=[Depends(main.require_admin)])
async def patch_lead(lead_id: str, payload: LeadPatch):
    existing = lead_snapshots().get(lead_id)
    if not existing:
        raise HTTPException(404, "Lead not found.")
    changes = payload.model_dump(exclude_unset=True)
    record = existing | changes | {"updated_at": iso(now())}
    if record.get("status") not in ACTIVE_STATUSES:
        record["next_follow_up_at"] = None
    main.append_jsonl(LEADS_FILE, record)
    return public_lead(record)


@app.post("/api/admin/leads/{lead_id}/follow-up", dependencies=[Depends(main.require_admin)])
async def mark_follow_up(lead_id: str):
    existing = lead_snapshots().get(lead_id)
    if not existing:
        raise HTTPException(404, "Lead not found.")
    contacted = now()
    count = int(existing.get("follow_up_count") or 0) + 1
    next_at = next_follow_up(count, contacted)
    status = "follow_up" if next_at else "cold"
    record = existing | {
        "status": status,
        "last_contact_at": iso(contacted),
        "follow_up_count": count,
        "next_follow_up_at": next_at,
        "updated_at": iso(contacted),
    }
    main.append_jsonl(LEADS_FILE, record)
    return public_lead(record)
