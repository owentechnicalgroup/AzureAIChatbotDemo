"""
Example demonstrating the simplified CERT-based FDIC flow.

Shows how the new atomic tools work together without complex coordination logic.
"""

import json
import asyncio
from typing import Optional

from .fdic_institution_search_tool import FDICInstitutionSearchTool
from .fdic_financial_data_tool import FDICFinancialDataTool
from .fdic_tool_schemas import (
    parse_institution_search_result,
    extract_cert_from_search,
    parse_financial_data_result
)


async def demonstrate_cert_flow():
    """
    Demonstrate the clean CERT-based flow between FDIC tools.
    
    This shows the simplified workflow:
    1. Search for institution by name/location
    2. Extract CERT from structured results  
    3. Use CERT for financial data query
    4. Parse structured financial results
    
    No string parsing, no RSSD handling, no backwards compatibility complexity.
    """
    print("=== FDIC Atomic Tools - Clean CERT Flow Demo ===\n")
    
    # Initialize tools
    search_tool = FDICInstitutionSearchTool()
    financial_tool = FDICFinancialDataTool()
    
    # Step 1: Search for institution
    print("1. Searching for Wells Fargo...")
    search_result = await search_tool._arun(
        name="Wells Fargo",
        limit=3
    )
    
    print("Search Results:")
    print(search_result[:500] + "..." if len(search_result) > 500 else search_result)
    print()
    
    # Step 2: Extract CERT from structured result
    try:
        cert_id = extract_cert_from_search(search_result)
        if not cert_id:
            print("❌ No institutions found in search")
            return
            
        print(f"2. Extracted CERT ID: {cert_id}")
        print()
        
    except Exception as e:
        print(f"❌ Failed to extract CERT: {e}")
        return
    
    # Step 3: Get financial data using CERT
    print("3. Retrieving financial data...")
    financial_result = await financial_tool._arun(
        cert_id=cert_id,
        analysis_type="key_ratios"
    )
    
    print("Financial Results:")
    print(financial_result[:800] + "..." if len(financial_result) > 800 else financial_result)
    print()
    
    # Step 4: Parse structured financial data
    try:
        financial_data = parse_financial_data_result(financial_result)
        
        if financial_data.get('success'):
            ratios = financial_data.get('profitability_ratios', {})
            roa = ratios.get('return_on_assets', {}).get('formatted', 'N/A')
            roe = ratios.get('return_on_equity', {}).get('formatted', 'N/A') 
            
            print(f"4. Key Ratios Extracted:")
            print(f"   - ROA: {roa}")
            print(f"   - ROE: {roe}")
            print(f"   - Report Date: {financial_data.get('report_date', 'N/A')}")
        else:
            print(f"❌ Financial data retrieval failed: {financial_data.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ Failed to parse financial data: {e}")
    
    print("\n✅ CERT-based flow completed successfully!")


async def test_error_handling():
    """Test error handling in the atomic tools."""
    print("\n=== Testing Error Handling ===\n")
    
    search_tool = FDICInstitutionSearchTool()
    financial_tool = FDICFinancialDataTool()
    
    # Test invalid search
    print("1. Testing invalid search (no criteria)...")
    result = await search_tool._arun()
    data = json.loads(result)
    assert not data['success']
    print(f"✅ Error handled: {data['error']}")
    
    # Test invalid CERT
    print("\n2. Testing invalid CERT ID...")
    result = await financial_tool._arun(cert_id="invalid")
    data = json.loads(result)
    assert not data['success']
    print(f"✅ Error handled: {data['error']}")
    
    print("\n✅ Error handling works correctly!")


def compare_with_old_approach():
    """
    Show the difference between old and new approaches.
    """
    print("\n=== Old vs New Approach Comparison ===\n")
    
    print("OLD (Complex, Brittle):")
    print("1. bank_analysis_tool(bank_name='Wells Fargo')")
    print("   ├─ Calls bank_lookup internally")  
    print("   ├─ Parses formatted text with regex: re.search(r'FDIC Certificate:\\s*(\\d+)')")
    print("   ├─ BREAKS: ImportError: No module named 're'")
    print("   ├─ Complex RSSD/CERT coordination logic")
    print("   └─ Brittle string parsing between APIs")
    print()
    
    print("NEW (Clean, Simple):")
    print("1. search_result = fdic_institution_search_tool(name='Wells Fargo')")
    print("2. cert_id = extract_cert_from_search(search_result)  # Structured data")
    print("3. financial_data = fdic_financial_data_tool(cert_id=cert_id)")
    print("   ├─ No string parsing - structured JSON throughout")
    print("   ├─ No RSSD complexity - pure CERT-based flow")
    print("   ├─ Each tool focused and debuggable")
    print("   └─ Ready for tool graph composition")
    print()
    
    print("Benefits:")
    print("✅ No regex imports needed")
    print("✅ No brittle string parsing")
    print("✅ Clean separation of concerns")
    print("✅ Structured data flow")
    print("✅ Easy to test and debug")
    print("✅ Ready for tool graphs")


if __name__ == "__main__":
    print("FDIC Atomic Tools Demo")
    print("=" * 50)
    
    # Show comparison first
    compare_with_old_approach()
    
    # Run async demos
    try:
        asyncio.run(demonstrate_cert_flow())
        asyncio.run(test_error_handling())
    except Exception as e:
        print(f"Demo failed: {e}")
        print("Note: This demo requires proper FDIC API configuration and network access")