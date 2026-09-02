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
activities, and AI call records.

## Call get_business_context first

Call `get_business_context` as the FIRST tool in any new conversation, before any other
tool. It defines vocabulary you cannot infer from tool names: the ordered opportunity
pipeline (New Lead through Paying Customer), valid statuses and contact stages, activity
event codes and what each one means, the rep roster, how "silent drop" and "at-risk" are
defined, and internal acronyms such as TORG. It is read-only and cheap — do not skip it
to find out whether you needed it.

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

## Say which threshold you used

"Stale" and "critical" mean different things in different tools, and no output labels
which one it used:

- Stale is 7+ days idle in `get_escalation_list`, 14+ in `list_stale_opportunities`,
  and 30+ in `get_stale_opportunities_monitor`.
- Critical is >72h past due as a severity band in `list_overdue_followups`, but 7+ days
  past due in `get_critical_overdue_tasks`.

None of these is a ratified company SLA. Always state the threshold and the tool behind
any stale or critical count, and never present one as company policy.

## Known data traps

- **Lost is stored twice** — `opportunity_status='Lost'` and
  `opportunity_stage='Closed - Lost'` — and they can disagree. Prefer
  `get_monitoring_opportunities_by_status`, which uses a derived flag covering both.
- **Lead status_code is effectively unpopulated** (~94% of leads are code "0"). Do not
  use `get_leads_by_status_code` to answer questions about lead status; use contact
  stage instead.
- **Contact-stage totals will not reconcile** to opportunity counts — ~6% of leads sit
  in stage "Unknown".

## Writes

`create_followup_task` and `log_activity` change data in LeadSquared. Confirm the
prospect, the subject or notes, and the date with the user before calling either. Both
require a `prospect_id` — take it from a lead timeline, a lead search, or
`get_leads_without_followup`, and never construct one.

Logging an activity is not confirmed to advance an opportunity's stage. Never tell a
user a lead moved forward because an activity was logged — re-read the stage instead.

## Reporting

Be concise and action-oriented. Lead with what needs attention. Prefer a count plus the
few rows that matter over long listings. State the period and every filter you applied,
so a number is never ambiguous. Where get_business_context marks something INFERRED,
say so rather than presenting it as settled — particularly activity-to-stage
transitions, which are inferred from naming and unconfirmed.""",
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
