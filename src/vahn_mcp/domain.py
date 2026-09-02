"""Authored LSQ domain model — semantics that cannot be derived from any API.

Two layers make up the business context exposed by `get_business_context`:

  1. This file — meanings, ordering, and policy. A human must maintain it;
     no endpoint can infer that fleet size is the proxy for deal importance,
     or that TORG means what it means.
  2. Live counts and rosters pulled from vahn-crm-service at call time.

Values below were read from production (crm-mcp.vahn.in) on 2026-09-02, so the
vocabulary is real. Items marked INFERRED are hypotheses that fit the data but
have NOT been confirmed by anyone at VAHN — they render with that caveat
attached. Confirm and delete the marker.
"""

from typing import Literal

# -- Closed enums (safe to enforce in tool signatures) --

Severity = Literal["medium", "high", "critical"]
Period = Literal["today", "this_week", "this_month", "last_week", "last_month"]
QualificationStatus = Literal["Qualified", "Not Qualified", "Closed"]
OpportunityStatus = Literal["Open", "Won", "Lost"]

# -- Opportunity pipeline --
# stage_rank comes from a SQL view in vahn-crm-service (surfaced as `stageRank`
# by get_opportunities_by_stage), which is the authoritative ordering. Mirrored
# here so the context tool can explain ordering without a round trip.

OPPORTUNITY_STAGES: list[dict] = [
    {"rank": 1, "name": "New Lead"},
    {"rank": 2, "name": "Contacted"},
    {"rank": 3, "name": "Qualified"},
    {"rank": 4, "name": "Demo Done"},
    {"rank": 5, "name": "Onboarded"},
    {"rank": 6, "name": "1st Transaction Done"},
    {"rank": 7, "name": "Paying Customer – Partial Fleet"},
    {"rank": 7, "name": "Paying Customer – Full Fleet"},
    {"rank": None, "name": "Closed - Lost", "is_lost": True},
]

# Two distinct stages share rank 7: a customer can be paying on part of their
# fleet or all of it. Partial -> Full is expansion, not pipeline progression.
TERMINAL_WON_STAGES = ["Paying Customer – Partial Fleet", "Paying Customer – Full Fleet"]

# 'Lost' is recorded in two places that can drift: opportunity_status = 'Lost'
# and opportunity_stage = 'Closed - Lost'. vahn-crm-service exposes a derived
# is_lost flag catching both; get_monitoring_opportunities_by_status uses it.
LOST_DRIFT_NOTE = (
    "Lost is stored twice — opportunity_status='Lost' and "
    "opportunity_stage='Closed - Lost' — and the two can disagree. Prefer "
    "get_monitoring_opportunities_by_status, which uses the derived is_lost "
    "flag covering both, over raw status filtering."
)

CONTACT_STAGES = ["Database", "Prospect", "Qualified", "Customer", "Closed", "Unknown"]

# -- Activity event codes --
# `advances_to` is INFERRED from name alignment with the stage list above, not
# confirmed. Nothing is known to advance a lead to either Paying Customer stage.

ACTIVITY_EVENTS: dict[str, dict] = {
    "200": {
        "name": "Customer Connect",
        "meaning": "First outbound touch logged against the lead.",
        "advances_to": "Contacted",
        "inferred": True,
    },
    "201": {
        "name": "Contacted - Lead Qualification",
        "meaning": "Qualification call. Sets qualification_status and an outcome.",
        "advances_to": "Qualified",
        "inferred": True,
    },
    "202": {
        "name": "UNKNOWN",
        "meaning": "Code 202 sits inside the used range but is absent from this "
                   "repo's docstrings and from the mcp-auth branch. Confirm with "
                   "the LSQ admin whether it is in use before emitting it.",
        "advances_to": None,
        "inferred": False,
    },
    "203": {
        "name": "Demo Done - Outcome",
        "meaning": "A product demo was delivered; records the demo outcome.",
        "advances_to": "Demo Done",
        "inferred": True,
    },
    "204": {
        "name": "Onboarded - Training",
        "meaning": "Customer onboarding/training session completed.",
        "advances_to": "Onboarded",
        "inferred": True,
    },
    "205": {
        "name": "First Transaction",
        "meaning": "Lead's first billable transaction.",
        "advances_to": "1st Transaction Done",
        "inferred": True,
    },
}

