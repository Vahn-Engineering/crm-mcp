"""Shared rendering and error handling for the record-level read API."""

import httpx


def api_error(e: Exception, *, relay: bool = False) -> str:
    """Turn an HTTP failure into something the model can act on.

    A 400 from this API names every valid value in its body, so the text is
    surfaced verbatim rather than swallowed — a wrong `sort` field is meant to
    be self-correcting. The 502/503 split on relay endpoints distinguishes
    "LeadSquared is unhappy, retrying may work" from "this deployment cannot
    serve activities at all".
    """
    if isinstance(e, httpx.HTTPStatusError):
        code = e.response.status_code
        try:
            body = e.response.text[:600]
        except Exception:
            body = ""
        if code == 400:
            return f"Request rejected (400). The API says: {body}\nFix the request and retry."
        if code == 401:
            return "Not authorised (401) — the service key is missing or wrong. This is a deployment problem, not something to retry."
        if code == 404:
            return "No such record (404)."
        if relay and code == 502:
            return f"LeadSquared rejected or timed out (502). This is upstream, not our service — retry with backoff. {body}"
        if relay and code == 503:
            return "Activity reads are disabled in this environment (503, leadsquared.enabled=false). Do NOT retry — no activity data is available here at all. Say so rather than reporting zero activities."
        return f"Request failed ({code}). {body}"
    if isinstance(e, httpx.RequestError):
        return f"Could not reach vahn-crm-service: {e}"
    return f"Unexpected error: {e}"


def envelope_footer(data: dict) -> list[str]:
    """Render paging state so the model knows whether it saw everything."""
    total = data.get("totalElements")
    page = data.get("page", 0)
    size = data.get("size")
    has_next = data.get("hasNext")
    shown = len(data.get("content") or [])

    if total is None:
        return []

    line = f"Showing {shown} of {total} (page {page}, size {size})"
    if has_next:
        pages = data.get("totalPages")
        line += (f" — MORE RESULTS EXIST across {pages} pages. Request page="
                 f"{page + 1} to continue, and say you have not seen them all "
                 f"if you stop here.")
    return ["", line]
