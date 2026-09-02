"""Monitoring tools — operational dashboards and alerting data."""

from vahn_mcp.crm_client import crm


async def get_critical_overdue_tasks() -> str:
    """Get tasks that are critically overdue (7+ days past due).

    These are the most urgent items needing immediate manager attention.
    """
    data = await crm.get_monitoring_tasks_overdue_critical()
    tasks = data.get("tasks", [])

    if not tasks:
        return "No critically overdue tasks (7+ days). All clear."

    total = data.get("count", len(tasks))
    lines = [f"**{total} critically overdue tasks (7+ days)**", ""]
    for t in tasks:
        lines.append(
            f"- **{t.get('subject', '-')}** — "
            f"Owner: {t.get('ownerName', 'Unassigned')}, "
            f"Due: {t.get('dueDate', '-')}, "
            f"Overdue: {t.get('daysOverdue', '?')} days, "
            f"Contact: {t.get('contactName', '-')}"
        )

    return "\n".join(lines)


async def get_overdue_tasks_summary() -> str:
    """Get a summary count of overdue tasks — today, yesterday, and critical (7+ days).

    Quick overview for managers — how many tasks are overdue and how badly.
    """
    data = await crm.get_monitoring_tasks_overdue_summary()

    yesterday = data.get("yesterday", 0)
    today = data.get("today", 0)
    critical = data.get("critical", 0)
    total = yesterday + today + critical

    if total == 0:
        return "No overdue tasks. All clear."

    lines = [
        "**Overdue Tasks Summary**",
        "",
        f"  Today: {today}",
        f"  Yesterday: {yesterday}",
        f"  Critical (7+ days): {critical}",
        f"  **Total: {total}**",
    ]

    return "\n".join(lines)


async def get_monitoring_opportunities_by_status(
    status: str | None = None,
) -> str:
    """Get opportunity counts by status with dual-Lost handling.

    Uses the derived is_lost flag that catches both opportunity_status='Lost'
    and opportunity_stage='Closed - Lost' to avoid drift between the two fields.

    Args:
        status: Optional filter — "Open", "Won", or "Lost".
    """
    data = await crm.get_monitoring_opportunities_by_status(status=status)
    opps = data.get("opportunities", [])

    if not opps:
        count = data.get("count", 0)
        if count > 0:
            return f"**{count} opportunities** with status '{status or 'all'}'"
        return f"No opportunities found."

    count = data.get("count", len(opps))
    lines = [f"**{count} opportunities** (status: {status or 'all'})", ""]
    for o in opps[:20]:
        lost_flag = " [LOST]" if o.get("isLost") else ""
        lines.append(
            f"- **{o.get('contactName', 'Unknown')}** — "
            f"{o.get('opportunityStage', '-')} / {o.get('opportunityStatus', '-')}{lost_flag}, "
            f"Owner: {o.get('ownerName', 'Unassigned')}"
        )
    if count > 20:
        lines.append(f"\n... and {count - 20} more")

    return "\n".join(lines)


async def get_stale_opportunities_monitor(days: int = 30) -> str:
    """Get open opportunities with no stage change in N days (monitoring view).

    Different from list_stale_opportunities — this is the monitoring/alerting
    version with a higher default threshold (30 days vs 14).

    Args:
        days: Minimum days without a stage change (default 30).
    """
    data = await crm.get_monitoring_opportunities_stale(days=days)
    opps = data.get("opportunities", [])

    if not opps:
        return f"No opportunities stale for {days}+ days."

    count = data.get("count", len(opps))
    lines = [f"**{count} opportunities stale for {days}+ days**", ""]
    for o in opps[:20]:
        lines.append(
            f"- **{o.get('contactName', 'Unknown')}** — "
            f"Stage: {o.get('opportunityStage', '-')}, "
            f"Idle: {o.get('daysSinceLastStageChange', '?')} days, "
            f"Owner: {o.get('ownerName', 'Unassigned')}"
        )
    if count > 20:
        lines.append(f"\n... and {count - 20} more")

    return "\n".join(lines)


async def get_opportunities_open_since(days: int = 30) -> str:
    """Get open opportunities created N+ days ago that are still not won.

    Helps identify deals that have been lingering too long in the pipeline.

    Args:
        days: Minimum age in days since creation (default 30).
    """
    data = await crm.get_monitoring_opportunities_open_since(days=days)
    opps = data.get("opportunities", [])

    if not opps:
        return f"No open opportunities older than {days} days."

    count = data.get("count", len(opps))
    lines = [f"**{count} open opportunities created {days}+ days ago**", ""]
    for o in opps[:20]:
        lines.append(
            f"- **{o.get('contactName', 'Unknown')}** — "
            f"Stage: {o.get('opportunityStage', '-')}, "
            f"Created: {o.get('opportunityCreatedOn', '-')}, "
            f"Open: {o.get('daysOpen', '?')} days, "
            f"Owner: {o.get('ownerName', 'Unassigned')}"
        )
    if count > 20:
        lines.append(f"\n... and {count - 20} more")

    return "\n".join(lines)


async def get_opportunities_summary() -> str:
    """Get a comprehensive opportunities summary for monitoring dashboards.

    Returns counts for: by status, stale 30 days, stale 7 days,
    open since 30 days, and opportunities with no follow-up task.
    """
    data = await crm.get_monitoring_opportunities_summary()

    lines = ["**Opportunities Summary (Monitoring)**", ""]

    by_status = data.get("byStatus", {})
    if by_status:
        lines.append("**By Status:**")
        for status, count in by_status.items():
            lines.append(f"  {status}: {count}")
        lines.append("")

    lines.append("**Alerts:**")
    lines.append(f"  Stale 30+ days: {data.get('stale30Days', 0)}")
    lines.append(f"  Stale 7+ days: {data.get('stale7Days', 0)}")
    lines.append(f"  Open since 30+ days: {data.get('openSince30Days', 0)}")
    lines.append(f"  No follow-up task: {data.get('noFollowup', 0)}")

    return "\n".join(lines)
