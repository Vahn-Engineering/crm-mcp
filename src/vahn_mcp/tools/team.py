"""Team summary tool."""

from vahn_mcp import domain
from vahn_mcp.crm_client import crm
from vahn_mcp.period import resolve_period


async def get_team_summary(
    period: domain.Period = "this_week",
) -> str:
    """Get a summary of all reps' activity — tasks created/completed, overdue count, activities logged.

    Args:
        period: Time period — "today", "this_week", "this_month", "last_week", "last_month".
    """
    start, end = resolve_period(period)
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
