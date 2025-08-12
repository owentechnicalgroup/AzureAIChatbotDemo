"""
Pydantic data models for Call Report data structures.

Provides type-safe models for FFIEC Call Report data processing,
validation, and serialization following banking industry standards.
"""

from datetime import date
from decimal import Decimal
from typing import Dict, List, Optional, Union
from pydantic import BaseModel, Field, field_validator, ConfigDict
import structlog

logger = structlog.get_logger(__name__).bind(log_type="SYSTEM")


class CallReportField(BaseModel):
    """
    Model for individual Call Report field data.
    
    Represents a single data point from a Call Report with
    proper validation and type safety for financial values.
    """
    
    field_id: str = Field(
        ..., 
        description="FFIEC field identifier (e.g., RCON2170)",
        min_length=8,
        max_length=8
    )
    field_name: str = Field(
        ..., 
        description="Human-readable field description"
    )
    value: Optional[Decimal] = Field(
        None,
        description="Field value in dollars (uses Decimal for precision)"
    )
    schedule: str = Field(
        ..., 
        description="FFIEC schedule identifier (e.g., RC, RI)"
    )
    report_date: Optional[date] = Field(
        None,
        description="Report date for this field value"
    )
    
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid"
    )
    
    @field_validator('field_id')
    @classmethod
    def validate_field_id(cls, v: str) -> str:
        """Validate FFIEC field ID format."""
        if not v:
            raise ValueError("Field ID cannot be empty")
        
        # Basic FFIEC field ID pattern validation
        if len(v) != 8:
            raise ValueError(f"Field ID must be 8 characters, got {len(v)}")
            
        # Should start with appropriate prefix
        valid_prefixes = ['RCON', 'RIAD', 'RCFD', 'RIFD']
        if not any(v.startswith(prefix) for prefix in valid_prefixes):
            raise ValueError(f"Field ID must start with one of {valid_prefixes}")
            
        return v.upper()
    
    @field_validator('schedule')
    @classmethod
    def validate_schedule(cls, v: str) -> str:
        """Validate schedule identifier."""
        if not v:
            raise ValueError("Schedule cannot be empty")
        return v.upper()
    
    @field_validator('value')
    @classmethod
    def validate_value(cls, v: Optional[Union[str, int, float, Decimal]]) -> Optional[Decimal]:
        """Validate and convert financial values to Decimal."""
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
            
            # Reasonable bounds check for financial data
            if decimal_value < Decimal('-1e12') or decimal_value > Decimal('1e12'):
                raise ValueError("Value outside reasonable financial range")
                
            return decimal_value
            
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid financial value: {v}") from e


class BankIdentification(BaseModel):
    """
    Model for bank identification information.
    
    Contains the core identifiers needed to uniquely identify
    a banking institution in regulatory systems.
    """
    
    legal_name: str = Field(
        ...,
        description="Official legal name of the bank",
        min_length=1,
        max_length=200
    )
    rssd_id: str = Field(
        ...,
        description="Legal Entity Identifier (RSSD ID)",
        min_length=4,
        max_length=10
    )
    fdic_cert_id: Optional[str] = Field(
        None,
        description="FDIC Certificate Number",
        max_length=10
    )
    location: Optional[str] = Field(
        None,
        description="Bank headquarters location (City, State)",
        max_length=100
    )
    
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid"
    )
    
    @field_validator('rssd_id')
    @classmethod
    def validate_rssd_id(cls, v: str) -> str:
        """Validate RSSD ID format."""
        if not v.isdigit():
            raise ValueError("RSSD ID must contain only digits")
        
        # RSSD IDs are typically 4-6 digits for major banks
        if len(v) < 4 or len(v) > 10:
            raise ValueError("RSSD ID must be 4-10 digits")
            
        return v
    
    @field_validator('fdic_cert_id')
    @classmethod
    def validate_fdic_cert_id(cls, v: Optional[str]) -> Optional[str]:
        """Validate FDIC Certificate ID format."""
        if v is None:
            return None
            
        if not v.isdigit():
            raise ValueError("FDIC Certificate ID must contain only digits")
            
        return v


