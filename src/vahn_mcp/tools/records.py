"""Record-level search over the mirrored Postgres — filters nobody pre-baked.

For aggregate questions prefer the existing report tools (get_pipeline_snapshot,
get_team_summary, get_rep_scorecard, list_overdue_followups) — they answer in one
call. Use these when you need a filter combination that has no report, one
specific record, or to page through a result set.
"""

from vahn_mcp import domain
from vahn_mcp.crm_client import crm
from vahn_mcp.tools._shared import api_error, envelope_footer


async def search_opportunities(
    stage: str | None = None,
    status: str | None = None,
    prospect_id: str | None = None,
    owner_id: str | None = None,
    created_from: str | None = None,
    created_to: str | None = None,
    modified_from: str | None = None,
    modified_to: str | None = None,
    sort: str | None = None,
    page: int = 0,
    size: int = 50,
) -> str:
    """Search opportunities with arbitrary filter combinations, paged.

    Stage names use en-dashes, not hyphens; a hyphen is corrected automatically
    where it matches a known stage. For counts by stage or status, use
    get_opportunities_by_stage or get_pipeline_snapshot instead — one call, no paging.

    Args:
        stage: Pipeline stage. Copy from get_business_context.
        status: "Open", "Won", or "Lost".
        prospect_id: Restrict to one lead's opportunities.
        owner_id: LSQ user id, not a display name.
        created_from: ISO local date-time, e.g. "2026-08-01T00:00:00".
        created_to: Same format.
        modified_from: Window on last modification.
        modified_to: Same format.
        sort: "field" or "field,desc". Valid: createdOn, modifiedOn, stage,
            status, createdAt, updatedAt. A wrong field returns an error naming
            the valid ones.
        page: Zero-based page number.
        size: Rows per page, default 50, capped at 200.
    """
    stage_fixed = domain.normalise_stage(stage)
    try:
        data = await crm.list_opportunities(
            stage=stage_fixed, status=status, prospectId=prospect_id,
            ownerId=owner_id, createdFrom=created_from, createdTo=created_to,
            modifiedFrom=modified_from, modifiedTo=modified_to,
            sort=sort, page=page, size=size,
        )
    except Exception as e:
        return api_error(e)

    rows = data.get("content") or []
    if not rows:
        hint = ""
        if stage_fixed:
            hint = (f" Filtered on stage '{stage_fixed}' — if that name is wrong the "
                    f"result is empty rather than an error, so check it against "
                    f"get_business_context.")
        return f"No opportunities matched those filters.{hint}"

    lines = [f"**Opportunities** ({data.get('totalElements', len(rows))} matching)"]
    if stage_fixed != stage:
        lines.append(f"_Corrected stage filter to '{stage_fixed}' (en-dash)_")
    lines.append("")

    for o in rows:
        lines.append(
            f"- **{o.get('company', 'Unknown')}** — {o.get('stage', '-')} / "
            f"{o.get('status', '-')}, created {o.get('createdOn', '-')}"
        )
        lines.append(f"    Opportunity: {o.get('opportunityId', '-')}  "
                     f"Prospect: {o.get('prospectId', '-')}")

    lines += envelope_footer(data)
    return "\n".join(lines)


