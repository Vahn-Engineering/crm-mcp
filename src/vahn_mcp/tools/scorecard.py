"""Rep scorecard tool."""

from datetime import datetime, timedelta

from vahn_mcp.crm_client import crm


async def get_rep_scorecard(
    rep_name: str,
    period: str = "this_week",
) -> str:
    """Get a sales rep's performance scorecard.

    Args:
        rep_name: The rep's name (e.g. "Mazhar Ali Khan").
        period: Time period — "today", "this_week", "this_month", "last_week", "last_month".
    """
    start, end = _resolve_period(period)

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


def _resolve_period(period: str) -> tuple[datetime, datetime]:
    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    match period:
        case "today":
            return today_start, now
        case "this_week":
            start = today_start - timedelta(days=today_start.weekday())
            return start, now
        case "this_month":
            start = today_start.replace(day=1)
            return start, now
        case "last_week":
            end = today_start - timedelta(days=today_start.weekday())
            start = end - timedelta(days=7)
            return start, end
        case "last_month":
            first_this_month = today_start.replace(day=1)
            end = first_this_month - timedelta(seconds=1)
            start = end.replace(day=1, hour=0, minute=0, second=0)
            return start, end
        case _:
            # Default to this week
            start = today_start - timedelta(days=today_start.weekday())
            return start, now
