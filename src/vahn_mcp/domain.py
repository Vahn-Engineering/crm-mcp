"""Authored LSQ domain model — semantics that cannot be derived from any API.

Two layers make up the business context exposed by `get_business_context`:

  1. This file — meanings, ordering, and policy a human must maintain.
  2. Live data pulled from vahn-crm-service at call time: the stage list with
     ranks, status counts, the rep roster, and (once the endpoint ships) the
     activity catalogue.

Vocabulary was read from production on 2026-09-02. Business definitions were
confirmed by VAHN on 2026-09-02 except where marked OPEN.
"""

from typing import Literal

# -- Closed enums (enforced in tool signatures) --

Severity = Literal["medium", "high", "critical"]
Period = Literal["today", "this_week", "this_month", "last_week", "last_month"]
QualificationStatus = Literal["Qualified", "Not Qualified", "Closed"]
OpportunityStatus = Literal["Open", "Won", "Lost"]

# -- Opportunity pipeline --
# Fallback only. get_opportunities_by_stage returns stageRank from a SQL view,
# which is authoritative; this list is used when the service is unreachable.

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

# CONFIRMED: the Partial/Full split is decided by the subscription payment the
# customer has made — partial or full — not by truck count or contract type.
FLEET_SPLIT_NOTE = (
    "Partial vs Full Fleet reflects the subscription payment made: a customer "
    "paying for part of their fleet sits at Partial, one paying for all of it at "
    "Full. Both are rank 7, so Partial → Full is revenue expansion, not pipeline "
    "progression."
)

# CONFIRMED: both Paying Customer stages are set by hand by sales users in LSQ.
# No activity or automation drives them, so they lag reality by however long it
# takes a rep to update the record.
MANUAL_STAGE_NOTE = (
    "Both Paying Customer stages are marked manually by sales users in LSQ. "
    "Nothing automatic moves an opportunity into them, so treat the count as "
    "'what reps have recorded', not 'who is actually paying'. A subscription "
    "that started yesterday may not be reflected yet."
)

# 'Lost' is recorded in two places that can drift: opportunity_status = 'Lost'
# and opportunity_stage = 'Closed - Lost'. vahn-crm-service exposes a derived
# is_lost flag catching both.
LOST_DRIFT_NOTE = (
    "Lost is stored twice — opportunity_status='Lost' and "
    "opportunity_stage='Closed - Lost' — and the two can disagree. Prefer "
    "get_monitoring_opportunities_by_status, which uses the derived is_lost "
    "flag covering both, over raw status filtering."
)

# -- Contact stages --
# CONFIRMED: 'Database' and 'Unknown' are bad data, not meaningful stages.

CONTACT_STAGES = ["Prospect", "Qualified", "Customer", "Closed"]
CONTACT_STAGES_INVALID = ["Database", "Unknown"]
CONTACT_STAGE_NOTE = (
    "'Database' (119 leads) and 'Unknown' (577) are incorrect data, not real "
    "stages. Exclude them from any breakdown you present, and never describe a "
    "lead as being 'in the Database stage'. They are why contact-stage totals "
    "do not reconcile against the opportunity count."
)

# -- Activity event codes --
# Fallback only. An activity catalogue endpoint is being added to
# vahn-crm-service; once live it is authoritative and this list is a stopgap.
# Code 202 is deliberately absent — it was never documented and the catalogue
# will settle whether it exists.

ACTIVITY_EVENTS_FALLBACK: dict[str, str] = {
    "200": "Customer Connect",
    "201": "Contacted - Lead Qualification",
    "203": "Demo Done - Outcome",
    "204": "Onboarded - Training",
    "205": "First Transaction",
}

DEFAULT_ACTIVITY_EVENT = "201"

# CONFIRMED: stage changes are driven by automations configured inside LSQ,
# keyed on the activity. The mapping lives in LSQ automation config, not here
# and not in vahn-crm-service — so no code→stage table in this repo could be
# trusted. Deliberately not modelled.
ACTIVITY_AUTOMATION_NOTE = (
    "Logging an activity can move an opportunity's stage, but only where an LSQ "
    "automation is configured for that activity. The mapping lives in LSQ "
    "automation config, which this server cannot read, and it can be changed "
    "without any code change here. So: never predict which stage an activity "
    "will produce, and never report that a lead advanced because you logged "
    "one. Re-read the opportunity afterwards to see what actually happened."
)

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

