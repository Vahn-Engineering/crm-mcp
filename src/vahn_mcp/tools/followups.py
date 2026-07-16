"""Overdue follow-up tasks tool."""

from vahn_mcp.crm_client import crm


async def list_overdue_followups(
    rep_name: str | None = None,
    severity: str | None = None,
    limit: int = 20,
) -> str:
    """List overdue follow-up tasks. Optionally filter by rep name and severity (medium/high/critical).

    Args:
        rep_name: Filter by task owner name (e.g. "Mazhar Ali Khan"). Omit for all reps.
        severity: Filter by severity level: "medium" (< 24h overdue), "high" (24-72h), "critical" (> 72h).
        limit: Max results to return (default 20).
    """
    data = await crm.get_overdue_followups(owner=rep_name, limit=limit * 2)

    tasks = data.get("tasks", [])
    if severity:
        tasks = [t for t in tasks if t.get("severity") == severity]
    tasks = tasks[:limit]

    if not tasks:
        owner_str = f" for {rep_name}" if rep_name else ""
        return f"No overdue follow-ups found{owner_str}."

    lines = [f"**{data['total']} overdue follow-ups** (showing {len(tasks)})", ""]
    by_sev = data.get("bySeverity", {})
    if by_sev:
        lines.append(f"Severity: {', '.join(f'{k}: {v}' for k, v in by_sev.items())}")
        lines.append("")

    for t in tasks:
        lines.append(
            f"- [{t['severity'].upper()}] **{t['subject']}** — "
            f"Owner: {t.get('owner', 'Unassigned')}, Due: {t['dueDate']}, "
            f"Overdue by {t['hoursOverdue']}h"
            + (f", Contact: {t['contactName']}" if t.get('contactName') else "")
        )

    return "\n".join(lines)
