"""AI bot call tools — local reads, richer than the LSQ activity-210 projection."""

from vahn_mcp.crm_client import crm
from vahn_mcp.tools._shared import api_error, envelope_footer


async def search_calls(
    disposition: str | None = None,
    sentiment: str | None = None,
    vendor: str | None = None,
    call_successful: bool | None = None,
    lsq_update_status: str | None = None,
    phone: str | None = None,
    follow_up_required: bool | None = None,
    min_duration_secs: int | None = None,
    start_from: str | None = None,
    start_to: str | None = None,
    include_lead: bool = False,
    page: int = 0,
    size: int = 50,
) -> str:
    """Search AI bot call records — outcomes, sentiment, duration, transcript summary.

    Local read, and considerably richer than the LeadSquared activity record for the
    same calls. Use this for anything about call content or outcomes. For aggregate
    dispositions only, get_call_outcome_breakdown is one call instead of paging.

    Args:
        disposition: Business outcome, e.g. "Interested", "Not Interested".
        sentiment: "positive", "neutral", or "negative".
        vendor: "ELEVENLABS" or "SARVAM". Case-insensitive.
        call_successful: The vendor's own technical verdict. Distinct from
            disposition — a call can connect cleanly and still go badly
            commercially, so do not treat this as a business outcome.
        lsq_update_status: "pending", "success", or "failed". Use "failed" to find
            calls whose outcome never reached the CRM.
        phone: Phone number; matches on a trailing suffix, so a local 10-digit
            number finds a +91-prefixed record.
        follow_up_required: Tri-state — false excludes unknowns rather than
            treating them as false.
        min_duration_secs: Inclusive floor. Useful for excluding instant disconnects.
        start_from: Window start on call start time, ISO "2026-08-01T00:00:00".
        start_to: Window end, same format.
        include_lead: Attach the resolved lead to each row. Costs one extra query
            per distinct phone number on the page, so leave it off for analytics
            and turn it on only when you need names.
        page: Zero-based page number.
        size: Rows per page, default 50, capped at 200.
    """
    try:
        data = await crm.list_calls(
            disposition=disposition, sentiment=sentiment, vendor=vendor,
            callSuccessful=call_successful, lsqUpdateStatus=lsq_update_status,
            phone=phone, followUpRequired=follow_up_required,
            minDurationSecs=min_duration_secs, startFrom=start_from,
            startTo=start_to, includeLead=include_lead or None,
            page=page, size=size,
        )
    except Exception as e:
        return api_error(e)

    rows = data.get("content") or []
    if not rows:
        return "No calls matched those filters."

    lines = [f"**Calls** ({data.get('totalElements', len(rows))} matching)", ""]
    ambiguous_seen = False
    for c in rows:
        head = (f"- **{c.get('disposition', 'No disposition')}** — "
                f"{c.get('startTime', '-')}, {c.get('callDurationSecs', 0)}s")
        if c.get("sentiment"):
            head += f", {c['sentiment']}"
        if c.get("vendor"):
            head += f" [{c['vendor']}]"
        lines.append(head)

        lead = c.get("lead")
        if lead:
            lines.append(f"    Lead: {lead.get('company', '-')} "
                         f"({lead.get('prospectId', '-')})")
        if c.get("ambiguous"):
            ambiguous_seen = True
            lines.append(f"    Phone matches {c.get('matchCount', '?')} contacts — "
                         f"lead attribution is a hint, not a fact")
        if c.get("lsqUpdateStatus") == "failed":
            lines.append("    Outcome never reached the CRM (lsqUpdateStatus=failed)")
        if c.get("transcriptSummary"):
            lines.append(f"    {c['transcriptSummary'][:200]}")

    if ambiguous_seen:
        lines += ["", "> Call records have no lead foreign key — leads are matched "
                      "by phone at read time. Where a number appears on several "
                      "contacts the match is flagged above; do not attribute those "
                      "calls to a specific company without confirming."]

    lines += envelope_footer(data)
    lines += ["", "> Full transcript, evaluation results and raw payload are not in "
                  "this listing — fetch a single call with get_call_details for those."]
    return "\n".join(lines)


async def get_call_details(conversation_id: str) -> str:
    """Get one AI bot call in full: qualification answers, evaluation results, and
    the resolved lead.

    Args:
        conversation_id: The call's conversation id.
    """
    try:
        data = await crm.get_call(conversation_id)
    except Exception as e:
        return api_error(e)

    lines = [
        f"**Call {conversation_id}**",
        f"  Started: {data.get('startTime', '-')}, "
        f"{data.get('callDurationSecs', 0)}s",
        f"  Disposition: {data.get('disposition', '-')}",
        f"  Sentiment: {data.get('sentiment', '-')}",
        f"  Vendor verdict (technical): {data.get('callSuccessful', '-')}",
        f"  Reached CRM: {data.get('lsqUpdateStatus', '-')}",
    ]

    lead = data.get("lead")
    if lead:
        lines += ["", "**Lead**",
                  f"  {lead.get('company', '-')} ({lead.get('prospectId', '-')})",
                  f"  Phone: {lead.get('phone', '-')}"]
        if data.get("ambiguous"):
            lines.append(f"  Phone matches {data.get('matchCount', '?')} contacts — "
                         f"treat this attribution as unconfirmed")

    qual = data.get("qualification") or {}
    if qual:
        lines += ["", "**Qualification captured on the call**"]
        for k, v in qual.items():
            if v not in (None, "", []):
                lines.append(f"  {k}: {v}")

    if data.get("transcriptSummary"):
        lines += ["", "**Summary**", f"  {data['transcriptSummary']}"]

    evals = data.get("evaluationResults")
    if evals:
        lines += ["", "**Evaluation results**", f"  {str(evals)[:800]}"]

    return "\n".join(lines)