# OPEN: no strategic-account threshold is defined yet. 30 trucks has been
# discussed as a candidate but is NOT in force — do not apply it.
STRATEGIC_ACCOUNT_NOTE = (
    "VAHN has no agreed fleet-size threshold for a 'strategic' or 'key' account "
    "yet. Do not invent one, and do not treat any particular truck count as "
    "significant. get_escalation_list ranks by raw fleet size only."
)

# -- Glossary --

GLOSSARY: dict[str, str] = {
    "TORG": "Truck Owner / Transporter — the core customer type: an operator who "
            "owns or runs trucks.",
    "Fuel Partner": "",  # OPEN — still undefined
    "Partial Fleet": "Customer subscribing and paying for part of their fleet.",
    "Full Fleet": "Customer subscribing and paying for their entire fleet.",
}

# -- Free-text fields with open value sets --
# OPEN: full picklists not yet supplied. The activity catalogue endpoint may
# cover these; until then only the values below are attested.

OPEN_VALUE_FIELDS: dict[str, list[str]] = {
    "qualified_outcome": ["Follow-up Required"],
    "not_qualified_outcome": ["Not Interested"],
    "type_of_connect": ["Phone call", "In Person Meet"],
}

# -- Thresholds --
# CONFIRMED: 'critical' means 7+ days overdue. The severity bands in
# list_overdue_followups are a finer scale whose top band is also labelled
# 'critical' at >72h — that label is misaligned with the company definition and
# should be renamed service-side. Until then, both are reported with their source.

CRITICAL_DEFINITION = "7+ days overdue"

THRESHOLDS: list[dict] = [
    {"concept": "critical (company definition)", "value": "7+ days overdue",
     "tool": "get_critical_overdue_tasks", "confirmed": True},
    {"concept": "severity band: medium", "value": "< 24h past due",
     "tool": "list_overdue_followups", "confirmed": False},
    {"concept": "severity band: high", "value": "24-72h past due",
     "tool": "list_overdue_followups", "confirmed": False},
    {"concept": "severity band: critical", "value": "> 72h past due",
     "tool": "list_overdue_followups", "confirmed": False},
    {"concept": "stale: escalation sweep", "value": "7+ days idle",
     "tool": "get_escalation_list", "confirmed": True},
    {"concept": "stale: rep-facing", "value": "14+ days idle",
     "tool": "list_stale_opportunities", "confirmed": True},
    {"concept": "stale: manager monitoring", "value": "30+ days idle",
     "tool": "get_stale_opportunities_monitor", "confirmed": True},
]

# CONFIRMED: the three stale thresholds are intentional and serve different
# audiences. Not a conflict — but still must be labelled in output.
STALE_NOTE = (
    "The 7 / 14 / 30-day stale thresholds are intentional and serve different "
    "audiences: 7 for the escalation sweep, 14 rep-facing, 30 for manager "
    "monitoring. Always say which threshold a stale count used, so a number is "
    "never ambiguous."
)

SEVERITY_MISMATCH_NOTE = (
    "VAHN defines critical as 7+ days overdue. The top severity band in "
    "list_overdue_followups is also called 'critical' but triggers at >72h "
    "(3 days), so it over-reports by the company definition. When quoting a "
    "critical count, use get_critical_overdue_tasks, or say explicitly that the "
    "severity band uses a lower bar."
)

# -- Data quality --

DATA_QUALITY_NOTES = [
    "Lead status_code reads ~94% '0' because the wrong column is being read — "
    "the field is not genuinely empty. Until vahn-crm-service is corrected, "
    "get_leads_by_status_code returns meaningless buckets: do not use it to "
    "answer questions about lead status, and use contact stage instead.",
    CONTACT_STAGE_NOTE,
]
