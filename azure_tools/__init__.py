"""
Azure Tools Package

Provides simplified interfaces for managing Azure resources including:
- Azure Data Factory
- Azure Batch
- Azure Key Vault
- Azure Storage
- Resource Locks
- Subscription and Resource Group Management
"""

from .auth import AzureAuthentication
from .base import AzureResourceBase
from .subscription_resource import SubscriptionResourceManager
from .batch import AzureBatchPool
from .keyvault import AzureKeyVault
from .storage import AzureStorage, AzureStorageCopy
from .locks import AzureResourceLock
from .adf import (
    ADFLinkedServices,
    ADFIntegrationRuntime,
    ADFManagedPrivateEndpoint,
    ADFTrigger,
    ADFPipeline,
)

__version__ = "0.1.0"

__all__ = [
    "AzureAuthentication",
    "AzureResourceBase", 
    "SubscriptionResourceManager",
    "AzureBatchPool",
    "AzureKeyVault",
    "AzureStorage",
    "AzureStorageCopy",
    "AzureResourceLock",
    "ADFLinkedServices",
    "ADFIntegrationRuntime",
    "ADFManagedPrivateEndpoint",
    "ADFTrigger",
    "ADFPipeline",
] 