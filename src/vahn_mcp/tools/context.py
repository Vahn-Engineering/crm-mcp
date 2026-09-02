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
            state = "" if act.get("active", True) else "  _(inactive — do not emit)_"
            default = ("  _(default)_" if act["code"] == domain.DEFAULT_ACTIVITY_EVENT
                       else "")
            lines.append(f"- **{act['code']} — {act['name']}**{default}{state}")
            for field, values in (act.get("fields") or {}).items():
                lines.append(f"    `{field}`: {', '.join(values)}")
        lines += ["", "> Source: live activity catalogue. These picklist values are "
                      "authoritative — use them verbatim."]
    else:
        for code, name in domain.ACTIVITY_EVENTS_FALLBACK.items():
            default = ("  _(default)_" if code == domain.DEFAULT_ACTIVITY_EVENT
                       else "")
            lines.append(f"- **{code} — {name}**{default}")
        lines += [
            "",
            "> Source: fallback list in domain.py — the activity catalogue endpoint "
            "is not live yet. This list is incomplete: code 202 is undocumented and "
            "may or may not exist, and the picklist values below are partial. Prefer "
            "echoing a value the user supplied over inventing one.",
        ]
        lines.append("")
        for field, values in domain.OPEN_VALUE_FIELDS.items():
            lines.append(f"- **{field}:** {', '.join(values)} — attested values only.")

    lines += ["", f"> {domain.ACTIVITY_AUTOMATION_NOTE}"]

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

    # -- Data quality --
    lines += ["", "## Data quality warnings", ""]
    for note in domain.DATA_QUALITY_NOTES:
        lines.append(f"- {note}")

    return "\n".join(lines)


async def _fetch_live() -> tuple[dict | None, str, list | None]:
    """Resolve live vocabulary and the activity catalogue, best source first.

    Stage/status/rep chain:
      1. /api/read/business-context — one call, can include zero-count stages.
      2. The reporting views — opportunities-by-stage carries stageRank and
         isLost from SQL, so ordering is authoritative rather than mirrored.
         Only sees stages that currently hold records.
      3. Nothing — the authored layer renders, flagged as possibly stale.

    The activity catalogue resolves independently: a 404 or an error just means
    the fallback list in domain.py is used.

    Note: the rep roster comes from team-summary, not lsq-users, because
    /api/read/lsq-users is not live yet (see server.py).
    """
    catalogue_task = asyncio.create_task(_fetch_catalogue())

    try:
        ctx = await crm.get_business_context()
    except Exception:
        ctx = None

    if ctx:
        reps = ctx.get("reps") or []
        if reps and isinstance(reps[0], dict):
            reps = [r["name"] for r in reps if r.get("active", True)]
        stages = [
            {
                "name": st.get("stage") or st.get("name"),
                "count": st.get("opportunities", 0),
                "rank": st.get("stageRank"),
                "is_lost": bool(st.get("isLost")),
            }
            for st in (ctx.get("stages") or [])
        ]
        return (
            {
                "stages": stages,
                "statusCounts": ctx.get("statusCounts") or {},
                "reps": sorted(reps),
            },
            "/api/read/business-context",
            await catalogue_task,
        )

    now = datetime.now()
    window_start = now.replace(
        hour=0, minute=0, second=0, microsecond=0
    ) - timedelta(days=90)

    by_stage, by_status, team = await asyncio.gather(
        crm.get_opportunities_by_stage(),
        crm.get_opportunities_by_status(),
        crm.get_team_summary(window_start.isoformat(), now.isoformat()),
        return_exceptions=True,
    )

    if all(isinstance(r, Exception) for r in (by_stage, by_status, team)):
        return None, "unavailable — vahn-crm-service unreachable", await catalogue_task

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
    if not isinstance(team, Exception):
        derived["reps"] = sorted(
            r["name"] for r in team.get("reps", []) if r.get("name")
        )

    return derived, "reporting views + team-summary (90d)", await catalogue_task


async def _fetch_catalogue() -> list | None:
    """Fetch the activity catalogue, or None if unavailable."""
    try:
        data = await crm.get_activity_catalogue()
    except Exception:
        return None
    if not data:
        return None
    return data.get("activities") or None
