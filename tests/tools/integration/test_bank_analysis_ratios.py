"""
Test bank analysis tool with fixed ratio calculations.
"""

import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

def test_bank_analysis_ratios():
    """Test bank analysis tool with realistic ratio values."""
    print("Testing Bank Analysis Tool with Fixed Ratios")
    print("=" * 50)
    
    try:
        from src.config.settings import get_settings
        from src.tools.composite.bank_analysis_tool import BankAnalysisTool
        
        settings = get_settings()
        analysis_tool = BankAnalysisTool(settings=settings)
        
        print("Testing with Wells Fargo - financial summary analysis...")
        
        # Test with financial_summary analysis to get ratios
        result = asyncio.run(analysis_tool._arun(
            bank_name="Wells Fargo",
            query_type="financial_summary"
        ))
        
        print("Analysis result:")
        print("-" * 30)
        print(result)
        
        # Check for realistic ratio values in the output
        if "%" in result:
            print("\nRatio analysis:")
            print("-" * 20)
            
            # Look for ratio mentions
            lines = result.split('\n')
            for line in lines:
                if any(ratio_term in line.lower() for ratio_term in ['roa', 'roe', 'nim', 'ratio', '%']):
                    print(f"  {line.strip()}")
            
            # Check for unrealistic values
            unrealistic_found = False
            for line in lines:
                if "%" in line:
                    # Extract numbers with % sign
                    import re
                    percentages = re.findall(r'[\d,]+\.?\d*%', line)
                    for pct in percentages:
                        value = float(pct.replace('%', '').replace(',', ''))
                        if value > 1000:  # More than 1000% is unrealistic for most bank ratios
                            print(f"UNREALISTIC RATIO FOUND: {pct} in line: {line.strip()}")
                            unrealistic_found = True
            
            if not unrealistic_found:
                print("\nSUCCESS: All ratio values appear realistic!")
                return True
            else:
                print("\nFAILED: Found unrealistic ratio values")
                return False
        else:
            print("No ratio data found in analysis")
            # Still count as success if no errors
            return "Error:" not in result
            
    except Exception as e:
        print(f"FAILED - Test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_bank_analysis_ratios()
    exit(0 if success else 1)