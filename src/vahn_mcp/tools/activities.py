"""Activity tools. THESE RELAY LIVE TO LEADSQUARED — see the rate-limit note.

Every function here costs an outbound LeadSquared call on a limiter shared with
the dialer that places real customer calls. None of them may be called in a
loop over leads.
"""

from vahn_mcp import domain
from vahn_mcp.crm_client import crm
from vahn_mcp.tools._shared import api_error, envelope_footer


async def get_activity_types(event_type: str | None = "custom") -> str:
    """List the LeadSquared activity-type catalogue: which numeric event codes exist
    and what each one means. Call this before writing an activity or interpreting an
    event code — codes hardcoded elsewhere in this server are contradicted by the CRM
    API contract and cannot be trusted.

    Relays to LeadSquared. The catalogue only changes when someone edits activity
    configuration in LSQ, so resolve a code once and reuse it for the conversation
    rather than re-fetching.

    Args:
        event_type: "custom" (VAHN's own types — the default and usually what you
            want), "email", "web", or "revenue". Pass None for the whole catalogue.
    """
    try:
        data = await crm.get_activity_types(event_type=event_type)
    except Exception as e:
        return api_error(e, relay=True)

    types = data.get("activityTypes") or []
    if not types:
        scope = f" for event type '{event_type}'" if event_type else ""
        return f"No activity types returned{scope}."

    lines = [f"**Activity types** ({data.get('total', len(types))})", ""]
    for t in types:
        code = t.get("activityEvent")
        name = t.get("eventName") or t.get("displayName") or "(unnamed)"
        label = t.get("eventTypeLabel")
        vahn = "  **[written by VAHN]**" if t.get("writtenByVahn") else ""
        lines.append(f"- **{code} — {name}** ({label}){vahn}")
        if t.get("description"):
            lines.append(f"    {t['description']}")
        if t.get("writtenBy"):
            lines.append(f"    Source: {t['writtenBy']}")

    lines += [
        "",
        "> Match on the numeric code or on writtenByVahn, not on eventName — the "
        "sales team can rename a display name in LSQ at any time. writtenByVahn is "
        "absent rather than false on types VAHN does not write.",
        f"> {domain.ACTIVITY_CODE_CONFLICT_NOTE}",
    ]
    return "\n".join(lines)


async def get_lead_activities(
    prospect_id: str,
    activity_event: int | None = None,
    page: int = 0,
    size: int = 50,
) -> str:
    """Get the activity history for ONE lead, live from LeadSquared.

    Use this for "what has happened with this lead". For a question spanning many
    leads use list_activities_by_type instead — calling this once per lead would
    contend with the production dialer for rate limit.

    Args:
        prospect_id: The lead's LeadSquared Prospect ID.
        activity_event: Optional numeric event code to filter to. Resolve it with
            get_activity_types first; do not guess.
        page: Zero-based page number.
        size: Rows per page, default 50, capped at 200 by the API.
    """
    try:
        data = await crm.list_activities(
            prospectId=prospect_id, activityEvent=activity_event,
            page=page, size=size,
        )
    except Exception as e:
        return api_error(e, relay=True)

    rows = data.get("content") or []
    if not rows:
        return (f"No activities returned for prospect {prospect_id}"
                + (f" with event code {activity_event}" if activity_event else "")
                + ". This came from LeadSquared directly, so it reflects LSQ's own "
                  "records.")

    lines = [f"**Activities for {prospect_id}**", ""]
    lines += _render_rows(rows)
    lines += envelope_footer(data)
    return "\n".join(lines)


async def get_opportunity_activities(
    opportunity_id: str,
    activity_event: int | None = None,
    page: int = 0,
    size: int = 50,
) -> str:
    """Get the activity history for ONE opportunity, live from LeadSquared.

    Args:
        opportunity_id: The opportunity id (LSQ ProspectActivityId).
        activity_event: Optional numeric event code. Resolve with get_activity_types.
        page: Zero-based page number.
        size: Rows per page, default 50, capped at 200.
    """
    try:
        data = await crm.list_activities(
            opportunityId=opportunity_id, activityEvent=activity_event,
            page=page, size=size,
        )
    except Exception as e:
        return api_error(e, relay=True)

    rows = data.get("content") or []
    if not rows:
        return f"No activities returned for opportunity {opportunity_id}."

    lines = [f"**Activities on opportunity {opportunity_id}**", ""]
    lines += _render_rows(rows)
    lines += envelope_footer(data)
    return "\n".join(lines)


