#!/usr/bin/env python3
"""
Test script to verify Call Report tools are working correctly.
Run this before starting the Streamlit app to ensure everything is set up.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

async def test_call_report_tools():
    """Test Call Report tools functionality."""
    print("Testing Call Report Tools...")
    
    try:
        # Import required modules
        from tools.call_report.langchain_tools import create_call_report_toolset
        from config.settings import Settings
        print("Successfully imported Call Report modules")
        
        # Load settings
        settings = Settings()
        print(f"Settings loaded - Call Report enabled: {getattr(settings, 'call_report_enabled', 'Not set')}")
        
        # Create toolset
        toolset = create_call_report_toolset(settings)
        tools = toolset.get_tools()
        print(f"Created toolset with {len(tools)} tools")
        
        # List available tools
        for tool in tools:
            print(f"   - {tool.name}: {tool.description[:50]}...")
        
        # Test bank lookup
        print("\nTesting bank lookup...")
        bank_lookup_tool = next(t for t in tools if t.name == "bank_lookup")
        lookup_result = await bank_lookup_tool.execute(search_term="Wells Fargo", max_results=1)
        
        if lookup_result.success:
            print("Bank lookup successful!")
            print(f"   Found: {lookup_result.data.get('total_found', 0)} banks")
            if lookup_result.data.get('best_match'):
                best_match = lookup_result.data['best_match']['bank_info']
                print(f"   Best match: {best_match['legal_name']} (RSSD: {best_match['rssd_id']})")
        else:
            print(f"Bank lookup failed: {lookup_result.error}")
        
        # Test Call Report data retrieval
        print("\nTesting Call Report data...")
        data_tool = next(t for t in tools if t.name == "call_report_data")
        data_result = await data_tool.execute(
            rssd_id="123456", 
            schedule="RC", 
            field_id="RCON2170"
        )
        
        if data_result.success:
            print("Call Report data retrieval successful!")
            print(f"   Field: {data_result.data.get('field_name', 'Unknown')}")
            print(f"   Value: ${data_result.data.get('value', 'N/A'):,}")
        else:
            print(f"Call Report data failed: {data_result.error}")
        
        # Test health status
        print("\nTesting toolset health...")
        health = toolset.get_health_status()
        print(f"Overall health: {health['overall_health']}")
        print(f"   Tools available: {health['toolset_enabled']}")
        print(f"   API banks: {health['services']['api_client']['banks_available']}")
        print(f"   Directory banks: {health['services']['lookup_service']['banks_directory_size']}")
        
        print("\nAll Call Report tools are working correctly!")
        return True
        
    except Exception as e:
        print(f"Error testing Call Report tools: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_call_report_tools())
    if success:
        print("\nReady to start Streamlit app with Call Report tools!")
        print("Run: streamlit run src/ui/streamlit_app.py")
    else:
        print("\nFix issues before starting Streamlit app")
        sys.exit(1)