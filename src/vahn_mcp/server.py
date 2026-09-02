"""VAHN Sales Monitoring MCP Server."""

from fastmcp import FastMCP
from fastmcp.server.auth.providers.in_memory import InMemoryOAuthProvider
from mcp.server.auth import routes as _auth_routes
from mcp.server.auth.routes import ClientRegistrationOptions
from mcp.shared.auth import OAuthClientInformationFull

from vahn_mcp.config import settings

# Patch metadata builder to advertise "none" auth method (public PKCE clients).
_original_build_metadata = _auth_routes.build_metadata


def _patched_build_metadata(*args, **kwargs):
    metadata = _original_build_metadata(*args, **kwargs)
    metadata.token_endpoint_auth_methods_supported = [
        "none", "client_secret_post", "client_secret_basic",
    ]
    return metadata


_auth_routes.build_metadata = _patched_build_metadata

from vahn_mcp.tools.context import get_business_context
from vahn_mcp.tools.followups import list_overdue_followups
from vahn_mcp.tools.scorecard import get_rep_scorecard
from vahn_mcp.tools.opportunities import list_stale_opportunities, get_pipeline_snapshot
from vahn_mcp.tools.timeline import get_lead_timeline
from vahn_mcp.tools.team import get_team_summary
from vahn_mcp.tools.search import search_leads
from vahn_mcp.tools.write import create_followup_task, log_activity, get_lead_details_from_lsq
# from vahn_mcp.tools.lsq_users import get_lsq_users  # endpoint not live yet
from vahn_mcp.tools.reporting import (
    get_opportunities_by_status,
    get_opportunities_by_stage,
    get_leads_by_contact_stage,
    get_leads_by_status_code,
)
from vahn_mcp.tools.escalation import (
    get_leads_without_followup,
    get_escalation_list,
    get_at_risk_customers,
)
from vahn_mcp.tools.leads import get_new_leads_count, get_new_leads_by_source
from vahn_mcp.tools.tasks import get_tasks_due_today, get_task_completion_rate
from vahn_mcp.tools.performance import (
    get_new_opportunities_count,
    get_won_opportunities,
    get_workload_distribution,
    get_call_outcome_breakdown,
)
from vahn_mcp.tools.monitoring import (
    get_critical_overdue_tasks,
    get_overdue_tasks_summary,
    get_monitoring_opportunities_by_status,
    get_stale_opportunities_monitor,
    get_opportunities_open_since,
    get_opportunities_summary,
)

auth = InMemoryOAuthProvider(
    base_url=settings.mcp_base_url,
    client_registration_options=ClientRegistrationOptions(enabled=True),
)

# Pre-register a static OAuth client so it survives server restarts.
# Use this client_id in Claude Team connector settings.
CLAUDE_CLIENT_ID = "vahn-mcp-claude"
auth.clients[CLAUDE_CLIENT_ID] = OAuthClientInformationFull(
    client_id=CLAUDE_CLIENT_ID,
    client_name="Claude",
    redirect_uris=[
        "https://claude.ai/api/mcp/auth_callback",
        "https://claude.ai/oauth/callback",
    ],
    grant_types=["authorization_code", "refresh_token"],
    response_types=["code"],
    token_endpoint_auth_method="none",
)

