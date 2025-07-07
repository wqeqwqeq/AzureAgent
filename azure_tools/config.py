# config.py
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings



class Settings(BaseSettings):
    # ───── Azure OpenAI ──────────────────────────────────
    azure_tenant_id: str = Field(..., alias="AZURE_TENANT_ID")
    azure_client_id: Optional[str] = Field(default=None, alias="AZURE_CLIENT_ID")
    azure_auth_method: str = Field("default", alias="AZURE_AUTH_METHOD")

    class Config:
        env_file = ".env"            # auto-loads .env if present
        env_file_encoding = "utf-8"
        case_sensitive = False        # require exact case matching for env vars
        extra = "ignore"             # silently ignore unknown vars


# instantiate once at import-time
settings = Settings()