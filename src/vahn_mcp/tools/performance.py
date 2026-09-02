"""Performance and analytics tools."""

from vahn_mcp.crm_client import crm
from vahn_mcp.period import resolve_period


async def get_new_opportunities_count(
    period: str = "this_week",
) -> str:
    """Get the count of new opportunities created in a time period.

    Args:
        period: Time period — "today", "this_week", "this_month", "last_week", "last_month".
    """
    start, end = resolve_period(period)
    data = await crm.get_new_opportunities_count(start.isoformat(), end.isoformat())

    count = data.get("newOpportunities", 0)
    return (
        f"**{count} new opportunities** created during {period} "
        f"({start.strftime('%b %d')} — {end.strftime('%b %d, %Y')})"
    )


async def get_won_opportunities(
    period: str = "this_week",
) -> str:
    """Get opportunities won in a time period.

    Note: uses modified_on as a proxy for when the opportunity was won,
    since status-change history is not yet tracked separately.

    Args:
        period: Time period — "today", "this_week", "this_month", "last_week", "last_month".
    """
    start, end = resolve_period(period)
    data = await crm.get_won_opportunities(start.isoformat(), end.isoformat())

    opps = data.get("opportunities", [])
    if not opps:
        return f"No won opportunities found during {period}."

    total = data.get("total", len(opps))
    lines = [
        f"**{total} won opportunities** ({period})",
        f"Period: {start.strftime('%b %d')} — {end.strftime('%b %d, %Y')}",
        "",
    ]
    for o in opps:
        lines.append(
            f"- **{o.get('contactName', 'Unknown')}** — "
            f"Stage: {o.get('stage', '-')}, "
            f"Won: {o.get('wonDate', '-')}, "
            f"Owner: {o.get('ownerId', 'Unassigned')}"
        )

    return "\n".join(lines)


async def get_workload_distribution() -> str:
    """Get workload distribution across reps — open opportunities and pending tasks per rep.

    Useful for managers to check if work is evenly distributed or if some reps are overloaded.
    """
    data = await crm.get_workload_distribution()
    distribution = data.get("distribution", [])

    if not distribution:
        return "No workload data available."

    total_reps = data.get("totalReps", len(distribution))
    lines = [
        f"**Workload Distribution** ({total_reps} reps)",
        "",
        f"{'Owner ID':<40} {'Open Opps':<12} {'Open Tasks':<12} {'Total'}",
        f"{'-'*40} {'-'*12} {'-'*12} {'-'*8}",
    ]
    for r in distribution:
        lines.append(
            f"{r.get('ownerId', 'Unknown'):<40} "
            f"{r.get('openOpportunities', 0):<12} "
            f"{r.get('openTasks', 0):<12} "
            f"{r.get('totalWorkload', 0)}"
        )

    return "\n".join(lines)


async def get_call_outcome_breakdown(
    period: str = "this_week",
) -> str:
    """Get a breakdown of AI/bot call outcomes by disposition.

    Reads from elevenlabs_conversations to show how calls are resolving.

    Args:
        period: Time period — "today", "this_week", "this_month", "last_week", "last_month".
    """
    start, end = resolve_period(period)
    data = await crm.get_call_outcome_breakdown(start.isoformat(), end.isoformat())

    by_disposition = data.get("byDisposition", {})
    if not by_disposition:
        return f"No call data found during {period}."

    total = data.get("totalCalls", sum(by_disposition.values()))
    lines = [
        f"**Call Outcome Breakdown** ({total} total calls, {period})",
        f"Period: {start.strftime('%b %d')} — {end.strftime('%b %d, %Y')}",
        "",
    ]
    for disposition, count in sorted(by_disposition.items(), key=lambda x: -x[1]):
        pct = round(count / total * 100, 1) if total else 0
        lines.append(f"  {disposition}: {count} ({pct}%)")

    return "\n".join(lines)
