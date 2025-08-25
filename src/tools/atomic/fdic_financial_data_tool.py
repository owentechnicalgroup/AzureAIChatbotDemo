"""
Atomic FDIC Financial Data Tool.

Clean, focused tool for retrieving financial data using FDIC BankFind Suite Financial Data API.
Requires CERT number from institution search tool.
"""

import asyncio
from typing import Optional, Type, Dict, Any
from datetime import datetime, timezone

import structlog
from pydantic import BaseModel, Field
from langchain.tools import BaseTool
from langchain.callbacks.manager import (
    AsyncCallbackManagerForToolRun,
    CallbackManagerForToolRun,
)

from ..infrastructure.banking.fdic_financial_api import FDICFinancialAPI
from ..infrastructure.banking.fdic_financial_models import FDICFinancialData

logger = structlog.get_logger(__name__).bind(log_type="SYSTEM")


class FDICFinancialDataInput(BaseModel):
    """Clean input schema for FDIC financial data retrieval."""
    
    cert_id: str = Field(
        ...,
        description="FDIC Certificate number (from institution search tool)",
        min_length=1,
        max_length=10
    )
    analysis_type: str = Field(
        "profitability",
        description="Type of financial analysis - see tool description for complete list of 24 analysis types covering all aspects of bank financial data"
    )
    quarters: int = Field(
        1,
        description="Number of recent quarters to retrieve (1-8)",
        ge=1,
        le=8
    )
    report_date: Optional[str] = Field(
        None,
        description="Specific report date (YYYY-MM-DD format), or None for most recent"
    )

    @property
    def is_valid_analysis_type(self) -> bool:
        """Check if analysis type is valid."""
        from ..infrastructure.banking.fdic_financial_constants import FIELD_SELECTION_TEMPLATES
        return self.analysis_type in FIELD_SELECTION_TEMPLATES


