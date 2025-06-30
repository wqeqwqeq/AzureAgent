import json
from typing import Dict
from .base import AzureResourceBase
from .auth import AzureAuthentication


class AzureBatchPool(AzureResourceBase):
    def __init__(
        self,
        resource_group_name: str,
        resource_name: str,
        pool_name: str,
        subscription_id: str = None,
        auth: AzureAuthentication = None,
    ):
        """
        Initialize Azure Batch Pool operations.

        Args:
            resource_group_name: Name of the resource group
            resource_name: Name of the batch account
            pool_name: Name of the pool
            subscription_id: Optional subscription ID
            auth: Optional AzureAuthentication instance. If not provided, creates a new one
        """
        super().__init__(
            resource_group_name=resource_group_name,
            resource_name=resource_name,
            resource_type="batch",
            subscription_id=subscription_id,
            auth=auth,
        )
        self.pool_name = pool_name

    def get_pool_config(self) -> Dict:
        """
        Get the current configuration of the batch pool.

        Returns:
            Dict containing the pool configuration
        """
        try:
            response = self.client.pool.get(
                resource_group_name=self.resource_group_name,
                account_name=self.resource_name,
                pool_name=self.pool_name,
            )
            return response.as_dict()
        except Exception as e:
            print(f"Error getting pool configuration: {str(e)}")
            raise

    def scale_pool_nodes(self, target_nodes: int, dry_run: bool = True) -> Dict:
        """
        Scale the number of nodes in the batch pool.

        Args:
            target_nodes: Target number of nodes (0 or positive integer)
            dry_run: If True, only show what would be changed without making changes

        Returns:
            Dict containing the updated pool configuration
        """
        try:
            if target_nodes < 0:
                raise ValueError("Target nodes must be 0 or a positive integer")

            # Get current pool configuration
            pool_config = self.get_pool_config()
            current_nodes = (
                pool_config.get("scaleSettings", {})
                .get("fixedScale", {})
                .get("targetDedicatedNodes", 0)
            )

            print(f"Current node count: {current_nodes}")
            print(f"Target node count: {target_nodes}")

            if current_nodes == target_nodes:
                print(
                    f"Pool {self.pool_name} already has {target_nodes} nodes. No changes needed."
                )
                return pool_config

            # Update the scale settings
            pool_config["scaleSettings"] = {
                "fixedScale": {"targetDedicatedNodes": target_nodes}
            }

            if dry_run:
                print(
                    f"What if: Would scale pool {self.pool_name} to {target_nodes} nodes"
                )
                print("New configuration:")
                print(json.dumps(pool_config, indent=2))
                return pool_config

            # Update the pool
            response = self.client.pool.update(
                resource_group_name=self.resource_group_name,
                account_name=self.resource_name,
                pool_name=self.pool_name,
                parameters=pool_config,
            )

            print(f"Successfully scaled pool {self.pool_name} to {target_nodes} nodes")
            return response.as_dict()

        except Exception as e:
            print(f"Error scaling pool nodes: {str(e)}")
            raise 