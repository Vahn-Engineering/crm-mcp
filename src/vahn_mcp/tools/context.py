"""Business context tool — call this before any other tool in a new conversation."""

import asyncio
from datetime import datetime, timedelta

from vahn_mcp import domain
from vahn_mcp.crm_client import crm


async def get_business_context() -> str:
    """Get VAHN's CRM vocabulary and sales flow: the ordered opportunity pipeline,
    valid statuses and contact stages, the activity event catalogue, the rep roster,
    risk definitions, glossary terms like TORG, and the threshold each tool uses for
    "stale" and "overdue".

    Call this FIRST in any new conversation, before any other tool. Tool names alone
    do not tell you which stage values are valid, which direction the pipeline runs,
    what internal acronyms mean, or which reps exist — guessing those produces empty
    result sets that look like real answers. It is read-only and cheap.

    Re-call it if the user mentions a stage, status, acronym, product, team, or rep
    name you have not already resolved against it.
    """
    live, source, catalogue = await _fetch_live()

    lines = ["**VAHN CRM — Business Context**", ""]

    # -- Pipeline --
    lines += ["## Opportunity pipeline (ordered)", ""]
    live_stages = (live or {}).get("stages")
    if live_stages:
        for st in live_stages:
            rank = f"[{st['rank']}]" if st.get("rank") else "[—]"
            noun = "opportunity" if st["count"] == 1 else "opportunities"
            lost = "  (terminal, counts as Lost)" if st.get("is_lost") else ""
            lines.append(f"- {rank} **{st['name']}** — {st['count']} {noun}{lost}")
        stage_source = "live"
    else:
        for stage in domain.OPPORTUNITY_STAGES:
            rank = f"[{stage['rank']}]" if stage["rank"] else "[—]"
            lost = "  (terminal, counts as Lost)" if stage.get("is_lost") else ""
            lines.append(f"- {rank} **{stage['name']}**{lost}")
        stage_source = "last known, from domain.py — may be stale"

    lines += [
        "",
        f"> Stage list source: {stage_source}.",
        f"> {domain.FLEET_SPLIT_NOTE}",
        f"> {domain.MANUAL_STAGE_NOTE}",
        f"> {domain.LOST_DRIFT_NOTE}",
    ]

    # -- Statuses / contact stages / reps --
    lines += ["", f"## Statuses, stages and reps  _(live source: {source})_", ""]
    statuses = (live or {}).get("statusCounts")
    if statuses:
        lines.append("- **Opportunity statuses:** "
                     + ", ".join(f"{k} ({v})" for k, v in statuses.items()))
    else:
        lines.append("- **Opportunity statuses:** Open, Won, Lost")

    lines.append(f"- **Contact stages (valid):** {', '.join(domain.CONTACT_STAGES)}")
    lines.append(f"- **Contact stages (bad data — exclude):** "
                 f"{', '.join(domain.CONTACT_STAGES_INVALID)}")

    reps = (live or {}).get("reps")
    if reps:
        lines.append(f"- **Reps ({len(reps)}):** {', '.join(reps)}")
    else:
        lines.append(
            "- **Reps:** roster unavailable. Do NOT report that a rep has no "
            "overdue work without first confirming the spelling with the user — "
            "an unrecognised name returns an empty list that looks identical."
        )

    # -- Activity catalogue --
    lines += ["", "## Activity event codes", ""]
    if catalogue:
        for act in catalogue:
            code = act.get("activityEvent")
            name = act.get("eventName") or act.get("displayName") or "(unnamed)"
            vahn = "  **[written by VAHN]**" if act.get("writtenByVahn") else ""
            lines.append(f"- **{code} — {name}** "
                         f"({act.get('eventTypeLabel', '?')}){vahn}")
        lines += [
            "",
            "> Source: live LeadSquared catalogue via get_activity_types — "
            "authoritative. Match on the numeric code or writtenByVahn, never on "
            "eventName: the sales team can rename a display name in LSQ at any "
            "time. Call get_activity_types for descriptions and field picklists.",
        ]
    else:
        lines.append("Catalogue unavailable — could not reach LeadSquared.")
        lines += [
            "",
            "> The codes below come from a docstring and are CONTRADICTED by the "
            "CRM API contract (which documents 164 as Customer Connect, not 200). "
            "Do not write an activity using them without resolving the code "
            "through get_activity_types first.",
            "",
        ]
        for code, name in domain.ACTIVITY_EVENTS_UNVERIFIED.items():
            lines.append(f"- {code} — {name}  _(unverified)_")

    lines += ["", "**Codes VAHN writes itself** (pinned in source, not LSQ config):"]
    for code, desc in domain.VAHN_WRITTEN_ACTIVITY_CODES.items():
        lines.append(f"- **{code}** — {desc}")

    lines += ["", f"> {domain.ACTIVITY_AUTOMATION_NOTE}",
              "", f"> {domain.ACTIVITY_RELAY_NOTE}"]

    # -- Risk definitions --
    lines += ["", "## Risk and escalation definitions", ""]
    for term, definition in domain.RISK_DEFINITIONS.items():
        lines.append(f"- **{term}:** {definition}")
    lines += ["", f"> {domain.STRATEGIC_ACCOUNT_NOTE}"]

    # -- Thresholds --
    lines += ["", "## Thresholds", ""]
    lines.append("| Concept | Threshold | Tool | Confirmed |")
    lines.append("|---|---|---|---|")
    for t in domain.THRESHOLDS:
        mark = "yes" if t["confirmed"] else "**no**"
        lines.append(f"| {t['concept']} | {t['value']} | `{t['tool']}` | {mark} |")
    lines += [
        "",
        f"> {domain.STALE_NOTE}",
        "",
        f"> {domain.SEVERITY_MISMATCH_NOTE}",
    ]

    # -- Call dispositions --
    lines += ["", "## AI call dispositions (observed, not a closed set)", ""]
    lines.append(", ".join(domain.CALL_DISPOSITIONS_OBSERVED))

    # -- Glossary --
    lines += ["", "## Glossary", ""]
    for term, definition in domain.GLOSSARY.items():
        lines.append(f"- **{term}:** "
                     f"{definition or '_undefined — ask the user, do not guess_'}")

    # -- API semantics --
    lines += ["", "## Read API behaviours that produce wrong answers silently", ""]
    for note in domain.API_SEMANTICS:
        lines.append(f"- {note}")

    # -- Data quality --
    lines += ["", "## Data quality warnings", ""]
    for note in domain.DATA_QUALITY_NOTES:
        lines.append(f"- {note}")

    return "\n".join(lines)


