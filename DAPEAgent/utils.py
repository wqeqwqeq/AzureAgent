"""
Utility functions for DAPEAgent operations.
"""

from typing import Dict, Any


def extract_token_usage(agent_result: Any) -> Dict[str, int]:
    """
    Extract token usage from agent result raw responses.
    
    Args:
        agent_result: The result object from Runner.run() containing raw_responses
        
    Returns:
        Dict containing token usage statistics with keys:
        - input_tokens: Number of input tokens
        - output_tokens: Number of output tokens  
        - cache_tokens: Number of cached tokens
        - total_tokens: Total number of tokens
    """
    try:
        total_tokens = 0
        input_tokens = 0
        output_tokens = 0
        cache_tokens = 0
        
        for response in agent_result.raw_responses:
            total_tokens += response.usage.total_tokens
            input_tokens += response.usage.input_tokens
            output_tokens += response.usage.output_tokens
            cache_tokens += response.usage.input_tokens_details.cached_tokens
        
        return {
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'cache_tokens': cache_tokens,
            'total_tokens': total_tokens
        }
    except Exception as e:
        # Return zero values if token extraction fails
        return {
            'input_tokens': 0,
            'output_tokens': 0,
            'cache_tokens': 0,
            'total_tokens': 0
        }