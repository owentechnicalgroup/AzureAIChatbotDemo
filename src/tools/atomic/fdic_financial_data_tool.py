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
        "financial_summary",
        description="Type of financial analysis: 'basic_info', 'financial_summary', or 'key_ratios'"
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
        return self.analysis_type in ["basic_info", "financial_summary", "key_ratios"]


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
institution Certificate numbers. Provides real regulatory financial metrics and ratios.

Required Input:
- cert_id: FDIC Certificate number (obtained from fdic_institution_search_tool)

Optional Parameters:
- analysis_type: Type of financial analysis to perform
  * "basic_info": Core financial metrics (assets, deposits, equity, net income)
  * "financial_summary": Complete balance sheet and income statement data
  * "key_ratios": Detailed profitability, capital, and asset quality ratios
- quarters: Number of recent quarters to retrieve (1-8, default: 1)
- report_date: Specific report date in YYYY-MM-DD format (default: most recent)

Financial Data Provided:
- Balance sheet items (assets, deposits, loans, equity)
- Income statement data (net income, interest income/expense)
- Regulatory ratios (ROA, ROE, NIM, capital ratios)
- Asset quality metrics (nonperforming loans)
- Calculated efficiency and performance ratios

Data Quality:
- Sourced from official FDIC regulatory filings
- Includes validation and completeness indicators
- Provides metadata about data availability
- Real financial calculations using regulatory formulas

Output Format:
- Structured JSON with financial metrics
- Formatted currency values and percentages  
- Data quality and completeness information
- Calculation methodology details

