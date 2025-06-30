from __future__ import annotations

"""DAPEAgent.utils.azure_adapters

Lightweight factory utilities that convert a *context dictionary* into the
correct helper class from `azure_tools`.  These functions are consumed by
both the TriageAgent and the task-specific agents so they don't need to know
about constructor details or caching.
"""

from functools import lru_cache
from typing import Literal, TypedDict

# Low-level resource helpers -------------------------------------------------
from azure_tools.adf.linked_services import ADFLinkedServices
from azure_tools.adf.triggers import ADFTrigger
from azure_tools.adf.pipelines import ADFPipeline
from azure_tools.adf.integration_runtime import ADFIntegrationRuntime
from azure_tools.adf.managed_pe import ADFManagedPrivateEndpoint

from azure_tools.batch import AzureBatchPool
from azure_tools.keyvault import AzureKeyVault
from azure_tools.locks import AzureResourceLock


class Context(TypedDict, total=False):
    """Common context object passed around the agents."""

    subscription_id: str
    resource_group_name: str
    resource_name: str           # Data Factory name, Batch account, Key Vault, etc.
    pool_name: str               # Only for Batch Pool operations


ResourceKey = Literal[
    "adf.linked_services",
    "adf.triggers",
    "adf.pipelines",
    "adf.integration_runtime",
    "adf.managed_pe",
    "batch.pool",
    "keyvault",
    "locks",
]


@lru_cache(maxsize=32)
def get_resource_handler(key: ResourceKey, **ctx: Context):
    """Return an initialised helper from *azure_tools* corresponding to *key*.

    The call is memoised so repeated use of the same parameters re-uses the
    same underlying Azure SDK client / auth token.
    """

    if key == "adf.linked_services":
        return ADFLinkedServices(**ctx)  # type: ignore[arg-type]
    elif key == "adf.triggers":
        return ADFTrigger(**ctx)  # type: ignore[arg-type]
    elif key == "adf.pipelines":
        return ADFPipeline(**ctx)  # type: ignore[arg-type]
    elif key == "adf.integration_runtime":
        return ADFIntegrationRuntime(**ctx)  # type: ignore[arg-type]
    elif key == "adf.managed_pe":
        return ADFManagedPrivateEndpoint(**ctx)  # type: ignore[arg-type]
    elif key == "batch.pool":
        if not ctx.get("pool_name"):
            raise ValueError("'pool_name' must be supplied for batch.pool operations")
        return AzureBatchPool(**ctx)  # type: ignore[arg-type]
    elif key == "keyvault":
        return AzureKeyVault(**ctx)  # type: ignore[arg-type]
    elif key == "locks":
        # Locks operate at the resource group scope – resource_name not required
        return AzureResourceLock(
            resource_group_name=ctx.get("resource_group_name", ""),
            subscription_id=ctx.get("subscription_id"),
        )

    raise ValueError(f"Unknown resource handler key: {key}")


def list_handler_keys() -> list[str]:
    """Expose the set of valid keys – useful for auto-suggestion."""

    return list(get_resource_handler.__annotations__["key"].__args__)  # type: ignore[attr-defined] 