async def search_tasks(
    status: str | None = None,
    owner_name: str | None = None,
    owner_id: str | None = None,
    task_type: str | None = None,
    priority: str | None = None,
    prospect_id: str | None = None,
    opportunity_id: str | None = None,
    overdue: bool | None = None,
    due_from: str | None = None,
    due_to: str | None = None,
    sort: str | None = None,
    page: int = 0,
    size: int = 50,
) -> str:
    """Search tasks with arbitrary filter combinations, paged.

    For the standard overdue view bucketed by severity, list_overdue_followups is
    one call. Use this for filter combinations it does not cover.

    Args:
        status: e.g. "Pending", "Completed".
        owner_name: Display name, exact and case-sensitive.
        owner_id: LSQ user id.
        task_type: e.g. "Call".
        priority: e.g. "High".
        prospect_id: Restrict to one lead. Note this excludes tasks whose lead
            was never mirrored locally — those remain reachable by other filters.
        opportunity_id: Restrict to one opportunity.
        overdue: Tri-state. true = not completed AND past due; false =
            everything else; omitting it applies no due-date filter at all.
            Omitted is not the same as false.
        due_from: ISO local date-time.
        due_to: Same format.
        sort: Valid: dueDate, createdOn, modifiedOn, completedOn, status,
            priority, ownerName, createdAt.
        page: Zero-based page number.
        size: Rows per page, default 50, capped at 200.
    """
    try:
        data = await crm.list_tasks(
            status=status, ownerName=owner_name, ownerId=owner_id,
            taskType=task_type, priority=priority, prospectId=prospect_id,
            opportunityId=opportunity_id, overdue=overdue,
            dueFrom=due_from, dueTo=due_to, sort=sort, page=page, size=size,
        )
    except Exception as e:
        return api_error(e)

    rows = data.get("content") or []
    if not rows:
        return "No tasks matched those filters."

    lines = [f"**Tasks** ({data.get('totalElements', len(rows))} matching)", ""]
    orphans = 0
    for t in rows:
        mark = "x" if t.get("status") == "Completed" else " "
        lines.append(
            f"- [{mark}] **{t.get('subject', '-')}** — due {t.get('dueDate', '-')}, "
            f"{t.get('status', '-')}, {t.get('priority', '-')}"
        )
        owner = t.get("ownerName") or t.get("ownerEmail") or "Unassigned"
        detail = f"    Owner: {owner}"
        if t.get("prospectId"):
            detail += f"  Prospect: {t['prospectId']}"
        else:
            orphans += 1
        lines.append(detail)

    if orphans:
        lines += ["", f"> {orphans} task(s) above have no lead attached — their "
                      f"contact was never mirrored locally. They are invisible to "
                      f"any prospect-filtered query."]

    lines += envelope_footer(data)
    return "\n".join(lines)


async def get_lead_record(prospect_id: str) -> str:
    """Get one lead's full local record — address, alternate contacts, fleet, KYC,
    commercial and onboarding detail, plus counts of related records.

    This is a local read. Prefer it over get_lead_details_from_lsq unless you
    specifically need a field that is not mirrored.

    Args:
        prospect_id: The lead's LeadSquared Prospect ID.
    """
    try:
        data = await crm.get_lead(prospect_id)
    except Exception as e:
        return api_error(e)

    lines = [
        f"**{data.get('company', 'Unknown')}**",
        f"  Prospect ID: {data.get('prospectId', prospect_id)}",
        f"  Contact: {data.get('firstName', '')} {data.get('lastName', '')}".rstrip(),
        f"  Phone: {data.get('phone', '-')} / {data.get('mobile', '-')}",
        f"  Type: {data.get('contactType', '-')}  Stage: {data.get('contactStage', '-')}",
        f"  Source: {data.get('source', '-')}  Onboarded: {data.get('isOnboarded', '-')}",
    ]

    for label, key in (("Address", "address"), ("Fleet", "fleet"),
                       ("Commercial", "commercial"), ("Onboarding", "onboarding"),
                       ("KYC", "kyc")):
        block = data.get(key) or {}
        populated = {k: v for k, v in block.items() if v not in (None, "", [])}
        if populated:
            lines += ["", f"**{label}**"]
            for k, v in populated.items():
                lines.append(f"  {k}: {v}")

    counts = data.get("relatedRecordCounts") or {}
    if counts:
        lines += ["", "**Related records**"]
        for k, v in counts.items():
            if k == "activitiesEndpoint":
                continue
            lines.append(f"  {k}: {v}")
        lines.append("  activities: not counted — costs a LeadSquared call. Use "
                     "get_lead_activities if you need them.")

    return "\n".join(lines)
