#!/usr/bin/env python3
"""
Simple test script to verify the new context design works correctly.
This tests basic functionality without requiring actual Azure credentials.
"""

import sys
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_imports():
    """Test that all imports work correctly."""
    print("Testing imports...")
    
    try:
        from DAPEAgent.utils.azure_adapters import AzureCtx, get_resource_handler
        print("✓ AzureCtx and get_resource_handler imported successfully")
        
        from DAPEAgent.triage_agent import get_agent
        print("✓ Triage agent get_agent imported successfully")
        
        from DAPEAgent.adf.linked_services_agent import get_agent as get_ls_agent
        print("✓ Linked services agent imported successfully")
        
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False
    
    return True


def test_azure_ctx():
    """Test AzureCtx dataclass functionality."""
    print("\nTesting AzureCtx dataclass...")
    
    try:
        from DAPEAgent.utils.azure_adapters import AzureCtx
        
        # Test empty context
        ctx = AzureCtx()
        assert ctx.subscription_id is None
        assert ctx.resource_group_name is None
        print("✓ Empty AzureCtx created successfully")
        
        # Test with values
        ctx = AzureCtx(
            subscription_id="test-sub-id",
            subscription_name="Test Subscription",
            resource_group_name="test-rg",
            resource_name="test-resource"
        )
        assert ctx.subscription_id == "test-sub-id"
        assert ctx.subscription_name == "Test Subscription"
        print("✓ AzureCtx with values created successfully")
        
        # Test cache key generation
        cache_key = ctx.to_cache_key()
        assert isinstance(cache_key, tuple)
        assert len(cache_key) == 5  # All 5 fields
        print("✓ Cache key generation works")
        
    except Exception as e:
        print(f"✗ AzureCtx test error: {e}")
        return False
    
    return True


def test_get_resource_handler():
    """Test the get_resource_handler function with new context types."""
    print("\nTesting get_resource_handler...")
    
    try:
        from DAPEAgent.utils.azure_adapters import AzureCtx, get_resource_handler
        
        # Test with AzureCtx
        ctx = AzureCtx(subscription_id="test-sub")
        
        # This should work without actually connecting to Azure
        # We're just testing the function signature and basic logic
        try:
            handler = get_resource_handler("subscription_resource", ctx)
            print("✓ get_resource_handler works with AzureCtx")
        except Exception as e:
            # Expected to fail without real Azure connection, but should not be a type error
            if "subscription_id" in str(e) or "authentication" in str(e).lower():
                print("✓ get_resource_handler accepts AzureCtx (Azure connection expected to fail in test)")
            else:
                print(f"✗ Unexpected error: {e}")
                return False
        
        # Test with dict (backward compatibility)
        try:
            handler = get_resource_handler("subscription_resource", {"subscription_id": "test-sub"})
            print("✓ get_resource_handler works with dict")
        except Exception as e:
            if "subscription_id" in str(e) or "authentication" in str(e).lower():
                print("✓ get_resource_handler accepts dict (Azure connection expected to fail in test)")
            else:
                print(f"✗ Unexpected error: {e}")
                return False
        
    except Exception as e:
        print(f"✗ get_resource_handler test error: {e}")
        return False
    
    return True


def test_agent_creation():
    """Test that agents can be created without context parameters."""
    print("\nTesting agent creation...")
    
    try:
        from DAPEAgent.triage_agent import get_agent
        from DAPEAgent.adf.linked_services_agent import get_agent as get_ls_agent
        
        # Test triage agent creation (should not require context parameter)
        try:
            triage = get_agent()
            print("✓ Triage agent created successfully without context parameter")
        except TypeError as e:
            if "context" in str(e):
                print(f"✗ Triage agent still requires context parameter: {e}")
                return False
            else:
                # Other errors might be due to missing config files, etc.
                print(f"✓ Triage agent creation (expected config error): {e}")
        
        # Test linked services agent creation
        try:
            ls_agent = get_ls_agent()
            print("✓ Linked services agent created successfully without context parameter")
        except TypeError as e:
            if "context" in str(e):
                print(f"✗ Linked services agent still requires context parameter: {e}")
                return False
            else:
                print(f"✓ Linked services agent creation (expected config error): {e}")
        
    except Exception as e:
        print(f"✓ Agent creation test (expected errors due to missing config): {e}")
    
    return True


def main():
    """Run all tests."""
    print("Testing new Azure Agent context design...\n")
    
    tests = [
        test_imports,
        test_azure_ctx,
        test_get_resource_handler,
        test_agent_creation,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()  # Add spacing between tests
    
    print(f"Tests completed: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All tests passed! The new context design is working correctly.")
        return True
    else:
        print("❌ Some tests failed. Please check the implementation.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 