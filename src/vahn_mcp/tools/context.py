"""Business context tool — call this before any other tool in a new conversation."""

import asyncio
from datetime import datetime, timedelta

from vahn_mcp import domain
from vahn_mcp.crm_client import crm


async def get_business_context() -> str:
    """Get VAHN's CRM vocabulary and sales flow: the ordered opportunity pipeline,
    valid statuses and contact stages, activity event codes and what each one means,
    the rep roster, risk definitions, and the threshold each tool uses for "stale"
    and "overdue".

    Call this FIRST in any new conversation, before any other tool. Tool names alone
    do not tell you which stage values are valid, which direction the pipeline runs,
    what internal acronyms like "TORG" refer to, or which reps exist — guessing those
    produces empty result sets that look like real answers. It is read-only and cheap.

    Re-call it if the user mentions a stage, status, acronym, product, team, or rep
    name you have not already resolved against it.
    """
    live, source = await _fetch_live()

    lines = ["**VAHN CRM — Business Context**", ""]

    # -- Pipeline --
    # Prefer live stages: get_opportunities_by_stage returns stageRank straight
    # from the SQL view, so it cannot drift from the authored mirror below.
    lines += ["## Opportunity pipeline (ordered)", ""]
    live_stages = (live or {}).get("stages")
    if live_stages:
        for st in live_stages:
            rank = f"[{st['rank']}]" if st.get("rank") else "[\u2014]"
            lost = "  (terminal, counts as Lost)" if st.get("is_lost") else ""
            noun = "opportunity" if st["count"] == 1 else "opportunities"
            lines.append(f"- {rank} **{st['name']}** \u2014 {st['count']} {noun}{lost}")
        stage_source = "live"
    else:
        for stage in domain.OPPORTUNITY_STAGES:
            rank = f"[{stage['rank']}]" if stage["rank"] else "[\u2014]"
            lost = "  (terminal, counts as Lost)" if stage.get("is_lost") else ""
            lines.append(f"- {rank} **{stage['name']}**{lost}")
        stage_source = "last known, from domain.py \u2014 may be stale"

    lines += [
        "",
        f"> Stage list source: {stage_source}. Ranks 1-7 run forward. Both Paying "
        f"Customer stages share rank 7: Partial \u2192 Full Fleet is expansion of "
        f"existing revenue, not pipeline progression. {domain.LOST_DRIFT_NOTE}",
    ]

    # -- Statuses / contact stages / reps --
    lines += ["", f"## Statuses, stages and reps  _(live source: {source})_", ""]
    statuses = (live or {}).get("statusCounts")
    if statuses:
        lines.append("- **Opportunity statuses:** "
                     + ", ".join(f"{k} ({v})" for k, v in statuses.items()))
    else:
        lines.append("- **Opportunity statuses:** Open, Won, Lost")

    lines.append(f"- **Contact stages:** {', '.join(domain.CONTACT_STAGES)}")

    reps = (live or {}).get("reps")
    if reps:
        lines.append(f"- **Reps ({len(reps)}):** {', '.join(reps)}")
    else:
        lines.append(
            "- **Reps:** roster unavailable. Do NOT report that a rep has no "
            "overdue work without first confirming the spelling with the user — "
            "an unrecognised name returns an empty list that looks identical."
        )

    # -- Activity codes --
    lines += ["", "## Activity event codes", ""]
    for code, meta in domain.ACTIVITY_EVENTS.items():
        default = "  _(default)_" if code == domain.DEFAULT_ACTIVITY_EVENT else ""
        lines.append(f"- **{code} — {meta['name']}**{default}: {meta['meaning']}")
        if meta.get("advances_to"):
            tag = " _(INFERRED, unconfirmed)_" if meta.get("inferred") else ""
            lines.append(f"    Expected to advance opportunity to: "
                         f"**{meta['advances_to']}**{tag}")
    lines += [
        "",
        "> Stage transitions above are inferred from name alignment, not confirmed "
        "by VAHN. Nothing is known to advance a lead into either Paying Customer "
        "stage. After logging an activity, re-read the opportunity's stage rather "
        "than assuming it moved.",
    ]

    # -- Risk definitions --
    lines += ["", "## Risk and escalation definitions", ""]
    for term, definition in domain.RISK_DEFINITIONS.items():
        lines.append(f"- **{term}:** {definition}")

    # -- Thresholds --
    lines += ["", "## Thresholds (per tool — not a single company SLA)", ""]
    lines.append(f"| Concept | Threshold | Tool |")
    lines.append(f"|---|---|---|")
    for t in domain.THRESHOLDS:
        lines.append(f"| {t['concept']} | {t['value']} | `{t['tool']}` |")
    lines.append("")
    for conflict in domain.THRESHOLD_CONFLICTS:
        lines.append(f"> {conflict}")
        lines.append("")

    # -- Call dispositions --
    lines += ["## AI call dispositions (observed, not a closed set)", ""]
    lines.append(", ".join(domain.CALL_DISPOSITIONS_OBSERVED))

    # -- Open-valued fields --
    lines += ["", "## Fields with open value sets", ""]
    for field, values in domain.OPEN_VALUE_FIELDS.items():
        lines.append(f"- **{field}:** {', '.join(values)} — attested values only. "
                     f"Prefer echoing a value the user supplied over inventing one.")

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


async def _fetch_live() -> tuple[dict | None, str]:
    """Resolve the live stage list, status counts and rep roster, best source first.

    1. /api/read/business-context — one call, and can include zero-count stages.
    2. The reporting views — opportunities-by-stage carries stageRank and isLost
       from SQL, so ordering is authoritative rather than mirrored from domain.py.
       Only sees stages that currently hold records.
    3. Nothing — the authored layer still renders, flagged as possibly stale.

    Note: the rep roster comes from team-summary, not lsq-users, because the
    /api/read/lsq-users endpoint is not live yet (see server.py).
    """
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
        return None, "unavailable \u2014 vahn-crm-service unreachable"

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

    return derived, "reporting views + team-summary (90d)"
