from __future__ import annotations

"""DAPEAgent.agent_builder

Common helper functions and shared state used by every agent in the DAPEAgent
package.

Responsibilities
----------------
1. Hold a singleton AsyncAzureOpenAI client wired with your project settings.
2. Provide convenience utilities such as `load_prompt` for reading prompt files.
"""

import os
from pathlib import Path
from typing import Optional, Sequence

from openai import AsyncAzureOpenAI

# The `agents` package comes from openai-functions-agent (or your fork)
from agents import (
    Agent,
    OpenAIChatCompletionsModel,
    set_default_openai_client,
    set_tracing_export_api_key,
    set_tracing_disabled,
)

# Project-level config (local to DAPEAgent package)
from .config import settings

# ---------------------------------------------------------------------------
# _Shared client instance
# ---------------------------------------------------------------------------

_openai_client: AsyncAzureOpenAI | None = None


def _build_client(azure_deployment: Optional[str] = None) -> AsyncAzureOpenAI:
    """Return a cached AsyncAzureOpenAI client (create on first call)."""
    global _openai_client
    if _openai_client is None:
        _openai_client = AsyncAzureOpenAI(
            api_key=settings.az_openai_api_key.get_secret_value(),
            api_version=settings.az_openai_api_version,
            azure_endpoint=settings.az_openai_endpoint,
            azure_deployment= azure_deployment or settings.az_openai_deployment,
        )
        # Register as default so downstream `agents` helpers pick it up
        set_tracing_disabled(True)
        
        # set_default_openai_client(_openai_client)

        # # Optional tracing integration
        # if settings.openai_trace_export_key:
        #     set_tracing_export_api_key(settings.openai_trace_export_key)
        #     set_tracing_disabled(False)
    return _openai_client



# ---------------------------------------------------------------------------
# Misc helpers
# ---------------------------------------------------------------------------

def load_yaml_prompt(path: str | Path) -> str:
    """Read a YAML prompt file and return the system_prompt content as a string."""
    import yaml
    
    prompt_content = Path(path).expanduser().read_text(encoding="utf-8")
    prompt_data = yaml.safe_load(prompt_content)
    return prompt_data 