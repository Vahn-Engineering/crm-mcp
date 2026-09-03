"""Lead search over the paged record endpoint."""

from vahn_mcp.crm_client import crm
from vahn_mcp.tools._shared import api_error, envelope_footer


async def search_leads(
    company: str | None = None,
    phone: str | None = None,
    contact_type: str | None = None,
    contact_stage: str | None = None,
    source: str | None = None,
    owner_id: str | None = None,
    email: str | None = None,
    is_onboarded: bool | None = None,
    created_from: str | None = None,
    created_to: str | None = None,
    sort: str | None = None,
    page: int = 0,
    size: int = 50,
) -> str:
    """Search leads by company, phone, type, stage, source, owner or created date.

    To map a batch of phone numbers or names to leads, use resolve_leads instead —
    it answers per input and tells you which ones were ambiguous. This tool returns
    a flat page, so it cannot say which input produced which row.

    Args:
        company: Company name, case-insensitive substring — partial names work.
        phone: Phone number, matched on a trailing suffix across all 7 phone
            columns, so a local 10-digit number finds a +91-prefixed record.
        contact_type: e.g. "TORG" (truck owner/transporter) or "FUEL_PARTNER".
            Comma-separated list allowed, ORed.
        contact_stage: e.g. "Prospect", "Qualified", "Customer", "Closed".
            Comma-separated list allowed. Avoid "Database" and "Unknown" —
            get_business_context explains why those are bad data.
        source: Lead source, case-insensitive. Comma-separated list allowed.
        owner_id: LSQ user id, not a display name. Comma-separated list allowed.
        email: Exact, case-insensitive.
        is_onboarded: Filter to onboarded or not-yet-onboarded leads.
        created_from: ISO local date-time, e.g. "2026-08-01T00:00:00". A bare
            date is rejected — include the time.
        created_to: Same format.
        sort: "field" or "field,desc". Valid: createdAt, updatedAt, company,
            contactStage, contactType, source, lastTransactionDate,
            onboardingDate. A wrong field returns an error naming the valid ones.
        page: Zero-based page number.
        size: Rows per page, default 50, capped at 200 by the API.
    """
    try:
        data = await crm.list_leads(
            company=company, phone=phone, contactType=contact_type,
            contactStage=contact_stage, source=source, ownerId=owner_id,
            email=email, isOnboarded=is_onboarded, createdFrom=created_from,
            createdTo=created_to, sort=sort, page=page, size=size,
        )
    except Exception as e:
        return api_error(e)

    rows = data.get("content") or []
    if not rows:
        return "No leads matched those filters."

    lines = [f"**Leads** ({data.get('totalElements', len(rows))} matching)", ""]
    for c in rows:
        onboarded = " [Onboarded]" if c.get("isOnboarded") else ""
        lines.append(
            f"- **{c.get('company', 'Unknown')}** "
            f"({c.get('contactType', '-')}){onboarded}\n"
            f"  Phone: {c.get('phone', '-')}, Stage: {c.get('contactStage', '-')}, "
            f"City: {c.get('city', '-')}\n"
            f"  Prospect ID: {c.get('prospectId', '-')}"
        )

    lines += envelope_footer(data)
    return "\n".join(lines)
