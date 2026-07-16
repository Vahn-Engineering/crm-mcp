"""Stale opportunities and pipeline snapshot tools."""

from vahn_mcp.crm_client import crm


async def list_stale_opportunities(
    stage: str | None = None,
    days_idle: int = 14,
    owner: str | None = None,
    limit: int = 20,
) -> str:
    """List opportunities that haven't moved stages in a given number of days.

    Args:
        stage: Filter by opportunity stage (e.g. "New Lead", "Contacted").
        days_idle: Minimum days without a stage change (default 14).
        owner: Filter by opportunity owner ID.
        limit: Max results (default 20).
    """
    data = await crm.get_stale_opportunities(
        stage=stage, days_idle=days_idle, owner=owner, limit=limit
    )

    opps = data.get("opportunities", [])
    if not opps:
        return f"No stale opportunities found (threshold: {days_idle} days idle)."

    lines = [
        f"**{data['total']} stale opportunities** (idle > {days_idle} days)",
        "",
    ]

    for o in opps:
        lines.append(
            f"- **{o.get('contactName', 'Unknown')}** — "
            f"Stage: {o['stage']}, Idle: {o['daysIdle']} days, "
            f"Last change: {o['lastStageChange']}"
        )

    return "\n".join(lines)


async def get_pipeline_snapshot(
    owner: str | None = None,
    stage: str | None = None,
) -> str:
    """Get a snapshot of the current pipeline — opportunity counts by stage and status.

    Args:
        owner: Filter by opportunity owner ID.
        stage: Filter by specific stage.
    """
    data = await crm.get_pipeline_snapshot(owner=owner, stage=stage)

    by_stage = data.get("byStage", {})
    by_status = data.get("byStatus", {})

    lines = [
        f"**Pipeline Snapshot** ({data['total']} total opportunities)",
        "",
        "**By Stage:**",
    ]

    for stage_name, count in sorted(by_stage.items()):
        lines.append(f"  {stage_name}: {count}")

    lines.append("")
    lines.append("**By Status:**")
    for status, count in sorted(by_status.items()):
        lines.append(f"  {status}: {count}")

    return "\n".join(lines)
