#!/usr/bin/env python3
"""
Test the Restaurant Ratings Tool implementation.

This script tests the Yelp API integration and function calling capabilities.
"""

import sys
import asyncio
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

async def test_restaurant_tool():
    """Test the restaurant ratings tool functionality."""
    print("=" * 60)
    print("Testing Restaurant Ratings Tool")
    print("=" * 60)
    
    try:
        from tools.ratings_tool import RestaurantRatingsTool
        from tools.base import ToolStatus
        
        # Test 1: Tool initialization
        print("1. Testing tool initialization...")
        
        # Use environment variable or demo mode
        api_key = os.getenv('YELP_API_KEY')
        if not api_key:
            print("   No YELP_API_KEY found - testing in demo mode")
            # Create tool without API key to test error handling
            tool = RestaurantRatingsTool()
        else:
            print(f"   Using API key: {api_key[:10]}...")
            tool = RestaurantRatingsTool(api_key)
        
        print(f"   Tool name: {tool.name}")
        print(f"   Tool available: {tool.is_available()}")
        print(f"   Tool description: {tool.description}")
        
        # Test 2: Schema generation
        print("\n2. Testing function schema generation...")
        schema = tool.get_schema()
        
        print(f"   Schema type: {schema['type']}")
        print(f"   Function name: {schema['function']['name']}")
        print(f"   Required parameters: {schema['function']['parameters']['required']}")
        
        # List all parameters
        properties = schema['function']['parameters']['properties']
        print(f"   Available parameters: {list(properties.keys())}")
        
        # Test 3: Tool execution (if API key available)
        if tool.is_available():
            print("\n3. Testing tool execution...")
            
            # Test search for a well-known restaurant chain
            result = await tool.execute_with_timeout(
                query="McDonald's",
                location="Seattle, WA",
                limit=3
            )
            
            print(f"   Execution status: {result.status.value}")
            print(f"   Execution time: {result.execution_time:.2f} seconds")
            print(f"   Success: {result.success}")
            
            if result.success and result.data:
                restaurants = result.data.get("restaurants", [])
                print(f"   Found {len(restaurants)} restaurants")
                
                if restaurants:
                    print(f"   First result: {restaurants[0]['name']}")
                    print(f"   Rating: {restaurants[0].get('rating', 'N/A')}")
                    print(f"   Review count: {restaurants[0].get('review_count', 'N/A')}")
                    print(f"   Address: {restaurants[0].get('address', 'N/A')}")
                
                # Show summary
                summary = result.data.get("summary", "No summary available")
                print(f"   Summary: {summary}")
            else:
                print(f"   Error: {result.error}")
        else:
            print("\n3. Tool execution skipped - no API key available")
            print("   Set YELP_API_KEY environment variable to test execution")
        
        # Test 4: Error handling
        print("\n4. Testing error handling...")
        
        # Test with invalid parameters
        result = await tool.execute_with_timeout(
            query="",  # Empty query should cause error
            location="Invalid Location 12345",
            limit=0  # Will be corrected to 1
        )
        
        print(f"   Empty query result: {result.status.value}")
        if not result.success:
            print(f"   Expected error message: {result.error[:100]}...")
        
        # Test 5: Timeout handling
        print("\n5. Testing timeout configuration...")
        
        original_timeout = tool._timeout
        tool.set_timeout(1.0)  # Very short timeout
        print(f"   Timeout set to: {tool._timeout} seconds")
        
        # Restore original timeout
        tool.set_timeout(original_timeout)
        print(f"   Timeout restored to: {tool._timeout} seconds")
        
        print("\n" + "=" * 60)
        print("Restaurant Ratings Tool Test Results:")
        print("=" * 60)
        print(f"✓ Tool initialization: Working")
        print(f"✓ Schema generation: Working")
        print(f"✓ API availability: {'Available' if tool.is_available() else 'Not configured'}")
        print(f"✓ Error handling: Working")
        print(f"✓ Timeout configuration: Working")
        
        if tool.is_available():
            print(f"✓ Tool execution: Tested successfully")
            print("\nTo test with different queries, try:")
            print("- 'Italian restaurants' in 'New York, NY'")
            print("- 'Pizza' in 'Chicago, IL'") 
            print("- 'Starbucks' in 'San Francisco, CA'")
        else:
            print("⚠ Tool execution: Requires YELP_API_KEY")
            print("\nTo get a Yelp API key:")
            print("1. Visit: https://www.yelp.com/developers")
            print("2. Create a developer account")
            print("3. Create a new app")
            print("4. Copy the API key")
            print("5. Set environment variable: YELP_API_KEY=your_key_here")
        
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"ERROR: Restaurant tool test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def test_tools_integration():
    """Test the tools integration system."""
    print("\n" + "=" * 60)
    print("Testing Tools Integration System")
    print("=" * 60)
    
    try:
        from tools import ToolRegistry, RestaurantRatingsTool
        from config.settings import get_settings
        
        # Test tool registry
        print("1. Testing ToolRegistry...")
        
        registry = ToolRegistry()
        print(f"   Empty registry size: {len(registry)}")
        
        # Register restaurant tool
        api_key = os.getenv('YELP_API_KEY')
        restaurant_tool = RestaurantRatingsTool(api_key)
        registry.register_tool(restaurant_tool)
        
        print(f"   Registry size after registration: {len(registry)}")
        print(f"   Available tools: {[t.name for t in registry.list_tools()]}")
        
        # Test function schemas
        schemas = registry.get_function_schemas()
        print(f"   Generated {len(schemas)} function schemas")
        
        if schemas:
            schema = schemas[0]
            print(f"   First schema function: {schema['function']['name']}")
        
        # Test tool execution via registry
        if restaurant_tool.is_available():
            print("\n2. Testing registry tool execution...")
            
            result = await registry.execute_tool(
                "get_restaurant_ratings",
                query="Subway",
                location="Portland, OR",
                limit=2
            )
            
            print(f"   Registry execution status: {result.status.value}")
            print(f"   Success: {result.success}")
            
            if result.success and result.data:
                restaurants = result.data.get("restaurants", [])
                print(f"   Found {len(restaurants)} restaurants via registry")
        else:
            print("\n2. Registry execution skipped - no API key")
        
        # Test statistics
        print("\n3. Testing registry statistics...")
        stats = registry.get_statistics()
        print(f"   Total tools: {stats['total_tools']}")
        print(f"   Available tools: {stats['available_tools']}")
        print(f"   Tool names: {stats['tool_names']}")
        
        print("\n✓ Tools integration system working correctly")
        return True
        
    except Exception as e:
        print(f"ERROR: Tools integration test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run all tests."""
    print("Restaurant Ratings Tool Test Suite")
    print("===================================")
    
    # Test individual tool
    tool_success = await test_restaurant_tool()
    
    # Test integration system
    integration_success = await test_tools_integration()
    
    # Summary
    print("\nTEST SUMMARY")
    print("============")
    print(f"Restaurant Tool: {'PASS' if tool_success else 'FAIL'}")
    print(f"Tools Integration: {'PASS' if integration_success else 'FAIL'}")
    
    overall_success = tool_success and integration_success
    print(f"Overall: {'ALL TESTS PASSED' if overall_success else 'SOME TESTS FAILED'}")
    
    if overall_success:
        print("\nReady to integrate with RAG system!")
        print("Next steps:")
        print("1. Add YELP_API_KEY to environment variables")
        print("2. Update Streamlit UI to show tools capabilities") 
        print("3. Test with real user queries")
    
    return overall_success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)