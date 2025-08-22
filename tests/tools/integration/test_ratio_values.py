"""
Test to examine actual ratio values returned by FDIC API.
"""

import asyncio
import json
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

def test_ratio_values():
    """Test to see what ratio values look like from FDIC API."""
    print("Testing FDIC API Ratio Values")
    print("=" * 40)
    
    try:
        from src.config.settings import get_settings
        from src.tools.infrastructure.banking.fdic_financial_api import FDICFinancialAPI
        
        settings = get_settings()
        
        # Create the financial API client
        financial_api = FDICFinancialAPI(
            api_key=settings.fdic_api_key,
            timeout=30.0,
            cache_ttl=1800
        )
        
        print("Testing ratio values with Wells Fargo (CERT 3511)...")
        
        # Test the financial API with financial_summary analysis type to get more fields
        result = asyncio.run(financial_api.get_financial_data(
            cert_id="3511",
            analysis_type="financial_summary",
            quarters=1
        ))
        
        print(f"API Success: {result.success}")
        
        if result.success and result.financial_records:
            record = result.financial_records[0]
            print(f"Certificate: {record.cert}")
            print(f"Report Date: {record.repdte}")
            
            # Show available fields for debugging
            available_fields = record.get_available_fields()
            print(f"Available fields: {available_fields}")
            
            # Check if we have fields needed for NIM calculation
            nim_fields = ['netintinc', 'asset', 'intinc', 'eintexp']
            print(f"NIM calculation fields available:")
            for field in nim_fields:
                value = getattr(record, field, None)
                print(f"  {field}: {value}")
            
            # Check ratio values
            ratio_fields = ['roa', 'roe', 'nim', 'cet1r', 'tier1r', 'totcapr']
            
            print(f"\nRatio Values (raw from FDIC):")
            print("-" * 30)
            
            for field in ratio_fields:
                value = getattr(record, field, None)
                if value is not None:
                    print(f"{field.upper()}: {value} (type: {type(value)})")
                    
                    # Also show formatted version
                    formatted = record.format_ratio(field)
                    print(f"  Formatted: {formatted}")
                else:
                    print(f"{field.upper()}: Not available")
            
            # Also check if we have the calculated ratios
            print(f"\nCalculated Ratios:")
            print("-" * 20)
            calculated = record.calculate_derived_ratios()
            for name, value in calculated.items():
                if value is not None:
                    print(f"{name}: {value} (type: {type(value)})")
                    
            return True
        else:
            print(f"FAILED - API call failed: {result.error_message}")
            return False
            
    except Exception as e:
        print(f"FAILED - Test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_ratio_values()
    exit(0 if success else 1)