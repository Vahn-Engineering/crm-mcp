"""VAHN Sales Monitoring MCP Server."""

from fastmcp import FastMCP

from vahn_mcp.tools.followups import list_overdue_followups
from vahn_mcp.tools.scorecard import get_rep_scorecard
from vahn_mcp.tools.opportunities import list_stale_opportunities, get_pipeline_snapshot
from vahn_mcp.tools.timeline import get_lead_timeline
from vahn_mcp.tools.team import get_team_summary
from vahn_mcp.tools.search import search_leads
from vahn_mcp.tools.write import create_followup_task, log_activity, get_lead_details_from_lsq

mcp = FastMCP(
    "VAHN Sales Monitor",
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

When presenting data, be concise and action-oriented. Highlight what needs attention.""",
)

# Register all tools
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


def main():
    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=8000,
    )


if __name__ == "__main__":
    main()
