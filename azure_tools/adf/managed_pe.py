from typing import Dict
from ..base import AzureResourceBase
from ..auth import AzureAuthentication


class ADFManagedPrivateEndpoint(AzureResourceBase):
    def __init__(
        self,
        resource_group_name: str,
        resource_name: str,
        subscription_id: str = None,
        auth: AzureAuthentication = None,
    ):
        """
        Initialize ADF Managed Private Endpoint resource.

        Args:
            resource_group_name: Name of the resource group
            resource_name: Name of the Azure Data Factory
            subscription_id: Azure subscription ID. If not provided, will be retrieved from Azure CLI
            auth: Optional AzureAuthentication instance. If not provided, creates a new one
        """
        super().__init__(
            resource_group_name=resource_group_name,
            resource_name=resource_name,
            resource_type="adf",
            subscription_id=subscription_id,
            auth=auth,
        )

    def get_managed_private_endpoint(
        self, managed_private_endpoint_name: str, managed_vnet_name: str = "default",
    ) -> Dict:
        """
        Get details of a managed private endpoint in Azure Data Factory.
        """
        try:
            response = self.client.managed_private_endpoints.get(
                resource_group_name=self.resource_group_name,
                factory_name=self.resource_name,
                managed_virtual_network_name=managed_vnet_name,
                managed_private_endpoint_name=managed_private_endpoint_name,
            )
            return response.as_dict()
        except Exception as e:
            print(f"Error getting managed private endpoint details: {str(e)}")
            raise

    def update_managed_private_endpoint_fqdn(
        self, managed_private_endpoint_name, fqdns, managed_vnet_name="default"
    ):
        """
        Update the FQDN in a managed private endpoint while preserving other properties.
        """
        try:
            existing_endpoint = self.get_managed_private_endpoint(
                managed_private_endpoint_name=managed_private_endpoint_name,
                managed_vnet_name=managed_vnet_name,
            )

            response = self.client.managed_private_endpoints.create_or_update(
                resource_group_name=self.resource_group_name,
                factory_name=self.resource_name,
                managed_virtual_network_name=managed_vnet_name,
                managed_private_endpoint_name=managed_private_endpoint_name,
                managed_private_endpoint={
                    "properties": {
                        "fqdns": fqdns,
                        "groupId": existing_endpoint["properties"]["group_id"],
                        "privateLinkResourceId": existing_endpoint["properties"][
                            "private_link_resource_id"
                        ],
                    }
                },
            )
            print(
                f"Successfully updated managed private endpoint: {managed_private_endpoint_name}"
            )
            return response
        except Exception as e:
            print(f"Error updating managed private endpoint: {str(e)}")
            raise 