class FDICFinancialDataTool(BaseTool):
    """
    Atomic tool for retrieving FDIC financial data.
    
    Provides clean, focused financial data retrieval using FDIC Financial Data API.
    Requires CERT number from institution search - no complex coordination logic.
    
    Key Features:
    - Direct CERT-based financial data retrieval
    - Multiple analysis types (basic, summary, ratios)
    - Historical data support (multiple quarters)
    - Real FDIC regulatory data
    - Structured output with calculated ratios
    
    Analysis Types:
    - basic_info: Core metrics (assets, deposits, equity, net income)
    - financial_summary: Complete balance sheet and income statement
    - key_ratios: Profitability, capital, and efficiency ratios
    
    Input Requirements:
    - cert_id: FDIC Certificate number (from fdic_institution_search_tool)
    
    Example Usage:
    - cert_id="3511", analysis_type="key_ratios" → Wells Fargo ratios
    - cert_id="628", analysis_type="financial_summary" → JPMorgan financials
    - cert_id="12345", quarters=4 → Last 4 quarters of data
    
    Output: Structured financial data with calculations and ratios
    """
    
    name: str = "fdic_financial_data"
    description: str = """Retrieve financial data for FDIC-insured institutions.

This atomic tool retrieves comprehensive financial data from the FDIC Financial Data API using 
institution Certificate numbers. Provides real regulatory financial metrics organized by analysis type.

Required Input:
- cert_id: FDIC Certificate number (obtained from fdic_institution_search_tool)

Optional Parameters:
- analysis_type: Type of financial analysis to perform (determines field selection)
- quarters: Number of recent quarters to retrieve (1-8, default: 1)  
- report_date: Specific report date in YYYY-MM-DD format (default: most recent)

ANALYSIS TYPES (24 comprehensive categories from FDIC RISView Data Dictionary):

🔍 INSTITUTION INFORMATION:
📋 "institution_profile": Basic institution info and classification
📁 "institution_identification": Core ID and reporting date fields  
🏛️ "institution_classification": Institution status and classification codes
📜 "charter_regulatory": Charter authority and regulatory oversight
🛡️ "insurance_classification": Deposit insurance status and fund membership
⭐ "specialized_institution_types": Special designations (community bank, minority-owned, etc.)

🌍 GEOGRAPHIC & ADMINISTRATIVE:
🗺️ "geographic_information": Location and market information
🏢 "fdic_administrative": FDIC regions and supervisory assignments
🏪 "office_branch_information": Branch network and office distribution

👥 CORPORATE STRUCTURE:
🏢 "holding_company_information": Bank holding company relationships
💼 "specialized_business": Specialized business activities and focus areas
📋 "call_report_information": Regulatory filing information

💰 BALANCE SHEET:
🏛️ "balance_sheet_assets": Asset composition and portfolio structure
🏦 "balance_sheet_liabilities": Funding structure and liability composition
💰 "deposit_composition": Detailed deposit mix and maturity analysis
🏠 "loan_portfolio": Loan composition by type and category
💎 "securities_investments": Securities holdings and short-term investments
🏗️ "borrowings_liabilities": Non-deposit liabilities and borrowing arrangements
🧱 "equity_capital_components": Detailed equity capital breakdown

⚠️ CREDIT RISK:
⚠️ "credit_quality": Asset quality and credit risk metrics
🛡️ "allowance_credit_losses": Allowance for credit losses and risk reserves
📉 "provision_credit_losses": Credit loss provisions and expense recognition
📊 "charge_offs_recoveries": Actual charge-offs and recoveries

💹 INCOME STATEMENT:
💹 "interest_income": Interest income by source and type
💸 "interest_expense": Interest expense and cost of funds
💼 "noninterest_income_expense": Fee income and operating expenses
💰 "net_income_components": Detailed net income and tax components
💵 "dividend_information": Dividend payments and distribution policies

📊 PERFORMANCE:
📊 "profitability": Earnings metrics and return ratios
📈 "performance_ratios": Key performance and profitability ratios
🏛️ "capital_ratios": Regulatory capital ratios and components
⚡ "efficiency_metrics": Operating efficiency and productivity ratios

Each analysis type requests only the specific fields needed for that analysis, optimizing API performance and providing focused data sets.

Data Quality:
- Sourced from official FDIC regulatory filings (RISView database)
- Field selection optimized per analysis type for performance
- Includes validation and completeness indicators
- Real financial calculations using regulatory formulas

Output Format:
- Structured JSON with financial metrics specific to analysis type
- Formatted currency values and percentages
- Field availability and completeness information  
- Analysis-specific calculations and derived metrics"""
    
    args_schema: Type[BaseModel] = FDICFinancialDataInput
    
    def __init__(self, **kwargs):
        """Initialize FDIC financial data tool."""
        super().__init__(**kwargs)
        
        # Get settings
        from src.config.settings import get_settings
        settings = kwargs.get('settings') or get_settings()
        
        # Initialize FDIC Financial API client
        object.__setattr__(self, '_financial_client', FDICFinancialAPI(
            api_key=settings.fdic_api_key,
            timeout=settings.fdic_financial_api_timeout,
            cache_ttl=settings.fdic_financial_cache_ttl
        ))
        
        logger.info("FDIC financial data tool initialized")
    
    @property
    def financial_client(self) -> FDICFinancialAPI:
        """Get the FDIC Financial API client."""
        return getattr(self, '_financial_client')
    
    def _run(
        self,
        cert_id: str,
        analysis_type: str = "financial_summary",
        quarters: int = 1,
        report_date: Optional[str] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Synchronous execution wrapper."""
        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    lambda: asyncio.run(self._arun(cert_id, analysis_type, quarters, report_date, None))
                )
                return future.result()
                
        except RuntimeError:
            return asyncio.run(self._arun(cert_id, analysis_type, quarters, report_date, None))
    
    async def _arun(
        self,
        cert_id: str,
        analysis_type: str = "profitability", 
        quarters: int = 1,
        report_date: Optional[str] = None,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ) -> str:
        """
        Retrieve FDIC financial data with clean, simple interface.
        
        Returns:
            Structured JSON string with financial data
        """
        try:
            start_time = datetime.now(timezone.utc)
            
            logger.info(
                "Starting FDIC financial data retrieval",
                cert_id=cert_id,
                analysis_type=analysis_type,
                quarters=quarters,
                report_date=report_date
            )
            
            # Validate input
            if not cert_id or not cert_id.isdigit():
                logger.warning(
                    "Invalid cert_id provided",
                    cert_id=cert_id,
                    analysis_type=analysis_type,
                    error="cert_id must be numeric"
                )
                return self._format_error("Invalid cert_id - must be numeric FDIC certificate number")
            
            # Get valid analysis types from constants
            from ..infrastructure.banking.fdic_financial_constants import FIELD_SELECTION_TEMPLATES
            valid_analysis_types = list(FIELD_SELECTION_TEMPLATES.keys())
            
            if analysis_type not in valid_analysis_types:
                logger.warning(
                    "Invalid analysis_type provided",
                    cert_id=cert_id,
                    analysis_type=analysis_type,
                    valid_types=valid_analysis_types
                )
                return self._format_error(f"Invalid analysis_type - use one of: {', '.join(valid_analysis_types)}")
            
            logger.info(
                "Calling FDIC Financial API",
                cert_id=cert_id,
                analysis_type=analysis_type,
                quarters=quarters,
                report_date=report_date
            )
            
            # Retrieve financial data from FDIC API
            response = await self.financial_client.get_financial_data(
                cert_id=cert_id,
                analysis_type=analysis_type,
                quarters=quarters,
                report_date=report_date
            )
            
            if not response.success:
                logger.error(
                    "FDIC API call failed",
                    cert_id=cert_id,
                    analysis_type=analysis_type,
                    error_message=response.error_message
                )
                return self._format_error(f"FDIC financial data retrieval failed: {response.error_message}")
            
            if not response.financial_records:
                logger.warning(
                    "No financial data found",
                    cert_id=cert_id,
                    analysis_type=analysis_type,
                    quarters=quarters
                )
                return self._format_no_data(cert_id)
            
            logger.info(
                "Processing financial data response",
                cert_id=cert_id,
                analysis_type=analysis_type,
                records_found=len(response.financial_records)
            )
            
            # Format results based on analysis type and available fields
            result = self._format_financial_data(response.financial_records[0], cert_id, analysis_type)
            
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            logger.info(
                "FDIC financial data retrieval completed successfully",
                cert_id=cert_id,
                analysis_type=analysis_type,
                quarters=quarters,
                execution_time=execution_time,
                result_size=len(result)
            )
            
            return result
            
        except Exception as e:
            logger.error(
                "FDIC financial data retrieval failed with exception",
                error=str(e),
                cert_id=cert_id,
                analysis_type=analysis_type,
                quarters=quarters,
                report_date=report_date
            )
            return self._format_error(f"Financial data retrieval failed: {str(e)}")
    
    def _format_financial_data(self, financial_data: FDICFinancialData, cert_id: str, analysis_type: str) -> str:
        """Format financial data dynamically based on analysis type and available fields."""
        from ..infrastructure.banking.fdic_financial_constants import (
            format_financial_value, 
            ANALYSIS_TYPE_DESCRIPTIONS,
            get_fields_for_analysis_type
        )
        
        # Get the expected fields for this analysis type
        expected_fields = set(get_fields_for_analysis_type(analysis_type))
        available_fields = set(financial_data.get_available_fields())
        
        # Get analysis type metadata
        analysis_metadata = ANALYSIS_TYPE_DESCRIPTIONS.get(analysis_type, {})
        
        # Helper function to safely get and format field values
        def format_field_value(field_name: str, field_data, is_ratio: bool = False) -> Dict[str, Any]:
            """Format a field value with proper handling for None values."""
            if field_data is None:
                return {
                    "value": None,
                    "formatted": "Not available",
                    "unit": "percentage" if is_ratio else "thousands_usd"
                }
            
            if is_ratio:
                return {
                    "value": float(field_data),
                    "formatted": f"{float(field_data):.2f}%",
                    "unit": "percentage"
                }
            else:
                return {
                    "value": float(field_data),
                    "formatted": format_financial_value(float(field_data)),
                    "unit": "thousands_usd"
                }
        
        # Build the result structure dynamically based on available fields
        result = {
            "success": True,
            "analysis_type": analysis_type,
            "cert_id": cert_id,
            "report_date": str(financial_data.repdte) if financial_data.repdte else None,
            "financial_data": {}
        }
        
        # Add analysis type description
        if analysis_metadata:
            result["analysis_info"] = {
                "description": analysis_metadata.get("description", ""),
                "use_cases": analysis_metadata.get("use_cases", [])
            }
        
        # Dynamically add fields based on what's available
        field_details = analysis_metadata.get("field_details", {})
        
        for field_name in expected_fields:
            if field_name in ["CERT", "REPDTE"]:
                continue  # Skip identifier fields
            
            field_value = getattr(financial_data, field_name.lower(), None)
            field_description = field_details.get(field_name, f"Field {field_name}")
            
            # Determine if this is a ratio field (typically percentage)
            is_ratio = field_name.endswith('R') or field_name in ['ROA', 'ROE', 'NIM', 'CET1R', 'TIER1R', 'TOTCAPR', 'NPTLA', 'ROAPTX', 'INTEXPY']
            
            if field_value is not None or field_name in available_fields:
                result["financial_data"][field_name] = {
                    **format_field_value(field_name, field_value, is_ratio),
                    "description": field_description,
                    "available": field_value is not None
                }
        
        # Add data quality metrics
        result["data_quality"] = {
            "analysis_type": analysis_type,
            "fields_requested": len(expected_fields),
            "fields_available": len(available_fields & expected_fields),
            "fields_missing": len(expected_fields - available_fields),
            "completeness_percentage": round((len(available_fields & expected_fields) / len(expected_fields)) * 100, 1) if expected_fields else 100,
            "report_date": str(financial_data.repdte) if financial_data.repdte else None,
            "total_fields_in_response": len(available_fields)
        }
        
        # Add missing fields list if any
        missing_fields = expected_fields - available_fields
        if missing_fields:
            result["data_quality"]["missing_fields"] = list(missing_fields)
        
        # Add calculated ratios if available and relevant
        if hasattr(financial_data, 'calculate_derived_ratios'):
            calculated_ratios = financial_data.calculate_derived_ratios()
            if calculated_ratios:
                result["calculated_metrics"] = {}
                for ratio_name, ratio_value in calculated_ratios.items():
                    if ratio_value is not None:
                        result["calculated_metrics"][ratio_name] = format_field_value(ratio_name, ratio_value, True)
        
        import json
        return json.dumps(result, indent=2)
    
    def _format_no_data(self, cert_id: str) -> str:
        """Format no data found message."""
        result = {
            "success": False,
            "error": "No financial data found",
            "cert_id": cert_id,
            "message": f"No financial data available for FDIC Certificate {cert_id}",
            "possible_reasons": [
                "Certificate number may be incorrect",
                "Institution may not report financial data to FDIC",
                "Institution may be inactive or merged",
                "Data may not be available for requested time period"
            ]
        }
        
        import json
        return json.dumps(result, indent=2)
    
    def _format_error(self, error_message: str) -> str:
        """Format error as structured JSON."""
        result = {
            "success": False,
            "error": error_message,
            "financial_data": None
        }
        
        import json
        return json.dumps(result, indent=2)
    
    def is_available(self) -> bool:
        """Check if FDIC financial data service is available."""
        return self.financial_client.is_available()