from mcp.server.fastmcp import FastMCP
import os
import json
from typing import Optional
from dotenv import load_dotenv

# Import the ADF Linked Services class
from azure_tools.adf.linked_services import ADFLinkedServices

load_dotenv()

# Initialize MCP server

mcp = FastMCP("adf_server")
@mcp.tool()
async def list_linked_services() -> str:
    """
    List all linked services in the Azure Data Factory.
    
    Args:
        filter_by_type: Optional filter to only show linked services of a specific type
    
    Returns:
        JSON string containing the list of linked services
    """

        # Initialize ADF Linked Services instance
    adf_resource_group = os.getenv("ADF_RESOURCE_GROUP", "SQL-RG")
    adf_factory_name = os.getenv("ADF_FACTORY_NAME", "adf-stanley")

    adf_service = ADFLinkedServices(
        resource_group_name=adf_resource_group,
        resource_name=adf_factory_name,
    )
    services = adf_service.list_linked_services()
    print(services)
    simplified_services = []
    for service in services:
        simplified_service = {
            "name": service.get("name", "Unknown"),
            "type": service.get("properties", {}).get("type", "Unknown"),
        }
        simplified_services.append(simplified_service)
    
    return json.dumps(simplified_services, indent=2)

if __name__ == "__main__":
    print("Starting ADF Server")
    mcp.run(transport='stdio') 