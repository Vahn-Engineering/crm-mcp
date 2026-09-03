"""Unit tests for the authored domain layer."""

import pytest

from vahn_mcp import domain


@pytest.mark.parametrize("given,expected", [
    ("Paying Customer - Full Fleet", "Paying Customer – Full Fleet"),
    ("paying customer – partial fleet", "Paying Customer – Partial Fleet"),
    ("  PAYING   CUSTOMER - FULL FLEET  ", "Paying Customer – Full Fleet"),
    # 'Closed - Lost' genuinely uses a hyphen — repairing it would break it.
    ("Closed - Lost", "Closed - Lost"),
    ("New Lead", "New Lead"),
    # Unknown values pass through: the API stays the authority on validity.
    ("Nonsense Stage", "Nonsense Stage"),
    (None, None),
    ("", ""),
])
def test_normalise_stage(given, expected):
    assert domain.normalise_stage(given) == expected


def test_normalise_stage_handles_multi_value_lists():
    """Categorical filters accept comma-separated lists; each part needs fixing."""
    out = domain.normalise_stage("Paying Customer - Full Fleet,Qualified")
    assert out == "Paying Customer – Full Fleet,Qualified"


def test_pipeline_ranks_are_ordered_and_lost_is_unranked():
    ranked = [s for s in domain.OPPORTUNITY_STAGES if s["rank"]]
    assert [s["rank"] for s in ranked] == sorted(s["rank"] for s in ranked)
    lost = [s for s in domain.OPPORTUNITY_STAGES if s.get("is_lost")]
    assert lost and all(s["rank"] is None for s in lost)


def test_both_paying_customer_stages_share_rank_seven():
    """Partial -> Full is revenue expansion, not pipeline progression."""
    paying = [s for s in domain.OPPORTUNITY_STAGES if "Paying Customer" in s["name"]]
    assert len(paying) == 2
    assert {s["rank"] for s in paying} == {7}


def test_bad_contact_stages_are_excluded_from_the_valid_list():
    assert not set(domain.CONTACT_STAGES) & set(domain.CONTACT_STAGES_INVALID)
