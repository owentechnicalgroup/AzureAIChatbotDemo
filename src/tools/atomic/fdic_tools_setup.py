"""
Setup and registration for clean atomic FDIC tools.

Provides helper functions to initialize and configure FDIC tools with proper
category metadata for the dynamic tool loading system.
"""

from typing import List
from langchain.tools import BaseTool

from ..categories import add_category_metadata, ToolCategory
from .fdic_institution_search_tool import FDICInstitutionSearchTool
from .fdic_financial_data_tool import FDICFinancialDataTool


def create_fdic_atomic_tools(settings=None) -> List[BaseTool]:
    """
    Create and configure clean atomic FDIC tools with proper metadata.
    
    Args:
        settings: Application settings (optional)
        
    Returns:
        List of configured FDIC atomic tools with category metadata
    """
    # Create tools
    fdic_institution_search = FDICInstitutionSearchTool(settings=settings)
    fdic_financial_data = FDICFinancialDataTool(settings=settings)
    
    # Add category metadata
    add_category_metadata(
        fdic_institution_search,
        category=ToolCategory.BANKING,
        requires_services=["fdic_api"],
        priority=10,  # High priority for institution search
        tags=["fdic", "institution", "search", "discovery", "cert"]
    )
    
    add_category_metadata(
        fdic_financial_data,
        category=ToolCategory.BANKING,
        requires_services=["fdic_financial_api"],
        priority=9,   # High priority for financial data
        tags=["fdic", "financial", "ratios", "metrics", "analysis"]
    )
    
    return [fdic_institution_search, fdic_financial_data]


def get_fdic_tool_summary() -> dict:
    """
    Get summary of FDIC atomic tools and their capabilities.
    
    Returns:
        Dictionary with tool information and usage guide
    """
    return {
        "tools": {
            "fdic_institution_search": {
                "purpose": "Search FDIC database for institutions by name/location",
                "input": "name, city, state, active_only, limit",
                "output": "Structured JSON with institution details and CERT numbers",
                "use_case": "Discovery and identification of banks for analysis"
            },
            "fdic_financial_data": {
                "purpose": "Retrieve financial data and ratios for specific institutions",
                "input": "cert_id (required), analysis_type, quarters, report_date",
                "output": "Structured JSON with financial metrics and calculated ratios",
                "use_case": "Financial analysis using official FDIC regulatory data"
            }
        },
        "workflow": {
            "1": "Search for institution: fdic_institution_search_tool(name='Wells Fargo')",
            "2": "Extract CERT: cert_id = extract_cert_from_search(search_result)",
            "3": "Get financials: fdic_financial_data_tool(cert_id=cert_id, analysis_type='key_ratios')",
            "4": "Parse results: parse_financial_data_result(financial_result)"
        },
        "benefits": [
            "Clean separation of concerns",
            "Structured JSON output (no string parsing)",
            "Simplified CERT-based flow",
            "Tool graph ready",
            "Official FDIC regulatory data",
            "Proper error handling"
        ],
        "replaces": {
            "bank_lookup_tool": "fdic_institution_search_tool (better naming + structured output)",
            "bank_analysis_tool": "Use both tools in sequence or create tool graph"
        }
    }