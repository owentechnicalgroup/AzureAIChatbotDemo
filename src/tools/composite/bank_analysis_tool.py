"""
LangChain-compatible Bank Analysis Tool with FDIC Financial Data API integration.

This tool combines real-time bank lookup with FDIC Financial Data API to provide
comprehensive financial analysis workflows using authoritative regulatory data.
"""

import asyncio
import json
from typing import Dict, Any, Optional, List, Type
from decimal import Decimal

import structlog
from pydantic import BaseModel, Field
from langchain.tools import BaseTool
from langchain.callbacks.manager import (
    AsyncCallbackManagerForToolRun,
    CallbackManagerForToolRun,
)

from ..atomic.fdic_institution_search_tool import FDICInstitutionSearchTool
from ..atomic.ffiec_call_report_data_tool import FFIECCallReportDataTool
from ..infrastructure.banking.fdic_financial_api import FDICFinancialAPI
from ..infrastructure.banking.fdic_financial_models import BankFinancialAnalysisInput
from ..infrastructure.banking.fdic_financial_constants import format_financial_value
from ..infrastructure.banking.fdic_models import BankAnalysisInput

logger = structlog.get_logger(__name__).bind(log_type="SYSTEM")


class BankAnalysisTool(BaseTool):
    """
    Enhanced LangChain-compatible bank analysis tool with FDIC Financial Data API integration.
    
    Combines real-time FDIC bank identification with authoritative FDIC Financial Data
    to provide comprehensive banking analysis in a single tool call using live regulatory data.
    """
    
    name: str = "bank_analysis"
    description: str = """Modern banking analysis tool with FDIC Financial Data API integration.

This tool provides comprehensive financial analysis using authoritative regulatory data sources:
- FDIC BankFind Suite API for real-time bank identification  
- FDIC Financial Data API for official regulatory financial metrics
- FFIEC Call Report data for detailed regulatory filings (when available)
- Real financial ratios calculated from actual regulatory data

Financial Analysis Capabilities:
- Complete financial summaries with balance sheet and income data
- Key financial ratios (ROA, ROE, NIM, capital ratios) from official FDIC data
- Asset quality metrics and regulatory capital information
- Real-time data directly from FDIC regulatory filings

Analysis Types:
- basic_info: Bank identification, assets, deposits, equity, and basic ratios
- financial_summary: Comprehensive balance sheet and income statement data
- key_ratios: Detailed profitability, capital, and asset quality ratios

Search by Bank Name (Recommended):
- bank_name: Institution name with intelligent matching (e.g., "Wells Fargo", "JPMorgan Chase")
- Optional: city and state for disambiguation if multiple banks share similar names

Example Usage:

1. Financial analysis of a major bank:
   - bank_name: "Bank of America"
   - query_type: "financial_summary"

2. Credit analysis with ratios:
   - bank_name: "First Merchants Bank" 
   - query_type: "key_ratios"

3. Basic bank information:
   - bank_name: "Chase Bank"
   - city: "New York"
   - state: "NY"
   - query_type: "basic_info"

Returns: Professional financial analysis using real FDIC regulatory data with formatted metrics and ratios."""
    
    args_schema: Type[BaseModel] = BankAnalysisInput
    
    def __init__(self, **kwargs):
        """Initialize the composite bank analysis tool with FDIC Financial API integration."""
        super().__init__(**kwargs)
        
        # Get settings from kwargs or use defaults
        from src.config.settings import get_settings
        settings = kwargs.get('settings') or get_settings()
        
        # Initialize component tools - use private attributes to avoid Pydantic conflicts
        object.__setattr__(self, '_bank_lookup', FDICInstitutionSearchTool(settings=settings))
        object.__setattr__(self, '_financial_client', FDICFinancialAPI(
            api_key=settings.fdic_api_key,
            timeout=settings.fdic_financial_api_timeout,
            cache_ttl=settings.fdic_financial_cache_ttl
        ))
        
        # Initialize FFIEC Call Report tool if available
        if (getattr(settings, 'ffiec_cdr_enabled', True) and 
            settings.ffiec_cdr_api_key and 
            settings.ffiec_cdr_username):
            object.__setattr__(self, '_ffiec_client', FFIECCallReportDataTool(settings=settings))
            object.__setattr__(self, '_has_ffiec', True)
            logger.info("BankAnalysisTool initialized with FDIC and FFIEC Call Report integration")
        else:
            object.__setattr__(self, '_ffiec_client', None)
            object.__setattr__(self, '_has_ffiec', False)
            logger.info("BankAnalysisTool initialized with FDIC integration only")
    
    @property
    def bank_lookup(self) -> FDICInstitutionSearchTool:
        """Get the bank lookup tool."""
        return getattr(self, '_bank_lookup')
    
    @property 
    def financial_client(self) -> FDICFinancialAPI:
        """Get the FDIC Financial API client."""
        return getattr(self, '_financial_client')
    
    @property
    def ffiec_client(self) -> Optional[FFIECCallReportDataTool]:
        """Get the FFIEC Call Report tool."""
        return getattr(self, '_ffiec_client', None)
    
    @property
    def has_ffiec_integration(self) -> bool:
        """Check if FFIEC Call Report integration is available."""
        return getattr(self, '_has_ffiec', False)
    
    def _run(
        self,
        bank_name: Optional[str] = None,
        query_type: str = "basic_info",
        city: Optional[str] = None,
        state: Optional[str] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Synchronous execution with enhanced FDIC search support."""
        try:
            # Try to get the current event loop
            loop = asyncio.get_running_loop()
            # If we're in an event loop, we need to handle this differently
            import concurrent.futures
            
            # Create a new event loop in a thread pool
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    lambda: asyncio.run(self._arun(bank_name, query_type, city, state, run_manager))
                )
                return future.result()
                
        except RuntimeError:
            # No event loop running, safe to use asyncio.run
            return asyncio.run(self._arun(bank_name, query_type, city, state, run_manager))
    
    async def _arun(
        self,
        bank_name: Optional[str] = None,
        query_type: str = "basic_info",
        city: Optional[str] = None,
        state: Optional[str] = None,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ) -> str:
        """
        Execute comprehensive bank analysis with clean FDIC integration.
        
        Args:
            bank_name: Bank name to search for (required)
            query_type: Type of analysis to perform ("basic_info", "financial_summary", "key_ratios")
            city: City to help identify the bank
            state: State abbreviation to help identify the bank
            run_manager: Optional callback manager
            
        Returns:
            Formatted analysis results using structured FDIC data
        """
        try:
            logger.info(
                "Executing enhanced bank analysis with FDIC integration",
                bank_name=bank_name,
                city=city,
                state=state,
                query_type=query_type
            )
            
            # Clean validation - require bank name for FDIC lookup
            if not bank_name:
                return "Error: bank_name is required for FDIC institution search"
            
            # Step 1: Initialize bank info structure
            bank_info = {
                "name": bank_name,
                "city": city,
                "state": state
            }
            
            # Step 2: Get FDIC Certificate ID using new structured tool
            cert_id = None
            
            # Try to extract certificate ID from the bank info or lookup result
            if bank_name and hasattr(self.bank_lookup, '_arun'):
                # Use new structured tool to get certificate ID
                try:
                    lookup_result = await self.bank_lookup._arun(name=bank_name, limit=1)
                    
                    # Parse structured JSON response from new tool
                    import json
                    result_data = json.loads(lookup_result)
                    
                    if result_data.get('success') and result_data.get('institutions'):
                        institution = result_data['institutions'][0]
                        cert_id = institution.get('cert')
                        # Update bank info with actual data including institution details
                        bank_info["name"] = institution.get('name', bank_name)
                        bank_info["location"] = institution.get('location', {})
                        bank_info["institution"] = institution  # Store full institution data for RSSD access
                        
                        logger.info(
                            "Successfully extracted certificate ID from structured lookup", 
                            cert_id=cert_id,
                            bank_name=bank_info["name"]
                        )
                    else:
                        logger.warning("No institutions found in lookup result", result=result_data)
                        
                except Exception as e:
                    logger.warning("Failed to lookup certificate ID", error=str(e), bank_name=bank_name)
            
            if not cert_id:
                # No way to get certificate ID - return helpful error
                return f"""Error: Cannot retrieve financial data without FDIC Certificate number.

Bank: {bank_info.get('name', bank_name or 'Unknown')}

The institution search did not return a valid FDIC Certificate number.
Please verify the bank name and try again with a more complete name.

Examples:
- "Wells Fargo Bank" instead of "Wells Fargo"  
- "JPMorgan Chase Bank" instead of "Chase"
- "Bank of America" with complete name

The bank name must match an active FDIC-insured institution."""
            
            # Step 3: Get financial data based on query type
            if query_type == "basic_info":
                return await self._get_basic_info(bank_info, cert_id)
            elif query_type == "financial_summary":
                return await self._get_financial_summary(bank_info, cert_id)
            elif query_type == "key_ratios":
                return await self._get_key_ratios(bank_info, cert_id)
            else:
                return f"Error: Unknown query_type '{query_type}'. Use 'basic_info', 'financial_summary', or 'key_ratios'"
                
        except Exception as e:
            logger.error("Bank analysis failed", error=str(e))
            return f"Error: Bank analysis failed - {str(e)}"
    
    async def _get_basic_info(self, bank_info: Dict[str, Any], cert_id: str) -> str:
        """Get basic bank information and key metrics using FDIC financial data."""
        try:
            logger.info("Getting basic info with FDIC Financial API", cert_id=cert_id)
            
            # Query basic financial information
            financial_response = await self.financial_client.get_financial_data(
                cert_id=cert_id,
                analysis_type="basic_info",
                quarters=1
            )
            
            if not financial_response.success or not financial_response.financial_records:
                return f"""Bank Analysis - Basic Information:

Bank: {bank_info.get('name', 'Unknown')}
FDIC Certificate: {cert_id}
Location: {bank_info.get('location', 'Not specified')}

Error: Financial data not available for certificate {cert_id}

Data Source: FDIC BankFind Suite Financial API"""
            
            # Get basic financial data
            latest_data = financial_response.financial_records[0]
            
            # Update bank_info with RSSD ID from FDIC data (or "N/A" if not available)
            # Try rssd first, then fed_rssd from the institution lookup, then fallback to N/A
            rssd_from_fdic = latest_data.rssd if latest_data.rssd else None
            rssd_from_lookup = bank_info.get("institution", {}).get("fed_rssd") if bank_info.get("institution") else None
            bank_info["rssd"] = rssd_from_fdic or rssd_from_lookup or "N/A"
            
            return f"""Bank Analysis - Basic Information:

Bank: {bank_info.get('name', 'Unknown')}
FDIC Certificate: {cert_id}
RSSD ID: {latest_data.rssd or 'Not available'}
Location: {bank_info.get('location', 'Not specified')}
Report Date: {latest_data.repdte}

Key Financial Metrics:
- Total Assets: {latest_data.format_asset()}
- Total Deposits: {latest_data.format_deposits()}
- Total Equity: {latest_data.format_equity()}
- Net Income: {latest_data.format_net_income()}

Basic Ratios:
- Return on Assets: {latest_data.format_ratio('roa')}
- Return on Equity: {latest_data.format_ratio('roe')}

Data Quality: {len(latest_data.get_available_fields())} financial metrics available
Data Source: FDIC BankFind Suite Financial API
Analysis Type: Basic Information"""
            
        except Exception as e:
            logger.error("Basic info retrieval failed", error=str(e), cert_id=cert_id)
            return f"Error retrieving basic info: {str(e)}"
    
    async def _get_financial_summary(self, bank_info: Dict[str, Any], cert_id: str) -> str:
        """Get comprehensive financial summary with real FDIC financial data."""
        try:
            logger.info("Getting financial summary with FDIC Financial API", cert_id=cert_id)
            
            # PATTERN: Query multiple financial fields efficiently using analysis_type
            financial_response = await self.financial_client.get_financial_data(
                cert_id=cert_id,
                analysis_type="financial_summary",
                quarters=1  # Most recent quarter
            )
            
            if not financial_response.success or not financial_response.financial_records:
                return f"""Bank Analysis - Financial Summary:

Bank: {bank_info.get('name', 'Unknown')}
FDIC Certificate: {cert_id}

Error: Financial data not available for certificate {cert_id}

Possible reasons:
- Bank may not report financial data to FDIC
- Certificate number may be incorrect
- Bank may be inactive or merged

Data Source: FDIC BankFind Suite Financial API"""
            
            # Get most recent financial data
            latest_data = financial_response.financial_records[0]
            
            # Update bank_info with RSSD ID from FDIC data (or "N/A" if not available)
            # Try rssd first, then fed_rssd from the institution lookup, then fallback to N/A
            rssd_from_fdic = latest_data.rssd if latest_data.rssd else None
            rssd_from_lookup = bank_info.get("institution", {}).get("fed_rssd") if bank_info.get("institution") else None
            bank_info["rssd"] = rssd_from_fdic or rssd_from_lookup or "N/A"
            
            return f"""Bank Analysis - Financial Summary:

Bank: {bank_info.get('name', 'Unknown')}
FDIC Certificate: {cert_id}
Report Date: {latest_data.repdte}

Balance Sheet:
- Total Assets: {latest_data.format_asset()}
- Total Deposits: {latest_data.format_deposits()}
- Total Loans & Leases: {format_financial_value(latest_data.lnls) if latest_data.lnls else "Not available"}
- Total Equity Capital: {latest_data.format_equity()}

Income Statement:
- Net Income: {latest_data.format_net_income()}
- Interest Income: {format_financial_value(latest_data.intinc) if latest_data.intinc else "Not available"}
- Interest Expense: {format_financial_value(latest_data.eintexp) if latest_data.eintexp else "Not available"}
- Net Interest Income: {format_financial_value(latest_data.netintinc) if latest_data.netintinc else "Not available"}

Data Quality: {len(latest_data.get_available_fields())} financial metrics available
Data Source: FDIC BankFind Suite Financial API
Analysis Type: Financial Summary"""
            
        except Exception as e:
            logger.error("Financial summary failed", error=str(e), cert_id=cert_id)
            return f"Error retrieving financial summary: {str(e)}"
    
    async def _get_key_ratios(self, bank_info: Dict[str, Any], cert_id: str) -> str:
        """Calculate key financial ratios from real FDIC data."""
        try:
            logger.info("Calculating key financial ratios with FDIC Financial API", cert_id=cert_id)
            
            # Query specific fields needed for ratio calculations
            financial_response = await self.financial_client.get_financial_data(
                cert_id=cert_id,
                analysis_type="key_ratios",
                quarters=1
            )
            
            if not financial_response.success or not financial_response.financial_records:
                return f"""Bank Analysis - Key Financial Ratios:

Bank: {bank_info.get('name', 'Unknown')}
FDIC Certificate: {cert_id}

Error: Financial data not available for ratio calculation

Possible reasons:
- Bank may not report financial data to FDIC
- Certificate number may be incorrect
- Bank may be inactive or merged

Data Source: FDIC BankFind Suite Financial API"""
                
            latest_data = financial_response.financial_records[0]
            
            # Update bank_info with RSSD ID from FDIC data (or "N/A" if not available)
            # Try rssd first, then fed_rssd from the institution lookup, then fallback to N/A
            rssd_from_fdic = latest_data.rssd if latest_data.rssd else None
            rssd_from_lookup = bank_info.get("institution", {}).get("fed_rssd") if bank_info.get("institution") else None
            bank_info["rssd"] = rssd_from_fdic or rssd_from_lookup or "N/A"
            
            # Get calculated ratios from FDIC data and derive additional ones
            calculated_ratios = latest_data.calculate_derived_ratios()
            
            # Format ratios for display
            def format_ratio(value: Optional[Decimal], from_calculated: bool = False) -> str:
                """Format ratio value as percentage."""
                if value is None:
                    return "Not available"
                return f"{value:.2f}%"
            
            # Primary ratios (from FDIC if available, otherwise calculated)
            roa = latest_data.roa if latest_data.roa is not None else calculated_ratios.get("calculated_roa")
            roe = latest_data.roe if latest_data.roe is not None else calculated_ratios.get("calculated_roe") 
            nim = latest_data.nim if latest_data.nim is not None else calculated_ratios.get("calculated_nim")
            
            return f"""Bank Analysis - Key Financial Ratios:

Bank: {bank_info.get('name', 'Unknown')}
FDIC Certificate: {cert_id}
Report Date: {latest_data.repdte}

Profitability Ratios:
- Return on Assets (ROA): {format_ratio(roa)}
- Return on Equity (ROE): {format_ratio(roe)}
- Net Interest Margin (NIM): {format_ratio(nim)}

Capital Ratios:
- Common Equity Tier 1 Ratio: {format_ratio(latest_data.cet1r)}
- Tier 1 Capital Ratio: {format_ratio(latest_data.tier1r)}
- Total Capital Ratio: {format_ratio(latest_data.totcapr)}

Additional Ratios (Calculated):
- Equity to Assets: {format_ratio(calculated_ratios.get("equity_to_assets"))}
- Loans to Deposits: {format_ratio(calculated_ratios.get("loans_to_deposits"))}
- Efficiency Ratio: {format_ratio(calculated_ratios.get("calculated_efficiency"))}

Asset Quality:
- Nonperforming Loans Ratio: {format_ratio(latest_data.nptla)}

Data Quality: {len(latest_data.get_available_fields())} financial metrics available
Calculation Method: FDIC reported ratios with calculated supplements
Data Source: FDIC BankFind Suite Financial API
Analysis Type: Key Financial Ratios

Additional Data Sources Available:
{self._get_data_sources_summary(bank_info.get('rssd'))}"""
            
        except Exception as e:
            logger.error("Key ratios calculation failed", error=str(e), cert_id=cert_id)
            return f"Error calculating financial ratios: {str(e)}"
    
    def _get_data_sources_summary(self, rssd_id: Optional[str] = None) -> str:
        """Get summary of available data sources for this bank."""
        sources = []
        
        # FDIC data is always available if tool is working
        sources.append("- FDIC Financial Data: Available")
        
        # Check FFIEC Call Report availability
        if self.has_ffiec_integration:
            if rssd_id:
                sources.append(f"- FFIEC Call Reports: Available (use ffiec_call_report_data tool with RSSD {rssd_id})")
            else:
                sources.append("- FFIEC Call Reports: Available (requires RSSD ID)")
        else:
            sources.append("- FFIEC Call Reports: Not configured")
        
        return "\n".join(sources)
    
    def is_available(self) -> bool:
        """Check if the bank analysis service is available."""
        return self.financial_client.is_available() and self.bank_lookup.is_available()