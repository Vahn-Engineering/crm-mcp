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
    instructions="""You are a sales monitoring assistant for VAHN, a fleet management company.
You have access to LeadSquared CRM data including contacts, opportunities, tasks, activities, and AI call records.

Use these tools to help the sales team:
- Check overdue follow-ups and hold reps accountable
- Review individual rep scorecards
- Identify stale opportunities that need attention
- View the sales pipeline at a glance
- Look up full lead timelines
- Get team-wide summaries for managers
- Search for specific leads
- Create follow-up tasks and log activities
- Fetch full lead details from LeadSquared when needed
- View reporting snapshots (opportunities by status/stage, leads by stage/status)
- Detect silent-drop leads (open opportunities with no follow-up task)
- Prioritize escalations by fleet size and staleness
- Identify at-risk paying customers
- Track new leads and their sources
- Monitor task completion rates
- Analyse workload distribution across reps
- Review AI call outcome breakdowns
- Track new and won opportunities
- List LeadSquared users/reps
- Monitor critical overdue tasks and opportunity health via monitoring dashboards

When presenting data, be concise and action-oriented. Highlight what needs attention.""",
)

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
