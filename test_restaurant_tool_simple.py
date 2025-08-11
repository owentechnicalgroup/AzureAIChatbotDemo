#!/usr/bin/env python3
"""
Simple test for Restaurant Ratings Tool (no Unicode characters).
"""

import sys
import asyncio
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

async def test_restaurant_tool_basic():
    """Basic test of the restaurant ratings tool."""
    print("Testing Restaurant Ratings Tool")
    print("===============================")
    
    try:
        from tools.ratings_tool import RestaurantRatingsTool
        from tools.base import ToolStatus
        
        # Test initialization
        api_key = os.getenv('YELP_API_KEY')
        tool = RestaurantRatingsTool(api_key)
        
        print(f"Tool name: {tool.name}")
        print(f"Tool available: {tool.is_available()}")
        print(f"Has API key: {bool(api_key)}")
        
        # Test schema
        schema = tool.get_schema()
        print(f"Schema function: {schema['function']['name']}")
        print(f"Required params: {schema['function']['parameters']['required']}")
        
        # Test with timeout
        tool.set_timeout(5.0)
        print(f"Timeout set to: {tool._timeout} seconds")
        
        print("\nBASIC TESTS PASSED")
        return True
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        return False

async def test_tool_registry_basic():
    """Basic test of tool registry."""
    print("\nTesting Tool Registry")
    print("====================")
    
    try:
        from tools import ToolRegistry, RestaurantRatingsTool
        
        registry = ToolRegistry()
        print(f"Empty registry size: {len(registry)}")
        
        # Register tool
        tool = RestaurantRatingsTool()
        registry.register_tool(tool)
        print(f"Registry size after registration: {len(registry)}")
        
        # Get statistics
        stats = registry.get_statistics()
        print(f"Total tools: {stats['total_tools']}")
        print(f"Available tools: {stats['available_tools']}")
        
        print("REGISTRY TESTS PASSED")
        return True
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        return False

async def main():
    """Run basic tests."""
    print("Restaurant Tool Basic Test Suite")
    print("=================================")
    
    tool_ok = await test_restaurant_tool_basic()
    registry_ok = await test_tool_registry_basic()
    
    print("\nSUMMARY")
    print("=======")
    print(f"Tool test: {'PASS' if tool_ok else 'FAIL'}")
    print(f"Registry test: {'PASS' if registry_ok else 'FAIL'}")
    
    if tool_ok and registry_ok:
        print("ALL BASIC TESTS PASSED")
        print("\nNext steps:")
        print("1. Add YELP_API_KEY to test API calls")
        print("2. Integrate with RAG system")
        print("3. Add to Streamlit UI")
    else:
        print("SOME TESTS FAILED")
    
    return tool_ok and registry_ok

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)