"""Stage history tools — queryable movement through the pipeline."""

from vahn_mcp import domain
from vahn_mcp.crm_client import crm
from vahn_mcp.tools._shared import api_error, envelope_footer


async def get_stage_changes(
    to_stage: str | None = None,
    from_stage: str | None = None,
    opportunity_id: str | None = None,
    changed_from: str | None = None,
    changed_to: str | None = None,
    page: int = 0,
    size: int = 50,
) -> str:
    """Query opportunity stage movements across the pipeline — newest first.

    to_stage answers "what moved into this stage" (e.g. what closed this week);
    from_stage answers "what churned out of it".

    Stage names use en-dashes, not hyphens. A hyphen is corrected automatically
    where it matches a known stage, but copy names from get_business_context to be
    safe — an unmatched name returns an empty result that looks like a real answer.

    Args:
        to_stage: Stage moved INTO.
        from_stage: Stage moved OUT OF.
        opportunity_id: Restrict to one opportunity.
        changed_from: Window start, ISO local date-time "2026-08-01T00:00:00".
        changed_to: Window end, same format.
        page: Zero-based page number.
        size: Rows per page, default 50, capped at 200.
    """
    to_fixed = domain.normalise_stage(to_stage)
    from_fixed = domain.normalise_stage(from_stage)

    try:
        data = await crm.list_stage_history(
            toStage=to_fixed, fromStage=from_fixed, opportunityId=opportunity_id,
            changedFrom=changed_from, changedTo=changed_to, page=page, size=size,
        )
    except Exception as e:
        return api_error(e)

    rows = data.get("content") or []

    notes = []
    if to_fixed != to_stage:
        notes.append(f"corrected to_stage to '{to_fixed}' (en-dash)")
    if from_fixed != from_stage:
        notes.append(f"corrected from_stage to '{from_fixed}' (en-dash)")

    if not rows:
        msg = "No stage changes matched those filters."
        if notes:
            msg += " Filters applied: " + "; ".join(notes) + "."
        else:
            msg += (" If you filtered on a stage name, check it against "
                    "get_business_context — stage names use en-dashes and a "
                    "mismatch returns an empty result rather than an error.")
        return msg

    lines = [f"**Stage changes** ({data.get('totalElements', len(rows))} matching)"]
    if notes:
        lines.append(f"_Filters {'; '.join(notes)}_")
    lines.append("")

    for h in rows:
        lines.append(
            f"- {h.get('fromStage') or '(new)'} → **{h.get('toStage', '-')}** "
            f"at {h.get('changedAt', '-')}"
        )
        if h.get("company"):
            lines.append(f"    {h['company']} ({h.get('opportunityId', '-')})")
        elif h.get("opportunityId"):
            lines.append(f"    Opportunity: {h['opportunityId']}")

    lines += envelope_footer(data)
    return "\n".join(lines)


async def get_opportunity_stage_history(opportunity_id: str) -> str:
    """Get one opportunity's full stage history, oldest first, with time spent in
    each stage already computed.

    This is the reliable source for time-in-stage — better than diffing created and
    modified dates.

    Args:
        opportunity_id: The opportunity id (LSQ ProspectActivityId).
    """
    try:
        data = await crm.get_opportunity_stage_history(opportunity_id)
    except Exception as e:
        return api_error(e)

    history = data.get("history") or data.get("content") or []
    current = data.get("currentStage")

    if not history:
        return (f"No stage history recorded for opportunity {opportunity_id}"
                + (f" (current stage: {current})." if current else "."))

    lines = [f"**Stage history — {opportunity_id}**"]
    if current:
        lines.append(f"Current stage: **{current}**")
    lines.append("")

    for h in history:
        line = (f"- {h.get('fromStage') or '(new)'} → **{h.get('toStage', '-')}** "
                f"at {h.get('changedAt', '-')}")
        days = h.get("daysInStage")
        if days is not None:
            line += f" — held {days} days"
        lines.append(line)

    # The final row deliberately has no daysInStage: that stage is still open.
    # Computing now-minus-changedAt would present a live stage as a completed one.
    if history and history[-1].get("daysInStage") is None:
        lines += ["", "> The last entry has no duration because that stage is still "
                      "open. Its elapsed time is not a completed measurement — do "
                      "not compare it against the closed stages above."]

    return "\n".join(lines)
