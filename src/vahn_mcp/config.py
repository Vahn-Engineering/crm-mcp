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

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        # Ignore unrecognised variables instead of refusing to start. A deployed
        # .env outlives the code that read it: when LSQ_ACCESS_KEY / LSQ_SECRET_KEY
        # were dropped here, pydantic-settings' default of extra="forbid" turned
        # those leftover lines into a boot failure. A config server should not
        # crash because the box knows about a setting it no longer needs.
        "extra": "ignore",
    }


settings = Settings()
