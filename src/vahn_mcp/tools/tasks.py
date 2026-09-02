"""Task analytics tools."""

from vahn_mcp.crm_client import crm
from vahn_mcp.period import resolve_period


async def get_tasks_due_today(
    owner_name: str | None = None,
) -> str:
    """Get all tasks due today, optionally filtered by owner.

    Args:
        owner_name: Filter by task owner name. Omit for all reps.
    """
    data = await crm.get_tasks_due_today(owner_id=owner_name)
    tasks = data.get("tasks", [])

    if not tasks:
        owner_str = f" for {owner_name}" if owner_name else ""
        return f"No tasks due today{owner_str}."

    total = data.get("total", len(tasks))
    owner_str = f" for {owner_name}" if owner_name else ""
    lines = [f"**{total} tasks due today{owner_str}**", ""]

    for t in tasks:
        lines.append(
            f"- **{t.get('taskType', 'Task')}**: {t.get('subject', '-')} — "
            f"Owner: {t.get('ownerName', 'Unassigned')}, "
            f"Due: {t.get('dueDate', '-')}"
        )

    return "\n".join(lines)


async def get_task_completion_rate(
    owner_name: str | None = None,
    period: str = "this_week",
) -> str:
    """Get task completion rate — completed vs pending with percentage.

    Args:
        owner_name: Filter by task owner name. Omit for all reps.
        period: Time period — "today", "this_week", "this_month", "last_week", "last_month".
    """
    start, end = resolve_period(period)
    data = await crm.get_task_completion_rate(
        start.isoformat(), end.isoformat(), owner_id=owner_name
    )

    total = data.get("totalTasks", 0)
    completed = data.get("completed", 0)
    rate = data.get("completionRate", 0)
    by_status = data.get("byStatus", {})

    owner_str = f" for {owner_name}" if owner_name else ""
    lines = [
        f"**Task Completion Rate{owner_str}** ({period})",
        f"Period: {start.strftime('%b %d')} — {end.strftime('%b %d, %Y')}",
        "",
        f"  Total: {total}",
        f"  Completed: {completed}",
    ]
    for status, count in by_status.items():
        if status != "Completed":
            lines.append(f"  {status}: {count}")
    lines.append(f"  **Completion rate: {rate}%**")

    return "\n".join(lines)
