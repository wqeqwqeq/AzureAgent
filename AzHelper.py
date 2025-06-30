# %%
from azure.identity import DefaultAzureCredential
from azure.mgmt.datafactory import DataFactoryManagementClient
from azure.mgmt.batch import BatchManagementClient
from azure.keyvault.secrets import SecretClient
from azure.mgmt.resource.locks import ManagementLockClient
import requests, time, json, re
from datetime import datetime, timedelta
from typing import List, Dict, Union, Literal
from subprocess import PIPE, run


class AzureAuthentication:
    """
    Shared authentication class for Azure resources.
    Manages credentials and tokens that can be shared across multiple resource instances.
    """
    
    def __init__(self, subscription_id: str = None):
        """
        Initialize Azure authentication.
        
        Args:
            subscription_id: Azure subscription ID. If not provided, will be retrieved from Azure CLI
        """
        self.credential = DefaultAzureCredential()
        self.token = None
        self.token_expiry = None
        self.subscription_id = subscription_id or self.get_subscription_id()
    
    def get_subscription_id(self):
        """Get the current subscription ID using Azure CLI"""
        cmd = "az account show --query id --output tsv"
        return self.run_cmd(cmd).stdout.strip()
    
    def get_token(self):
        """
        Get a new token if current one is expired or doesn't exist.
        Returns cached token if still valid.
        """
        now = datetime.now()
        if (
            self.token is None
            or self.token_expiry is None
            or (self.token_expiry is not None and now >= self.token_expiry)
        ):
            print("Generating new token...")
            token_response = self.credential.get_token(
                "https://management.azure.com/.default"
            )
            self.token = token_response.token
            # Convert expires_on (Unix timestamp) to datetime
            self.token_expiry = datetime.fromtimestamp(
                token_response.expires_on
            ) - timedelta(minutes=5)
        return self.token
    
    @staticmethod
    def run_cmd(msg):
        """Run a shell command and return the result"""
        return run(
            args=msg, stdout=PIPE, stderr=PIPE, universal_newlines=True, shell=True,
        )


