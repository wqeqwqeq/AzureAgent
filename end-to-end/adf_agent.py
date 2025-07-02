from __future__ import annotations
import logging
import os
import asyncio
import json
from dotenv import load_dotenv
from typing import List, Dict, Union, Optional

from openai import AsyncAzureOpenAI
from agents import Agent, Runner, function_tool, trace, set_default_openai_client, set_tracing_disabled, OpenAIChatCompletionsModel, set_tracing_export_api_key
# Import the ADF Linked Services class
from azure_tools.adf.linked_services import ADFLinkedServices

from DAPEAgent.config import settings

client = AsyncAzureOpenAI(
    api_key=settings.az_openai_api_key.get_secret_value(),
    api_version=settings.az_openai_api_version,
    azure_endpoint=settings.az_openai_endpoint,
    azure_deployment=settings.az_openai_deployment,
)

# set_default_openai_client(client)
# set_tracing_export_api_key(os.getenv("OPENAI_API_KEY"))
# # Set up tracing
# set_tracing_disabled(False)

# Initialize ADF Linked Services instance
# These would typically come from environment variables or configuration
adf_resource_group = os.getenv("ADF_RESOURCE_GROUP", "SQL-RG")
adf_factory_name = os.getenv("ADF_FACTORY_NAME", "adf-stanley")
# adf_subscription_id = os.getenv("ADF_SUBSCRIPTION_ID")

adf_service = ADFLinkedServices(
    resource_group_name=adf_resource_group,
    resource_name=adf_factory_name,
    # subscription_id=adf_subscription_id
)


@function_tool
def list_linked_services(filter_by_type: Optional[str] = None) -> str:
    """
    List all linked services in the Azure Data Factory.
    
    Args:
        filter_by_type: Optional filter to only show linked services of a specific type
    
    Returns:
        JSON string containing the list of linked services
    """
    try:
        services = adf_service.list_linked_services(filter_by_type=filter_by_type)
        return json.dumps(services, indent=2)
    except Exception as e:
        return f"Error listing linked services: {str(e)}"


@function_tool
def get_linked_service_details(linked_service_name: str) -> str:
    """
    Get detailed information about a specific linked service.
    
    Args:
        linked_service_name: Name of the linked service to get details for
    
    Returns:
        JSON string containing the linked service details
    """
    try:
        service_details = adf_service.get_linked_service_details(linked_service_name)
        return json.dumps(service_details, indent=2)
    except Exception as e:
        return f"Error getting linked service details: {str(e)}"


@function_tool
def update_snowflake_linked_service(
    linked_service_name: str,
    old_fqdn: str,
    new_fqdn: str,
    dry_run: bool = True
) -> str:
    """
    Update the Snowflake account FQDN in a linked service.
    
    Args:
        linked_service_name: Name of the Snowflake linked service to update
        old_fqdn: Current FQDN to replace
        new_fqdn: New FQDN to use
        dry_run: If True, only shows what would be changed without making actual changes
    
    Returns:
        Status message about the update operation
    """
    try:
        result = adf_service.update_linked_service_sf_account(
            linked_service_name=linked_service_name,
            old_fqdn=old_fqdn,
            new_fqdn=new_fqdn,
            dry_run=dry_run
        )
        
        if dry_run:
            return f"Dry run completed. Would update linked service '{linked_service_name}' from '{old_fqdn}' to '{new_fqdn}'"
        else:
            return f"Successfully updated linked service '{linked_service_name}' from '{old_fqdn}' to '{new_fqdn}'"
    except Exception as e:
        return f"Error updating linked service: {str(e)}"


@function_tool
def test_linked_service_connection(linked_service_name: str) -> str:
    """
    Test the connection of a linked service.
    
    Args:
        linked_service_name: Name of the linked service to test
    
    Returns:
        Result of the connection test
    """
    try:
        test_result = adf_service.test_linked_service_connection(linked_service_name)
        
        if test_result.get("succeeded"):
            return f"Connection test successful for linked service '{linked_service_name}'"
        else:
            error_message = test_result.get("errors", [{}])[0].get("message", "Unknown error")
            return f"Connection test failed for linked service '{linked_service_name}': {error_message}"
    except Exception as e:
        return f"Error testing linked service connection: {str(e)}"



# Create the ADF Linked Services agent
adf_agent = Agent(
    name="ADF Linked Services Specialist",
    instructions="""You are an Azure Data Factory Linked Services specialist.
    
    You help users manage ADF linked services including:
    - Listing all linked services or filtering by type
    - Getting detailed information about specific linked services
    - Updating Snowflake linked service configurations (FQDN changes)
    - Testing linked service connections
    
    Always be professional and provide clear explanations of operations.
    When updating linked services, always suggest doing a dry run first to preview changes.
    If connection tests fail, provide helpful troubleshooting suggestions.
    
    Available operations:
    - list_linked_services: Get all linked services, optionally filtered by type
    - get_linked_service_details: Get detailed configuration of a specific linked service
    - update_snowflake_linked_service: Update Snowflake FQDN in linked services
    - test_linked_service_connection: Test if a linked service can connect successfully
    """,
    model=OpenAIChatCompletionsModel(
        model="gpt-4o-mini",
        openai_client=client
    ),
    tools=[
        list_linked_services,
        get_linked_service_details,
        update_snowflake_linked_service,
        test_linked_service_connection,
    ],
)


async def main():
    """Demonstrate the ADF Linked Services agent functionality."""
    with trace(workflow_name="ADF Linked Services Demo"):
        print("\n=== ADF Linked Services Agent Demo ===\n")
        
        # 1. List all linked services
        print("Step 1: List all linked services")
        result = await Runner.run(
            adf_agent,
            input="Can you show me all the linked services in my ADF?"
        )
        print(f"\nResponse: {result.final_output}\n")

        # 2. Filter linked services by type
        print("Step 2: Filter linked services by Snowflake type")
        result = await Runner.run(
            adf_agent,
            input=result.to_input_list()
            + [{"content": "Now show me only the Snowflake linked services.", "role": "user"}]
        )
        print(f"\nResponse: {result.final_output}\n")

        # 3. Get details of a specific linked service
        print("Step 3: Get details of a specific linked service")
        result = await Runner.run(
            adf_agent,
            input=result.to_input_list()  
            + [{"content": "Can you get the details for the first linked service you found?", "role": "user"}]
        )
        print(f"\nResponse: {result.final_output}\n")

        # 4. Perform a dry run update
        print("Step 4: Perform a dry run update of Snowflake FQDN")
        result = await Runner.run(
            adf_agent,
            input=result.to_input_list()
            + [{"content": "I need to update a Snowflake1 to change the FQDN from 'testhaha' to 'new-account.snowflakecomputing.com'. No Dry Run.", "role": "user"}]
        )
        print(f"\nResponse: {result.final_output}\n")

        # 5. Test connection
        print("Step 5: Test linked service connection")
        result = await Runner.run(
            adf_agent,
            input=result.to_input_list()
            + [{"content": "Can you test the connection for any one of the linked services? You can choose which one you want to test.", "role": "user"}]
        )
        print(f"\nResponse: {result.final_output}\n")

    print("\n=== Demo Complete ===\n")


if __name__ == "__main__":
    asyncio.run(main()) 