import json
import os
import re
import shutil
import subprocess
import uuid
import base64
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
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

app = FastAPI(title="LODEX Intake API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")],
    allow_methods=["*"],
    allow_headers=["*"],
)


class IntakeChat(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    project_summary: str = ""
    media_notes: str = ""


class AppointmentRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    phone: str = Field(min_length=7, max_length=40)
    email: str | None = Field(default=None, max_length=254)
    address: str = Field(min_length=5, max_length=300)
    preferred_date: str
    preferred_time: str
    project_summary: str = Field(min_length=5, max_length=6000)
    uploads: list[dict] = Field(default_factory=list)
    assumptions_confirmed: bool


def client() -> AsyncOpenAI:
    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(503, "AI analysis is not configured yet. You can still submit an appointment request.")
    return AsyncOpenAI()


def sanitize_filename(filename: str | None) -> str:
    name = Path(filename or "upload").name
    return re.sub(r"[^a-zA-Z0-9._-]", "_", name)[:120]


async def analyze_image(path: Path, media_type: str, description: str) -> str:
    """Return observable details and follow-up questions; never a price."""
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    prompt = f"""This is a customer-uploaded image for {BUSINESS_NAME}. Customer description: {description or '(none)'}.
Describe only visible, relevant job details. Separate what you can see from what must be confirmed. Ask no more than four questions needed to scope a handyman visit. Never state a price, never claim licensing or insurance, and never assume hidden damage or dimensions."""
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


@app.post("/api/intake/upload")
async def upload_media(
    file: Annotated[UploadFile, File(...)],
    description: Annotated[str, Form()] = "",
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

    analysis = "Upload saved. Describe what you want us to notice so we can confirm the scope."
    analyzed_type = file.content_type
    analysis_target = target
    if file.content_type.startswith("video/"):
        frame = first_video_frame(target)
        if frame:
            analysis_target, analyzed_type = frame, "image/jpeg"
        else:
            analysis = "Video received. Automated frame analysis is unavailable at the moment, so tell us what you want checked and we will confirm it at the meet-and-greet."
    if analyzed_type.startswith("image/") and os.getenv("OPENAI_API_KEY"):
        try:
            analysis = await analyze_image(analysis_target, analyzed_type, description)
        except Exception:
            analysis = "Upload received. Tell us what you want built or fixed and we’ll continue the scope review together."
    record = {"upload_id": upload_id, "filename": sanitize_filename(file.filename), "media_type": file.content_type, "description": description, "stored_path": str(target), "analysis": analysis}
    with (UPLOAD_DIR.parent / "uploads.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")
    return {
        "upload_id": upload_id,
        "filename": sanitize_filename(file.filename),
        "media_type": file.content_type,
        "description": description,
        "analysis": analysis,
        "message": "Uploaded. Tell us what you want built or fixed, and we’ll confirm the job details together.",
    }


@app.post("/api/intake/chat")
async def intake_chat(payload: IntakeChat):
    system = f"""You are the intake assistant for {BUSINESS_NAME}, a Northeast Ohio handyman and property-maintenance service.
Your job is to clarify a small repair, installation, assembly, cleaning, or maintenance request before an in-person meet-and-greet.
Never state or imply a final price. Do not invent what is visible in photos or videos. Clearly label uncertainty.
Ask one or two concise follow-up questions at a time, prioritizing: scope, exact location/area, material or item, dimensions/quantity, access/safety constraints, desired result, timing, and anything the customer can confirm in person.
When sufficient information is available, summarize the assumptions in bullets and ask the customer to confirm them, then invite them to choose a meet-and-greet time. Keep answers under 180 words."""
    prompt = f"Project summary so far: {payload.project_summary or '(none)'}\nMedia notes: {payload.media_notes or '(none)'}\nCustomer says: {payload.message}"
    response = await client().responses.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
        input=[{"role": "system", "content": system}, {"role": "user", "content": prompt}],
    )
    return {"reply": response.output_text}


@app.post("/api/appointments/request")
async def request_appointment(request: AppointmentRequest):
    if not request.assumptions_confirmed:
        raise HTTPException(400, "Please confirm the project assumptions before requesting a meet-and-greet.")
    record = request.model_dump() | {
        "id": uuid.uuid4().hex,
        "status": "requested",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "note": "Requested time is not a final booking until LODEX confirms it.",
    }
    with (UPLOAD_DIR.parent / "appointment-requests.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")
    return {
        "id": record["id"],
        "message": "Meet-and-greet requested. We will confirm the time and final scope before any final price is set.",
    }
