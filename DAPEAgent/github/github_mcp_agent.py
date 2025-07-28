import os
import asyncio
from typing import List, Dict, Optional
from dotenv import load_dotenv

from openai import AsyncAzureOpenAI
from agents import Agent, Runner, trace, set_default_openai_client, set_tracing_disabled, OpenAIChatCompletionsModel, set_tracing_export_api_key
from agents.mcp import MCPServerStdio

load_dotenv()

class GitHubAgent:
    """GitHub specialist agent with MCP server integration."""
    
    def __init__(self):
        self.agent: Optional[Agent] = None
        self.mcp_server: Optional[MCPServerStdio] = None
        self.model: Optional[OpenAIChatCompletionsModel] = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize the GitHub agent and MCP server."""
        if self._initialized:
            return
        
        # Setup Azure OpenAI client and model
        azure_openai_client = AsyncAzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT")
        )
        
        set_default_openai_client(azure_openai_client)
        set_tracing_export_api_key(os.getenv("OPENAI_API_KEY"))
        set_tracing_disabled(False)
        
        self.model = OpenAIChatCompletionsModel(
            model="gpt-4o",
            openai_client=azure_openai_client
        )
        
        # Setup MCP server
        params = {
            "command": "docker", 
            "args": [
                "run", "-i", "--rm", 
                "-e", f"GITHUB_PERSONAL_ACCESS_TOKEN={os.getenv('GITHUB_PAT')}", 
                "-e", "GITHUB_READ_ONLY=1", 
                "ghcr.io/github/github-mcp-server"
            ]
        }
        
        self.mcp_server = MCPServerStdio(params=params, client_session_timeout_seconds=240)
        await self.mcp_server.__aenter__()
        
        # Create agent with instructions
        instructions = """You are a Github specialist with access to Github mcp server.

You will be expected to ask questions related to Github"""
        
        self.agent = Agent(
            name="github specialist", 
            instructions=instructions, 
            model=self.model, 
            mcp_servers=[self.mcp_server]
        )
        
        self._initialized = True
    
    async def cleanup(self):
        """Cleanup MCP server resources."""
        if self.mcp_server:
            try:
                await self.mcp_server.__aexit__(None, None, None)
            except Exception:
                pass
        
        self.agent = None
        self.mcp_server = None
        self.model = None
        self._initialized = False
    
    async def get_response(self, user_input: str, chat_history: Optional[List[Dict[str, str]]] = None) -> str:
        """Get response from GitHub agent with optional chat history context."""
        if not self._initialized:
            await self.initialize()
        
        if not self.agent:
            raise RuntimeError("Agent not initialized")
        
        # Build context with chat history
        if chat_history:
            context = "Previous conversation:\n"
            for msg in chat_history[-10:]:  # Keep last 10 exchanges
                context += f"User: {msg['user']}\nAssistant: {msg['assistant']}\n\n"
            context += f"Current question: {user_input}"
            full_input = context
        else:
            full_input = user_input
        
        with trace("github_mcp_agent"):
            result = await Runner.run(self.agent, full_input)
            return result.final_output
    
    async def __aenter__(self):
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.cleanup()

# Convenience function for one-off usage
async def create_github_agent() -> GitHubAgent:
    """Create and initialize a new GitHub agent."""
    agent = GitHubAgent()
    await agent.initialize()
    return agent

# Example usage function
async def main():
    """Example interactive usage of the GitHub agent."""
    async with GitHubAgent() as github_agent:
        print("=== GitHub Agent Interactive Mode ===")
        print("Type 'quit' or 'exit' to end the conversation\n")
        
        conversation_history = []
        
        while True:
            try:
                user_input = input("User: ").strip()
                if user_input.lower() in ['quit', 'exit', 'q']:
                    break
                if not user_input:
                    continue
                
                response = await github_agent.get_response(user_input, conversation_history)
                print(f"Assistant: {response}\n")
                
                # Store conversation history
                conversation_history.append({
                    'user': user_input,
                    'assistant': response
                })
                
            except KeyboardInterrupt:
                print("\nGoodbye!")
                break
            except Exception as e:
                print(f"Error: {e}\n")