DEFAULT_ACTIVITY_EVENT = "201"

# -- AI call dispositions --
# Observed in production from elevenlabs_conversations. Not a closed set.

CALL_DISPOSITIONS_OBSERVED = [
    "INTERESTED",
    "NOT_INTERESTED",
    "NO_RESPONSE",
    "BUSY_CALL_BACK",
    "DISCONNECTED_CALL_BACK",
    "NOT_A_TRUCKING_BUSINESS",
]

# -- Risk and escalation definitions --

RISK_DEFINITIONS: dict[str, str] = {
    "silent drop": "An open opportunity with zero pending follow-up tasks — "
                   "nobody is scheduled to touch it. See get_leads_without_followup.",
    "escalation priority": "Stale opportunities ranked by fleet size, which is the "
                           "proxy for deal importance. See get_escalation_list.",
    "at-risk customer": "An open task marked 'Unsatisfied' against a contact already "
                        "at Paying Customer (Partial or Full Fleet) — a churn signal "
                        "on existing revenue. See get_at_risk_customers.",
}

# -- Glossary --
# UNANSWERED: these terms appear in tool docstrings and production data with no
# definition anywhere in the codebase. An empty string renders as "needs definition".

GLOSSARY: dict[str, str] = {
    "TORG": "",
    "Fuel Partner": "",
    "Database (contact stage)": "",
    "Closed (contact stage)": "",
    "Unknown (contact stage)": "",
    "Partial Fleet vs Full Fleet": "",
}

# -- Free-text fields with open value sets --

OPEN_VALUE_FIELDS: dict[str, list[str]] = {
    "qualified_outcome": ["Follow-up Required"],
    "not_qualified_outcome": ["Not Interested"],
    "type_of_connect": ["Phone call", "In Person Meet"],
}

# -- Thresholds --
# CONFLICT: the same words mean different numbers across tools. Until VAHN
# ratifies one set, the context tool reports each tool's own threshold rather
# than implying a single company SLA.

THRESHOLDS: list[dict] = [
    {"concept": "overdue severity: medium", "value": "< 24h past due",
     "tool": "list_overdue_followups"},
    {"concept": "overdue severity: high", "value": "24-72h past due",
     "tool": "list_overdue_followups"},
    {"concept": "overdue severity: critical", "value": "> 72h past due",
     "tool": "list_overdue_followups"},
    {"concept": "critically overdue task", "value": "7+ days past due",
     "tool": "get_critical_overdue_tasks"},
    {"concept": "stale opportunity", "value": "14+ days idle (default)",
     "tool": "list_stale_opportunities"},
    {"concept": "stale opportunity (monitoring)", "value": "30+ days idle (default)",
     "tool": "get_stale_opportunities_monitor"},
    {"concept": "escalation candidate", "value": "7+ days idle (default)",
     "tool": "get_escalation_list"},
]

THRESHOLD_CONFLICTS = [
    "'Critical' means two different things: >72h past due in "
    "list_overdue_followups severity, but 7+ days past due in "
    "get_critical_overdue_tasks. Always say which tool a critical count came from.",
    "'Stale' has three defaults — 7, 14 and 30 days idle — across "
    "get_escalation_list, list_stale_opportunities and "
    "get_stale_opportunities_monitor. None is a ratified company SLA. State the "
    "threshold whenever you report a stale count.",
]

DATA_QUALITY_NOTES = [
    "Lead status_code is effectively unpopulated in production: ~94% of leads "
    "are code '0' and the rest Unknown. get_leads_by_status_code cannot "
    "meaningfully segment anything — do not use it to answer questions about "
    "lead status; use contact stage instead.",
    "~6% of leads have contact stage 'Unknown', so contact-stage totals will "
    "not reconcile to the opportunity count.",
]
