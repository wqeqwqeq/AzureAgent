# %%
import os
import asyncio
from dotenv import load_dotenv

from openai import AsyncAzureOpenAI
from agents import Agent, Runner, trace, set_default_openai_client, set_tracing_disabled, OpenAIChatCompletionsModel, set_tracing_export_api_key
from agents.mcp import MCPServerStdio
import time

load_dotenv()

# Set up Azure OpenAI client
azure_openai_client = AsyncAzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT")
)

# %%
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

# %%
print(    {"command": "docker", 
              "args": ["run", "-i", "--rm", 
                       "-e", f"GITHUB_PERSONAL_ACCESS_TOKEN={os.getenv('GITHUB_PAT')}", 
                       "-e", "GITHUB_TOOLSETS=repos,pull_requests,context", 
                       "-e", "GITHUB_READ_ONLY=1", 
                       "ghcr.io/github/github-mcp-server"]})

# %%
# Agent instructions
instructions = """You are an Github specialist with access to Github mcp server.

You will be expect to ask questions related to Github
"""

async def main():
    """Interactive GitHub agent with MCP server."""
    
    # MCP server parameters
    params = {"command": "docker", 
              "args": ["run", "-i", "--rm", 
                       "-e", f"GITHUB_PERSONAL_ACCESS_TOKEN={os.getenv('GITHUB_PAT')}", 
                       "-e", "GITHUB_READ_ONLY=1", 
                       "ghcr.io/github/github-mcp-server"]
              }
    now = time.time()
    async with MCPServerStdio(params=params, client_session_timeout_seconds=240) as mcp_server:
        print(f"MCP server started in {time.time() - now} seconds")
        agent = Agent(
            name="github specialist", 
            instructions=instructions, 
            model=model, 
            mcp_servers=[mcp_server]
        )
        
        print("\n=== GITHUB Agent (MCP) Interactive Mode ===")
        print("Type 'quit' or 'exit' to end the conversation\n")
        
        conversation_history = []
        
        while True:
            try:
                user_input = input("User: ").strip()
                if user_input.lower() in ['quit', 'exit', 'q']:
                    break
                if not user_input:
                    continue
                
                # Build conversation context with history
                if conversation_history:
                    context = "Previous conversation:\n"
                    for msg in conversation_history[-10:]:  # Keep last 10 exchanges
                        context += f"User: {msg['user']}\nAssistant: {msg['assistant']}\n\n"
                    context += f"Current question: {user_input}"
                    full_input = context
                else:
                    full_input = user_input
                    
                with trace("github_mcp_interactive"):
                    result = await Runner.run(agent, full_input)
                    print(f"Assistant: {result.final_output}\n")
                    
                    # Store conversation history
                    conversation_history.append({
                        'user': user_input,
                        'assistant': result.final_output
                    })
                    
            except KeyboardInterrupt:
                print("\nGoodbye!")
                break
            except Exception as e:
                print(f"Error: {e}\n")
                
    print("\n=== Session Complete ===\n")

# %%
asyncio.run(main())

# %%



