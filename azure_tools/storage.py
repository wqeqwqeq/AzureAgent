from typing import List, Dict
from .base import AzureResourceBase
from .auth import AzureAuthentication


class AzureStorage(AzureResourceBase):
    def __init__(
        self,
        resource_name: str,
        subscription_id: str = None,
        resource_group_name: str = None,
        auth: AzureAuthentication = None,
    ):
        """
        Initialize Azure Storage resource.

        Args:
            resource_group_name: Name of the resource group
            resource_name: Name of the Storage Account
            subscription_id: Azure subscription ID. If not provided, will be retrieved from Azure CLI
            auth: Optional AzureAuthentication instance. If not provided, creates a new one
        """
        super().__init__(
            resource_group_name=resource_group_name,
            resource_name=resource_name,
            resource_type="storage",
            subscription_id=subscription_id,
            auth=auth,
        )

    def list_containers(self) -> List[Dict]:
        """
        List all containers in the storage account.

        Returns:
            List of dictionaries containing container properties (name, last_modified, public_access)
        """
        try:
            containers = []
            for container in self.blob_service_client.list_containers():
                containers.append(
                    {
                        "name": container.name,
                        "last_modified": container.last_modified,
                        "public_access": container.public_access,
                    }
                )
            return containers
        except Exception as e:
            print(f"Error listing containers: {str(e)}")
            raise

    def list_blobs(self, container_name: str) -> List[Dict]:
        """
        List all blobs in a specific container.

        Args:
            container_name: Name of the container to list blobs from

        Returns:
            List of dictionaries containing blob properties (name, size, last_modified, content_type)
        """
        try:
            blobs = []
            container_client = self.blob_service_client.get_container_client(container_name)
            for blob in container_client.list_blobs():
                blobs.append(
                    {
                        "name": blob.name,
                        "size": blob.size,
                        "last_modified": blob.last_modified,
                        "content_type": blob.content_settings.content_type if blob.content_settings else None,
                    }
                )
            return blobs
        except Exception as e:
            print(f"Error listing blobs in container {container_name}: {str(e)}")
            raise

    def create_container_if_not_exists(self, container_name: str, public_access: str = None) -> None:
        """
        Create a container if it doesn't exist.

        Args:
            container_name: Name of the container to create
            public_access: Public access level ('blob', 'container', or None for private)
        """
        try:
            container_client = self.blob_service_client.get_container_client(container_name)
            if not container_client.exists():
                container_client.create_container(public_access=public_access)
                print(
                    f"Successfully created container {container_name} in {self.resource_name}"
                )
            else:
                print(f"Container {container_name} already exists in {self.resource_name}")
        except Exception as e:
            print(f"Error creating container {container_name}: {str(e)}")
            raise


class AzureStorageCopy:
    def __init__(
        self,
        sourceStgName: str,
        targetStgName: str,
    ):
        """
        Initialize Azure Storage Copy operations between two storage accounts.

        Args:
            sourceSTG: Source AzureStorage instance
            targetSTG: Target AzureStorage instance
        """
        self.sourceSTG = AzureStorage(resource_name=sourceStgName)
        self.targetSTG = AzureStorage(resource_name=targetStgName)

    def copy_blob(
        self, 
        source_container: str, 
        source_blob: str, 
        target_container: str, 
        target_blob: str = None, 
        overwrite: bool = True
    ) -> None:
        """
        Copy one blob from source storage account to target storage account.

        Args:
            source_container: Name of the source container
            source_blob: Name of the source blob
            target_container: Name of the target container
            target_blob: Name of the target blob (defaults to source_blob if not provided)
            overwrite: Whether to overwrite existing blob, default is True
        """
        try:
            if target_blob is None:
                target_blob = source_blob

            # Get source blob client
            source_blob_client = self.sourceSTG.blob_service_client.get_blob_client(
                container=source_container, blob=source_blob
            )
            
            # Get target blob client
            target_blob_client = self.targetSTG.blob_service_client.get_blob_client(
                container=target_container, blob=target_blob
            )
            
            # Ensure target container exists
            self.targetSTG.create_container_if_not_exists(target_container)
            
            # Copy blob using URL
            target_blob_client.upload_blob_from_url(
                source_url=source_blob_client.url, overwrite=overwrite
            )
            
            print(
                f"Successfully copied blob {source_blob} from {self.sourceSTG.resource_name}/{source_container} "
                f"to {self.targetSTG.resource_name}/{target_container}/{target_blob}"
            )
        except Exception as e:
            print(f"Error copying blob {source_blob}: {str(e)}")
            raise

    def copy_container(
        self, 
        source_container: str, 
        target_container: str = None, 
        overwrite: bool = True
    ) -> None:
        """
        Copy entire container from source storage account to target storage account.

        Args:
            source_container: Name of the source container
            target_container: Name of the target container (defaults to source_container if not provided)
            overwrite: Whether to overwrite existing blobs
        """
        try:
            if target_container is None:
                target_container = source_container

            # List all blobs in source container
            blobs = self.sourceSTG.list_blobs(source_container)
            
            # Ensure target container exists
            self.targetSTG.create_container_if_not_exists(target_container)
            
            copied_count = 0
            for blob in blobs:
                try:
                    self.copy_blob(
                        source_container=source_container,
                        source_blob=blob["name"],
                        target_container=target_container,
                        target_blob=blob["name"],
                        overwrite=overwrite
                    )
                    copied_count += 1
                except Exception as e:
                    print(f"Failed to copy blob {blob['name']}: {str(e)}")
                    continue
            
            print(
                f"Successfully copied {copied_count}/{len(blobs)} blobs from "
                f"{self.sourceSTG.resource_name}/{source_container} to "
                f"{self.targetSTG.resource_name}/{target_container}"
            )
        except Exception as e:
            print(f"Error copying container {source_container}: {str(e)}")
            raise
