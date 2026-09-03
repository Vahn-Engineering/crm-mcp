"""The activity-type cache. Every fetch occupies a slot in the shared LSQ queue."""

from tests.stub_service import Stub
from vahn_mcp import catalogue


async def test_second_read_is_served_from_cache():
    types, prov = await catalogue.get_activity_types()
    assert prov == "fetched live"
    before = len(Stub.calls)

    types2, prov2 = await catalogue.get_activity_types()
    assert types2 == types
    assert "cached" in prov2
    assert len(Stub.calls) == before, "a cached read must not touch the service"


async def test_a_failed_refresh_keeps_serving_the_good_copy():
    """Stale-but-labelled beats nothing, and beats the contradicted hardcoded list."""
    await catalogue.get_activity_types()
    Stub.set("/api/read/activity-types", "upstream down", status=502)

    types, prov = await catalogue.get_activity_types(force_refresh=True)
    assert types, "a failed refresh must not discard a working catalogue"
    assert "STALE" in prov
    assert catalogue.resolve_code(210) == "AI Bot Call"


async def test_cold_failure_returns_nothing_rather_than_guessing():
    Stub.set("/api/read/activity-types", "upstream down", status=502)
    types, prov = await catalogue.get_activity_types()
    assert types is None
    assert "unavailable" in prov


async def test_resolve_code_is_none_before_the_catalogue_loads():
    assert catalogue.resolve_code(210) is None


async def test_unknown_code_does_not_resolve():
    await catalogue.get_activity_types()
    assert catalogue.resolve_code(999) is None
