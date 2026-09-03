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

    # -- Record-level read API (branch feature/mcp-read-apis) --
    # Every list endpoint returns the same envelope: content/page/size/
    # totalElements/totalPages/hasNext/hasPrevious/sort. size caps at 200.

    @staticmethod
    def _params(**kw) -> dict:
        """Drop None and blank values — the API ignores blanks anyway."""
        return {k: v for k, v in kw.items()
                if v is not None and not (isinstance(v, str) and not v.strip())}

    async def list_leads(self, **filters) -> dict:
        async with self._client() as c:
            r = await c.get("/api/read/leads", params=self._params(**filters))
            r.raise_for_status()
            return r.json()

    async def get_lead(self, prospect_id: str) -> dict:
        async with self._client() as c:
            r = await c.get(f"/api/read/leads/{prospect_id}")
            r.raise_for_status()
            return r.json()

    async def list_opportunities(self, **filters) -> dict:
        async with self._client() as c:
            r = await c.get("/api/read/opportunities", params=self._params(**filters))
            r.raise_for_status()
            return r.json()

    async def get_opportunity(self, opportunity_id: str) -> dict:
        async with self._client() as c:
            r = await c.get(f"/api/read/opportunities/{opportunity_id}")
            r.raise_for_status()
            return r.json()

    async def list_tasks(self, **filters) -> dict:
        async with self._client() as c:
            r = await c.get("/api/read/tasks", params=self._params(**filters))
            r.raise_for_status()
            return r.json()

    async def get_task(self, task_id: str) -> dict:
        async with self._client() as c:
            r = await c.get(f"/api/read/tasks/{task_id}")
            r.raise_for_status()
            return r.json()

    # -- Activities: these RELAY TO LEADSQUARED. Rate-limited, shared with the
    # -- dialer. Never call in a loop over leads. 502 = LSQ unhappy (retry),
    # -- 503 = LSQ disabled in this environment (do not retry).

    async def get_activity_types(
        self, event_type: str | None = None, include_schema: bool = False
    ) -> dict:
        """The activity-type catalogue. Relays to LSQ. Cache on the caller side."""
        async with self._client() as c:
            r = await c.get(
                "/api/read/activity-types",
                params=self._params(eventType=event_type,
                                    includeSchema=include_schema or None),
            )
            r.raise_for_status()
            return r.json()

    async def list_activities(self, **filters) -> dict:
        """Relays to LSQ. One call per page. Never loop this per lead."""
        async with self._client() as c:
            r = await c.get("/api/read/activities", params=self._params(**filters))
            r.raise_for_status()
            return r.json()

    async def get_activity(self, activity_id: str) -> dict:
        """Relays to LSQ. Returns fields keyed by display name with schemaName."""
        async with self._client() as c:
            r = await c.get(f"/api/read/activities/{activity_id}")
            r.raise_for_status()
            return r.json()

    # -- Calls: local, and richer than LSQ activity 210 --

    async def list_calls(self, **filters) -> dict:
        async with self._client() as c:
            r = await c.get("/api/read/calls", params=self._params(**filters))
            r.raise_for_status()
            return r.json()

    async def get_call(self, conversation_id: str) -> dict:
        async with self._client() as c:
            r = await c.get(f"/api/read/calls/{conversation_id}")
            r.raise_for_status()
            return r.json()

    # -- Call queue: why a lead has or hasn't been called --

    async def list_call_queue(self, **filters) -> dict:
        async with self._client() as c:
            r = await c.get("/api/read/call-queue", params=self._params(**filters))
            r.raise_for_status()
            return r.json()

    # -- WhatsApp events --

    async def list_whatsapp_events(self, **filters) -> dict:
        async with self._client() as c:
            r = await c.get("/api/read/whatsapp-events",
                            params=self._params(**filters))
            r.raise_for_status()
            return r.json()

    # -- Stage history --

    async def list_stage_history(self, **filters) -> dict:
        async with self._client() as c:
            r = await c.get("/api/read/stage-history", params=self._params(**filters))
            r.raise_for_status()
            return r.json()

    async def get_opportunity_stage_history(self, opportunity_id: str) -> dict:
        """Unpaged, oldest-first, with daysInStage precomputed."""
        async with self._client() as c:
            r = await c.get(
                f"/api/read/opportunities/{opportunity_id}/stage-history"
            )
            r.raise_for_status()
            return r.json()

    # -- Users --

    async def get_user(self, user_id: str) -> dict:
        """Accepts an LSQ user id OR an email address. Includes a workload block."""
        async with self._client() as c:
            r = await c.get(f"/api/read/users/{user_id}")
            r.raise_for_status()
            return r.json()

    async def list_users(self) -> dict:
        """Flat roster. This is the real endpoint — /api/read/lsq-users never shipped."""
        async with self._client() as c:
            r = await c.get("/api/read/users")
            r.raise_for_status()
            return r.json()

    # -- Unified timeline: prefer over /api/read/lead-timeline/{id}, whose
    # -- activity section is permanently empty (lsq_activities has zero rows).

    async def get_lead_timeline_merged(
        self, prospect_id: str, sources: str | None = None, limit: int = 100
    ) -> dict:
        async with self._client() as c:
            r = await c.get(
                f"/api/read/leads/{prospect_id}/timeline",
                params=self._params(sources=sources, limit=limit),
            )
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
