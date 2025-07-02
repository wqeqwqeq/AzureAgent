import time
from typing import Dict, Optional, Union, List
from datetime import datetime
from ..base import AzureResourceBase
from ..auth import AzureAuthentication


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
        self, pipeline_name: str, activity_name: str = None, parameters: Optional[Dict] = None,
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