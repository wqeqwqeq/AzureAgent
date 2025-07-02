import asyncio
from agents import Runner, trace
from DAPEAgent.triage_agent import get_triage_agent
from DAPEAgent.config import AzureCtx


async def main():
    """Main async function to run the triage agent."""
    triage_agent = get_triage_agent()

    with trace("test"):
        result = await Runner.run(
            triage_agent,
            input=[{"content": "what's the value for secrete test-secret-2 and test-secret-1 in the key vault stanleyakvprod in resource group adf ", "role": "user"}],
            context=AzureCtx(subscription_id="ee5f77a1-2e59-4335-8bdf-f7ea476f6523")  # Add initial context instance
        )
    
    print("Agent Response:")
    print(result)
    return result


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
