"""Rep scorecard tool."""

from vahn_mcp.crm_client import crm
from vahn_mcp.period import resolve_period


async def get_rep_scorecard(
    rep_name: str,
    period: str = "this_week",
) -> str:
    """Get a sales rep's performance scorecard.

    Args:
        rep_name: The rep's name (e.g. "Mazhar Ali Khan").
        period: Time period — "today", "this_week", "this_month", "last_week", "last_month".
    """
    start, end = resolve_period(period)

    data = await crm.get_rep_scorecard(
        rep_name, start.isoformat(), end.isoformat()
    )

    tasks = data.get("tasks", {})
    activities = data.get("activities", {})
    by_status = tasks.get("byStatus", {})
    by_type = activities.get("byType", {})

    lines = [
        f"**Scorecard for {rep_name}** ({period})",
        f"Period: {start.strftime('%b %d')} — {end.strftime('%b %d, %Y')}",
        "",
        "**Tasks**",
        f"  Created: {sum(by_status.values())}",
        f"  Completed: {by_status.get('Completed', 0)}",
        f"  Currently overdue: {tasks.get('currentlyOverdue', 0)}",
        "",
        "**Activities**",
        f"  Total logged: {activities.get('total', 0)}",
    ]

    if by_type:
        for event_name, count in by_type.items():
            lines.append(f"  {event_name}: {count}")

    return "\n".join(lines)
