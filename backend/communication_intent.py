from __future__ import annotations

from enum import StrEnum


class CommunicationIntent(StrEnum):
    """First-class output intent for communication generation and delivery.

    See GitHub issue #56 for the implementation plan.
    """

    SEND_TO_CUSTOMER = "send_to_customer"
    DRAFT_WITH_NOTES = "draft_with_notes"
    ANALYZE = "analyze"
    EMAIL = "email"


PAYLOAD_ONLY_INTENTS = frozenset({CommunicationIntent.SEND_TO_CUSTOMER})


def requires_payload_only(intent: CommunicationIntent | str) -> bool:
    """Return whether the intent must contain only customer-visible payload text."""
    try:
        normalized = CommunicationIntent(intent)
    except ValueError:
        return False
    return normalized in PAYLOAD_ONLY_INTENTS


# TODO(#56): carry this intent from voice/chat/web entry points into the communications hub.
# TODO(#56): for SEND_TO_CUSTOMER, force generation to return only customer-visible payload.
# TODO(#56): add a transport-boundary guard before SMS/MMS/email/voice delivery.
# TODO(#56): reject/quarantine drafting scaffolding such as "Subject:", "Message:",
#            template instructions, placeholders, commentary, or alternate versions.
# TODO(#56): add tests proving scaffolding can never enter a sendable payload.
# TODO(#56): decide whether EMAIL remains a distinct intent or becomes
#            SEND_TO_CUSTOMER plus channel + structured subject/body fields.
