"""Direct LeadSquared API client for unsynced fields and fallback queries."""

import httpx

from vahn_mcp.config import settings


class LsqClient:
    """Calls LeadSquared API directly for data not synced to vahn-crm-service."""

    def __init__(self):
        self._base = settings.lsq_base_url.rstrip("/")
        self._headers = {
            "x-LSQ-AccessKey": settings.lsq_access_key,
            "x-LSQ-SecretKey": settings.lsq_secret_key,
        }

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self._base,
            headers=self._headers,
            timeout=30.0,
        )

    async def get_lead_by_id(self, lead_id: str) -> dict:
        """Fetch full lead details directly from LSQ."""
        async with self._client() as c:
            r = await c.get(
                "LeadManagement.svc/Lead.GetById",
                params={"leadId": lead_id},
            )
            r.raise_for_status()
            return r.json()

    async def search_leads(self, filters: dict) -> dict:
        """Search leads on LSQ with filters."""
        async with self._client() as c:
            r = await c.post(
                "LeadManagement.svc/Leads.Get",
                json=filters,
            )
            r.raise_for_status()
            return r.json()


lsq = LsqClient()