class AzureResourceBase:
    def __init__(
        self,
        resource_group_name: str,
        resource_name: str,
        resource_type: Literal["adf", "batch", "keyvault", "locks"],
        subscription_id: str = None,
        auth: AzureAuthentication = None,
    ):
        """
        Base class for Azure resource operations.

        Args:
            resource_group_name: Name of the resource group
            resource_name: Name of the resource (ADF factory, Batch account, or Key Vault)
            resource_type: Type of resource ('adf', 'batch', 'keyvault', or 'locks')
            subscription_id: Azure subscription ID. If not provided, will be retrieved from Azure CLI
            auth: Optional AzureAuthentication instance. If not provided, creates a new one
        """
        self.resource_group_name = resource_group_name
        self.resource_name = resource_name
        self.resource_type = resource_type.lower()
        
        # Use provided auth instance or create a new one
        if auth is not None:
            self.auth = auth
            self.subscription_id = auth.subscription_id
        else:
            self.auth = AzureAuthentication(subscription_id)
            self.subscription_id = self.auth.subscription_id
        
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
        else:
            raise ValueError(
                f"Unsupported resource type: {resource_type}. Must be 'adf', 'batch', 'keyvault', or 'locks'"
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

    @staticmethod
    def run_cmd(msg):
        """Run a shell command and return the result"""
        return AzureAuthentication.run_cmd(msg)


class ADFLinkedServices(AzureResourceBase):
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

    def get_linked_service_sdk(self, linked_service_name):
        """
        Get the details of a linked service using Azure SDK.
        """
        try:
            response = self.client.linked_services.get(
                resource_group_name=self.resource_group_name,
                factory_name=self.resource_name,
                linked_service_name=linked_service_name,
            )
            return response.as_dict()
        except Exception as e:
            print(f"Error getting linked service details using SDK: {str(e)}")
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
                    f"(?<=://){re.escape(old_fqdn)}(?=\.)", new_fqdn, connection_string,
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
                    f"(?<=://){re.escape(old_fqdn)}(?=\.)",
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


class ADFManagedPrivateEndpoint(AzureResourceBase):
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


class ADFIntegrationRuntime(AzureResourceBase):
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


class AzureKeyVault(AzureResourceBase):
    def get_secret(self, secret_name: str) -> str:
        """
        Get a secret from the key vault.

        Args:
            secret_name: Name of the secret to retrieve

        Returns:
            The secret value as a string
        """
        try:
            secret = self.secret_client.get_secret(secret_name)
            return secret.value
        except Exception as e:
            print(f"Error getting secret {secret_name}: {str(e)}")
            raise

    def list_secrets(self) -> List[Dict]:
        """
        List all secrets in the current key vault.

        Returns:
            List of dictionaries containing secret properties (name, created_on, updated_on, enabled)
        """
        try:
            secrets = []
            for secret in self.secret_client.list_properties_of_secrets():
                secrets.append(
                    {
                        "name": secret.name,
                        "created_on": secret.created_on,
                        "updated_on": secret.updated_on,
                        "enabled": secret.enabled,
                    }
                )
            return secrets
        except Exception as e:
            print(f"Error listing secrets: {str(e)}")
            raise

    def set_secret(self, secret_name: str, secret_value: str) -> None:
        """
        Set a secret in the key vault.

        Args:
            secret_name: Name of the secret to set
            secret_value: Value of the secret to set
        """
        try:
            self.secret_client.set_secret(secret_name, secret_value)
            print(
                f"Successfully set secret {secret_name} in {self.resource_name} under {self.resource_group_name}"
            )
        except Exception as e:
            print(f"Error setting secret {secret_name}: {str(e)}")
            raise


class AzureResourceLock(AzureResourceBase):
    def __init__(
        self, 
        resource_group_name: str, 
        subscription_id: str = None,
        auth: AzureAuthentication = None,
    ):
        """
        Initialize Azure Resource Locker operations.

        Args:
            resource_group_name: Name of the resource group
            subscription_id: Azure subscription ID. If not provided, will be retrieved from Azure CLI
            auth: Optional AzureAuthentication instance. If not provided, creates a new one
        """
        super().__init__(
            resource_group_name=resource_group_name,
            resource_name=None,  # Not needed for lock operations
            resource_type="locks",  # Custom type for lock operations
            subscription_id=subscription_id,
            auth=auth,
        )
        self.lock_client = ManagementLockClient(
            credential=self.credential, subscription_id=self.subscription_id
        )
        # Initialize lock objects
        self.lock_objs = self.get_locks()
        self.deleted = False

    def get_locks(self) -> List:
        """
        Get all locks in the resource group.

        Returns:
            List of lock objects, empty list if no locks exist
        """
        try:
            all_locks = self.lock_client.management_locks.list_at_resource_group_level(
                resource_group_name=self.resource_group_name
            )

            # Convert ItemPaged to list
            lock_list = list(all_locks)

            if not lock_list:
                print(f"No locks found in resource group {self.resource_group_name}")
            else:
                print(
                    f"Found {len(lock_list)} locks in resource group {self.resource_group_name}"
                )

            return lock_list

        except Exception as e:
            print(f"Error getting resource locks: {str(e)}")
            raise

    def release_locks(self) -> None:
        """
        Delete all locks in the resource group.

        Returns:
            List of lock objects that were deleted
        """
        try:
            if not self.lock_objs:
                print("No locks to delete")
                return

            for lock in self.lock_objs:
                self.lock_client.management_locks.delete_at_resource_group_level(
                    self.resource_group_name, lock.name
                )
                print(f"Temporarily released lock: {lock.name}")

            self.deleted = True
        except Exception as e:
            print(f"Error managing resource locks: {str(e)}")
            raise

    def recreate_locks(self) -> None:
        """
        Recreate locks in the resource group.
        Only works if locks were previously deleted.
        """
        try:
            if not self.lock_objs:
                print("No locks to recreate")
                return

            if not self.deleted:
                print("Locks were not deleted, skipping recreation")
                return

            for lock in self.lock_objs:
                self.lock_client.management_locks.create_or_update_at_resource_group_level(
                    resource_group_name=self.resource_group_name,
                    lock_name=lock.name,
                    parameters={"level": lock.level, "notes": lock.notes},
                )
                print(f"Reset lock: {lock.name}")

        except Exception as e:
            print(f"Error recreating resource locks: {str(e)}")
            raise

    def create_lock(
        self, lock_name: str, level: str = "CanNotDelete", notes: str = None
    ) -> None:
        """
        Create a new resource lock at the resource group level.

        Args:
            lock_name: Name of the lock to create
            level: Lock level, either "CanNotDelete" or "ReadOnly". Defaults to "CanNotDelete"
            notes: Optional notes about the lock
        """
        try:
            if level not in ["CanNotDelete", "ReadOnly"]:
                raise ValueError(
                    "Lock level must be either 'CanNotDelete' or 'ReadOnly'"
                )

            # Check if lock already exists
            for lock in self.lock_objs:
                if lock.name == lock_name:
                    print(f"Lock {lock_name} already exists")
                    return

            # Create the lock
            self.lock_client.management_locks.create_or_update_at_resource_group_level(
                resource_group_name=self.resource_group_name,
                lock_name=lock_name,
                parameters={"level": level, "notes": notes},
            )
            print(f"Created lock: {lock_name} with level {level}")

            # Update local lock objects
            self.lock_objs = self.get_locks()

        except Exception as e:
            print(f"Error creating resource lock: {str(e)}")
            raise


class ADFTrigger(AzureResourceBase):
    # Valid trigger types in Azure Data Factory
    VALID_TRIGGER_TYPES = {
        "TumblingWindowTrigger",
        "ScheduleTrigger",
    }

    def list_triggers(self, trigger_type: str = None) -> List:
        """
        List all triggers in the Data Factory, optionally filtered by type.
        By default, only shows Schedule and TumblingWindow triggers.

        Args:
            trigger_type: Optional trigger type to filter by. Must be one of:
                - TumblingWindowTrigger
                - ScheduleTrigger

        Returns:
            List of trigger objects, filtered by type if specified

        Raises:
            ValueError: If an invalid trigger type is specified
        """
        try:
            if trigger_type and trigger_type not in self.VALID_TRIGGER_TYPES:
                raise ValueError(
                    f"Invalid trigger type: {trigger_type}. "
                    f"Must be one of: {', '.join(sorted(self.VALID_TRIGGER_TYPES))}"
                )

            print(f"Listing all triggers in the Data Factory: {self.resource_name}")
            triggers = self.client.triggers.list_by_factory(
                self.resource_group_name, self.resource_name
            )

            # Convert ItemPaged to list and filter
            trigger_list = list(triggers)

            # Filter by specific type if provided, otherwise only show schedule and tumbling
            if trigger_type:
                filtered_triggers = [
                    trigger
                    for trigger in trigger_list
                    if trigger.properties.type == trigger_type
                ]
                print(f"Found {len(filtered_triggers)} {trigger_type} triggers")
                return filtered_triggers
            else:
                filtered_triggers = [
                    trigger
                    for trigger in trigger_list
                    if trigger.properties.type in self.VALID_TRIGGER_TYPES
                ]
                print(f"Found {len(filtered_triggers)} schedule/tumbling triggers")
                return filtered_triggers

        except Exception as e:
            print(f"Error listing triggers: {str(e)}")
            raise

    def manage_trigger(self, trigger_name: str, action: str) -> None:
        """
        Manage a specific trigger (start/stop).

        Args:
            trigger_name: Name of the trigger to manage
            action: Action to perform ('start' or 'stop')
        """
        try:
            trigger_obj = self.client.triggers.get(
                self.resource_group_name, self.resource_name, trigger_name
            )
            print(f"Current trigger state: {trigger_obj.properties.runtime_state}")

            if action == "stop" and trigger_obj.properties.runtime_state == "Started":
                print(f"Stopping trigger: {trigger_name}")
                operation = self.client.triggers.begin_stop(
                    self.resource_group_name, self.resource_name, trigger_name
                )
                operation.wait()
                print(f"Trigger {trigger_name} stopped")
            elif (
                action == "start" and trigger_obj.properties.runtime_state == "Stopped"
            ):
                print(f"Starting trigger: {trigger_name}")
                operation = self.client.triggers.begin_start(
                    self.resource_group_name, self.resource_name, trigger_name
                )
                operation.wait()
                print(f"Trigger {trigger_name} started")
            else:
                print(
                    f"Trigger {trigger_name} is already in the desired state, skipping {action}"
                )

        except Exception as e:
            print(f"Error managing trigger {trigger_name}: {str(e)}")
            raise

    def manage_all_triggers(self, action: str) -> None:
        """
        Manage all triggers in the Data Factory (start/stop).

        Args:
            action: Action to perform ('start' or 'stop')
        """
        try:
            print(
                f"Managing all triggers in Data Factory: {self.resource_name} with action: {action}"
            )
            triggers = self.list_triggers()

            for trigger in triggers:
                print(
                    f"Working on {trigger.name} under {self.resource_group_name}/{self.resource_name}..."
                )
                self.manage_trigger(trigger.name, action)

        except Exception as e:
            print(f"Error managing all triggers: {str(e)}")
            raise

    def reset_tumbling_with_start_time(
        self, trigger_name: str, new_start_time: Union[str, datetime]
    ) -> None:
        """
        Reset the start time of a tumbling window trigger by recreating it.
        This is necessary because start time cannot be updated directly.

        Args:
            trigger_name: Name of the trigger to reset
            new_start_time: New start time as either:
                - ISO 8601 format string (e.g., '2024-03-20T00:00:00Z')
                - datetime object

        Raises:
            ValueError: If the trigger is not a tumbling window trigger
            ValueError: If the start time string is not in valid ISO 8601 format
        """
        try:
            # Convert string to datetime if needed
            if isinstance(new_start_time, str):
                try:
                    new_start_time = datetime.fromisoformat(
                        new_start_time.replace("Z", "+00:00")
                    )
                except ValueError as e:
                    raise ValueError(
                        f"Invalid start time format. Must be ISO 8601 format (e.g., '2024-03-20T00:00:00Z'). Error: {str(e)}"
                    )

            # Get the trigger details
            trigger_obj = self.client.triggers.get(
                self.resource_group_name, self.resource_name, trigger_name
            )

            # Verify it's a tumbling window trigger
            if trigger_obj.properties.type != "TumblingWindowTrigger":
                raise ValueError(
                    f"Trigger {trigger_name} is not a tumbling window trigger. "
                    f"Found type: {trigger_obj.properties.type}"
                )

            # Store original state and properties
            original_state = trigger_obj.properties.runtime_state
            trigger_properties = trigger_obj.properties

            # Stop the trigger if it's running
            if original_state == "Started":
                print(f"Stopping trigger {trigger_name} before recreation...")
                self.manage_trigger(trigger_name, "stop")

            # Delete the trigger
            print(f"Deleting trigger {trigger_name}... temporarily")
            self.client.triggers.delete(
                self.resource_group_name, self.resource_name, trigger_name
            )

            # Update the start time in the properties
            trigger_properties.start_time = new_start_time

            # Recreate the trigger with updated start time
            print(f"Recreating trigger {trigger_name} with new start time...")
            self.client.triggers.create_or_update(
                self.resource_group_name, self.resource_name, trigger_name, trigger_obj,
            )

            # Restore original state if it was running
            if original_state == "Started":
                print(f"Restoring trigger {trigger_name} to running state...")
                self.manage_trigger(trigger_name, "start")

            print(
                f"Successfully reset start time for trigger {trigger_name} to {new_start_time}"
            )

        except Exception as e:
            print(f"Error resetting trigger start time: {str(e)}")
            raise


class ADFPipeline(AzureResourceBase):
    def __init__(
        self, 
        resource_group_name: str, 
        resource_name: str, 
        subscription_id: str = None,
        auth: AzureAuthentication = None,
    ):
        """
        Initialize Azure Data Factory Pipeline operations.

        Args:
            resource_group_name: Name of the resource group
            resource_name: Name of the ADF factory
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
        self.run_id = None

    def create_run(self, pipeline_name: str, parameters: Dict = None) -> str:
        """
        Create a pipeline run and store the run ID as instance variable.

        Args:
            pipeline_name: Name of the pipeline to run
            parameters: Optional dictionary of parameters to pass to the pipeline

        Returns:
            Pipeline run ID as a string
        """
        try:
            print(f"Starting pipeline: {pipeline_name}")

            # Prepare parameters if provided
            pipeline_parameters = parameters or {}

            # Create pipeline run
            run_response = self.client.pipelines.create_run(
                resource_group_name=self.resource_group_name,
                factory_name=self.resource_name,
                pipeline_name=pipeline_name,
                parameters=pipeline_parameters,
            )

            self.run_id = run_response.run_id
            return self.run_id

        except Exception as e:
            print(f"Error starting pipeline {pipeline_name}: {str(e)}")
            raise

    def check_status(self) -> Dict:
        """
        Check the status of the current pipeline run.

        Returns:
            Dictionary containing pipeline run details including status
        """
        try:
            if not self.run_id:
                raise ValueError("No active pipeline run. Call create_run() first.")

            run_details = self.client.pipeline_runs.get(
                resource_group_name=self.resource_group_name,
                factory_name=self.resource_name,
                run_id=self.run_id,
            )
            return run_details.as_dict()

        except Exception as e:
            print(f"Error getting pipeline run status for {self.run_id}: {str(e)}")
            raise

    def fetch_activity(self, activity_name: str = None) -> Union[Dict, List[Dict]]:
        """
        Fetch activity results after pipeline run is successful.

        Args:
            activity_name: Optional specific activity name. If None, returns all activities.

        Returns:
            Dictionary for specific activity or List of dictionaries for all activities
        """
        try:
            if not self.run_id:
                raise ValueError("No active pipeline run. Call create_run() first.")

            # Check if pipeline is successful
            status_result = self.check_status()
            if status_result.get("status") != "Succeeded":
                print(
                    f"Warning: Pipeline status is {status_result.get('status')}, not 'Succeeded'"
                )

            # Get pipeline run details to get timing
            run_start = status_result.get("runStart")
            run_end = status_result.get("runEnd") or datetime.utcnow().isoformat() + "Z"

            # Query activity runs
            activity_runs = self.client.activity_runs.query_by_pipeline_run(
                resource_group_name=self.resource_group_name,
                factory_name=self.resource_name,
                run_id=self.run_id,
                filter_parameters={
                    "lastUpdatedAfter": run_start,
                    "lastUpdatedBefore": run_end,
                },
            )

            activities_list = [run.as_dict() for run in activity_runs.value]

            # Return all activities if no specific name provided
            if activity_name is None:
                print(f"Retrieved {len(activities_list)} activities")
                return activities_list

            # Find specific activity
            for activity in activities_list:
                if activity.get("activity_name") == activity_name:
                    print(
                        f"Found activity {activity_name} with status: {activity.get('status')}"
                    )
                    return activity

        except Exception as e:
            print(f"Error fetching activity results: {str(e)}")
            raise

    def run_and_fetch(
        self, pipeline_name: str, activity_name: str = None, parameters: Dict = None,
    ):
        """
        Wrapper to run pipeline and fetch activity results.

        Args:
            pipeline_name: Name of the pipeline to run
            activity_name: Optional specific activity name. If None, returns all activities.
            parameters: Optional dictionary of parameters to pass to the pipeline

        Returns:
            Dictionary for specific activity or List of dictionaries for all activities
        """
        try:
            # Create and run pipeline
            self.create_run(pipeline_name, parameters)

            # Wait for completion
            print("Waiting for pipeline to complete...")
            while True:
                status_result = self.check_status()
                status = status_result.get("status")
                print(f"Pipeline status: {status}")

                if status in ["Succeeded", "Failed", "Cancelled"]:
                    break

                time.sleep(10)  # Wait 10 seconds before checking again

            # Fetch activity results
            if status == "Succeeded":
                return self.fetch_activity(activity_name)["output"]["resultSets"]
            else:
                raise Exception(f"Pipeline failed with status: {status}")

        except Exception as e:
            print(f"Error in run_and_fetch: {str(e)}")
            raise


# %%
