"""Reporting snapshot tools — backed by SQL views."""

from vahn_mcp.crm_client import crm


async def get_opportunities_by_status() -> str:
    """Get a breakdown of opportunities by status (Open / Won / Lost).

    Returns current counts — useful for a quick health check of the pipeline.
    """
    data = await crm.get_opportunities_by_status()
    by_status = data.get("byStatus", {})

    if not by_status:
        return "No opportunity data available."

    total = data.get("total", sum(by_status.values()))
    lines = [f"**Opportunities by Status** ({total} total)", ""]
    for status, count in by_status.items():
        lines.append(f"  {status}: {count}")

    return "\n".join(lines)


async def get_opportunities_by_stage() -> str:
    """Get a ranked breakdown of opportunities by pipeline stage.

    Stages are ordered from New Lead (1) through Paying Customer (7).
    Closed-Lost opportunities are listed separately.
    """
    data = await crm.get_opportunities_by_stage()
    stages = data.get("stages", [])

    if not stages:
        return "No opportunity data available."

    total = data.get("total", sum(s["opportunities"] for s in stages))
    lines = [f"**Opportunities by Stage** ({total} total)", ""]
    for s in stages:
        rank = s.get("stageRank")
        rank_str = f"[{rank}]" if rank else "[—]"
        lost = " (Lost)" if s.get("isLost") else ""
        lines.append(f"  {rank_str} {s['stage']}: {s['opportunities']}{lost}")

    return "\n".join(lines)


async def get_leads_by_contact_stage() -> str:
    """Get a breakdown of leads/contacts by their contact stage."""
    data = await crm.get_leads_by_contact_stage()
    by_stage = data.get("byContactStage", {})

    if not by_stage:
        return "No lead data available."

    total = data.get("total", sum(by_stage.values()))
    lines = [f"**Leads by Contact Stage** ({total} total)", ""]
    for stage, count in by_stage.items():
        lines.append(f"  {stage}: {count}")

    return "\n".join(lines)
