"""GitHub MCP Agent module.

Provides an agent that uses GitHub MCP server tools through tool filtering.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from agents import (
    Agent,
    OpenAIChatCompletionsModel,
)
from agents.mcp import MCPServerStdio, ToolFilterContext

from ..agent_builder import _build_client, load_yaml_prompt

def allow_tools(ctx: ToolFilterContext, tool) -> bool:
    """
    Tool filter function to allow specific GitHub MCP tools.
    
    Args:
        ctx: Tool filter context
        tool: The tool to check
        
    Returns:
        bool: True if tool is allowed, False otherwise
    """
    # Allow all GitHub tools by default since we're using the GitHub MCP server
    return True

def get_github_mcp_agent(
    user_input: Optional[str] = None
) -> tuple[Agent, MCPServerStdio]:
    """
    Get the GitHub MCP Agent instance.
    
    Args:
        user_input: Optional user's question or request
    
    Returns:
        tuple[Agent, MCPServerStdio]: The GitHub MCP Agent and MCP server
    """

    # Load prompt from YAML file
    yaml_path = Path(__file__).parent / "prompts" / "github_mcp_prompt.yaml"
    prompt_data = load_yaml_prompt(yaml_path)
    system_prompt = prompt_data.get("system_prompt", "You are a GitHub specialist with access to GitHub MCP server.")
    model = prompt_data.get("model", "gpt-4o")
    handoff_description = prompt_data.get("handoff_description", "GitHub MCP Agent")

    # Create MCP server with tool filtering  
    mcp_server = MCPServerStdio(
        params={
            "command": "docker", 
            "args": [
                "run", "-i", "--rm", 
                "-e", f"GITHUB_PERSONAL_ACCESS_TOKEN={os.getenv('GITHUB_PAT')}", 
                "-e", "GITHUB_READ_ONLY=1", 
                "ghcr.io/github/github-mcp-server"
            ]
        }, 
        client_session_timeout_seconds=240, 
        tool_filter=allow_tools,
        cache_tools_list=True
    )

    agent = Agent(
        name="GitHub MCP Agent",
        model=OpenAIChatCompletionsModel(model, openai_client=_build_client()),
        instructions=system_prompt,
        mcp_servers=[mcp_server],
        handoff_description=handoff_description
    )
    
    return agent, mcp_server



