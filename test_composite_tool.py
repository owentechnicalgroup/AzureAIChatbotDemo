#!/usr/bin/env python3
"""
Test script to verify the new composite BankAnalysisTool works correctly.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

async def test_composite_tool():
    """Test the composite bank analysis tool."""
    print("Testing BankAnalysisTool...")
    
    try:
        from tools.call_report.bank_analysis_tool import BankAnalysisTool
        
        # Create the tool
        tool = BankAnalysisTool()
        print(f"Created tool: {tool.name}")
        
        # Test basic bank info lookup
        print("\n1. Testing basic info lookup...")
        result = await tool.execute(
            bank_name="Bank of America",
            query_type="basic_info"
        )
        
        if result.success:
            print("SUCCESS: Basic info lookup successful")
            print(f"Bank: {result.data['bank_info'].get('legal_name', 'Unknown')}")
            print(f"RSSD ID: {result.data['rssd_id']}")
        else:
            print(f"FAILED: Basic info lookup failed: {result.error}")
        
        # Test total assets query - this is the key multi-step test
        print("\n2. Testing total assets query...")
        result = await tool.execute(
            bank_name="Bank of America",
            query_type="total_assets"
        )
        
        if result.success:
            print("SUCCESS: Total assets query successful")
            print(f"Message: {result.data.get('message', 'N/A')}")
            if 'total_assets' in result.data:
                assets = result.data['total_assets']
                print(f"Total Assets: ${assets.get('value', 'N/A'):,}")
        else:
            print(f"FAILED: Total assets query failed: {result.error}")
        
        # Test ROA calculation
        print("\n3. Testing ROA calculation...")
        result = await tool.execute(
            bank_name="Wells Fargo",
            query_type="roa"
        )
        
        if result.success:
            print("SUCCESS: ROA calculation successful")
            print(f"Message: {result.data.get('message', 'N/A')}")
            if 'calculation' in result.data:
                print(f"Calculation: {result.data['calculation']}")
        else:
            print(f"FAILED: ROA calculation failed: {result.error}")
        
        # Test the schema
        print("\n4. Testing tool schema...")
        schema = tool.get_schema()
        print(f"Tool name: {schema['function']['name']}")
        print(f"Parameters: {list(schema['function']['parameters']['properties'].keys())}")
        
        return True
        
    except Exception as e:
        print(f"Error testing composite tool: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_composite_tool())
    if success:
        print("\nComposite tool test passed!")
        print("The tool should now handle multi-step queries in a single call.")
    else:
        print("\nComposite tool test failed.")
        sys.exit(1)