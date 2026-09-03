"""Batch lead resolution — map phones, names or companies to CRM leads in one call."""

from vahn_mcp.crm_client import crm
from vahn_mcp.tools._shared import api_error

# The API caps a batch at 100 values across all three arrays.
MAX_BATCH = 100


async def resolve_leads(
    phones: list[str] | None = None,
    contact_names: list[str] | None = None,
    companies: list[str] | None = None,
) -> str:
    """Resolve a batch of phone numbers, contact names or company names to CRM leads —
    one result per input, told apart as matched, ambiguous, or not found.

    Use this whenever you have a list of identifiers and need the leads behind them:
    numbers from a call log, names from a transcript, a pasted column. It costs one
    database query no matter how many values you send, so never look values up one at
    a time.

    Feed the resolved prospect IDs into the record tools as a comma-separated list —
    `search_tasks(prospect_id="id1,id2,id3")` — to stay at two calls total.

    Args:
        phones: Phone numbers. Matched on a trailing suffix across all 7 phone
            columns, so local 10-digit form finds a +91-prefixed record.
        contact_names: Contact names. Exact after normalising case and spacing, so
            "ravi kumar" matches "Ravi Kumar" — but "Ravi K" does not. Not fuzzy.
        companies: Company names. Case-insensitive substring, so partial names work.
        Provide any combination; 100 values total across all three.
    """
    payload = {}
    if phones:
        payload["phones"] = phones
    if contact_names:
        payload["contactNames"] = contact_names
    if companies:
        payload["companies"] = companies

    if not payload:
        return "Provide at least one of phones, contact_names, or companies."

    total = sum(len(v) for v in payload.values())
    if total > MAX_BATCH:
        return (f"{total} values is over the {MAX_BATCH} limit for one batch. Split "
                f"it and call again — this is a resolve-a-handful endpoint, not an "
                f"export.")

    try:
        data = await crm.resolve_leads(payload)
    except Exception as e:
        return api_error(e)

    results = data.get("results") or []
    if not results:
        return "No results returned."

    lines = [
        f"**Resolved {data.get('requested', total)} inputs** — "
        f"{data.get('matched', 0)} matched, {data.get('ambiguous', 0)} ambiguous, "
        f"{data.get('notFound', 0)} not found",
        "",
    ]

    matched_ids, ambiguous, not_found = [], [], []

    for r in results:
        status = r.get("status")
        label = f"{r.get('inputType', '?')} `{r.get('input', '')}`"

        if status == "matched":
            lead = r.get("lead") or {}
            pid = lead.get("prospectId", "-")
            matched_ids.append(pid)
            lines.append(f"- **{label}** → {lead.get('company', 'Unknown')}  `{pid}`")
        elif status == "ambiguous":
            ambiguous.append(r)
            cands = r.get("candidates") or []
            lines.append(f"- **{label}** → AMBIGUOUS, "
                         f"{r.get('matchCount', len(cands))} leads match:")
            for c in cands:
                lines.append(f"    - {c.get('company', 'Unknown')}  "
                             f"`{c.get('prospectId', '-')}`")
            if r.get("candidatesTruncated"):
                lines.append("    - …more candidates not listed")
        else:
            not_found.append(r.get("input", ""))
            lines.append(f"- **{label}** → not found")

    if matched_ids:
        lines += [
            "",
            "**Unambiguous prospect IDs**, ready to pass as one comma-separated "
            "filter:",
            "",
            f"`{','.join(matched_ids)}`",
        ]

    # An ambiguous input genuinely does not resolve to one lead. Choosing for the
    # user — either silently — produces wrong tasks against a real company or
    # silently omits a lead they asked about. Both are worse than saying so.
    if ambiguous:
        lines += [
            "",
            f"> {len(ambiguous)} input(s) matched several leads and are NOT in the "
            f"list above. Do not pick one silently. Either ask which lead was meant, "
            f"or include every candidate and say the results cover all of them — "
            f"then tell the user which inputs were ambiguous either way.",
        ]

    if not_found:
        lines += [
            "",
            f"> {len(not_found)} input(s) matched no lead: "
            f"{', '.join(repr(x) for x in not_found[:10])}"
            + ("…" if len(not_found) > 10 else "")
            + ". Names must match exactly after case and spacing are normalised; "
              "try the company name as a substring instead.",
        ]

    return "\n".join(lines)