async def _fetch_live() -> tuple[dict | None, str, list | None]:
    """Resolve the live stage list, status counts, rep roster and activity catalogue.

    All four come from endpoints that exist. The stage list carries stageRank
    straight from a SQL view, so pipeline ordering is authoritative rather than
    mirrored from domain.py. The roster comes from /api/read/users, falling back
    to team-summary, which only sees reps active in the window.

    The catalogue is a LeadSquared relay and resolves independently — losing it
    does not cost the rest of the context.
    """
    catalogue_task = asyncio.create_task(_fetch_catalogue())

    now = datetime.now()
    window_start = now.replace(
        hour=0, minute=0, second=0, microsecond=0
    ) - timedelta(days=90)

    by_stage, by_status, users, team = await asyncio.gather(
        crm.get_opportunities_by_stage(),
        crm.get_opportunities_by_status(),
        crm.list_users(),
        crm.get_team_summary(window_start.isoformat(), now.isoformat()),
        return_exceptions=True,
    )

    catalogue = await catalogue_task

    if all(isinstance(r, Exception) for r in (by_stage, by_status, users, team)):
        return None, "unavailable — vahn-crm-service unreachable", catalogue

    derived: dict = {}
    if not isinstance(by_stage, Exception):
        derived["stages"] = [
            {
                "name": st["stage"],
                "count": st.get("opportunities", 0),
                "rank": st.get("stageRank"),
                "is_lost": bool(st.get("isLost")),
            }
            for st in by_stage.get("stages", [])
        ]
    if not isinstance(by_status, Exception):
        derived["statusCounts"] = by_status.get("byStatus", {})

    roster_source = None
    if not isinstance(users, Exception):
        raw = users.get("users") if isinstance(users, dict) else users
        names = []
        for u in (raw or []):
            if isinstance(u, dict):
                nm = (u.get("name")
                      or f"{u.get('firstName', '')} {u.get('lastName', '')}".strip())
                if nm:
                    names.append(nm)
        if names:
            derived["reps"] = sorted(names)
            roster_source = "/api/read/users (full roster)"
    if "reps" not in derived and not isinstance(team, Exception):
        derived["reps"] = sorted(
            r["name"] for r in team.get("reps", []) if r.get("name")
        )
        roster_source = "team-summary, last 90 days only — an idle rep is invisible"

    source = "reporting views"
    if roster_source:
        source += f"; roster from {roster_source}"
    return derived, source, catalogue


async def _fetch_catalogue() -> list | None:
    """Fetch the LSQ activity catalogue, or None if unavailable."""
    try:
        data = await crm.get_activity_types(event_type="custom")
    except Exception:
        return None
    if not data:
        return None
    return data.get("activityTypes") or None
