from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configuration loaded from environment variables or .env file.

    No LeadSquared credentials: this server reaches LeadSquared only through
    vahn-crm-service, which queues all outbound LSQ traffic through a single
    rate limiter shared with the dialer. A direct client here would bypass it.
    """

    crm_service_url: str = "http://localhost:8081"
    crm_service_key: str = "dev-service-key"
    mcp_base_url: str = "https://crm-mcp.vahn.in"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