mcp = FastMCP(
    "VAHN Sales Monitor",
    auth=auth,
    instructions="""You are a sales monitoring assistant for VAHN, a fleet management
company, working over LeadSquared (LSQ) CRM data: contacts, opportunities, tasks,
activities, and AI call records. VAHN's customers are TORGs — truck owners and
transporters — who subscribe per fleet.

## Call get_business_context first

Call `get_business_context` as the FIRST tool in any new conversation, before any other
tool. It defines vocabulary you cannot infer from tool names: the ordered opportunity
pipeline (New Lead through Paying Customer), valid statuses and contact stages, the
activity event catalogue with its picklist values, the rep roster, how "silent drop" and
"at-risk" are defined, and internal terms. It is read-only and cheap — do not skip it to
find out whether you needed it.

Re-call it whenever the user names a stage, status, acronym, product, team, or rep you
have not yet resolved against it.

## Filter values are not validated

Every stage, status, type, and rep argument is free text passed through to the CRM. An
invalid or misspelled value does not raise an error — it returns zero rows, which the
tools render identically to a genuine empty result. So:

- Resolve a rep name against the roster before reporting they have no overdue work.
  "No overdue follow-ups for X" from an unrecognised name means the name was wrong, not
  that X is on top of their pipeline.
- Resolve stage and status values before filtering, and name the value you filtered on
  whenever you report a count.

## Critical means 7+ days overdue

That is VAHN's definition — use `get_critical_overdue_tasks` for it. The top severity
band in `list_overdue_followups` is also labelled "critical" but triggers at >72 hours,
so it over-reports against the company bar. If you quote a critical count from the
severity bands, say explicitly that it uses a lower threshold.

## Always state which stale threshold you used

Three thresholds exist deliberately, for different audiences: 7+ days idle for the
escalation sweep (`get_escalation_list`), 14+ rep-facing (`list_stale_opportunities`),
30+ for manager monitoring (`get_stale_opportunities_monitor`). All three are legitimate.
None is interchangeable — name the threshold behind any stale count.

## Stage movement is not yours to predict

Logging an activity can move an opportunity's stage, but only where an LSQ automation is
configured for that activity. That mapping lives in LSQ automation config, which this
server cannot read and which can change without any code change here. Never predict
which stage an activity will produce, and never tell a user a lead advanced because you
logged one — re-read the opportunity to see what actually happened.

Both Paying Customer stages are marked by hand by sales users in LSQ. Nothing automatic
moves an opportunity into them, so those counts are "what reps have recorded", not "who
is actually paying". The Partial/Full split reflects whether the customer's subscription
payment covers part of their fleet or all of it.

## Known data traps

- **Lost is stored twice** — `opportunity_status='Lost'` and
  `opportunity_stage='Closed - Lost'` — and they can disagree. Prefer
  `get_monitoring_opportunities_by_status`, which uses a derived flag covering both.
- **Lead status_code reads the wrong column**, so ~94% of leads bucket as "0". The
  field is not genuinely empty — it is being read incorrectly. Do not use
  `get_leads_by_status_code` for anything until that is fixed; use contact stage.
- **Contact stages "Database" and "Unknown" are bad data**, not real stages. Exclude
  them from breakdowns and never describe a lead as being in them. They are why
  contact-stage totals do not reconcile against opportunity counts.
- **No strategic-account threshold exists.** Do not treat any fleet size as
  significant on your own; `get_escalation_list` ranks by raw fleet size only.

## Writes

`create_followup_task` and `log_activity` change data in LeadSquared. Confirm the
prospect, the subject or notes, and the date with the user before calling either. Both
require a `prospect_id` — `search_leads`, `get_lead_timeline`, and
`get_leads_without_followup` all print one. Never construct or guess an ID.

Use only picklist values from the activity catalogue in get_business_context. Where the
catalogue is unavailable, echo a value the user supplied rather than inventing one — a
wrong value written to LeadSquared is worse than a missing one.

## Reporting

Be concise and action-oriented. Lead with what needs attention. Prefer a count plus the
few rows that matter over long listings. State the period and every filter you applied,
so a number is never ambiguous.""",
)

# -- Entry point: defines the vocabulary every other tool's filters expect --
mcp.tool()(get_business_context)

# -- Existing tools --
mcp.tool()(list_overdue_followups)
mcp.tool()(get_rep_scorecard)
mcp.tool()(list_stale_opportunities)
mcp.tool()(get_pipeline_snapshot)
mcp.tool()(get_lead_timeline)
mcp.tool()(get_team_summary)
mcp.tool()(search_leads)
mcp.tool()(create_followup_task)
mcp.tool()(log_activity)
mcp.tool()(get_lead_details_from_lsq)
# mcp.tool()(get_lsq_users)  # endpoint not live yet

# -- Reporting snapshots --
mcp.tool()(get_opportunities_by_status)
mcp.tool()(get_opportunities_by_stage)
mcp.tool()(get_leads_by_contact_stage)
mcp.tool()(get_leads_by_status_code)

# -- Escalation & risk --
mcp.tool()(get_leads_without_followup)
mcp.tool()(get_escalation_list)
mcp.tool()(get_at_risk_customers)

# -- Lead analytics --
mcp.tool()(get_new_leads_count)
mcp.tool()(get_new_leads_by_source)

# -- Task analytics --
mcp.tool()(get_tasks_due_today)
mcp.tool()(get_task_completion_rate)

# -- Performance analytics --
mcp.tool()(get_new_opportunities_count)
mcp.tool()(get_won_opportunities)
mcp.tool()(get_workload_distribution)
mcp.tool()(get_call_outcome_breakdown)

# -- Monitoring --
mcp.tool()(get_critical_overdue_tasks)
mcp.tool()(get_overdue_tasks_summary)
mcp.tool()(get_monitoring_opportunities_by_status)
mcp.tool()(get_stale_opportunities_monitor)
mcp.tool()(get_opportunities_open_since)
mcp.tool()(get_opportunities_summary)


def main():
    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=8000,
    )


if __name__ == "__main__":
    main()
