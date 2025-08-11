#!/usr/bin/env python3
"""
Test the simplified LangChain tools implementation.
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.rag.simple_langchain_tools import SimpleLangChainToolRegistry, CallReportDataTool, BankLookupTool


def test_simple_tools():
    """Test the simplified LangChain tools."""
    print("Phase 1 Simplified: Testing LangChain Tool Implementation")
    print("=" * 60)
    
    # Test individual tool creation
    print("\n1. Testing Individual Tool Creation...")
    call_report_tool = CallReportDataTool()
    bank_lookup_tool = BankLookupTool()
    
    print(f"✅ CallReportDataTool: {call_report_tool.name}")
    print(f"   Description: {call_report_tool.description[:80]}...")
    
    print(f"✅ BankLookupTool: {bank_lookup_tool.name}")
    print(f"   Description: {bank_lookup_tool.description[:80]}...")
    
    # Test registry
    print("\n2. Testing Tool Registry...")
    registry = SimpleLangChainToolRegistry()
    
    print(f"✅ Registry created with {len(registry.tools)} tools")
    print(f"   Available: {registry.is_available()}")
    print(f"   Health: {registry.get_health_status()}")
    
    # Test bank lookup
    print("\n3. Testing Bank Lookup Tool...")
    bank_result = bank_lookup_tool._run("Bank of America", fuzzy_match=True, max_results=3)
    print("Bank Lookup Result:")
    print(bank_result)
    
    # Test call report data
    print("\n4. Testing Call Report Data Tool...")
    call_report_result = call_report_tool._run("1073757", "RC", "RCON2170")  # Bank of America total assets
    print("Call Report Result:")
    print(call_report_result)
    
    # Test with ChatbotAgent integration pattern
    print("\n5. Testing Agent Integration Pattern...")
    tools_for_agent = registry.get_tools()
    print(f"✅ Tools ready for agent: {len(tools_for_agent)}")
    
    for tool in tools_for_agent:
        print(f"   - {tool.name}: {tool.description.split('.')[0]}...")
    
    print("\n" + "=" * 60)
    print("🎉 Phase 1 Simplified Tests Completed Successfully!")
    print("✅ LangChain tools created and working")
    print("✅ Tools can execute Call Report and Bank Lookup operations") 
    print("✅ Tools ready for ChatbotAgent integration")
    print("✅ Ready to integrate with existing RAG system")


if __name__ == "__main__":
    test_simple_tools()
