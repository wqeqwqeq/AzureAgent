from typing import List, Dict
from .base import AzureResourceBase
from .auth import AzureAuthentication


class AzureKeyVault(AzureResourceBase):
    def __init__(
        self,
        resource_group_name: str,
        resource_name: str,
        subscription_id: str = None,
        auth: AzureAuthentication = None,
    ):
        """
        Initialize Azure Key Vault resource.

        Args:
            resource_group_name: Name of the resource group
            resource_name: Name of the Key Vault
            subscription_id: Azure subscription ID. If not provided, will be retrieved from Azure CLI
            auth: Optional AzureAuthentication instance. If not provided, creates a new one
        """
        super().__init__(
            resource_group_name=resource_group_name,
            resource_name=resource_name,
            resource_type="keyvault",
            subscription_id=subscription_id,
            auth=auth,
        )

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