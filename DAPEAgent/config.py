# config.py
from pathlib import Path
from typing import Optional

from pydantic import Field, SecretStr, AnyHttpUrl, PostgresDsn

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # ───── Azure OpenAI ──────────────────────────────────
    az_openai_api_key: SecretStr = Field(..., alias="AZURE_OPENAI_API_KEY")
    az_openai_endpoint: str = Field(..., alias="AZURE_OPENAI_ENDPOINT")
    az_openai_deployment: str = Field("gpt-4.1", alias="AZURE_OPENAI_DEPLOYMENT")
    az_openai_api_version: str = Field("2024-05-01-preview", alias="AZURE_OPENAI_API_VERSION")
    openai_trace_export_key: Optional[str] = Field(default=None, alias="OPENAI_TRACE_EXPORT_KEY")


    class Config:
        env_file = ".env"            # auto-loads .env if present
        env_file_encoding = "utf-8"
        case_sensitive = False        # require exact case matching for env vars
        extra = "ignore"             # silently ignore unknown vars


# instantiate once at import-time
settings = Settings()

# helper for project root
ROOT_DIR: Path = Path(__file__).resolve().parent.parent  # Go up one more level since we're in DAPEAgent/ 