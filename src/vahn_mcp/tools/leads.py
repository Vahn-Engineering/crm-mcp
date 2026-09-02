"""Lead analytics tools."""

from vahn_mcp.crm_client import crm
from vahn_mcp.period import resolve_period


async def get_new_leads_count(
    period: str = "this_week",
) -> str:
    """Get the count of new leads created in a time period.

    Args:
        period: Time period — "today", "this_week", "this_month", "last_week", "last_month".
    """
    start, end = resolve_period(period)
    data = await crm.get_new_leads_count(start.isoformat(), end.isoformat())

    count = data.get("newLeads", 0)
    return (
        f"**{count} new leads** created during {period} "
        f"({start.strftime('%b %d')} — {end.strftime('%b %d, %Y')})"
    )


async def get_new_leads_by_source(
    period: str = "this_week",
) -> str:
    """Get new leads broken down by source for a time period.

    Args:
        period: Time period — "today", "this_week", "this_month", "last_week", "last_month".
    """
    start, end = resolve_period(period)
    data = await crm.get_new_leads_by_source(start.isoformat(), end.isoformat())

    by_source = data.get("bySource", {})
    if not by_source:
        return f"No new leads found during {period}."

    total = data.get("total", sum(by_source.values()))
    lines = [
        f"**{total} new leads by source** ({period})",
        f"Period: {start.strftime('%b %d')} — {end.strftime('%b %d, %Y')}",
        "",
    ]
    for source, count in sorted(by_source.items(), key=lambda x: -x[1]):
        lines.append(f"  {source}: {count}")

    return "\n".join(lines)
