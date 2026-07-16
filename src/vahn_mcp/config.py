from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configuration loaded from environment variables or .env file."""

    crm_service_url: str = "http://localhost:8081"
    crm_service_key: str = "dev-service-key"
    lsq_base_url: str = "https://api-in21.leadsquared.com/v2/"
    lsq_access_key: str = ""
    lsq_secret_key: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
