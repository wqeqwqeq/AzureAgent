import requests
import time
from ..base import AzureResourceBase
from ..auth import AzureAuthentication


class ADFIntegrationRuntime(AzureResourceBase):
    def __init__(
        self,
        resource_group_name: str,
        resource_name: str,
        subscription_id: str = None,
        auth: AzureAuthentication = None,
    ):
        """
        Initialize ADF Integration Runtime resource.

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

    def get_ir(self, ir_name):
        """
        Get the details of an integration runtime
        Returns the JSON response from the API
        """
        try:
            # Construct the API URL
            ir_resource_id = f"subscriptions/{self.subscription_id}/resourcegroups/{self.resource_group_name}/providers/Microsoft.DataFactory/factories/{self.resource_name}/integrationruntimes/{ir_name}"
            api_url = f"https://management.azure.com/{ir_resource_id}/getStatus?api-version=2018-06-01"

            # Make the API call
            headers = {
                "Authorization": f"Bearer {self._get_token()}",
                "Content-Type": "application/json",
            }

            response = requests.post(api_url, headers=headers)
            response.raise_for_status()

            return response.json()
        except Exception as e:
            print(f"Error getting integration runtime details: {str(e)}")
            raise

    def get_ir_status(self, ir_name):
        """
        Get the status of an integration runtime
        Returns True if interactive authoring is enabled, False otherwise
        """
        try:
            status_data = self.get_ir(ir_name)
            interactive_status = (
                status_data.get("properties", {})
                .get("typeProperties", {})
                .get("interactiveQuery", {})
                .get("status")
            )

            is_enabled = interactive_status == "Enabled"
            return is_enabled
        except Exception as e:
            print(f"Error getting integration runtime status: {str(e)}")
            raise

    def get_ir_type(self, ir_name):
        """
        Get the type of an integration runtime
        Returns the type as a string (e.g., "Managed", "SelfHosted", etc.)
        """
        try:
            # Fetch the integration runtime details
            ir_details = self.get_ir(ir_name)

            # Extract the type from the JSON response
            ir_type = ir_details.get("properties", {}).get("type", None)

            if ir_type is None:
                raise ValueError(f"Integration runtime type not found for {ir_name}")

            return ir_type
        except Exception as e:
            print(f"Error getting integration runtime type: {str(e)}")
            raise

    def enable_interactive_authoring(self, ir_name, minutes=10):
        """
        Enable interactive authoring for the specified integration runtime.
        Only works for Managed integration runtimes.
        """
        # First check if it's a Managed integration runtime
        ir_type = self.get_ir_type(ir_name)
        if ir_type != "Managed":
            print(
                f"Interactive authoring is only supported for Managed integration runtimes. Current type: {ir_type}"
            )
            return

        # Check if interactive authoring is already enabled
        if self.get_ir_status(ir_name):
            print(
                f"Interactive authoring is already enabled for integration runtime {ir_name}"
            )
            return

        # Construct the API URL
        ir_resource_id = f"subscriptions/{self.subscription_id}/resourcegroups/{self.resource_group_name}/providers/Microsoft.DataFactory/factories/{self.resource_name}/integrationruntimes/{ir_name}"
        api_url = f"https://management.azure.com/{ir_resource_id}/enableInteractiveQuery?api-version=2018-06-01"

        # Make the API call
        headers = {
            "Authorization": f"Bearer {self._get_token()}",
            "Content-Type": "application/json",
        }
        body = {"autoTerminationMinutes": minutes}

        response = requests.post(api_url, headers=headers, json=body)
        response.raise_for_status()

        print(f"Successfully triggered interactive authoring for {minutes} minutes")
        while not self.get_ir_status(ir_name):
            print("Waiting for interactive authoring to be enabled...")
            time.sleep(10)
        print("Interactive authoring is now enabled") 