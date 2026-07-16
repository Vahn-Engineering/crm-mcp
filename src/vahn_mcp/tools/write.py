"""Write tools — create tasks, log activities, fetch from LSQ directly."""

from vahn_mcp.crm_client import crm
from vahn_mcp.lsq_client import lsq


async def create_followup_task(
    prospect_id: str,
    subject: str,
    due_date: str,
    owner_name: str | None = None,
    description: str | None = None,
) -> str:
    """Create a follow-up task for a lead in LeadSquared.

    Args:
        prospect_id: The LeadSquared Prospect ID for the lead.
        subject: Task subject/title (e.g. "Follow up on demo scheduling").
        due_date: Due date in ISO format (e.g. "2026-07-15T10:00:00").
        owner_name: Task owner name. If omitted, defaults to the lead's owner.
        description: Optional task description.
    """
    data = {
        "prospectId": prospect_id,
        "subject": subject,
        "dueDate": due_date,
    }
    if owner_name:
        data["ownerName"] = owner_name
    if description:
        data["description"] = description

    result = await crm.create_task(data)

    if result.get("success"):
        return f"Task created successfully: **{subject}** (due: {due_date})"
    else:
        return f"Failed to create task: {result.get('error', 'Unknown error')}"


async def log_activity(
    prospect_id: str,
    activity_event: str = "201",
    notes: str | None = None,
    qualification_status: str | None = None,
    qualified_outcome: str | None = None,
    not_qualified_outcome: str | None = None,
    type_of_connect: str | None = None,
    follow_up_date_time: str | None = None,
    demo_date_time: str | None = None,
) -> str:
    """Log a sales activity for a lead in LeadSquared.

    Args:
        prospect_id: The LeadSquared Prospect ID.
        activity_event: Activity event code (default "201" = Contacted - Lead Qualification).
            Common codes: 200=Customer Connect, 201=Contacted-Lead Qualification,
            203=Demo Done-Outcome, 204=Onboarded-Training, 205=First Transaction.
        notes: Free-text activity notes.
        qualification_status: "Qualified", "Not Qualified", or "Closed".
        qualified_outcome: e.g. "Follow-up Required" (when qualified).
        not_qualified_outcome: e.g. "Not Interested" (when not qualified).
        type_of_connect: "Phone call", "In Person Meet", etc.
        follow_up_date_time: Follow-up date in ISO format.
        demo_date_time: Demo date in ISO format.
    """
    data: dict = {
        "prospectId": prospect_id,
        "activityEvent": activity_event,
    }
    if notes:
        data["notes"] = notes
    if qualification_status:
        data["qualificationStatus"] = qualification_status
    if qualified_outcome:
        data["qualifiedOutcome"] = qualified_outcome
    if not_qualified_outcome:
        data["notQualifiedOutcome"] = not_qualified_outcome
    if type_of_connect:
        data["typeOfConnect"] = type_of_connect
    if follow_up_date_time:
        data["followUpDateTime"] = follow_up_date_time
    if demo_date_time:
        data["demoDateTime"] = demo_date_time

    result = await crm.log_activity(data)

    if result.get("success"):
        return f"Activity logged successfully for prospect {prospect_id}."
    else:
        return f"Failed to log activity: {result.get('error', 'Unknown error')}"


async def get_lead_details_from_lsq(prospect_id: str) -> str:
    """Fetch full lead details directly from LeadSquared API. Use this for fields not synced to the CRM database (Notes, Lead Score, Tags, etc).

    Args:
        prospect_id: The LeadSquared Prospect ID.
    """
    try:
        data = await lsq.get_lead_by_id(prospect_id)

        if not data:
            return f"No lead found in LeadSquared with ID: {prospect_id}"

        # Format key fields
        lines = [f"**Lead Details (direct from LeadSquared)**", ""]

        # Show all fields, grouped sensibly
        for key, value in sorted(data.items()):
            if value and str(value).strip() and str(value) != "null":
                lines.append(f"  {key}: {value}")

        return "\n".join(lines)
    except Exception as e:
        return f"Error fetching from LeadSquared: {e}"
