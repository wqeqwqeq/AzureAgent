from typing import List
from azure.mgmt.resource.locks import ManagementLockClient
from .base import AzureResourceBase
from .auth import AzureAuthentication


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

            self.lock_objs = self.get_locks()
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