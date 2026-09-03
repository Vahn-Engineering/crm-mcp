"""Contract checks on the registered tool surface itself."""

import pytest

from vahn_mcp.server import mcp


@pytest.fixture(scope="module")
async def tools():
    return await mcp.list_tools()


async def test_context_tool_is_registered_first(tools):
    """Instructions tell the model to call it first; it should also lead the list."""
    assert tools[0].name == "get_business_context"


async def test_tool_names_are_unique(tools):
    names = [t.name for t in tools]
    assert len(names) == len(set(names))


async def test_every_tool_documents_itself(tools):
    """A tool with no description is unusable — the model cannot route to it."""
    undocumented = [t.name for t in tools if not (t.description or "").strip()]
    assert not undocumented


async def test_every_parameter_is_documented(tools):
    """An undocumented arg gets guessed at, and these filters fail silently.

    FastMCP lifts the docstring's Args: section into each property's own
    description, so that is where to look — not the tool summary.
    """
    missing = []
    for t in tools:
        for arg, schema in (t.parameters.get("properties") or {}).items():
            if not (schema.get("description") or "").strip():
                missing.append(f"{t.name}.{arg}")
    assert not missing, f"args with no description: {missing}"


async def test_enums_are_enforced_not_free_text(tools):
    """These were silently coerced before; the schema must reject bad values."""
    by_name = {t.name: t for t in tools}
    expected = {
        ("get_team_summary", "period"): {"today", "this_week", "this_month",
                                         "last_week", "last_month"},
        ("list_overdue_followups", "severity"): {"medium", "high", "critical"},
        ("log_activity", "qualification_status"): {"Qualified", "Not Qualified",
                                                   "Closed"},
    }
    for (tool, arg), values in expected.items():
        schema = by_name[tool].parameters["properties"][arg]
        found = set(schema.get("enum") or [])
        if not found:
            for branch in schema.get("anyOf", []):
                found |= set(branch.get("enum") or [])
        assert found == values, f"{tool}.{arg} lost its enum"


async def test_no_tool_reaches_leadsquared_directly():
    """All LSQ traffic must go through the service's shared rate limiter."""
    import pathlib
    src = pathlib.Path("src")
    offenders = [
        str(f) for f in src.rglob("*.py")
        if any(marker in f.read_text()
               for marker in ("LeadManagement.svc", "x-LSQ-", "lsq_client"))
    ]
    assert not offenders, f"direct LeadSquared access reintroduced in {offenders}"


async def test_routing_table_only_names_tools_that_exist(tools):
    """The instructions route the model between overlapping tools. If a tool is
    renamed or deleted, the table silently sends it somewhere that isn't there."""
    import re
    from vahn_mcp.server import mcp

    names = {t.name for t in tools}
    params = set()
    for t in tools:
        params |= set(t.parameters.get("properties") or {})

    referenced = set(re.findall(r"`([a-z][a-z0-9_]+)`", mcp.instructions))
    # Backticks also wrap argument names and field names; only judge the ones
    # that look like tool references — verb_noun with an underscore.
    candidates = {r for r in referenced if "_" in r and r not in params}
    unknown = candidates - names
    assert not unknown, f"instructions reference non-existent tools: {unknown}"


async def test_every_overlapping_cluster_is_routed(tools):
    """The clusters that caused ambiguity must each appear in the routing table."""
    from vahn_mcp.server import mcp
    must_route = [
        "list_overdue_followups", "get_critical_overdue_tasks", "search_tasks",
        "get_opportunities_by_stage", "get_pipeline_snapshot",
        "list_stale_opportunities", "get_stale_opportunities_monitor",
        "search_opportunities", "resolve_leads", "search_leads",
    ]
    missing = [t for t in must_route if f"`{t}`" not in mcp.instructions]
    assert not missing, f"overlapping tools with no routing guidance: {missing}"
