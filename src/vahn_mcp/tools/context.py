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
    lines += ["## Opportunity pipeline (ordered)", ""]
    counts = (live or {}).get("stageCounts", {})
    for stage in domain.OPPORTUNITY_STAGES:
        rank = f"[{stage['rank']}]" if stage["rank"] else "[—]"
        count = counts.get(stage["name"])
        count_str = f" — {count} open" if count is not None else ""
        lost = "  (terminal, counts as Lost)" if stage.get("is_lost") else ""
        lines.append(f"- {rank} **{stage['name']}**{count_str}{lost}")
    lines += [
        "",
        f"> Ranks 1-7 run forward. Both Paying Customer stages share rank 7: "
        f"Partial → Full Fleet is expansion of existing revenue, not pipeline "
        f"progression. {domain.LOST_DRIFT_NOTE}",
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
    """Resolve live counts and the rep roster, best source first.

    1. /api/read/business-context — authoritative, includes zero-count stages.
    2. pipeline-snapshot + team-summary — works with today's backend, but only
       sees values that currently have records against them.
    3. Nothing — service unreachable; the authored layer still renders.
    """
    try:
        ctx = await crm.get_business_context()
    except Exception:
        ctx = None

    if ctx:
        reps = ctx.get("reps") or []
        if reps and isinstance(reps[0], dict):
            reps = [r["name"] for r in reps if r.get("active", True)]
        return (
            {
                "stageCounts": ctx.get("stageCounts") or {},
                "statusCounts": ctx.get("statusCounts") or {},
                "reps": sorted(reps),
            },
            "/api/read/business-context",
        )

    now = datetime.now()
    window_start = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=90)

    snapshot, team = await asyncio.gather(
        crm.get_pipeline_snapshot(),
        crm.get_team_summary(window_start.isoformat(), now.isoformat()),
        return_exceptions=True,
    )

    if isinstance(snapshot, Exception) and isinstance(team, Exception):
        return None, "unavailable — vahn-crm-service unreachable"

    derived: dict = {}
    if not isinstance(snapshot, Exception):
        derived["stageCounts"] = snapshot.get("byStage", {})
        derived["statusCounts"] = snapshot.get("byStatus", {})
    if not isinstance(team, Exception):
        derived["reps"] = sorted(
            r["name"] for r in team.get("reps", []) if r.get("name")
        )

    return derived, "derived from pipeline-snapshot + team-summary (90d)"
