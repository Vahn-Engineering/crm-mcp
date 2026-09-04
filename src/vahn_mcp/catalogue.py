"""In-memory cache for the LeadSquared activity-type catalogue.

The catalogue only changes when someone edits activity configuration in LSQ, and
every read of it goes through vahn-crm-service's outbound queue. Fetching it once
per process instead of once per tool call keeps that queue free for the dialer.

Cached for the process lifetime with a TTL, and shared by every tool that needs
to resolve an event code — get_business_context, the activity tools, and any
future writer that needs to validate a code before posting.
"""

import asyncio
import time

from vahn_mcp.crm_client import crm

# The catalogue is edited by hand in LSQ, so it changes on the order of weeks.
# An hour is short enough that a same-day edit is picked up without a restart.
TTL_SECONDS = 3600

_lock = asyncio.Lock()
_cache: list | None = None
_fetched_at: float = 0.0
_last_error: str | None = None


async def get_activity_types(force_refresh: bool = False) -> tuple[list | None, str]:
    """Return (activity types, provenance). Never raises.

    A failed fetch does not clear a previously good catalogue — stale data with
    its age stated is more useful than nothing, and far better than falling back
    to the hardcoded codes, which the CRM API contract contradicts.
    """
    global _cache, _fetched_at, _last_error

    async with _lock:
        age = time.monotonic() - _fetched_at
        if _cache is not None and not force_refresh and age < TTL_SECONDS:
            return _cache, f"cached {int(age)}s ago"

        try:
            data = await crm.get_activity_types(event_type="custom")
            types = (data or {}).get("activityTypes") or None
            if types:
                _cache = types
                _fetched_at = time.monotonic()
                _last_error = None
                return _cache, "fetched live"
            _last_error = "catalogue returned no activity types"
        except Exception as e:
            _last_error = str(e)

        if _cache is not None:
            return _cache, (f"STALE, {int(age)}s old — refresh failed: "
                            f"{_last_error}")
        return None, f"unavailable: {_last_error}"


def invalidate() -> None:
    """Drop the cache, so the next read refetches."""
    global _cache, _fetched_at
    _cache, _fetched_at = None, 0.0


def resolve_code(code: int | str) -> str | None:
    """Look up an event name from the cached catalogue without a fetch.

    Returns None when the catalogue has not been loaded or the code is unknown —
    callers must not fall back to the hardcoded list, which is contradicted by
    the CRM API contract.
    """
    if _cache is None:
        return None
    target = str(code).strip()
    for t in _cache:
        if str(t.get("activityEvent")) == target:
            return t.get("eventName") or t.get("displayName")
    return None
