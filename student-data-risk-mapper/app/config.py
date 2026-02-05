"""Application configuration loaded from environment variables."""
from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with validation."""

    # Application
    secret_key: str
    base_url: str = "http://localhost:8000"
    debug: bool = False

    # Database
    database_url: str
    database_url_sync: str

    # Microsoft Entra ID (Azure AD)
    entra_client_id: str
    entra_client_secret: str
    entra_tenant_id: str

    # Role mapping via group IDs (optional)
    entra_admin_group_id: Optional[str] = None
    entra_auditor_group_id: Optional[str] = None

    @property
    def entra_authority(self) -> str:
        """Microsoft Entra authority URL."""
        return f"https://login.microsoftonline.com/{self.entra_tenant_id}"

    @property
    def entra_openid_config_url(self) -> str:
        """OpenID Connect discovery endpoint."""
        return f"{self.entra_authority}/v2.0/.well-known/openid-configuration"

    @property
    def redirect_uri(self) -> str:
        """OAuth callback URI."""
        return f"{self.base_url}/auth/callback"

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