Use Cases:
1. Financial analysis: Get comprehensive bank financials
2. Ratio analysis: Calculate and compare financial ratios
3. Trend analysis: Retrieve multiple quarters for trending
4. Regulatory analysis: Access official FDIC filing data"""
    
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
        analysis_type: str = "financial_summary", 
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
            
            if analysis_type not in ["basic_info", "financial_summary", "key_ratios"]:
                logger.warning(
                    "Invalid analysis_type provided",
                    cert_id=cert_id,
                    analysis_type=analysis_type,
                    valid_types=["basic_info", "financial_summary", "key_ratios"]
                )
                return self._format_error("Invalid analysis_type - use 'basic_info', 'financial_summary', or 'key_ratios'")
            
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
            
            # Format results based on analysis type
            if analysis_type == "basic_info":
                result = self._format_basic_info(response.financial_records[0], cert_id)
            elif analysis_type == "financial_summary":
                result = self._format_financial_summary(response.financial_records[0], cert_id)
            elif analysis_type == "key_ratios":
                result = self._format_key_ratios(response.financial_records[0], cert_id)
            else:
                logger.error(
                    "Unsupported analysis type in formatting",
                    cert_id=cert_id,
                    analysis_type=analysis_type
                )
                result = self._format_error(f"Unsupported analysis type: {analysis_type}")
            
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
    
    def _format_basic_info(self, financial_data: FDICFinancialData, cert_id: str) -> str:
        """Format basic financial information."""
        result = {
            "success": True,
            "analysis_type": "basic_info",
            "cert_id": cert_id,
            "report_date": str(financial_data.repdte) if financial_data.repdte else None,
            "financial_data": {
                "total_assets": {
                    "value": float(financial_data.asset) if financial_data.asset else None,
                    "formatted": financial_data.format_asset(),
                    "unit": "thousands_usd"
                },
                "total_deposits": {
                    "value": float(financial_data.dep) if financial_data.dep else None,
                    "formatted": financial_data.format_deposits(),
                    "unit": "thousands_usd"
                },
                "total_equity": {
                    "value": float(financial_data.eq) if financial_data.eq else None,
                    "formatted": financial_data.format_equity(),
                    "unit": "thousands_usd"
                },
                "net_income": {
                    "value": float(financial_data.netinc) if financial_data.netinc else None,
                    "formatted": financial_data.format_net_income(),
                    "unit": "thousands_usd"
                }
            },
            "basic_ratios": {
                "return_on_assets": {
                    "value": float(financial_data.roa) if financial_data.roa else None,
                    "formatted": financial_data.format_ratio('roa'),
                    "unit": "percentage"
                },
                "return_on_equity": {
                    "value": float(financial_data.roe) if financial_data.roe else None,
                    "formatted": financial_data.format_ratio('roe'),
                    "unit": "percentage"
                }
            },
            "data_quality": {
                "fields_available": len(financial_data.get_available_fields()),
                "report_date": str(financial_data.repdte) if financial_data.repdte else None
            }
        }
        
        import json
        return json.dumps(result, indent=2)
    
    def _format_financial_summary(self, financial_data: FDICFinancialData, cert_id: str) -> str:
        """Format comprehensive financial summary."""
        from ..infrastructure.banking.fdic_financial_constants import format_financial_value
        
        result = {
            "success": True,
            "analysis_type": "financial_summary",
            "cert_id": cert_id,
            "report_date": str(financial_data.repdte) if financial_data.repdte else None,
            "balance_sheet": {
                "total_assets": {
                    "value": float(financial_data.asset) if financial_data.asset else None,
                    "formatted": financial_data.format_asset()
                },
                "total_deposits": {
                    "value": float(financial_data.dep) if financial_data.dep else None,
                    "formatted": financial_data.format_deposits()
                },
                "loans_and_leases": {
                    "value": float(financial_data.lnls) if financial_data.lnls else None,
                    "formatted": format_financial_value(float(financial_data.lnls)) if financial_data.lnls else "Not available"
                },
                "total_equity": {
                    "value": float(financial_data.eq) if financial_data.eq else None,
                    "formatted": financial_data.format_equity()
                }
            },
            "income_statement": {
                "net_income": {
                    "value": float(financial_data.netinc) if financial_data.netinc else None,
                    "formatted": financial_data.format_net_income()
                },
                "interest_income": {
                    "value": float(financial_data.intinc) if financial_data.intinc else None,
                    "formatted": format_financial_value(float(financial_data.intinc)) if financial_data.intinc else "Not available"
                },
                "interest_expense": {
                    "value": float(financial_data.eintexp) if financial_data.eintexp else None,
                    "formatted": format_financial_value(float(financial_data.eintexp)) if financial_data.eintexp else "Not available"
                },
                "net_interest_income": {
                    "value": float(financial_data.netintinc) if financial_data.netintinc else None,
                    "formatted": format_financial_value(float(financial_data.netintinc)) if financial_data.netintinc else "Not available"
                }
            },
            "data_quality": {
                "fields_available": len(financial_data.get_available_fields()),
                "report_date": str(financial_data.repdte) if financial_data.repdte else None,
                "completeness": "High" if len(financial_data.get_available_fields()) > 10 else "Partial"
            }
        }
        
        import json
        return json.dumps(result, indent=2)
    
    def _format_key_ratios(self, financial_data: FDICFinancialData, cert_id: str) -> str:
        """Format key financial ratios and performance metrics."""
        # Get calculated ratios
        calculated_ratios = financial_data.calculate_derived_ratios()
        
        def format_ratio_value(value) -> Dict[str, Any]:
            """Helper to format ratio values."""
            if value is None:
                return {"value": None, "formatted": "Not available", "unit": "percentage"}
            return {
                "value": float(value),
                "formatted": f"{float(value):.2f}%",
                "unit": "percentage"
            }
        
        result = {
            "success": True,
            "analysis_type": "key_ratios",
            "cert_id": cert_id,
            "report_date": str(financial_data.repdte) if financial_data.repdte else None,
            "profitability_ratios": {
                "return_on_assets": format_ratio_value(
                    financial_data.roa if financial_data.roa else calculated_ratios.get("calculated_roa")
                ),
                "return_on_equity": format_ratio_value(
                    financial_data.roe if financial_data.roe else calculated_ratios.get("calculated_roe")
                ),
                "net_interest_margin": format_ratio_value(
                    financial_data.nim if financial_data.nim else calculated_ratios.get("calculated_nim")
                )
            },
            "capital_ratios": {
                "common_equity_tier1": format_ratio_value(financial_data.cet1r),
                "tier1_capital": format_ratio_value(financial_data.tier1r),
                "total_capital": format_ratio_value(financial_data.totcapr)
            },
            "efficiency_ratios": {
                "equity_to_assets": format_ratio_value(calculated_ratios.get("equity_to_assets")),
                "loans_to_deposits": format_ratio_value(calculated_ratios.get("loans_to_deposits")),
                "efficiency_ratio": format_ratio_value(calculated_ratios.get("calculated_efficiency"))
            },
            "asset_quality": {
                "nonperforming_loans_ratio": format_ratio_value(financial_data.nptla)
            },
            "calculation_methodology": {
                "fdic_reported_ratios": ["roa", "roe", "nim", "cet1r", "tier1r", "totcapr", "nptla"],
                "calculated_ratios": list(calculated_ratios.keys()),
                "data_source": "FDIC BankFind Suite Financial API"
            },
            "data_quality": {
                "fields_available": len(financial_data.get_available_fields()),
                "ratio_completeness": len([r for r in [financial_data.roa, financial_data.roe, financial_data.nim] if r is not None]),
                "report_date": str(financial_data.repdte) if financial_data.repdte else None
            }
        }
        
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