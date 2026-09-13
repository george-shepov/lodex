from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Mapping


SMS_TEMPLATE_CATALOG_VERSION = "lodex-a2p-service-2026-09-13-v2"


@dataclass(frozen=True)
class MessageTemplate:
    template_id: str
    purpose: str
    body: str
    variables: tuple[str, ...]
    requires_media: bool = False


SMS_TEMPLATES: dict[str, MessageTemplate] = {
    "service_photo_request": MessageTemplate(
        template_id="service_photo_request",
        purpose="Customer inquiry follow-up requesting project photos.",
        body=(
            "LODEX: Hi [First Name], thanks for contacting us about [Service]. "
            "Could you send a few photos of the area so we can better understand the work? "
            "Reply STOP to opt out or HELP for assistance."
        ),
        variables=("First Name", "Service"),
    ),
    "estimate_ready": MessageTemplate(
        template_id="estimate_ready",
        purpose="Deliver an estimate, link to project information, and invite customer questions or approval.",
        body=(
            "LODEX: Hi [First Name], your estimate for [Project Description] is [Amount]. "
            "You can review your project information at https://lodex.work. "
            "Please reply with any questions or let us know if you’d like to proceed. "
            "Reply STOP to opt out."
        ),
        variables=("First Name", "Project Description", "Amount"),
    ),
    "appointment_confirmation": MessageTemplate(
        template_id="appointment_confirmation",
        purpose="Confirm an appointment after LODEX has accepted the requested date and time.",
        body=(
            "LODEX: Your [Service] appointment is confirmed for [Date] at [Time] at [Service Address]. "
            "Please reply if you need to reschedule or call LODEX at (216) 247-4724. "
            "Reply STOP to opt out."
        ),
        variables=("Service", "Date", "Time", "Service Address"),
    ),
    "arrival_update": MessageTemplate(
        template_id="arrival_update",
        purpose="Notify a customer that LODEX is en route and provide an ETA.",
        body=(
            "LODEX: Hi [First Name], we’re on our way to your appointment and expect to arrive around [Time]. "
            "Reply here with any access or parking instructions. Reply STOP to opt out."
        ),
        variables=("First Name", "Time"),
    ),
    "work_complete": MessageTemplate(
        template_id="work_complete",
        purpose="Notify a customer that work is complete and include completion photos.",
        body=(
            "LODEX: Hi [First Name], the [Project Description] work is complete. "
            "We’ve attached photos for your review. Please reply with any questions about the completed work. "
            "Reply STOP to opt out."
        ),
        variables=("First Name", "Project Description"),
        requires_media=True,
    ),
}


_TOKEN_RE = re.compile(r"\[([^\]]+)\]")


def get_sms_template(template_id: str) -> MessageTemplate:
    try:
        return SMS_TEMPLATES[template_id]
    except KeyError as exc:
        raise KeyError(f"Unknown SMS template: {template_id}") from exc


def render_sms_template(template_id: str, values: Mapping[str, object]) -> str:
    template = get_sms_template(template_id)
    missing = [name for name in template.variables if not str(values.get(name, "")).strip()]
    if missing:
        raise ValueError(f"Missing SMS template value(s): {', '.join(missing)}")

    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        return str(values[name]).strip()

    rendered = _TOKEN_RE.sub(replace, template.body)
    if _TOKEN_RE.search(rendered):
        raise ValueError(f"Unresolved SMS template variable in {template_id}")
    return rendered


def campaign_sample_messages() -> list[str]:
    return [template.body for template in SMS_TEMPLATES.values()]
