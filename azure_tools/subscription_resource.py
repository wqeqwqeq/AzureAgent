from azure.mgmt.resource import ResourceManagementClient, SubscriptionClient
from subprocess import PIPE, run
from typing import Optional
from .auth import AzureAuthentication


class SubscriptionResourceManager:
    """
    Manages subscription and resource group operations.
    Uses composition with AzureAuthentication and is the source of truth for subscription operations.
    """
    
    def __init__(
        self,
        subscription_id: str = None,
        auth: AzureAuthentication = None,
    ):
        """
        Initialize subscription and resource management.

        Args:
            subscription_id: Azure subscription ID. If not provided, will be auto-detected
            auth: Optional AzureAuthentication instance. If not provided, creates a new one
        """
        # Use provided auth instance or create a new one
        self.auth = auth if auth is not None else AzureAuthentication()
        
        # For backward compatibility, expose credential
        self.credential = self.auth.credential
        
        # Create subscription client first
        self.subscription_client = SubscriptionClient(credential=self.credential)
        
        # Handle subscription_id using SDK
        self.subscription_id = subscription_id or SubscriptionResourceManager.get_current_subscription_id()
        
        # Create resource management client
        self.resource_client = ResourceManagementClient(
            credential=self.credential, 
            subscription_id=self.subscription_id
        )


    @staticmethod
    def get_current_subscription_id():
        """Get the current subscription ID using Azure CLI"""
        cmd = "az account show --query id --output tsv"
        return SubscriptionResourceManager.run_cmd(cmd).stdout.strip()
    
    @staticmethod
    def get_current_subscription_name():
        """Get the current subscription name using Azure CLI"""
        cmd = "az account show --query name --output tsv"
        return SubscriptionResourceManager.run_cmd(cmd).stdout.strip()

    @staticmethod
    def switch_subscription(subscription_name_or_id):
        """
        Switch to a different subscription using Azure CLI.
        
        Args:
            subscription_name_or_id: Either the subscription name or subscription ID
            
        Returns:
            CompletedProcess: Result of the az account set command
            
        Raises:
            RuntimeError: If the subscription switch fails
        """
        cmd = f"az account set --subscription \"{subscription_name_or_id}\""
        result = SubscriptionResourceManager.run_cmd(cmd)
        
        if result.returncode != 0:
            raise RuntimeError(f"Failed to switch subscription: {result.stderr}")
        
        return result

    def get_sub_id_by_name(self, target_name):
        """
        Get subscription ID by subscription display name.
        
        Args:
            target_name: The friendly name of the subscription
            
        Returns:
            str: The subscription ID if found, raises RuntimeError if not found
        """
        subscription_id = next(
            (s.subscription_id for s in self.subscription_client.subscriptions.list()
                if s.display_name == target_name),  # exact match (case-sensitive)
            None
        )
        
        if subscription_id is None:
            raise RuntimeError(f'No subscription called "{target_name}" was found')
        
        return subscription_id
    # TODO: Can hardcode the subscription 
    def list_subscriptions(self):
        """
        List all subscriptions the signed-in identity can see.
        
        Returns:
            Iterator of subscriptions
        """
        return self.subscription_client.subscriptions.list()

    # Resource Group methods
    def list_rg_in_subscription(self):
        """
        List all resource groups in the current subscription.
        
        Returns:
            Iterator of resource groups
        """
        return self.resource_client.resource_groups.list()

    def list_resource_in_rg(self, resource_group):
        """
        List all resources in a specific resource group.
        
        Args:
            resource_group: Name of the resource group
            
        Returns:
            Iterator of resources in the resource group
        """
        return self.resource_client.resources.list_by_resource_group(
            resource_group_name=resource_group
        )

    def get_resource_group(self, resource_group_name):
        """
        Get details of a specific resource group.
        
        Args:
            resource_group_name: Name of the resource group
            
        Returns:
            Resource group details
        """
        return self.resource_client.resource_groups.get(resource_group_name)

    def list_resource_in_sub(self, resource_type: Optional[str] = None):
        """
        List resources in the subscription, optionally filtered by resource type.
        
        Args:
            resource_type: Optional resource type filter. Allowed values:
                - Microsoft.KeyVault/vaults
                - Microsoft.DataFactory/factories
                - Microsoft.Batch/batchAccounts
                
        Returns:
            Iterator of resources in the subscription
            
        Raises:
            ValueError: If an invalid resource type is provided
        """
        # Define allowed resource types
        allowed_resource_types = {
            "Microsoft.KeyVault/vaults",
            "Microsoft.DataFactory/factories", 
            "Microsoft.Batch/batchAccounts"
        }
        
        # Validate resource type if provided
        if resource_type and resource_type not in allowed_resource_types:
            raise ValueError(
                f"Invalid resource type '{resource_type}'. "
                f"Allowed types: {', '.join(sorted(allowed_resource_types))}"
            )
        
        # List resources with optional filter
        if resource_type:
            filter_str = f"resourceType eq '{resource_type}'"
            return [i.as_dict() for i in self.resource_client.resources.list(filter=filter_str)]
        else:
            return [i.as_dict() for i in self.resource_client.resources.list()]


    @staticmethod
    def run_cmd(msg):
        """Run a shell command and return the result"""
        return run(
            args=msg, stdout=PIPE, stderr=PIPE, universal_newlines=True, shell=True,
        )

