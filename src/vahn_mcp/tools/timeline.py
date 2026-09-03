"""Unified lead timeline — merged, time-ordered, activities read live from LSQ."""

from vahn_mcp.crm_client import crm
from vahn_mcp.tools._shared import api_error


async def get_lead_timeline(
    lead_name: str | None = None,
    prospect_id: str | None = None,
    phone: str | None = None,
    sources: str | None = None,
    limit: int = 100,
) -> str:
    """Get one lead's full history as a single time-ordered stream: activities,
    calls, WhatsApp events, tasks and stage changes merged together.

    Provide one of lead_name, prospect_id, or phone.

    The activity portion reads live from LeadSquared and is rate-limited, so never
    call this in a loop across leads. Exclude "activity" from sources to keep the
    whole call local and skip that hop.

    Args:
        lead_name: Company name, partial match.
        prospect_id: Exact LeadSquared Prospect ID.
        phone: Phone number.
        sources: Comma-separated subset of activity,call,whatsapp,task,stage.
            Omit for all. An unknown source is rejected.
        limit: Max merged entries, newest first. Default 100, capped at 500.
    """
    if not prospect_id:
        if lead_name:
            search = await crm.search_leads(company=lead_name, limit=1)
        elif phone:
            search = await crm.search_leads(phone=phone, limit=1)
        else:
            return "Please provide a lead_name, prospect_id, or phone number."

        contacts = search.get("contacts", [])
        if not contacts:
            return f"No lead found matching '{lead_name or phone}'."
        prospect_id = contacts[0]["prospectId"]

    try:
        data = await crm.get_lead_timeline_merged(
            prospect_id, sources=sources, limit=limit
        )
    except Exception as e:
        return api_error(e, relay=True)

    contact = data.get("contact") or data.get("lead") or {}
    lines = [
        f"**Lead Timeline: {contact.get('company', 'Unknown')}**",
        f"  Prospect ID: {prospect_id}",
    ]
    if contact:
        lines += [
            f"  Phone: {contact.get('phone', '-')}",
            f"  Type: {contact.get('contactType', '-')}  "
            f"Stage: {contact.get('contactStage', '-')}",
        ]

    # Partial failure is reported by the API rather than hidden. A timeline that
    # silently dropped its activity half looks identical to a lead nobody
    # contacted, so this has to surface before any "no contact" conclusion.
    warnings = data.get("warnings") or []
    if warnings:
        lines += ["", "**INCOMPLETE — some sources are missing:**"]
        for w in warnings:
            lines.append(f"  - {w}")
        lines.append("  Do not conclude there was no contact with this lead: part "
                     "of the history could not be read.")

    entries = data.get("entries") or data.get("timeline") or []
    if not entries:
        lines += ["", "No timeline entries returned."]
        if not warnings:
            lines.append("With no warnings above, this lead genuinely has no "
                         "recorded history in the requested sources.")
        return "\n".join(lines)

    lines += ["", f"**History** ({len(entries)} entries, newest first)", ""]
    for e in entries:
        src = (e.get("source") or "?").upper()
        lines.append(f"- `{src}` {e.get('timestamp', '-')} — "
                     f"{e.get('title', '(untitled)')}")
        for key in ("notes", "disposition", "status", "toStage", "eventType"):
            if e.get(key):
                lines.append(f"    {key}: {str(e[key])[:160]}")

    if data.get("truncated"):
        lines += ["", f"> Truncated at limit={limit}. Older entries exist — raise "
                      f"the limit (max 500) or narrow sources if you need them."]

    lines += ["", "> Tasks are placed at their DUE date, not their creation date, so "
                  "an overdue task appears where it was meant to happen."]
    return "\n".join(lines)
