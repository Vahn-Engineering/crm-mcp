"""Escalation and risk detection tools."""

from vahn_mcp.crm_client import crm


async def get_leads_without_followup(limit: int = 20) -> str:
    """Find open opportunities that have zero pending follow-up tasks (silent-drop detection).

    These are leads that may have fallen through the cracks — an opportunity exists
    but nobody has a task to follow up on it.

    Args:
        limit: Max results to return (default 20).
    """
    data = await crm.get_leads_without_followup(limit=limit)
    opps = data.get("opportunities", [])

    if not opps:
        return "No silent-drop leads found — all open opportunities have pending tasks."

    total = data.get("total", len(opps))
    lines = [
        f"**{total} open opportunities with NO pending follow-up task** (showing {len(opps)})",
        "",
    ]
    for o in opps:
        lines.append(
            f"- **{o.get('contactName', 'Unknown')}** — "
            f"Stage: {o.get('stage', '-')}, "
            f"Owner: {o.get('ownerId', 'Unassigned')}, "
            f"Prospect: {o.get('prospectId', '-')}"
        )

    return "\n".join(lines)


async def get_escalation_list(
    days_threshold: int = 7,
    limit: int = 20,
) -> str:
    """Get the escalation priority list — stale opportunities ranked by fleet size (deal importance).

    Combines staleness (days stuck in current stage) with fleet size as a proxy for
    deal importance. Higher fleet-size deals that have been idle longest appear first.

    Args:
        days_threshold: Minimum days idle in current stage to include (default 7).
        limit: Max results to return (default 20).
    """
    data = await crm.get_escalation_list(
        days_threshold=days_threshold, limit=limit
    )
    escalations = data.get("escalations", [])

    if not escalations:
        return "No opportunities currently need escalation."

    total = data.get("total", len(escalations))
    lines = [
        f"**Escalation List** ({total} total, showing {len(escalations)})",
        f"Threshold: {data.get('daysThreshold', days_threshold)} days idle",
        "",
        f"{'Fleet':<8} {'Stage':<25} {'Days Idle':<12} {'Contact':<20} {'Owner'}",
        f"{'-'*8} {'-'*25} {'-'*12} {'-'*20} {'-'*15}",
    ]
    for o in escalations:
        lines.append(
            f"{str(o.get('fleetSize', '-')):<8} "
            f"{o.get('stage', '-'):<25} "
            f"{str(o.get('daysInStage', '-')):<12} "
            f"{o.get('contactName', 'Unknown'):<20} "
            f"{o.get('ownerId', 'Unassigned')}"
        )

    return "\n".join(lines)


async def get_at_risk_customers(limit: int = 20) -> str:
    """Find at-risk customers — open "Unsatisfied" tasks for Partial/Full Paying Customers.

    These are existing paying customers who have open dissatisfaction signals that
    need immediate attention to prevent churn.

    Args:
        limit: Max results to return (default 20).
    """
    data = await crm.get_at_risk_customers(limit=limit)
    tasks = data.get("tasks", [])

    if not tasks:
        return "No at-risk customers found."

    total = data.get("total", len(tasks))
    lines = [
        f"**{total} At-Risk Customers** (showing {len(tasks)})",
        "",
    ]
    for t in tasks:
        lines.append(
            f"- **{t.get('contactName', 'Unknown')}** — "
            f"Task: {t.get('subject', '-')}, "
            f"Owner: {t.get('ownerName', 'Unassigned')}"
        )

    return "\n".join(lines)
