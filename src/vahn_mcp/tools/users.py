"""User lookup — resolve a rep and see their workload."""

from vahn_mcp.crm_client import crm
from vahn_mcp.tools._shared import api_error


async def get_user(user_id_or_email: str) -> str:
    """Look up one rep by LSQ user id OR email address, with their current workload.

    Use this to resolve a rep before filtering on their name elsewhere — an
    unrecognised name returns an empty result that reads like "nothing assigned".

    Args:
        user_id_or_email: Either an LSQ user id or an email address; both work.
    """
    try:
        data = await crm.get_user(user_id_or_email)
    except Exception as e:
        return api_error(e)

    name = (data.get("name")
            or f"{data.get('firstName', '')} {data.get('lastName', '')}".strip()
            or "(unnamed)")
    lines = [
        f"**{name}**",
        f"  User ID: {data.get('userId') or data.get('id', '-')}",
        f"  Email: {data.get('emailAddress') or data.get('email', '-')}",
    ]

    workload = data.get("workload") or {}
    if workload:
        lines += ["", "**Workload**"]
        for k, v in workload.items():
            lines.append(f"  {k}: {v}")
        lines += [
            "",
            "> Task counts key off owner name while opportunity counts key off "
            "owner id — the two LeadSquared objects use different owner "
            "references. Overdue uses the same definition as every other tool "
            "(pending and past due), so those figures agree.",
        ]

    return "\n".join(lines)
