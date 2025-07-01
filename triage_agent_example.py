"""
Example script demonstrating the improved triage agent design.

The new design allows natural language input without manually specifying context.
The LLM automatically extracts subscription, resource group, and resource names
from user queries and stores them in a shared context that all agents can access.
"""

import asyncio
from DAPEAgent.triage_agent import get_agent
from DAPEAgent.utils.azure_adapters import AzureCtx
from agents import Runner


async def main():
    # Create an empty context - the LLM will populate it based on user input
    ctx = AzureCtx()
    
    # Get the triage agent (no context parameter needed anymore!)
    triage = get_agent()
    
    # Example queries demonstrating natural language extraction
    queries = [
        "List all subscriptions I have access to",
        "Switch to subscription 'Azure Subscription 1' and list resource groups",
        "Show me all linked services in the Data Factory 'adf-stanley' in resource group 'sql-rg'",
        "Test the connection for linked service 'Snowflake1' in the same Data Factory",
    ]
    
    for query in queries:
        print(f"\n{'='*60}")
        print(f"Query: {query}")
        print('='*60)
        
        try:
            # Run the query - the context will be automatically populated
            result = await Runner.run(triage, query, context=ctx)
            
            # Show the result
            print(f"Result: {result.final_output}")
            
            # Show what context was gathered automatically
            print(f"\nContext after query:")
            print(f"  Subscription ID: {ctx.subscription_id}")
            print(f"  Subscription Name: {ctx.subscription_name}")
            print(f"  Resource Group: {ctx.resource_group_name}")
            print(f"  Resource Name: {ctx.resource_name}")
            
        except Exception as e:
            print(f"Error: {str(e)}")
        
        # Optional: reset specific context for next query if needed
        # ctx.resource_name = None  # Reset resource name for next query


async def interactive_mode():
    """Interactive mode for testing the agent."""
    ctx = AzureCtx()
    triage = get_agent()
    
    print("Azure Agent Interactive Mode")
    print("Type 'quit' to exit, 'context' to see current context")
    print("Examples:")
    print("  - 'List my subscriptions'")
    print("  - 'Switch to subscription ContosoProd'")
    print("  - 'Show linked services in adf-prod in resource group prod-rg'")
    print()
    
    while True:
        user_input = input("You: ").strip()
        
        if user_input.lower() in ['quit', 'exit']:
            break
        elif user_input.lower() == 'context':
            print(f"Current context:")
            print(f"  Subscription ID: {ctx.subscription_id}")
            print(f"  Subscription Name: {ctx.subscription_name}")
            print(f"  Resource Group: {ctx.resource_group_name}")
            print(f"  Resource Name: {ctx.resource_name}")
            continue
        elif not user_input:
            continue
        
        try:
            result = await Runner.run(triage, user_input, context=ctx)
            print(f"Agent: {result.final_output}")
        except Exception as e:
            print(f"Error: {str(e)}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        asyncio.run(interactive_mode())
    else:
        asyncio.run(main()) 