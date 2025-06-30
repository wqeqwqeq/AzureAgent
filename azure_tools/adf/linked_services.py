import requests
import json
import re
from typing import List, Dict, Union
from ..base import AzureResourceBase
from ..auth import AzureAuthentication


class ADFLinkedServices(AzureResourceBase):
    def __init__(
        self,
        resource_group_name: str,
        resource_name: str,
        subscription_id: str = None,
        auth: AzureAuthentication = None,
    ):
        """
        Initialize ADF Linked Services resource.

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

    def list_linked_services(
        self, filter_by_type: Union[str, List[str]] = None
    ) -> List[Dict]:
        """
        List all linked services in the Azure Data Factory.
        """
        try:
            # Get all linked services
            linked_services = self.client.linked_services.list_by_factory(
                resource_group_name=self.resource_group_name,
                factory_name=self.resource_name,
            )

            # Convert to list of dictionaries and filter if needed
            services_list = []
            for service in linked_services:
                service_dict = service.as_dict()

                # If filter_by_type is specified, check if service type matches
                if filter_by_type:
                    service_type = service_dict.get("properties", {}).get("type")
                    if isinstance(filter_by_type, str):
                        # Single type filter
                        if service_type == filter_by_type:
                            services_list.append(service_dict)
                    elif isinstance(filter_by_type, list):
                        # Multiple type filter
                        if service_type in filter_by_type:
                            services_list.append(service_dict)
                else:
                    services_list.append(service_dict)

            return services_list

        except Exception as e:
            print(f"Error listing linked services: {str(e)}")
            raise

    def get_linked_service_details(self, linked_service_name):
        """
        Get the details of a linked service using API calls.
        """
        try:
            # Construct the API URL
            api_url = f"https://management.azure.com/subscriptions/{self.subscription_id}/resourcegroups/{self.resource_group_name}/providers/Microsoft.DataFactory/factories/{self.resource_name}/linkedservices/{linked_service_name}?api-version=2018-06-01"

            # Make the API call
            headers = {
                "Authorization": f"Bearer {self._get_token()}",
                "Content-Type": "application/json",
            }

            response = requests.get(api_url, headers=headers)
            response.raise_for_status()

            return response.json()
        except Exception as e:
            print(f"Error getting linked service details: {str(e)}")
            raise


    def update_linked_service_sf_account(
        self,
        linked_service_name: str,
        old_fqdn: str,
        new_fqdn: str,
        dry_run: bool = True,
    ) -> Dict:
        """
        Update the Snowflake account FQDN in a linked service.
        """
        try:
            # Get the current linked service details
            linked_service = self.get_linked_service_details(linked_service_name)

            # Check if it's a Snowflake service
            service_type = linked_service.get("properties", {}).get("type")
            print(
                f"\nUpdating {service_type} Linked Service {linked_service_name} from {old_fqdn} to {new_fqdn}"
            )

            # Update the connection string based on Snowflake version
            if service_type == "Snowflake":
                # For Snowflake V1
                connection_string = linked_service["properties"]["typeProperties"][
                    "connectionString"
                ]
                new_connection_string = re.sub(
                    rf"(?<=://){re.escape(old_fqdn)}(?=\.)", new_fqdn, connection_string,
                )
                # Check if the regex found a match, no replacement happened
                if new_connection_string == connection_string:
                    print(
                        f"Warning: Could not find exact match for '{old_fqdn}' in connection string"
                    )
                    return
                print(f"New ConnectionString: {new_connection_string}")
                linked_service["properties"]["typeProperties"][
                    "connectionString"
                ] = new_connection_string

            else:
                # For Snowflake V2
                current_identifier = linked_service["properties"]["typeProperties"][
                    "accountIdentifier"
                ]
                new_identifier = re.sub(
                    rf"(?<=://){re.escape(old_fqdn)}(?=\.)",
                    new_fqdn,
                    current_identifier,
                )
                # Check if the regex found a match, no replacement happened
                if new_fqdn == current_identifier:
                    print(
                        f"Warning: Could not find exact match for '{old_fqdn}' in account identifier"
                    )
                    return
                linked_service["properties"]["typeProperties"][
                    "accountIdentifier"
                ] = new_fqdn

            if dry_run:
                print(f"What if: Would update linked service {linked_service_name}")
                print("New configuration:")
                print(json.dumps(linked_service, indent=2))
                return

            # Update the linked service using Azure SDK
            response = self.client.linked_services.create_or_update(
                resource_group_name=self.resource_group_name,
                factory_name=self.resource_name,
                linked_service_name=linked_service_name,
                linked_service=linked_service,
            )

            print(f"Successfully updated linked service: {linked_service_name}")
            return response.as_dict()

        except Exception as e:
            print(f"Error updating linked service: {str(e)}")
            raise

    def test_linked_service_connection(self, linked_service_name, parameters=None):
        """
        Test the connection of a linked service
        """
        try:
            # First get the linked service details
            linked_service = self.get_linked_service_details(linked_service_name)

            # If parameters are provided, update the linked service properties
            if parameters:
                linked_service["properties"]["parameters"] = parameters

            # Construct the test connectivity request body
            body = {"linkedService": linked_service}

            # Construct the API URL
            api_url = f"https://management.azure.com/subscriptions/{self.subscription_id}/resourcegroups/{self.resource_group_name}/providers/Microsoft.DataFactory/factories/{self.resource_name}/testConnectivity?api-version=2018-06-01"

            # Make the API call
            headers = {
                "Authorization": f"Bearer {self._get_token()}",
                "Content-Type": "application/json",
            }

            print("Testing linked service connection with the following configuration:")
            print(json.dumps(body, indent=2))

            response = requests.post(api_url, headers=headers, json=body)
            response.raise_for_status()

            result = response.json()
            if result.get("succeeded"):
                print("Linked service connection test successful")
            else:
                print(
                    f"Linked service connection test failed: {result.get('errors', [{}])[0].get('message', 'Unknown error')}"
                )

            return result
        except Exception as e:
            print(f"Error testing linked service connection: {str(e)}")
            raise 