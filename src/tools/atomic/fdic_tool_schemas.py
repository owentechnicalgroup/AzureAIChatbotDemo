"""
Clean input/output schemas for FDIC atomic tools.

Provides structured, validated data models for FDIC tool interactions
without backwards compatibility complexity.
"""

from typing import Dict, Any, List, Optional
from datetime import date
from decimal import Decimal
from pydantic import BaseModel, Field, field_validator


class FDICInstitutionResult(BaseModel):
    """
    Clean output schema for institution search results.
    
    Represents a single institution found by fdic_institution_search_tool
    with all data needed for downstream financial queries.
    """
    
    name: str = Field(..., description="Institution name")
    cert: str = Field(..., description="FDIC Certificate number - use for financial queries")
    location: Dict[str, Optional[str]] = Field(..., description="Location details")
    status: str = Field(..., description="Active or Inactive")
    financial: Dict[str, Optional[float]] = Field(..., description="Basic financial metrics")


class FDICInstitutionSearchResult(BaseModel):
    """
    Complete search result from fdic_institution_search_tool.
    
    Structured output that downstream tools can parse reliably.
    """
    
    success: bool = Field(..., description="Whether search succeeded")
    count: int = Field(..., description="Number of institutions found")
    institutions: List[FDICInstitutionResult] = Field(..., description="List of institutions")
    message: Optional[str] = Field(None, description="Additional info or error message")
    error: Optional[str] = Field(None, description="Error message if success=False")


class FDICFinancialMetric(BaseModel):
    """
    Structured financial metric with value and formatting.
    """
    
    value: Optional[float] = Field(None, description="Raw numeric value")
    formatted: str = Field(..., description="Human-readable formatted value")
    unit: str = Field(..., description="Unit of measurement")


class FDICFinancialRatio(BaseModel):
    """
    Structured financial ratio with metadata.
    """
    
    value: Optional[float] = Field(None, description="Ratio as decimal (e.g., 0.15 for 15%)")
    formatted: str = Field(..., description="Formatted percentage string")
    unit: str = Field(..., description="Always 'percentage' for ratios")


class FDICBasicInfoResult(BaseModel):
    """
    Result schema for basic_info analysis type.
    """
    
    success: bool = Field(..., description="Whether data retrieval succeeded")
    analysis_type: str = Field(..., description="Always 'basic_info'")
    cert_id: str = Field(..., description="FDIC Certificate number")
    report_date: Optional[str] = Field(None, description="Report date (YYYY-MM-DD)")
    financial_data: Dict[str, FDICFinancialMetric] = Field(..., description="Core financial metrics")
    basic_ratios: Dict[str, FDICFinancialRatio] = Field(..., description="Basic ratios")
    data_quality: Dict[str, Any] = Field(..., description="Data quality indicators")


class FDICFinancialSummaryResult(BaseModel):
    """
    Result schema for financial_summary analysis type.
    """
    
    success: bool = Field(..., description="Whether data retrieval succeeded")
    analysis_type: str = Field(..., description="Always 'financial_summary'")
    cert_id: str = Field(..., description="FDIC Certificate number")
    report_date: Optional[str] = Field(None, description="Report date (YYYY-MM-DD)")
    balance_sheet: Dict[str, FDICFinancialMetric] = Field(..., description="Balance sheet items")
    income_statement: Dict[str, FDICFinancialMetric] = Field(..., description="Income statement items")
    data_quality: Dict[str, Any] = Field(..., description="Data quality indicators")


class FDICKeyRatiosResult(BaseModel):
    """
    Result schema for key_ratios analysis type.
    """
    
    success: bool = Field(..., description="Whether data retrieval succeeded")
    analysis_type: str = Field(..., description="Always 'key_ratios'")
    cert_id: str = Field(..., description="FDIC Certificate number")
    report_date: Optional[str] = Field(None, description="Report date (YYYY-MM-DD)")
    profitability_ratios: Dict[str, FDICFinancialRatio] = Field(..., description="Profitability metrics")
    capital_ratios: Dict[str, FDICFinancialRatio] = Field(..., description="Capital adequacy ratios")
    efficiency_ratios: Dict[str, FDICFinancialRatio] = Field(..., description="Operational efficiency ratios")
    asset_quality: Dict[str, FDICFinancialRatio] = Field(..., description="Asset quality metrics")
    calculation_methodology: Dict[str, Any] = Field(..., description="How ratios were calculated")
    data_quality: Dict[str, Any] = Field(..., description="Data quality indicators")


class FDICErrorResult(BaseModel):
    """
    Error result schema for FDIC tools.
    """
    
    success: bool = Field(False, description="Always False for errors")
    error: str = Field(..., description="Error message")
    cert_id: Optional[str] = Field(None, description="Certificate ID if applicable")
    message: Optional[str] = Field(None, description="Additional error context")


def parse_institution_search_result(json_string: str) -> FDICInstitutionSearchResult:
    """
    Parse JSON result from fdic_institution_search_tool.
    
    Args:
        json_string: JSON output from fdic_institution_search_tool
        
    Returns:
        Structured FDICInstitutionSearchResult
        
    Raises:
        ValueError: If JSON is invalid or doesn't match expected schema
    """
    import json
    
    try:
        data = json.loads(json_string)
        return FDICInstitutionSearchResult.model_validate(data)
    except Exception as e:
        raise ValueError(f"Failed to parse institution search result: {e}")


def parse_financial_data_result(json_string: str) -> Dict[str, Any]:
    """
    Parse JSON result from fdic_financial_data_tool.
    
    Args:
        json_string: JSON output from fdic_financial_data_tool
        
    Returns:
        Parsed financial data as dictionary (schema varies by analysis_type)
        
    Raises:
        ValueError: If JSON is invalid
    """
    import json
    
    try:
        data = json.loads(json_string)
        
        # Validate that it's a proper result
        if not isinstance(data, dict) or 'success' not in data:
            raise ValueError("Invalid financial data result format")
        
        return data
    except Exception as e:
        raise ValueError(f"Failed to parse financial data result: {e}")


def extract_cert_from_search(search_result: str) -> Optional[str]:
    """
    Extract CERT number from institution search result for financial queries.
    
    Args:
        search_result: JSON output from fdic_institution_search_tool
        
    Returns:
        CERT number of first institution, or None if no results
        
    Raises:
        ValueError: If search result is invalid
    """
    try:
        parsed = parse_institution_search_result(search_result)
        
        if parsed.success and parsed.institutions:
            return parsed.institutions[0].cert
        
        return None
    except Exception as e:
        raise ValueError(f"Failed to extract CERT from search result: {e}")


# Validation helpers for tool inputs
def validate_cert_id(cert_id: str) -> bool:
    """Validate FDIC Certificate ID format."""
    return cert_id.isdigit() and 1 <= len(cert_id) <= 10


def validate_analysis_type(analysis_type: str) -> bool:
    """Validate financial analysis type."""
    return analysis_type in ["basic_info", "financial_summary", "key_ratios"]


def validate_state_code(state: str) -> bool:
    """Validate US state abbreviation."""
    return len(state) == 2 and state.isupper() and state.isalpha()