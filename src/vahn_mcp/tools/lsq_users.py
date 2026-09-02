"""LeadSquared users list tool."""

from vahn_mcp.crm_client import crm


async def get_lsq_users() -> str:
    """Get a list of all LeadSquared users (sales reps).

    Returns user names and IDs — useful for looking up owner IDs
    when filtering other tools by rep.
    """
    data = await crm.get_lsq_users()
    users = data.get("users", [])

    if not users:
        return "No LSQ users found."

    lines = [f"**LeadSquared Users** ({len(users)} total)", ""]
    for u in users:
        email = f" ({u['email']})" if u.get("email") else ""
        lines.append(
            f"- **{u.get('name', 'Unknown')}**{email} — "
            f"ID: {u.get('userId', '-')}"
        )

    return "\n".join(lines)
