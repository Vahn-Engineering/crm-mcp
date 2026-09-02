"""Lead search tool."""

from vahn_mcp.crm_client import crm


async def search_leads(
    contact_type: str | None = None,
    stage: str | None = None,
    phone: str | None = None,
    company: str | None = None,
    limit: int = 20,
) -> str:
    """Search for leads/contacts by type, stage, phone, or company name.

    Args:
        contact_type: Filter by type (e.g. "TORG", "Fuel Partner").
        stage: Filter by contact stage (e.g. "Prospect").
        phone: Search by phone number (partial match across all phone fields).
        company: Search by company name (partial match).
        limit: Max results (default 20).
    """
    data = await crm.search_leads(
        contact_type=contact_type,
        stage=stage,
        phone=phone,
        company=company,
        limit=limit,
    )

    contacts = data.get("contacts", [])
    if not contacts:
        return "No leads found matching your criteria."

    lines = [
        f"**{data['total']} leads found** (showing {data['returned']})",
        "",
    ]

    for c in contacts:
        onboarded = " [Onboarded]" if c.get("isOnboarded") else ""
        lines.append(
            f"- **{c.get('company', 'Unknown')}** ({c.get('contactType', '-')}){onboarded}\n"
            f"  Phone: {c.get('phone', '-')}, Stage: {c.get('contactStage', '-')}, "
            f"City: {c.get('city', '-')}\n"
            f"  Prospect ID: {c.get('prospectId', '-')}"
        )

    return "\n".join(lines)
