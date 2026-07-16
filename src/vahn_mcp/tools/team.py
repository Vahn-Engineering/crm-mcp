"""Team summary tool."""

from datetime import datetime, timedelta

from vahn_mcp.crm_client import crm


async def get_team_summary(
    period: str = "this_week",
) -> str:
    """Get a summary of all reps' activity — tasks created/completed, overdue count, activities logged.

    Args:
        period: Time period — "today", "this_week", "this_month", "last_week", "last_month".
    """
    start, end = _resolve_period(period)
    data = await crm.get_team_summary(start.isoformat(), end.isoformat())

    reps = data.get("reps", [])
    if not reps:
        return "No rep activity found for this period."

    lines = [
        f"**Team Summary** ({period})",
        f"Period: {start.strftime('%b %d')} — {end.strftime('%b %d, %Y')}",
        f"Reps: {data.get('totalReps', 0)}",
        "",
        f"{'Rep':<25} {'Tasks':<8} {'Done':<8} {'Overdue':<10} {'Activities':<10}",
        f"{'-'*25} {'-'*8} {'-'*8} {'-'*10} {'-'*10}",
    ]

    for r in reps:
        lines.append(
            f"{r['name']:<25} {r['tasksCreated']:<8} {r['tasksCompleted']:<8} "
            f"{r['currentlyOverdue']:<10} {r['activitiesLogged']:<10}"
        )

    return "\n".join(lines)


def _resolve_period(period: str) -> tuple[datetime, datetime]:
    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    match period:
        case "today":
            return today_start, now
        case "this_week":
            return today_start - timedelta(days=today_start.weekday()), now
        case "this_month":
            return today_start.replace(day=1), now
        case "last_week":
            end = today_start - timedelta(days=today_start.weekday())
            return end - timedelta(days=7), end
        case "last_month":
            first = today_start.replace(day=1)
            end = first - timedelta(seconds=1)
            return end.replace(day=1, hour=0, minute=0, second=0), end
        case _:
            return today_start - timedelta(days=today_start.weekday()), now
