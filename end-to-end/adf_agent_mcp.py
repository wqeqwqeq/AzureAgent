from __future__ import annotations
import logging
import os
import asyncio
from dotenv import load_dotenv

from openai import AsyncAzureOpenAI
from agents import Agent, Runner, trace, set_default_openai_client, set_tracing_disabled, OpenAIChatCompletionsModel, set_tracing_export_api_key
from agents.mcp import MCPServerStdio

load_dotenv()

# Set up Azure OpenAI client
azure_openai_client = AsyncAzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT")
)

openai_client = azure_openai_client
set_default_openai_client(openai_client)

# Set up tracing
set_tracing_export_api_key(os.getenv("OPENAI_API_KEY"))
set_tracing_disabled(False)

# Model configuration
model = OpenAIChatCompletionsModel(
    model="gpt-4o",
    openai_client=openai_client
)

# Agent instructions
instructions = """You are an Azure Data Factory Linked Services specialist.

You help users manage ADF linked services including:
- Listing all linked services 
Always be professional and provide clear explanations of operations.
When users ask about linked services, use the available tools to retrieve the information.

Available operations:
- list_linked_services: Get all linked services
"""

async def main():
    """Demonstrate the ADF Linked Services agent with MCP server."""
    
    # MCP server parameters
    params = {"command": "uv", "args": ["run", "adf_server.py"]}
    
    async with MCPServerStdio(params=params, client_session_timeout_seconds=240) as mcp_server:
        agent = Agent(
            name="adf_specialist", 
            instructions=instructions, 
            model=model, 
            mcp_servers=[mcp_server]
        )
        
        with trace("adf_mcp_test"):
            print("\n=== ADF Linked Services Agent (MCP) Demo ===\n")
            
            # Test 1: List all linked services
            print("Step 1: List all linked services")
            request = "Can you show me all the linked services in my ADF?"
            result = await Runner.run(agent, request)
            print(f"\nResponse: {result.final_output}\n")
            
            # Test 2: Filter by type
            print("Step 2: Filter linked services by Snowflake type")
            request = "Now show me only the Snowflake linked services."
            result = await Runner.run(agent, request)
            print(f"\nResponse: {result.final_output}\n")
            
    print("\n=== Demo Complete ===\n")

if __name__ == "__main__":
    asyncio.run(main()) 