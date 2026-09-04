"""Call queue tool — explains why a lead has or hasn't been called."""

from vahn_mcp.crm_client import crm
from vahn_mcp.tools._shared import api_error, envelope_footer


async def get_call_queue(
    status: str | None = None,
    campaign: str | None = None,
    prospect_id: str | None = None,
    phone: str | None = None,
    locked: bool | None = None,
    due_now: bool | None = None,
    min_attempts: int | None = None,
    next_attempt_from: str | None = None,
    next_attempt_to: str | None = None,
    page: int = 0,
    size: int = 50,
) -> str:
    """Inspect the dialer queue — the only thing that explains a lead with no call
    record. A lead may be pending with a future attempt time, exhausted after
    repeated failures, or locked by a worker mid-dial.

    Results are ordered by next attempt time ascending by default, which is the
    order the dialer will actually work them.

    Read-only: requeue and cancel live behind a separate admin route, so nothing
    here can move the dialer.

    Args:
        status: "pending", "in_progress", "exhausted", etc.
        campaign: e.g. "whatsapp_click", "cold_outreach".
        prospect_id: Filter to one lead.
        phone: Trailing-suffix match, so a 10-digit number finds a +91 record.
        locked: Tri-state. true = held by a worker right now, false = free rows.
        due_now: Shorthand for "next attempt is in the past". Combine with
            locked=false to answer "what is the dialer behind on right now".
            An explicit next_attempt_to wins over this and is never widened.
        min_attempts: Inclusive floor on total attempts.
        next_attempt_from: Window start on next attempt time, ISO date-time.
        next_attempt_to: Window end, same format.
        page: Zero-based page number.
        size: Rows per page, default 50, capped at 200.
    """
    try:
        data = await crm.list_call_queue(
            status=status, campaign=campaign, prospectId=prospect_id,
            phone=phone, locked=locked, dueNow=due_now,
            minAttempts=min_attempts, nextAttemptFrom=next_attempt_from,
            nextAttemptTo=next_attempt_to, page=page, size=size,
        )
    except Exception as e:
        return api_error(e)

    rows = data.get("content") or []
    if not rows:
        return "Nothing in the call queue matched those filters."

    lines = [f"**Call queue** ({data.get('totalElements', len(rows))} matching)", ""]
    for q in rows:
        head = (f"- **{q.get('status', '-')}** — next attempt "
                f"{q.get('nextAttemptAt', '-')}, {q.get('attemptCount', 0)} attempts")
        if q.get("campaign"):
            head += f" [{q['campaign']}]"
        lines.append(head)

        if q.get("company") or q.get("prospectId"):
            lines.append(f"    Lead: {q.get('company', '-')} "
                         f"({q.get('prospectId', '-')})")
        if q.get("locked"):
            lines.append("    Locked by a worker right now — mid-dial")
        if q.get("terminalReason"):
            lines.append(f"    Stopped: {q['terminalReason']}")

        # Retry counters are reported per reason on purpose: the queue backs off
        # differently for a no-answer than for an initiation failure, so the
        # breakdown carries information the total does not.
        retries = q.get("retryCounts") or {}
        parts = [f"{k}: {v}" for k, v in retries.items() if v]
        if parts:
            lines.append(f"    Retries — {', '.join(parts)}")

    lines += envelope_footer(data)
    lines += ["", "> Retry counters are broken out by reason because the queue backs "
                  "off differently for each: three no-answers and three initiation "
                  "failures mean different things."]
    return "\n".join(lines)
