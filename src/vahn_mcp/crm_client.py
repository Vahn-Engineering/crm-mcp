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
