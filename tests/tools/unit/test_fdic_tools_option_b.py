"""
Test script for Option B implementation - Clean atomic FDIC tools.

Validates that the new tools work correctly and the old tool is properly deprecated.
"""

import asyncio
import json
import warnings
from typing import Optional

from .fdic_institution_search_tool import FDICInstitutionSearchTool
from .fdic_financial_data_tool import FDICFinancialDataTool
from .fdic_tool_schemas import extract_cert_from_search, parse_financial_data_result
from .fdic_tools_setup import create_fdic_atomic_tools, get_fdic_tool_summary


def test_tool_initialization():
    """Test that tools initialize without errors."""
    print("🧪 Testing tool initialization...")
    
    try:
        # Test individual tool creation
        search_tool = FDICInstitutionSearchTool()
        financial_tool = FDICFinancialDataTool()
        
        print(f"✅ Search tool initialized: {search_tool.name}")
        print(f"✅ Financial tool initialized: {financial_tool.name}")
        
        # Test tool factory
        tools = create_fdic_atomic_tools()
        print(f"✅ Tool factory created {len(tools)} tools")
        
        return True
    except Exception as e:
        print(f"❌ Tool initialization failed: {e}")
        return False


def test_deprecated_tool_warnings():
    """Test that deprecated tool shows warnings."""
    print("\n🧪 Testing deprecated tool warnings...")
    
    try:
        # This should trigger a deprecation warning
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            from .bank_lookup_tool import BankLookupTool
            
            if w and any("deprecated" in str(warning.message).lower() for warning in w):
                print("✅ Deprecation warning properly triggered")
                return True
            else:
                print("⚠️  Deprecation warning not triggered")
                return False
                
    except Exception as e:
        print(f"❌ Deprecated tool test failed: {e}")
        return False


def test_tool_schemas():
    """Test that schema parsing functions work."""
    print("\n🧪 Testing tool schemas...")
    
    try:
        # Test search result parsing
        sample_search_result = {
            "success": True,
            "count": 1,
            "institutions": [
                {
                    "name": "Test Bank",
                    "cert": "12345",
                    "location": {"city": "Test City", "state": "TS"},
                    "status": "Active",
                    "financial": {"total_assets_thousands": 1000000}
                }
            ]
        }
        
        json_string = json.dumps(sample_search_result)
        cert_id = extract_cert_from_search(json_string)
        
        if cert_id == "12345":
            print("✅ CERT extraction works correctly")
        else:
            print(f"❌ CERT extraction failed: got {cert_id}, expected 12345")
            return False
        
        # Test financial result parsing
        sample_financial_result = {
            "success": True,
            "analysis_type": "basic_info",
            "cert_id": "12345"
        }
        
        financial_json = json.dumps(sample_financial_result)
        financial_data = parse_financial_data_result(financial_json)
        
        if financial_data["success"] and financial_data["cert_id"] == "12345":
            print("✅ Financial data parsing works correctly")
        else:
            print("❌ Financial data parsing failed")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Schema testing failed: {e}")
        return False


def test_tool_summary():
    """Test that tool summary provides useful information."""
    print("\n🧪 Testing tool summary...")
    
    try:
        summary = get_fdic_tool_summary()
        
        required_keys = ["tools", "workflow", "benefits", "replaces"]
        for key in required_keys:
            if key not in summary:
                print(f"❌ Missing key in summary: {key}")
                return False
        
        if "fdic_institution_search" in summary["tools"] and "fdic_financial_data" in summary["tools"]:
            print("✅ Tool summary contains correct tool information")
        else:
            print("❌ Tool summary missing tool information")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Tool summary test failed: {e}")
        return False


async def test_mock_tool_flow():
    """Test the basic tool flow with mock data (no actual API calls)."""
    print("\n🧪 Testing mock tool flow...")
    
    try:
        # Test input validation without API calls
        search_tool = FDICInstitutionSearchTool()
        financial_tool = FDICFinancialDataTool()
        
        # Test validation errors
        result = await search_tool._arun()  # No parameters
        if "Error" in result and "search parameter" in result:
            print("✅ Search tool validation works")
        else:
            print("❌ Search tool validation failed")
            return False
        
        result = await financial_tool._arun(cert_id="invalid")  # Invalid cert
        if "Error" in result and "numeric" in result:
            print("✅ Financial tool validation works")
        else:
            print("❌ Financial tool validation failed")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Mock tool flow test failed: {e}")
        return False


def test_banking_toolset_integration():
    """Test that banking toolset properly loads new tools."""
    print("\n🧪 Testing banking toolset integration...")
    
    try:
        from ..infrastructure.toolsets.banking_toolset import BankingToolset
        from src.config.settings import get_settings
        
        settings = get_settings()
        toolset = BankingToolset(settings)
        
        tools = toolset.get_tools()
        tool_names = [tool.name for tool in tools]
        
        expected_tools = ["fdic_institution_search", "fdic_financial_data"]
        missing_tools = [name for name in expected_tools if name not in tool_names]
        
        if missing_tools:
            print(f"❌ Banking toolset missing tools: {missing_tools}")
            return False
        else:
            print(f"✅ Banking toolset contains new tools: {tool_names}")
            return True
            
    except Exception as e:
        print(f"❌ Banking toolset integration test failed: {e}")
        return False


def run_all_tests():
    """Run all tests and provide summary."""
    print("🚀 Testing Option B Implementation - Clean Atomic FDIC Tools")
    print("=" * 70)
    
    tests = [
        ("Tool Initialization", test_tool_initialization),
        ("Deprecated Tool Warnings", test_deprecated_tool_warnings),
        ("Tool Schemas", test_tool_schemas),
        ("Tool Summary", test_tool_summary),
        ("Banking Toolset Integration", test_banking_toolset_integration),
    ]
    
    async_tests = [
        ("Mock Tool Flow", test_mock_tool_flow),
    ]
    
    results = []
    
    # Run synchronous tests
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            results.append((test_name, False))
    
    # Run async tests
    for test_name, test_func in async_tests:
        try:
            result = asyncio.run(test_func())
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 TEST SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 Option B implementation successful!")
        print("✅ Clean atomic FDIC tools are working correctly")
        print("✅ Old tool is properly deprecated")
        print("✅ Banking toolset integration complete")
        print("✅ Ready for tool graph composition")
    else:
        print(f"\n⚠️  Option B implementation has issues ({total - passed} failures)")
        print("Some tests failed - check the output above for details")
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)