"""Lead timeline tool."""

from vahn_mcp.crm_client import crm


async def get_lead_timeline(
    lead_name: str | None = None,
    prospect_id: str | None = None,
    phone: str | None = None,
) -> str:
    """Get the full timeline for a lead — contact info, opportunities, tasks, activities, and calls.

    Provide one of: lead_name (company name search), prospect_id (exact LSQ ID), or phone number.

    Args:
        lead_name: Company name to search for (partial match).
        prospect_id: Exact LeadSquared Prospect ID.
        phone: Phone number to search for.
    """
    # Resolve prospect_id if not provided
    if not prospect_id:
        if lead_name:
            search = await crm.search_leads(company=lead_name, limit=1)
        elif phone:
            search = await crm.search_leads(phone=phone, limit=1)
        else:
            return "Please provide a lead_name, prospect_id, or phone number."

        contacts = search.get("contacts", [])
        if not contacts:
            query = lead_name or phone
            return f"No lead found matching '{query}'."
        prospect_id = contacts[0]["prospectId"]

    data = await crm.get_lead_timeline(prospect_id)

    contact = data.get("contact", {})
    lines = [
        f"**Lead Timeline: {contact.get('company', 'Unknown')}**",
        f"  Name: {contact.get('firstName', '-')}",
        f"  Phone: {contact.get('phone', '-')}",
        f"  Type: {contact.get('contactType', '-')}",
        f"  Stage: {contact.get('contactStage', '-')}",
        f"  Onboarded: {contact.get('isOnboarded', False)}",
        f"  Prospect ID: {prospect_id}",
        "",
    ]

    # Opportunities
    opps = data.get("opportunities", [])
    if opps:
        lines.append(f"**Opportunities ({len(opps)})**")
        for o in opps:
            lines.append(
                f"  - {o['stage']} / {o['status']} — Created: {o.get('createdOn', '-')}"
            )
        lines.append("")

    # Stage history
    history = data.get("stageHistory", [])
    if history:
        lines.append(f"**Stage Changes ({len(history)})**")
        for h in history:
            lines.append(
                f"  - {h.get('fromStage', '(new)')} → {h['toStage']} at {h['changedAt']}"
            )
        lines.append("")

    # Tasks
    tasks = data.get("tasks", [])
    if tasks:
        lines.append(f"**Tasks ({len(tasks)})**")
        for t in tasks:
            status_mark = "x" if t["status"] == "Completed" else " "
            lines.append(
                f"  - [{status_mark}] {t['subject']} — Due: {t.get('dueDate', '-')}, Owner: {t.get('owner', '-')}"
            )
        lines.append("")

    # Activities
    activities = data.get("activities", [])
    if activities:
        lines.append(f"**Activities ({len(activities)})**")
        for a in activities:
            note_str = f" — {a['notes'][:80]}..." if a.get("notes") else ""
            lines.append(
                f"  - {a['eventName']} ({a.get('date', '-')}) "
                f"[{a.get('qualificationStatus', '-')}]{note_str}"
            )
        lines.append("")

    # Calls
    calls = data.get("calls", [])
    if calls:
        lines.append(f"**AI Calls ({len(calls)})**")
        for c in calls:
            summary = c.get("summary", "")
            summary_str = f" — {summary[:80]}..." if summary else ""
            lines.append(
                f"  - {c.get('startTime', '-')} [{c.get('disposition', '-')}] "
                f"{c.get('durationSecs', 0)}s{summary_str}"
            )

    if not opps and not tasks and not activities and not calls:
        lines.append("No activity recorded for this lead.")

    return "\n".join(lines)
