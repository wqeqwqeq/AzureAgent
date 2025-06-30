from typing import List, Union
from datetime import datetime
from ..base import AzureResourceBase
from ..auth import AzureAuthentication


class ADFTrigger(AzureResourceBase):
    def __init__(
        self,
        resource_group_name: str,
        resource_name: str,
        subscription_id: str = None,
        auth: AzureAuthentication = None,
    ):
        """
        Initialize ADF Trigger resource.

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