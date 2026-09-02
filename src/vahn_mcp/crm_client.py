"""HTTP client for vahn-crm-service REST APIs."""

import httpx

from vahn_mcp.config import settings


class CrmClient:
    """Calls vahn-crm-service /api/read/* and /api/internal/* endpoints."""

    def __init__(self):
        self._base = settings.crm_service_url.rstrip("/")
        self._headers = {"x-service-key": settings.crm_service_key}

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self._base,
            headers=self._headers,
            timeout=30.0,
            verify=False,
        )

    # -- Read endpoints --

    async def get_overdue_followups(
        self, owner: str | None = None, limit: int = 50
    ) -> dict:
        params: dict = {"limit": limit}
        if owner:
            params["owner"] = owner
        async with self._client() as c:
            r = await c.get("/api/read/overdue-followups", params=params)
            r.raise_for_status()
            return r.json()

    async def get_rep_scorecard(
        self, owner_name: str, start: str, end: str
    ) -> dict:
        async with self._client() as c:
            r = await c.get(
                f"/api/read/rep-scorecard/{owner_name}",
                params={"start": start, "end": end},
            )
            r.raise_for_status()
            return r.json()

    async def get_stale_opportunities(
        self,
        stage: str | None = None,
        days_idle: int = 14,
        owner: str | None = None,
        limit: int = 50,
    ) -> dict:
        params: dict = {"daysIdle": days_idle, "limit": limit}
        if stage:
            params["stage"] = stage
        if owner:
            params["owner"] = owner
        async with self._client() as c:
            r = await c.get("/api/read/stale-opportunities", params=params)
            r.raise_for_status()
            return r.json()

    async def get_pipeline_snapshot(
        self, owner: str | None = None, stage: str | None = None
    ) -> dict:
        params: dict = {}
        if owner:
            params["owner"] = owner
        if stage:
            params["stage"] = stage
        async with self._client() as c:
            r = await c.get("/api/read/pipeline-snapshot", params=params)
            r.raise_for_status()
            return r.json()

    async def get_lead_timeline(self, prospect_id: str) -> dict:
        async with self._client() as c:
            r = await c.get(f"/api/read/lead-timeline/{prospect_id}")
            r.raise_for_status()
            return r.json()

    async def get_team_summary(self, start: str, end: str) -> dict:
        async with self._client() as c:
            r = await c.get(
                "/api/read/team-summary", params={"start": start, "end": end}
            )
            r.raise_for_status()
            return r.json()

    async def search_leads(
        self,
        contact_type: str | None = None,
        stage: str | None = None,
        phone: str | None = None,
        company: str | None = None,
        limit: int = 50,
    ) -> dict:
        params: dict = {"limit": limit}
        if contact_type:
            params["contactType"] = contact_type
        if stage:
            params["stage"] = stage
        if phone:
            params["phone"] = phone
        if company:
            params["company"] = company
        async with self._client() as c:
            r = await c.get("/api/read/search-leads", params=params)
            r.raise_for_status()
            return r.json()

    async def get_lsq_users(self) -> dict:
        async with self._client() as c:
            r = await c.get("/api/read/lsq-users")
            r.raise_for_status()
            return r.json()

    # -- Reporting views --

    async def get_opportunities_by_status(self) -> dict:
        async with self._client() as c:
            r = await c.get("/api/read/opportunities-by-status")
            r.raise_for_status()
            return r.json()

    async def get_opportunities_by_stage(self) -> dict:
        async with self._client() as c:
            r = await c.get("/api/read/opportunities-by-stage")
            r.raise_for_status()
            return r.json()

    async def get_leads_by_contact_stage(self) -> dict:
        async with self._client() as c:
            r = await c.get("/api/read/leads-by-contact-stage")
            r.raise_for_status()
            return r.json()

    async def get_leads_by_status_code(self) -> dict:
        async with self._client() as c:
            r = await c.get("/api/read/leads-by-status-code")
            r.raise_for_status()
            return r.json()

    # -- Escalation & risk --

    async def get_leads_without_followup(self, limit: int = 50) -> dict:
        async with self._client() as c:
            r = await c.get(
                "/api/read/leads-without-followup", params={"limit": limit}
            )
            r.raise_for_status()
            return r.json()

    async def get_escalation_list(
        self, days_threshold: int = 7, limit: int = 50
    ) -> dict:
        async with self._client() as c:
            r = await c.get(
                "/api/read/escalation-list",
                params={"daysThreshold": days_threshold, "limit": limit},
            )
            r.raise_for_status()
            return r.json()

    async def get_at_risk_customers(self, limit: int = 50) -> dict:
        async with self._client() as c:
            r = await c.get(
                "/api/read/at-risk-customers", params={"limit": limit}
            )
            r.raise_for_status()
            return r.json()

    # -- Lead analytics --

    async def get_new_leads_count(self, start: str, end: str) -> dict:
        async with self._client() as c:
            r = await c.get(
                "/api/read/new-leads-count",
                params={"start": start, "end": end},
            )
            r.raise_for_status()
            return r.json()

    async def get_new_leads_by_source(self, start: str, end: str) -> dict:
        async with self._client() as c:
            r = await c.get(
                "/api/read/new-leads-by-source",
                params={"start": start, "end": end},
            )
            r.raise_for_status()
            return r.json()

    # -- Task analytics --

    async def get_tasks_due_today(self, owner_id: str | None = None) -> dict:
        params: dict = {}
        if owner_id:
            params["ownerId"] = owner_id
        async with self._client() as c:
            r = await c.get("/api/read/tasks-due-today", params=params)
            r.raise_for_status()
            return r.json()

    async def get_task_completion_rate(
        self, start: str, end: str, owner_id: str | None = None
    ) -> dict:
        params: dict = {"start": start, "end": end}
        if owner_id:
            params["ownerId"] = owner_id
        async with self._client() as c:
            r = await c.get("/api/read/task-completion-rate", params=params)
            r.raise_for_status()
            return r.json()

    # -- Performance analytics --

    async def get_new_opportunities_count(self, start: str, end: str) -> dict:
        async with self._client() as c:
            r = await c.get(
                "/api/read/new-opportunities-count",
                params={"start": start, "end": end},
            )
            r.raise_for_status()
            return r.json()

    async def get_won_opportunities(self, start: str, end: str) -> dict:
        async with self._client() as c:
            r = await c.get(
                "/api/read/won-opportunities",
                params={"start": start, "end": end},
            )
            r.raise_for_status()
            return r.json()

    async def get_workload_distribution(self) -> dict:
        async with self._client() as c:
            r = await c.get("/api/read/workload-distribution")
            r.raise_for_status()
            return r.json()

    async def get_call_outcome_breakdown(
        self, start: str | None = None, end: str | None = None
    ) -> dict:
        params: dict = {}
        if start:
            params["start"] = start
        if end:
            params["end"] = end
        async with self._client() as c:
            r = await c.get(
                "/api/read/call-outcome-breakdown", params=params
            )
            r.raise_for_status()
            return r.json()

    # -- Monitoring endpoints --

    async def get_monitoring_tasks_overdue_critical(self) -> dict:
        async with self._client() as c:
            r = await c.get("/monitoring/tasks/overdue/critical")
            r.raise_for_status()
            return r.json()

    async def get_monitoring_tasks_overdue_summary(self) -> dict:
        async with self._client() as c:
            r = await c.get("/monitoring/tasks/overdue/summary")
            r.raise_for_status()
            return r.json()

    async def get_monitoring_opportunities_by_status(
        self, status: str | None = None
    ) -> dict:
        params: dict = {}
        if status:
            params["status"] = status
        async with self._client() as c:
            r = await c.get(
                "/monitoring/opportunities/by-status", params=params
            )
            r.raise_for_status()
            return r.json()

    async def get_monitoring_opportunities_stale(
        self, days: int = 30
    ) -> dict:
        async with self._client() as c:
            r = await c.get(
                "/monitoring/opportunities/stale", params={"days": days}
            )
            r.raise_for_status()
            return r.json()

    async def get_monitoring_opportunities_open_since(
        self, days: int = 30
    ) -> dict:
        async with self._client() as c:
            r = await c.get(
                "/monitoring/opportunities/open-since", params={"days": days}
            )
            r.raise_for_status()
            return r.json()

    async def get_monitoring_opportunities_summary(self) -> dict:
        async with self._client() as c:
            r = await c.get("/monitoring/opportunities/summary")
            r.raise_for_status()
            return r.json()

    # -- Business context --

    async def get_business_context(self) -> dict | None:
        """Fetch the live CRM vocabulary from a dedicated endpoint.

        Returns None if vahn-crm-service does not implement the endpoint yet,
        letting callers fall back to deriving values from the reporting views.

        Expected response shape:
            {
              "stageCounts": {stage_name: int, ...},
              "statusCounts": {"Open": int, "Won": int, "Lost": int},
              "reps": [{"name": str, "active": bool}, ...]
            }
        """
        async with self._client() as c:
            r = await c.get("/api/read/business-context")
            if r.status_code == 404:
                return None
            r.raise_for_status()
            return r.json()

    # -- Write endpoints --

    async def create_task(self, data: dict) -> dict:
        async with self._client() as c:
            r = await c.post("/api/internal/tasks/create", json=data)
            r.raise_for_status()
            return r.json()

    async def log_activity(self, data: dict) -> dict:
        async with self._client() as c:
            r = await c.post("/api/internal/activities/log", json=data)
            r.raise_for_status()
            return r.json()


crm = CrmClient()
