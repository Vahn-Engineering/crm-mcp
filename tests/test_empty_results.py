"""Every list tool must render an empty result as prose, not crash or emit a stub.

An empty page is the single most common response shape in this API — it is what
you get from a wrong filter as well as a genuinely quiet week.
"""

import pytest

from tests.stub_service import Stub, envelope
from vahn_mcp.tools import (
    call_queue, calls, records, resolve, stage_history, whatsapp,
)

EMPTY_CASES = [
    ("/api/read/tasks", lambda: records.search_tasks()),
    ("/api/read/opportunities", lambda: records.search_opportunities()),
    ("/api/read/calls", lambda: calls.search_calls()),
    ("/api/read/call-queue", lambda: call_queue.get_call_queue()),
    ("/api/read/whatsapp-events", lambda: whatsapp.search_whatsapp_events()),
    ("/api/read/stage-history", lambda: stage_history.get_stage_changes()),
]


@pytest.mark.parametrize("path,call", EMPTY_CASES, ids=[c[0] for c in EMPTY_CASES])
async def test_empty_page_renders_as_a_sentence(path, call):
    Stub.set(path, envelope([], total=0))
    out = await call()
    assert isinstance(out, str) and out.strip()
    assert "None" not in out, "a None leaked into user-facing text"
    assert "{" not in out, "raw structure leaked into user-facing text"
    assert len(out) < 500, "an empty result should be brief, not a full header"


async def test_resolve_with_no_input_asks_for_one():
    out = await resolve.resolve_leads()
    assert "Provide at least one" in out
    assert not Stub.calls, "must not call the service with an empty batch"


async def test_resolve_rejects_an_oversized_batch_before_calling():
    out = await resolve.resolve_leads(phones=[str(i) for i in range(101)])
    assert "over the 100 limit" in out
    assert not Stub.calls, "the size guard must run before the request"


async def test_service_unreachable_is_reported_not_raised(monkeypatch):
    from vahn_mcp.crm_client import crm
    monkeypatch.setattr(crm, "_base", "http://127.0.0.1:1")   # nothing listening
    out = await records.search_tasks()
    assert "Could not reach vahn-crm-service" in out
