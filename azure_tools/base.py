from azure.mgmt.datafactory import DataFactoryManagementClient
from azure.mgmt.batch import BatchManagementClient
from azure.keyvault.secrets import SecretClient
from azure.mgmt.resource.locks import ManagementLockClient
from azure.storage.blob import BlobServiceClient
from typing import Literal
from .auth import AzureAuthentication
from .subscription_resource import SubscriptionResourceManager
from subprocess import PIPE, run


class AzureResourceBase:
    def __init__(
        self,
        resource_group_name: str,
        resource_name: str,
        resource_type: Literal["adf", "batch", "keyvault", "locks", "storage"],
        subscription_id: str = None,
        auth: AzureAuthentication = None,
    ):
        """
        Base class for Azure resource operations.

        Args:
            resource_group_name: Name of the resource group
            resource_name: Name of the resource (ADF factory, Batch account, Key Vault, or Storage account)
            resource_type: Type of resource ('adf', 'batch', 'keyvault', 'locks', or 'storage')
            subscription_id: Azure subscription ID. If not provided, will be retrieved from environment or CLI
            auth: Optional AzureAuthentication instance. If not provided, creates a new one
        """
        self.resource_group_name = resource_group_name
        self.resource_name = resource_name
        self.resource_type = resource_type.lower()
        
        # Use provided auth instance or create a new one
        self.auth = auth if auth is not None else AzureAuthentication()
        
        # Handle subscription_id independently
        if subscription_id is None:
            subscription_id = SubscriptionResourceManager.get_current_subscription_id()
        
        self.subscription_id = subscription_id
        
        # For backward compatibility, expose credential and token methods
        self.credential = self.auth.credential
        
        # Initialize appropriate client based on resource type
        if self.resource_type == "adf":
            self.client = DataFactoryManagementClient(
                credential=self.credential, subscription_id=self.subscription_id,
            )
        elif self.resource_type == "batch":
            self.client = BatchManagementClient(
                credential=self.credential, subscription_id=self.subscription_id,
            )
        elif self.resource_type == "keyvault":
            self.secret_client = SecretClient(
                vault_url=f"https://{resource_name}.vault.azure.net",
                credential=self.credential,
            )
        elif self.resource_type == "locks":
            self.lock_client = ManagementLockClient(
                credential=self.credential, subscription_id=self.subscription_id,
            )
        elif self.resource_type == "storage":
            self.blob_service_client = BlobServiceClient(
                account_url=f"https://{resource_name}.blob.core.windows.net",
                credential=self.credential,
            )
        else:
            raise ValueError(
                f"Unsupported resource type: {resource_type}. Must be 'adf', 'batch', 'keyvault', 'locks', or 'storage'"
            )



    def _get_token(self):
        """
        Get a token using the shared authentication instance.
        This method is kept for backward compatibility.
        """
        return self.auth.get_token()

    def get_resource_details(self):
        """
        Get details of the resource based on its type
        """
        try:
            if self.resource_type == "adf":
                return self.client.factories.get(
                    resource_group_name=self.resource_group_name,
                    factory_name=self.resource_name,
                )
            elif self.resource_type == "batch":
                return self.client.batch_account.get(
                    resource_group_name=self.resource_group_name,
                    account_name=self.resource_name,
                )
        except Exception as e:
            print(f"Error getting {self.resource_type} details: {str(e)}")
            raise