# config.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings



class Settings(BaseSettings):
    # ───── Azure OpenAI ──────────────────────────────────
    az_openai_api_key: SecretStr = Field(..., alias="AZURE_OPENAI_API_KEY")
    az_openai_endpoint: str = Field(..., alias="AZURE_OPENAI_ENDPOINT")
    az_openai_deployment: str = Field("gpt-4.1", alias="AZURE_OPENAI_DEPLOYMENT")
    az_openai_api_version: str = Field("2024-05-01-preview", alias="AZURE_OPENAI_API_VERSION")
    azure_auth_method: str = Field("default", alias="AZURE_AUTH_METHOD")
    azure_tenant_id: str = Field(..., alias="AZURE_TENANT_ID")
    azure_client_id: Optional[str] = Field(default=None, alias="AZURE_CLIENT_ID")
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")

    class Config:
        env_file = ".env"            # auto-loads .env if present
        env_file_encoding = "utf-8"
        case_sensitive = False        # require exact case matching for env vars
        extra = "ignore"             # silently ignore unknown vars


# instantiate once at import-time
settings = Settings()

# helper for project root
ROOT_DIR: Path = Path(__file__).resolve().parent.parent  # Go up one more level since we're in DAPEAgent/ 

