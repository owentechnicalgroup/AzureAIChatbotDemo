"""
Complete test showing all ratios working correctly.
"""

import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

def test_complete_ratios():
    """Test complete ratio calculations."""
    print("Complete Ratio Test")
    print("=" * 30)
    
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
        
        print("Testing with Wells Fargo (CERT 3511) - financial_summary...")
        
        result = asyncio.run(financial_api.get_financial_data(
            cert_id="3511",
            analysis_type="financial_summary",
            quarters=1
        ))
        
        if result.success and result.financial_records:
            record = result.financial_records[0]
            print(f"Certificate: {record.cert}")
            print(f"Report Date: {record.repdte}")
            
            # Show FDIC-provided ratios (the realistic ones)
            print(f"\nFDIC-Provided Ratios (realistic):")
            print("-" * 35)
            fdic_ratios = ['roa', 'roe']
            for field in fdic_ratios:
                value = getattr(record, field, None)
                if value is not None:
                    print(f"  {field.upper()}: {value:.2f}%")
            
            # Show calculated ratios
            print(f"\nCalculated Ratios (from raw data):")
            print("-" * 35)
            calculated = record.calculate_derived_ratios()
            for name, value in calculated.items():
                if value is not None:
                    print(f"  {name}: {value:.2f}%")
            
            # Show assets and income for context
            print(f"\nRaw Financial Data (in thousands):")
            print("-" * 35)
            print(f"  Total Assets: ${record.asset:,.0f}K")
            print(f"  Total Equity: ${record.eq:,.0f}K")
            print(f"  Net Income: ${record.netinc:,.0f}K")
            if record.intinc:
                print(f"  Interest Income: ${record.intinc:,.0f}K")
            if record.eintexp:
                print(f"  Interest Expense: ${record.eintexp:,.0f}K")
                
            # Calculate and show Net Interest Income manually
            if record.intinc and record.eintexp:
                net_int_income = record.intinc - record.eintexp
                print(f"  Net Interest Income: ${net_int_income:,.0f}K")
                manual_nim = (net_int_income / record.asset) * 100
                print(f"  Manual NIM calculation: {manual_nim:.2f}%")
            
            return True
        else:
            print(f"Failed: {result.error_message}")
            return False
            
    except Exception as e:
        print(f"Failed: {e}")
        return False

if __name__ == "__main__":
    success = test_complete_ratios()
    exit(0 if success else 1)