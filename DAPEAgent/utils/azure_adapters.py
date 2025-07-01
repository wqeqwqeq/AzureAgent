from __future__ import annotations

"""DAPEAgent.utils.azure_adapters

Lightweight factory utilities that convert a *context object* into the
correct helper class from `azure_tools`.  These functions are consumed by
both the TriageAgent and the task-specific agents so they don't need to know
about constructor details or caching.
"""

from dataclasses import dataclass
from functools import lru_cache
from typing import Literal, TypedDict, Union

# Low-level resource helpers -------------------------------------------------
from azure_tools.adf.linked_services import ADFLinkedServices
from azure_tools.adf.triggers import ADFTrigger
from azure_tools.adf.pipelines import ADFPipeline
from azure_tools.adf.integration_runtime import ADFIntegrationRuntime
from azure_tools.adf.managed_pe import ADFManagedPrivateEndpoint

from azure_tools.batch import AzureBatchPool
from azure_tools.keyvault import AzureKeyVault
from azure_tools.locks import AzureResourceLock
from azure_tools.subscription_resource import SubscriptionResourceManager


@dataclass
class AzureCtx:
    """Azure context object passed around the agents using the agents framework's context system."""
    subscription_id: str | None = None
    subscription_name: str | None = None
    resource_group_name: str | None = None
    resource_name: str | None = None
    pool_name: str | None = None  # Only for Batch Pool operations

    def to_cache_key(self) -> tuple:
        """Convert context to a hashable tuple for caching purposes."""
        return (
            self.subscription_id,
            self.subscription_name,
            self.resource_group_name,
            self.resource_name,
            self.pool_name,
        )


# Backward compatibility - keep the old TypedDict for now
class Context(TypedDict, total=False):
    """Legacy context object - use AzureCtx instead."""
    subscription_id: str
    resource_group_name: str
    resource_name: str
    pool_name: str


ResourceKey = Literal[
    "adf.linked_services",
    "adf.triggers", 
    "adf.pipelines",
    "adf.integration_runtime",
    "adf.managed_pe",
    "batch.pool",
    "keyvault",
    "locks",
    "subscription_resource",
]


def _extract_context_values(ctx: Union[AzureCtx, Context, dict]) -> dict:
    """Extract context values as a dict from either AzureCtx dataclass or dict/TypedDict."""
    if isinstance(ctx, AzureCtx):
        # Convert dataclass to dict, filtering out None values
        return {k: v for k, v in ctx.__dict__.items() if v is not None}
    else:
        # It's already a dict-like object
        return dict(ctx)


def _make_cache_key(key: ResourceKey, context_values: dict) -> tuple:
    """Create a hashable cache key from resource key and context values."""
    # Sort items to ensure consistent ordering
    sorted_items = tuple(sorted(context_values.items()))
    return (key, sorted_items)


# Simple cache for resource handlers
_resource_handler_cache = {}


def get_resource_handler(key: ResourceKey, ctx: Union[AzureCtx, Context, dict] = None, **kwargs):
    """Return an initialised helper from *azure_tools* corresponding to *key*.

    The call is cached so repeated use of the same parameters re-uses the
    same underlying Azure SDK client / auth token.
    
    Args:
        key: The resource handler key
        ctx: Context object (AzureCtx dataclass, Context TypedDict, or dict)
        **kwargs: Additional context values (for backward compatibility)
    """
    # Merge context from both ctx parameter and kwargs
    context_values = {}
    if ctx is not None:
        context_values.update(_extract_context_values(ctx))
    context_values.update(kwargs)

    # Check cache first
    cache_key = _make_cache_key(key, context_values)
    if cache_key in _resource_handler_cache:
        return _resource_handler_cache[cache_key]

    # Create new instance
    if key == "adf.linked_services":
        handler = ADFLinkedServices(**context_values)
    elif key == "adf.triggers":
        handler = ADFTrigger(**context_values)
    elif key == "adf.pipelines":
        handler = ADFPipeline(**context_values)
    elif key == "adf.integration_runtime":
        handler = ADFIntegrationRuntime(**context_values)
    elif key == "adf.managed_pe":
        handler = ADFManagedPrivateEndpoint(**context_values)
    elif key == "batch.pool":
        if not context_values.get("pool_name"):
            raise ValueError("'pool_name' must be supplied for batch.pool operations")
        handler = AzureBatchPool(**context_values)
    elif key == "keyvault":
        handler = AzureKeyVault(**context_values)
    elif key == "locks":
        # Locks operate at the resource group scope – resource_name not required
        handler = AzureResourceLock(
            resource_group_name=context_values.get("resource_group_name", ""),
            subscription_id=context_values.get("subscription_id"),
        )
    elif key == "subscription_resource":
        # Subscription and resource management operations
        handler = SubscriptionResourceManager(
            subscription_id=context_values.get("subscription_id"),
        )
    else:
        raise ValueError(f"Unknown resource handler key: {key}")

    # Cache and return
    _resource_handler_cache[cache_key] = handler
    return handler


def list_handler_keys() -> list[str]:
    """Expose the set of valid keys – useful for auto-suggestion."""
    return list(get_resource_handler.__annotations__["key"].__args__)  # type: ignore[attr-defined] 