async def list_activities_by_type(
    activity_event: int,
    date_from: str,
    date_to: str,
    page: int = 0,
    size: int = 100,
) -> str:
    """List every activity of one type across ALL leads, in an explicit date window.

    This is the correct way to answer a cross-lead activity question — it costs one
    LeadSquared call per page rather than one per lead. Correlate results back to
    leads using the prospectId on each row, which is a cheap local lookup.

    The date window is required: LeadSquared mandates it, and defaulting it would
    silently cap results with no way to tell a narrow window from a quiet period.

    Args:
        activity_event: Numeric event code, required. Resolve with get_activity_types.
        date_from: Window start, ISO local date-time e.g. "2026-08-01T00:00:00".
            A bare date is rejected — include the time.
        date_to: Window end, same format. Must be after date_from.
        page: Zero-based page number.
        size: Rows per page, default 100, capped at 200.
    """
    try:
        data = await crm.list_activities(
            activityEvent=activity_event, **{"from": date_from, "to": date_to},
            page=page, size=size,
        )
    except Exception as e:
        return api_error(e, relay=True)

    rows = data.get("content") or []
    if not rows:
        return (f"No activities with event code {activity_event} between "
                f"{date_from} and {date_to}. Note this is a window, not a verdict — "
                f"a wider window may return results.")

    lines = [
        f"**Activity code {activity_event}** — {date_from} to {date_to}",
        "",
    ]
    lines += _render_rows(rows, cross_lead=True)
    lines += envelope_footer(data)
    lines += [
        "",
        "> In this mode LeadSquared omits eventName, so it reads as null above — "
        "resolve the code via get_activity_types. prospectId is the correlation key "
        "back to each lead.",
    ]
    return "\n".join(lines)


async def get_activity_details(activity_id: str) -> str:
    """Get one activity in full, with its custom fields resolved to human labels
    instead of bare mx_Custom_N keys.

    Use this instead of requesting the catalogue's schema — it returns the same
    information already parsed, for one record.

    Args:
        activity_id: The activity's id.
    """
    try:
        data = await crm.get_activity(activity_id)
    except Exception as e:
        return api_error(e, relay=True)

    lines = [
        f"**Activity {data.get('eventName') or '(unnamed)'}** "
        f"(code {data.get('eventCode', '-')})",
        f"  Activity ID: {data.get('activityId', '-')}",
        f"  Prospect: {data.get('prospectId', '-')}",
        f"  Created: {data.get('createdOn', '-')} by {data.get('createdBy', '-')}",
        f"  Active: {data.get('isActive', '-')}",
    ]

    fields = data.get("fields") or {}
    if fields:
        lines += ["", "**Fields**"]
        for label, meta in fields.items():
            if isinstance(meta, dict):
                lines.append(f"  {label}: {meta.get('value', '-')}  "
                             f"_({meta.get('schemaName', '?')}, "
                             f"{meta.get('dataType', '?')})_")
            else:
                lines.append(f"  {label}: {meta}")
    else:
        lines.append("\nNo populated fields — blank values are omitted entirely.")

    return "\n".join(lines)


def _render_rows(rows: list[dict], *, cross_lead: bool = False) -> list[str]:
    """Render activity rows. Field availability varies by query mode, so every
    field is treated as optional rather than assumed present."""
    out = []
    for a in rows:
        name = a.get("eventName") or f"(code {a.get('eventCode', '?')})"
        head = f"- **{name}** — {a.get('createdOn', '-')}"
        if a.get("ownerName"):
            head += f", by {a['ownerName']}"
        if a.get("direction"):
            head += f", {a['direction']}"
        out.append(head)
        if cross_lead and a.get("prospectId"):
            out.append(f"    Prospect: {a['prospectId']}")
        if a.get("opportunityId"):
            out.append(f"    Opportunity: {a['opportunityId']}")
        if a.get("notes"):
            out.append(f"    {a['notes'][:200]}")
    return out
