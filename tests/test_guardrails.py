"""Every test here pins a way this API returns a wrong answer instead of an error.

If one of these fails, the server has gone back to reporting something false with
confidence — which is worse than reporting nothing.
"""

import pytest

from tests.stub_service import Stub, envelope
from vahn_mcp.tools import activities, calls, records, resolve, stage_history, timeline


# -- Paging: a partial page must never read as the whole set --

@pytest.mark.asyncio
async def test_more_pages_are_announced():
    Stub.set("/api/read/tasks", envelope(
        [{"taskId": "t1", "subject": "A", "status": "Pending", "dueDate": "2026-09-01",
          "ownerName": "Ravi", "prospectId": "p1"}],
        size=50, total=412))
    out = await records.search_tasks()
    assert "MORE RESULTS EXIST" in out
    assert "page=1" in out, "must name the next page, not just hint at one"


@pytest.mark.asyncio
async def test_single_page_makes_no_paging_claim():
    Stub.set("/api/read/tasks", envelope(
        [{"taskId": "t1", "subject": "A", "status": "Pending", "prospectId": "p1"}],
        total=1))
    out = await records.search_tasks()
    assert "MORE RESULTS EXIST" not in out


# -- En-dash: a hyphen silently matches nothing --

@pytest.mark.asyncio
async def test_hyphen_in_stage_is_repaired_and_disclosed():
    Stub.set("/api/read/opportunities", envelope(
        [{"opportunityId": "o1", "stage": "Paying Customer – Full Fleet",
          "status": "Won", "company": "Acme", "prospectId": "p1"}], total=1))
    out = await records.search_opportunities(stage="Paying Customer - Full Fleet")
    assert "Corrected stage filter" in out
    sent = [c for c in Stub.calls if "/api/read/opportunities?" in c]
    assert sent and "%E2%80%93" in sent[0], "en-dash must reach the API url-encoded"


@pytest.mark.asyncio
async def test_empty_stage_result_warns_about_the_name():
    Stub.set("/api/read/opportunities", envelope([], total=0))
    out = await records.search_opportunities(stage="Nonexistent Stage")
    assert "get_business_context" in out, "an empty page must not look authoritative"


# -- Ambiguity must be surfaced, never resolved silently --

@pytest.mark.asyncio
async def test_ambiguous_phone_is_excluded_from_the_id_list():
    Stub.set("/api/read/leads/resolve", {
        "requested": 2, "matched": 1, "ambiguous": 1, "notFound": 0,
        "results": [
            {"inputType": "phone", "input": "111", "status": "matched",
             "lead": {"prospectId": "p-good", "company": "Acme"}},
            {"inputType": "phone", "input": "222", "status": "ambiguous",
             "matchCount": 2, "candidates": [
                 {"prospectId": "p-dup-1", "company": "A"},
                 {"prospectId": "p-dup-2", "company": "B"}]},
        ]})
    out = await resolve.resolve_leads(phones=["111", "222"])
    assert "`p-good`" in out
    assert "p-dup-1,p-dup-2" not in out, "ambiguous ids must not be silently batched"
    assert "Do not pick one silently" in out


@pytest.mark.asyncio
async def test_ambiguous_call_match_is_flagged_as_a_hint():
    Stub.set("/api/read/calls", envelope([
        {"conversationId": "c1", "disposition": "Interested",
         "startTime": "2026-09-01T10:00:00", "callDurationSecs": 60,
         "ambiguous": True, "matchCount": 3,
         "lead": {"company": "Maybe Transports", "prospectId": "p9"}}], total=1))
    out = await calls.search_calls()
    assert "hint, not a fact" in out


# -- LSQ relay failures: 503 must not read as "zero activities" --

@pytest.mark.asyncio
async def test_activities_503_is_not_reported_as_no_activities():
    Stub.set("/api/read/activities", "leadsquared.enabled=false", status=503)
    out = await activities.get_lead_activities("p1")
    assert "disabled in this environment" in out
    assert "Do NOT retry" in out
    assert "no activities" not in out.lower().replace("reporting zero activities", "")


@pytest.mark.asyncio
async def test_activities_502_is_marked_retryable():
    Stub.set("/api/read/activities", "LSQ timed out", status=502)
    out = await activities.get_lead_activities("p1")
    assert "retry with backoff" in out


# -- 400 bodies name the valid values, so they must survive to the model --

