"""
Pydantic data models for FDIC Financial Data API structures.

Provides type-safe models for FDIC financial data processing,
validation, and serialization following FDIC Financial API standards.
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Union, Any
from pydantic import BaseModel, Field, field_validator, ConfigDict
import structlog

from .fdic_financial_constants import (
    FINANCIAL_FIELD_MAPPINGS,
    format_financial_value,
    validate_financial_field_name,
    assess_data_quality
)

logger = structlog.get_logger(__name__).bind(log_type="SYSTEM")


class FDICFinancialData(BaseModel):
    """
    Model for FDIC financial data fields.
    
    Represents financial data for a single banking institution as returned 
    by the FDIC BankFind Suite Financial Data API with comprehensive validation.
    """
    
    # Core identifiers (always present)
    cert: str = Field(
        ...,
        description="FDIC Certificate number - unique identifier",
        max_length=10
    )
    repdte: date = Field(
        ...,
        description="Report date (end of quarter)"
    )
    
    # Basic Financial Fields (in thousands of dollars)
    asset: Optional[Decimal] = Field(
        None,
        description="Total assets in thousands of dollars"
    )
    dep: Optional[Decimal] = Field(
        None,
        description="Total deposits in thousands of dollars"
    )
    lnls: Optional[Decimal] = Field(
        None,
        description="Total loans and leases in thousands of dollars"
    )
    eq: Optional[Decimal] = Field(
        None,
        description="Total equity capital in thousands of dollars"
    )
    
    # Income Statement Fields (in thousands of dollars)
    netinc: Optional[Decimal] = Field(
        None,
        description="Net income in thousands of dollars"
    )
    intinc: Optional[Decimal] = Field(
        None,
        description="Total interest income in thousands of dollars"
    )
    eintexp: Optional[Decimal] = Field(
        None,
        description="Total interest expense in thousands of dollars"
    )
    netintinc: Optional[Decimal] = Field(
        None,
        description="Net interest income in thousands of dollars"
    )
    nonii: Optional[Decimal] = Field(
        None,
        description="Total noninterest income in thousands of dollars"
    )
    nonix: Optional[Decimal] = Field(
        None,
        description="Total noninterest expense in thousands of dollars"
    )
    
    # Capital Fields (in thousands of dollars)
    tier1cap: Optional[Decimal] = Field(
        None,
        description="Tier 1 capital in thousands of dollars"
    )
    totcap: Optional[Decimal] = Field(
        None,
        description="Total capital in thousands of dollars"
    )
    rwajcet1: Optional[Decimal] = Field(
        None,
        description="Risk-weighted assets for CET1 in thousands of dollars"
    )
    
    # Financial Ratios (as percentages)
    roa: Optional[Decimal] = Field(
        None,
        description="Return on assets ratio (percentage)"
    )
    roe: Optional[Decimal] = Field(
        None,
        description="Return on equity ratio (percentage)"
    )
    nim: Optional[Decimal] = Field(
        None,
        description="Net interest margin (percentage)"
    )
    effratio: Optional[Decimal] = Field(
        None,
        description="Efficiency ratio (percentage)"
    )
    
    # Capital Ratios (as percentages)
    cet1r: Optional[Decimal] = Field(
        None,
        description="Common equity tier 1 ratio (percentage)"
    )
    tier1r: Optional[Decimal] = Field(
        None,
        description="Tier 1 capital ratio (percentage)"
    )
    totcapr: Optional[Decimal] = Field(
        None,
        description="Total capital ratio (percentage)"
    )
    
    # Asset Quality Fields
    nptla: Optional[Decimal] = Field(
        None,
        description="Nonperforming loans to total loans (percentage)"
    )
    alll: Optional[Decimal] = Field(
        None,
        description="Allowance for loan and lease losses in thousands of dollars"
    )
    chargeoffs: Optional[Decimal] = Field(
        None,
        description="Net charge-offs in thousands of dollars"
    )
    
    # Additional identifier
    rssd: Optional[str] = Field(
        None,
        description="RSSD identifier",
        max_length=10
    )
    
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="allow",  # Allow additional fields from FDIC API
        populate_by_name=True
    )
    
    @field_validator('cert')
    @classmethod
    def validate_cert(cls, v: str) -> str:
        """Validate FDIC Certificate number format."""
        if not v.isdigit():
            raise ValueError("FDIC Certificate number must contain only digits")
        
        # FDIC cert numbers are typically 1-6 digits
        if len(v) > 10:
            raise ValueError("FDIC Certificate number too long")
            
        return v
    
    @field_validator('rssd')
    @classmethod
    def validate_rssd(cls, v: Optional[str]) -> Optional[str]:
        """Validate RSSD ID format."""
        if v is None:
            return None
            
        if not v.isdigit():
            raise ValueError("RSSD ID must contain only digits")
        
        # RSSD IDs are typically 4-10 digits
        if len(v) < 4 or len(v) > 10:
            logger.warning("RSSD ID length unusual", rssd=v, length=len(v))
            
        return v
    
    @field_validator('repdte')
    @classmethod
    def validate_report_date(cls, v: date) -> date:
        """Validate report date is reasonable for financial data."""
        from datetime import date as dt_date
        
        # Financial data reporting started around 1976
        min_date = dt_date(1976, 1, 1)
        max_date = dt_date.today()
        
        if v < min_date or v > max_date:
            raise ValueError(f"Report date must be between {min_date} and {max_date}")
            
        return v
    
    @field_validator(
        'asset', 'dep', 'lnls', 'eq', 'netinc', 'intinc', 'eintexp', 
        'netintinc', 'nonii', 'nonix', 'tier1cap', 'totcap', 
        'rwajcet1', 'alll', 'chargeoffs'
    )
    @classmethod
    def validate_financial_amount(cls, v: Optional[Union[str, int, float, Decimal]]) -> Optional[Decimal]:
        """Validate and convert financial amounts to Decimal (values in thousands)."""
        if v is None:
            return None
            
        try:
            # Convert to Decimal for financial precision
            if isinstance(v, str):
                # Handle common formatting
                v = v.replace(',', '').replace('$', '').strip()
                if not v:
                    return None
            
            decimal_value = Decimal(str(v))
            
            # Reasonable bounds check for financial data (in thousands)
            # Allow negative values for income/loss items
            if abs(decimal_value) > Decimal('1e12'):
                logger.warning("Financial amount exceptionally large", amount=float(decimal_value))
                
            return decimal_value
            
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid financial amount: {v}") from e
    
    @field_validator('roa', 'roe', 'nim', 'effratio', 'cet1r', 'tier1r', 'totcapr', 'nptla')
    @classmethod
    def validate_ratio(cls, v: Optional[Union[str, int, float, Decimal]]) -> Optional[Decimal]:
        """Validate and convert ratio values to Decimal (percentages)."""
        if v is None:
            return None
            
        try:
            if isinstance(v, str):
                v = v.replace('%', '').strip()
                if not v:
                    return None
            
            decimal_value = Decimal(str(v))
            
            # Reasonable bounds for ratios (most should be -100% to +100%)
            if abs(decimal_value) > Decimal('500'):
                logger.warning("Ratio value unusually high", ratio=float(decimal_value))
                
            return decimal_value
            
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid ratio value: {v}") from e
    
    def format_asset(self, auto_scale: bool = True) -> str:
        """Format total assets for display."""
        return format_financial_value(self.asset, auto_scale=auto_scale)
    
    def format_deposits(self, auto_scale: bool = True) -> str:
        """Format total deposits for display."""
        return format_financial_value(self.dep, auto_scale=auto_scale)
    
    def format_net_income(self, auto_scale: bool = True) -> str:
        """Format net income for display."""
        return format_financial_value(self.netinc, auto_scale=auto_scale)
    
    def format_equity(self, auto_scale: bool = True) -> str:
        """Format total equity for display.""" 
        return format_financial_value(self.eq, auto_scale=auto_scale)
    
    def format_ratio(self, ratio_name: str) -> str:
        """
        Format a ratio field for display with percentage sign.
        
        Args:
            ratio_name: Name of the ratio field
            
        Returns:
            Formatted ratio string
        """
        ratio_value = getattr(self, ratio_name.lower(), None)
        if ratio_value is None:
            return "Not available"
        return f"{ratio_value:.2f}%"
    
    def get_available_fields(self) -> List[str]:
        """
        Get list of fields that have non-null values.
        
        Returns:
            List of field names with data
        """
        available_fields = []
        for field_name, field_value in self.__dict__.items():
            if field_value is not None and field_name not in ['cert', 'repdte']:
                available_fields.append(field_name.upper())
        return available_fields
    
    def assess_data_completeness(self) -> Dict[str, Any]:
        """
        Assess the completeness and quality of the financial data.
        
        Returns:
            Dictionary with data quality assessment
        """
        available_fields = self.get_available_fields()
        quality_level, assessment = assess_data_quality(available_fields)
        
        return {
            **assessment,
            "cert": self.cert,
            "report_date": self.repdte.isoformat(),
            "fields_with_data": available_fields
        }
    
    def calculate_derived_ratios(self) -> Dict[str, Optional[Decimal]]:
        """
        Calculate derived ratios from available data if FDIC ratios not provided.
        
        Returns:
            Dictionary of calculated ratios
        """
        calculated_ratios = {}
        
        # Return on Assets (ROA) = Net Income / Total Assets
        if self.netinc is not None and self.asset is not None and self.asset > 0:
            calculated_ratios["calculated_roa"] = (self.netinc / self.asset) * 100
        
        # Return on Equity (ROE) = Net Income / Total Equity
        if self.netinc is not None and self.eq is not None and self.eq > 0:
            calculated_ratios["calculated_roe"] = (self.netinc / self.eq) * 100
        
        # Net Interest Margin (NIM) = Net Interest Income / Average Assets
        if self.netintinc is not None and self.asset is not None and self.asset > 0:
            calculated_ratios["calculated_nim"] = (self.netintinc / self.asset) * 100
        elif self.intinc is not None and self.eintexp is not None and self.asset is not None and self.asset > 0:
            # Calculate from components if net interest income not available
            net_int_inc = self.intinc - self.eintexp
            calculated_ratios["calculated_nim"] = (net_int_inc / self.asset) * 100
        
        # Efficiency Ratio = Noninterest Expense / (Net Interest Income + Noninterest Income)
        if (self.nonix is not None and self.netintinc is not None and 
            self.nonii is not None):
            revenue = self.netintinc + self.nonii
            if revenue > 0:
                calculated_ratios["calculated_efficiency"] = (self.nonix / revenue) * 100
        
        # Equity to Assets Ratio
        if self.eq is not None and self.asset is not None and self.asset > 0:
            calculated_ratios["equity_to_assets"] = (self.eq / self.asset) * 100
        
        # Loans to Deposits Ratio
        if self.lnls is not None and self.dep is not None and self.dep > 0:
            calculated_ratios["loans_to_deposits"] = (self.lnls / self.dep) * 100
        
        return calculated_ratios
    
    def get_financial_summary(self) -> Dict[str, str]:
        """
        Get a formatted summary of key financial metrics.
        
        Returns:
            Dictionary with formatted financial summary
        """
        return {
            "total_assets": self.format_asset(),
            "total_deposits": self.format_deposits(),
            "net_income": self.format_net_income(),
            "total_equity": self.format_equity(),
            "return_on_assets": self.format_ratio("roa"),
            "return_on_equity": self.format_ratio("roe"),
            "net_interest_margin": self.format_ratio("nim"),
            "tier_1_capital_ratio": self.format_ratio("tier1r"),
            "report_date": self.repdte.isoformat()
        }


class FDICFinancialAPIResponse(BaseModel):
    """
    Model for FDIC Financial Data API responses.
    
    Standardizes financial API response format for consistency
    and proper error handling following FDIC API patterns.
    """
    
    success: bool = Field(
        ...,
        description="Whether the API call was successful"
    )
    data: Optional[List[FDICFinancialData]] = Field(
        None,
        description="List of FDIC financial data records if successful"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Response metadata (total count, pagination, etc.)"
    )
    error_message: Optional[str] = Field(
        None,
        description="Error message if unsuccessful"
    )
    timestamp: Optional[str] = Field(
        None,
        description="Response timestamp"
    )
    query_info: Optional[Dict[str, Any]] = Field(
        None,
        description="Information about the query that generated this response"
    )
    
    model_config = ConfigDict(
        validate_assignment=True,
        extra="allow"  # Allow additional fields from FDIC API
    )
    
    @field_validator('error_message')
    @classmethod
    def validate_error_with_success(cls, v: Optional[str], info) -> Optional[str]:
        """Ensure error message is present when success=False."""
        if hasattr(info, 'data') and 'success' in info.data:
            success = info.data['success']
            if not success and not v:
                raise ValueError("Error message required when success=False")
        return v
    
    @property
    def financial_records(self) -> List[FDICFinancialData]:
        """
        Get the list of financial records from the response.
        
        Returns:
            List of FDICFinancialData objects, empty list if none
        """
        return self.data or []
    
    @property
    def total_count(self) -> int:
        """
        Get the total count of results from metadata.
        
        Returns:
            Total number of results available
        """
        if self.metadata and 'total' in self.metadata:
            return int(self.metadata['total'])
        return len(self.financial_records)
    
    @property
    def has_data(self) -> bool:
        """Check if the response contains financial data."""
        return self.success and bool(self.financial_records)
    
    def get_latest_record(self) -> Optional[FDICFinancialData]:
        """
        Get the most recent financial record by report date.
        
        Returns:
            Latest FDICFinancialData record or None if no data
        """
        if not self.financial_records:
            return None
        
        # Assuming records are sorted by report date descending
        return max(self.financial_records, key=lambda x: x.repdte)
    
    def get_records_by_cert(self, cert_id: str) -> List[FDICFinancialData]:
        """
        Filter records by FDIC certificate number.
        
        Args:
            cert_id: FDIC certificate number
            
        Returns:
            List of matching financial records
        """
        return [record for record in self.financial_records if record.cert == cert_id]
    
    def get_date_range(self) -> Optional[Dict[str, date]]:
        """
        Get the date range covered by the financial records.
        
        Returns:
            Dictionary with min and max dates or None if no data
        """
        if not self.financial_records:
            return None
        
        dates = [record.repdte for record in self.financial_records]
        return {
            "min_date": min(dates),
            "max_date": max(dates)
        }
    
    def aggregate_summary(self) -> Dict[str, Any]:
        """
        Get aggregate summary statistics for the response data.
        
        Returns:
            Dictionary with aggregate statistics
        """
        if not self.financial_records:
            return {"record_count": 0}
        
        # Count records by bank
        banks = set(record.cert for record in self.financial_records)
        
        # Get date range
        date_range = self.get_date_range()
        
        # Calculate data completeness
        total_possible_fields = len(FINANCIAL_FIELD_MAPPINGS)
        avg_completeness = sum(
            len(record.get_available_fields()) for record in self.financial_records
        ) / len(self.financial_records)
        
        return {
            "record_count": len(self.financial_records),
            "unique_banks": len(banks),
            "date_range": date_range,
            "average_field_completeness": round(avg_completeness, 1),
            "completeness_percentage": round((avg_completeness / total_possible_fields) * 100, 1)
        }


class FDICFinancialCacheEntry(BaseModel):
    """
    Model for FDIC Financial API response cache entries.
    
    Stores cached financial API responses with metadata for cache management.
    """
    
    response: FDICFinancialAPIResponse = Field(
        ...,
        description="Cached FDIC Financial API response"
    )
    query_hash: str = Field(
        ...,
        description="Hash of the original query parameters"
    )
    cached_at: datetime = Field(
        ...,
        description="When the response was cached"
    )
    expires_at: datetime = Field(
        ...,
        description="When the cache entry expires"
    )
    query_params: Optional[Dict[str, Any]] = Field(
        None,
        description="Original query parameters for debugging"
    )
    
    model_config = ConfigDict(
        validate_assignment=True,
        extra="forbid"
    )
    
    def is_expired(self) -> bool:
        """Check if the cache entry has expired."""
        return datetime.now() > self.expires_at
    
    def time_to_expiry(self) -> float:
        """Get time until expiry in seconds."""
        return (self.expires_at - datetime.now()).total_seconds()
    
    def refresh_expiry(self, ttl_seconds: int) -> None:
        """Refresh the expiry time for the cache entry."""
        self.expires_at = datetime.now() + timedelta(seconds=ttl_seconds)


class BankFinancialAnalysisInput(BaseModel):
    """
    Enhanced input schema for bank financial analysis with FDIC Financial API.
    
    Extends bank analysis capabilities to support comprehensive financial
    data analysis using real FDIC financial metrics.
    """
    
    # Bank identification (at least one required)
    cert_id: Optional[str] = Field(
        None,
        description="FDIC Certificate number for specific bank"
    )
    bank_name: Optional[str] = Field(
        None,
        description="Bank name to search for (alternative to cert_id)"
    )
    rssd_id: Optional[str] = Field(
        None,
        description="Bank RSSD ID (alternative to cert_id)"
    )
    
    # Analysis configuration
    analysis_type: str = Field(
        "basic_info",
        description="Type of analysis: 'basic_info', 'financial_summary', 'key_ratios', 'comprehensive'"
    )
    report_date: Optional[str] = Field(
        None,
        description="Specific report date (YYYY-MM-DD) or 'latest'"
    )
    historical_quarters: int = Field(
        1,
        description="Number of quarters of historical data (1-20)",
        ge=1,
        le=20
    )
    
    # Location filters (for bank identification)
    city: Optional[str] = Field(
        None,
        description="City to help identify the bank"
    )
    state: Optional[str] = Field(
        None,
        description="State abbreviation to help identify the bank"
    )
    
    # Advanced options
    include_calculated_ratios: bool = Field(
        True,
        description="Include derived ratio calculations if FDIC ratios unavailable"
    )
    include_peer_comparison: bool = Field(
        False,
        description="Include peer comparison data (banks of similar size)"
    )
    
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid"
    )
    
    @field_validator('cert_id')
    @classmethod
    def validate_cert_id(cls, v: Optional[str]) -> Optional[str]:
        """Validate FDIC Certificate number format."""
        if v is None:
            return None
        if not v.isdigit():
            raise ValueError("FDIC Certificate number must contain only digits")
        return v
    
    @field_validator('analysis_type')
    @classmethod
    def validate_analysis_type(cls, v: str) -> str:
        """Validate analysis type."""
        valid_types = ['basic_info', 'financial_summary', 'key_ratios', 'comprehensive', 'asset_quality']
        if v not in valid_types:
            raise ValueError(f"Analysis type must be one of: {valid_types}")
        return v
    
    @field_validator('state')
    @classmethod
    def validate_state(cls, v: Optional[str]) -> Optional[str]:
        """Validate state abbreviation format."""
        if v is None:
            return None
        if len(v) != 2:
            raise ValueError("State must be 2-character abbreviation")
        return v.upper()
    
    def has_bank_identifier(self) -> bool:
        """Check if at least one bank identifier is provided."""
        return bool(self.cert_id or self.bank_name or self.rssd_id)
    
    def get_primary_identifier(self) -> Dict[str, str]:
        """Get the primary identifier type and value."""
        if self.cert_id:
            return {"type": "cert_id", "value": self.cert_id}
        elif self.rssd_id:
            return {"type": "rssd_id", "value": self.rssd_id}
        elif self.bank_name:
            return {"type": "bank_name", "value": self.bank_name}
        else:
            return {"type": "none", "value": ""}