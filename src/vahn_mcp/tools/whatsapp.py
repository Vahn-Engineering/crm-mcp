"""WhatsApp event tool — delivery, clicks and replies, filterable."""

from vahn_mcp.crm_client import crm
from vahn_mcp.tools._shared import api_error, envelope_footer


async def search_whatsapp_events(
    event_category: str | None = None,
    event_type: str | None = None,
    phone: str | None = None,
    prospect_id: str | None = None,
    has_error: bool | None = None,
    lsq_push_status: str | None = None,
    error_code: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    page: int = 0,
    size: int = 50,
) -> str:
    """Search WhatsApp events — deliveries, link clicks, and interactive replies.

    Useful for tracing whether an outreach message landed, was clicked, or failed.

    Args:
        event_category: "DELIVERY_STATUS", "LINK_CLICK", "INTERACTIVE_REPLY", or
            "UNRECOGNIZED". An unknown value returns an error listing the valid
            ones, not an empty result.
        event_type: e.g. "DELIVERED", "FAILED", "CLICKED".
        phone: Trailing-suffix match, so a 10-digit number finds a +91 record.
        prospect_id: The lead this event was correlated to. Absent for numbers
            that could not be matched to a lead.
        has_error: Tri-state. Keys off the error code, not the cause field —
            the provider sets a cause on successes too.
        lsq_push_status: Whether the event reached LeadSquared.
        error_code: Exact match. "0" is the provider's success sentinel and does
            not count as an error.
        date_from: Window start on event time, ISO "2026-08-01T00:00:00".
        date_to: Window end, same format.
        page: Zero-based page number.
        size: Rows per page, default 50, capped at 200.
    """
    try:
        data = await crm.list_whatsapp_events(
            eventCategory=event_category, eventType=event_type, phone=phone,
            prospectId=prospect_id, hasError=has_error,
            lsqPushStatus=lsq_push_status, errorCode=error_code,
            **{"from": date_from, "to": date_to},
            page=page, size=size,
        )
    except Exception as e:
        return api_error(e)

    rows = data.get("content") or []
    if not rows:
        return "No WhatsApp events matched those filters."

    lines = [f"**WhatsApp events** ({data.get('totalElements', len(rows))} matching)",
             ""]
    for ev in rows:
        head = (f"- **{ev.get('eventType', '-')}** ({ev.get('eventCategory', '-')})"
                f" — {ev.get('eventTs', '-')}")
        lines.append(head)
        if ev.get("company") or ev.get("prospectId"):
            lines.append(f"    Lead: {ev.get('company', '-')} "
                         f"({ev.get('prospectId', 'unmatched')})")
        if ev.get("errorCode") and ev.get("errorCode") != "0":
            lines.append(f"    Error {ev['errorCode']}: {ev.get('cause', '-')}")
        if ev.get("lsqPushStatus") and ev["lsqPushStatus"] != "success":
            lines.append(f"    Did not reach LSQ: {ev['lsqPushStatus']}")

    lines += envelope_footer(data)
    return "\n".join(lines)