class CallReportData(BaseModel):
    """
    Model for complete Call Report data for a bank.
    
    Contains bank identification and all associated field data
    for a specific reporting period.
    """
    
    bank_id: str = Field(
        ...,
        description="Bank identifier (RSSD ID)"
    )
    report_date: date = Field(
        ...,
        description="Call Report date (end of quarter)"
    )
    fields: List[CallReportField] = Field(
        default_factory=list,
        description="List of Call Report field data"
    )
    bank_info: Optional[BankIdentification] = Field(
        None,
        description="Bank identification information"
    )
    
    model_config = ConfigDict(
        validate_assignment=True,
        extra="forbid"
    )
    
    @field_validator('report_date')
    @classmethod
    def validate_report_date(cls, v: date) -> date:
        """Validate report date is reasonable."""
        from datetime import date as dt_date
        
        # Call Reports started around 1976
        min_date = dt_date(1976, 1, 1)
        max_date = dt_date.today()
        
        if v < min_date or v > max_date:
            raise ValueError(f"Report date must be between {min_date} and {max_date}")
            
        return v
    
    def get_field_by_id(self, field_id: str) -> Optional[CallReportField]:
        """
        Get a specific field by its ID.
        
        Args:
            field_id: FFIEC field identifier
            
        Returns:
            CallReportField if found, None otherwise
        """
        for field in self.fields:
            if field.field_id == field_id:
                return field
        return None
    
    def get_fields_by_schedule(self, schedule: str) -> List[CallReportField]:
        """
        Get all fields for a specific schedule.
        
        Args:
            schedule: Schedule identifier (e.g., "RC", "RI")
            
        Returns:
            List of CallReportField objects for the schedule
        """
        return [field for field in self.fields if field.schedule.upper() == schedule.upper()]
    
    def get_field_value(self, field_id: str) -> Optional[Decimal]:
        """
        Get the value of a specific field.
        
        Args:
            field_id: FFIEC field identifier
            
        Returns:
            Decimal value if field exists and has value, None otherwise
        """
        field = self.get_field_by_id(field_id)
        return field.value if field else None


class FinancialRatio(BaseModel):
    """
    Model for calculated financial ratios.
    
    Represents a calculated financial ratio with its components
    and methodology for transparency and validation.
    """
    
    ratio_name: str = Field(
        ...,
        description="Name of the financial ratio (e.g., ROA, ROE)"
    )
    value: Optional[Decimal] = Field(
        None,
        description="Calculated ratio value (typically as percentage)"
    )
    components: Dict[str, Decimal] = Field(
        default_factory=dict,
        description="Source fields and values used in calculation"
    )
    calculation_method: str = Field(
        ...,
        description="Formula used for calculation"
    )
    bank_id: str = Field(
        ...,
        description="Bank identifier (RSSD ID)"
    )
    report_date: date = Field(
        ...,
        description="Report date for the calculation"
    )
    
    model_config = ConfigDict(
        validate_assignment=True,
        extra="forbid"
    )
    
    @field_validator('value')
    @classmethod
    def validate_ratio_value(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        """Validate ratio value is reasonable."""
        if v is None:
            return None
            
        # Most financial ratios should be within reasonable bounds
        # ROA typically -5% to +5%, ROE -50% to +50%, etc.
        if v < Decimal('-100') or v > Decimal('100'):
            logger.warning(
                "Ratio value outside typical range",
                ratio_value=float(v)
            )
            
        return v


class CallReportAPIResponse(BaseModel):
    """
    Model for Call Report API responses.
    
    Standardizes API response format for consistency
    and proper error handling.
    """
    
    success: bool = Field(
        ...,
        description="Whether the API call was successful"
    )
    data: Optional[Dict] = Field(
        None,
        description="Response data if successful"
    )
    error_message: Optional[str] = Field(
        None,
        description="Error message if unsuccessful"
    )
    timestamp: Optional[str] = Field(
        None,
        description="Response timestamp"
    )
    
    model_config = ConfigDict(
        validate_assignment=True,
        extra="allow"  # Allow additional fields for flexibility
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


class BankSearchRequest(BaseModel):
    """
    Model for bank search requests.
    
    Validates and standardizes bank lookup parameters
    for consistent search behavior.
    """
    
    search_term: str = Field(
        ...,
        description="Bank name or identifier to search for",
        min_length=2,
        max_length=100
    )
    fuzzy_match: bool = Field(
        True,
        description="Enable fuzzy matching for bank names"
    )
    max_results: int = Field(
        10,
        description="Maximum number of results to return",
        ge=1,
        le=50
    )
    
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid"
    )
    
    @field_validator('search_term')
    @classmethod
    def validate_search_term(cls, v: str) -> str:
        """Clean and validate search term."""
        # Remove common bank suffixes for better matching
        cleaned = v.strip()
        
        # Basic validation - no special characters that could cause issues
        if any(char in cleaned for char in ['<', '>', '&', '"', "'"]):
            raise ValueError("Search term contains invalid characters")
            
        return cleaned