@pytest.mark.asyncio
async def test_400_body_is_passed_through_verbatim():
    Stub.set("/api/read/opportunities",
             "Invalid sort field 'bogus'. Valid: createdOn, modifiedOn, stage",
             status=400)
    out = await records.search_opportunities(sort="bogus")
    assert "Valid: createdOn, modifiedOn, stage" in out


# -- Timeline: a missing half must not read as "never contacted" --

@pytest.mark.asyncio
async def test_timeline_partial_failure_is_surfaced_before_the_history():
    Stub.set("/api/read/leads/p1/timeline", {
        "contact": {"company": "Acme"},
        "warnings": ["activity source unavailable"],
        "entries": [{"source": "task", "timestamp": "2026-09-01", "id": "t1",
                     "title": "Call back"}]})
    out = await timeline.get_lead_timeline(prospect_id="p1")
    assert "INCOMPLETE" in out
    assert out.index("INCOMPLETE") < out.index("**History**"), \
        "the warning must appear before the history it undermines"
    assert "Do not conclude there was no contact" in out


# -- Stage history: the open stage has no duration --

@pytest.mark.asyncio
async def test_open_stage_has_no_duration_and_says_why():
    Stub.set("/api/read/opportunities/o1/stage-history", {
        "currentStage": "Qualified",
        "history": [
            {"fromStage": None, "toStage": "New Lead",
             "changedAt": "2026-06-01T00:00:00", "daysInStage": 9},
            {"fromStage": "New Lead", "toStage": "Qualified",
             "changedAt": "2026-06-10T00:00:00"},
        ]})
    out = await stage_history.get_opportunity_stage_history("o1")
    assert "held 9 days" in out
    assert "still open" in out


# -- Tasks whose lead was never mirrored are invisible to prospect filters --

@pytest.mark.asyncio
async def test_orphan_tasks_are_counted_and_explained():
    Stub.set("/api/read/tasks", envelope([
        {"taskId": "t1", "subject": "Has lead", "status": "Pending",
         "prospectId": "p1", "company": "Acme"},
        {"taskId": "t2", "subject": "Orphan", "status": "Pending",
         "ownerEmail": "x@vahn.in"}], total=2))
    out = await records.search_tasks()
    assert "1 task(s) above have no lead attached" in out


# -- Activity codes: never fall back to the contradicted hardcoded list --

@pytest.mark.asyncio
async def test_catalogue_failure_forbids_guessing_a_code():
    Stub.set("/api/read/activity-types", "boom", status=502)
    out = await activities.get_activity_types()
    assert "Do not fall back to codes" in out
    assert "200" not in out, "the contradicted hardcoded codes must not appear"


@pytest.mark.asyncio
async def test_cross_lead_rows_resolve_names_from_the_catalogue():
    """LSQ omits eventName in cross-lead mode; a bare code is unreadable."""
    await activities.get_activity_types()          # prime the cache
    Stub.set("/api/read/activities", envelope([
        {"activityId": "a1", "eventCode": 210, "eventName": None,
         "createdOn": "2026-08-20 09:12:00", "prospectId": "p1"}], total=1))
    out = await activities.list_activities_by_type(
        210, "2026-08-01T00:00:00", "2026-09-01T00:00:00")
    assert "AI Bot Call" in out
    assert "(code 210)" not in out


# -- Resolving a name to a lead must not pick one of several matches --

@pytest.mark.asyncio
async def test_timeline_refuses_to_guess_between_matching_leads():
    Stub.set("/api/read/leads/resolve", {
        "requested": 1, "matched": 0, "ambiguous": 1, "notFound": 0,
        "results": [{"inputType": "company", "input": "Sharma", "status": "ambiguous",
                     "matchCount": 2, "candidates": [
                         {"prospectId": "p1", "company": "Sharma Transports"},
                         {"prospectId": "p2", "company": "Sharma Logistics"}]}]})
    out = await timeline.get_lead_timeline(lead_name="Sharma")
    assert "matches 2 leads" in out
    assert "Sharma Transports" in out and "Sharma Logistics" in out
    assert "**History**" not in out, "must not render one lead's timeline as the answer"


@pytest.mark.asyncio
async def test_timeline_reports_an_unmatched_name_plainly():
    Stub.set("/api/read/leads/resolve", {
        "requested": 1, "matched": 0, "ambiguous": 0, "notFound": 1,
        "results": [{"inputType": "company", "input": "Nobody",
                     "status": "not_found"}]})
    out = await timeline.get_lead_timeline(lead_name="Nobody")
    assert "No lead found matching 'Nobody'" in out
