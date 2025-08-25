"""
Pydantic data models for FDIC BankFind Suite API data structures.

Provides type-safe models for FDIC institution data processing,
validation, and serialization following FDIC API standards.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Dict, List, Optional, Union
from pydantic import BaseModel, Field, field_validator, ConfigDict
import structlog

logger = structlog.get_logger(__name__).bind(log_type="SYSTEM")


class FDICInstitution(BaseModel):
    """
    Model for FDIC institution data.
    
    Represents a banking institution as returned by the FDIC BankFind Suite API
    with proper validation and type safety for financial and regulatory data.
    """
    
    # Core identifiers
    cert: Optional[str] = Field(
        None,
        description="FDIC Certificate number - unique identifier",
        max_length=10
    )
    name: str = Field(
        ...,
        description="Institution name as reported to FDIC",
        min_length=1,
        max_length=200
    )
    rssd: Optional[str] = Field(
        None,
        description="RSSD ID (Federal Reserve identifier)",
        max_length=10
    )
    fed_rssd: Optional[str] = Field(
        None,
        description="Federal Reserve RSSD identifier (alternative RSSD field)",
        max_length=10
    )
    
    # Location information
    city: Optional[str] = Field(
        None,
        description="City where institution is located",
        max_length=100
    )
    county: Optional[str] = Field(
        None,
        description="County where institution is located",
        max_length=100
    )
    stname: Optional[str] = Field(
        None,
        description="Full state name (e.g., 'California')",
        max_length=50
    )
    stalp: Optional[str] = Field(
        None,
        description="State abbreviation (e.g., 'CA')",
        min_length=2,
        max_length=2
    )
    zip: Optional[str] = Field(
        None,
        description="ZIP code",
        max_length=10
    )
    
    # Institution status and characteristics
    active: Optional[bool] = Field(
        None,
        description="Whether institution is currently active"
    )
    charter_type: Optional[str] = Field(
        None,
        description="Type of charter (e.g., 'N' for National)",
        max_length=50
    )
    fed_rssd: Optional[str] = Field(
        None,
        description="Federal Reserve RSSD identifier",
        max_length=10
    )
    
    # Financial information (in thousands of dollars)
    asset: Optional[Decimal] = Field(
        None,
        description="Total assets in thousands of dollars"
    )
    dep: Optional[Decimal] = Field(
        None,
        description="Total deposits in thousands of dollars"
    )
    offices: Optional[int] = Field(
        None,
        description="Number of offices/branches",
        ge=0
    )
    
    # Regulatory dates
    open_date: Optional[str] = Field(
        None,
        description="Date institution opened"
    )
    cert_date: Optional[str] = Field(
        None,
        description="Date FDIC certificate was granted"
    )
    
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="allow"  # Allow extra fields from FDIC API
    )
    
    @field_validator('cert')
    @classmethod
    def validate_cert(cls, v: Optional[str]) -> Optional[str]:
        """Validate FDIC Certificate number format."""
        if v is None:
            return None
        
        if not v.isdigit():
            raise ValueError("FDIC Certificate number must contain only digits")
        
        # FDIC cert numbers are typically 1-6 digits
        if len(v) > 10:
            raise ValueError("FDIC Certificate number too long")
            
        return v
    
    @field_validator('rssd', 'fed_rssd')
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
    
    @field_validator('stalp')
    @classmethod
    def validate_state_abbrev(cls, v: Optional[str]) -> Optional[str]:
        """Validate state abbreviation format."""
        if v is None:
            return None
            
        if len(v) != 2:
            raise ValueError("State abbreviation must be exactly 2 characters")
            
        return v.upper()
    
    @field_validator('asset', 'dep')
    @classmethod
    def validate_financial_amount(cls, v: Optional[Union[str, int, float, Decimal]]) -> Optional[Decimal]:
        """Validate and convert financial amounts to Decimal."""
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
            # Max assets could be several trillion for large banks
            if decimal_value < Decimal('0') or decimal_value > Decimal('1e12'):
                logger.warning("Financial amount outside typical range", amount=float(decimal_value))
                
            return decimal_value
            
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid financial amount: {v}") from e
    
    @field_validator('offices')
    @classmethod
    def validate_offices(cls, v: Optional[int]) -> Optional[int]:
        """Validate number of offices."""
        if v is None:
            return None
            
        if v < 0:
            raise ValueError("Number of offices cannot be negative")
            
        # Reasonable upper bound - largest banks have thousands of branches
        if v > 10000:
            logger.warning("Number of offices unusually high", offices=v)
            
        return v


class FDICSearchFilters(BaseModel):
    """
    Model for FDIC API search filters.
    
    Encapsulates the search parameters that can be used
    with the FDIC BankFind Suite API.
    """
    
    name: Optional[str] = Field(
        None,
        description="Institution name to search for",
        max_length=200
    )
    city: Optional[str] = Field(
        None,
        description="City to filter results",
        max_length=100
    )
    county: Optional[str] = Field(
        None,
        description="County to filter results",
        max_length=100
    )
    state: Optional[str] = Field(
        None,
        description="State abbreviation to filter results",
        max_length=2
    )
    active_only: bool = Field(
        True,
        description="Only return active institutions"
    )
    limit: int = Field(
        50,
        description="Maximum number of results",
        ge=1,
        le=10000
    )
    
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid"
    )
    
    @field_validator('state')
    @classmethod
    def validate_state_filter(cls, v: Optional[str]) -> Optional[str]:
        """Validate state filter format."""
        if v is None:
            return None
        
        if len(v) != 2:
            raise ValueError("State filter must be 2-character abbreviation")
            
        return v.upper()
    
    def to_fdic_query(self) -> Dict[str, str]:
        """
        Convert filters to FDIC API query parameters.
        
        Returns:
            Dictionary of query parameters for FDIC API
        """
        params = {}
        
        # Build search query using FDIC Elasticsearch syntax
        search_parts = []
        if self.name:
            search_parts.append(f'NAME:"{self.name}"')
        
        if search_parts:
            params['search'] = ' '.join(search_parts)
        
        # Build filters using FDIC syntax
        filters = []
        if self.city:
            filters.append(f'CITY:"{self.city}"')
        if self.county:
            filters.append(f'COUNTY:"{self.county}"')
        if self.state:
            filters.append(f'STALP:{self.state}')
        if self.active_only:
            filters.append('ACTIVE:1')
        
        if filters:
            params['filters'] = ' AND '.join(filters)
        
        # Add limit and format
        params['limit'] = str(self.limit)
        params['format'] = 'json'
        
        return params


class FDICAPIResponse(BaseModel):
    """
    Model for FDIC BankFind Suite API responses.
    
    Standardizes API response format for consistency
    and proper error handling following FDIC API structure.
    """
    
    success: bool = Field(
        ...,
        description="Whether the API call was successful"
    )
    data: Optional[List[FDICInstitution]] = Field(
        None,
        description="List of FDIC institutions if successful"
    )
    meta: Optional[Dict] = Field(
        None,
        description="Metadata about the response (total count, etc.)"
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
        extra="allow"  # Allow additional fields from FDIC API
    )
    
    @field_validator('error_message')
    @classmethod
    def validate_error_with_success(cls, v: Optional[str], info) -> Optional[str]:
        """Ensure error message is present when success=False."""
        # Access context from ValidationInfo in Pydantic v2
        if hasattr(info, 'data') and 'success' in info.data:
            success = info.data['success']
            if not success and not v:
                raise ValueError("Error message required when success=False")
        return v
    
    @property
    def institutions(self) -> List[FDICInstitution]:
        """
        Get the list of institutions from the response.
        
        Returns:
            List of FDICInstitution objects, empty list if none
        """
        return self.data or []
    
    @property
    def total_count(self) -> int:
        """
        Get the total count of results from metadata.
        
        Returns:
            Total number of results available
        """
        if self.meta and 'total' in self.meta:
            return int(self.meta['total'])
        return len(self.institutions)
    
    def is_success(self) -> bool:
        """Check if the API response was successful."""
        return self.success and bool(self.institutions)


class FDICCacheEntry(BaseModel):
    """
    Model for FDIC API response cache entries.
    
    Stores cached FDIC API responses with metadata for cache management.
    """
    
    response: FDICAPIResponse = Field(
        ...,
        description="Cached FDIC API response"
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


class BankLookupInput(BaseModel):
    """
    Enhanced input schema for bank lookup tool with FDIC API support.
    
    Supports the new FDIC search capabilities while maintaining
    backward compatibility with existing tool interface.
    """
    
    search_term: Optional[str] = Field(
        None,
        description="Bank name or identifier to search for (e.g., 'Wells Fargo', 'Chase')"
    )
    city: Optional[str] = Field(
        None,
        description="City to filter results by (e.g., 'New York', 'Los Angeles')"
    )
    county: Optional[str] = Field(
        None,
        description="County to filter results by (e.g., 'Cook County', 'Miami-Dade')"
    )
    state: Optional[str] = Field(
        None,
        description="State abbreviation to filter by (e.g., 'CA', 'TX', 'NY')"
    )
    active_only: bool = Field(
        True,
        description="Only return active institutions"
    )
    fuzzy_match: bool = Field(
        True,
        description="Enable fuzzy matching for approximate name matching"
    )
    max_results: int = Field(
        5,
        description="Maximum number of results to return (1-50)",
        ge=1,
        le=50
    )
    
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid"
    )
    
    @field_validator('state')
    @classmethod
    def validate_state(cls, v: Optional[str]) -> Optional[str]:
        """Validate state abbreviation format."""
        if v is None:
            return None
        
        if len(v) != 2:
            raise ValueError("State must be 2-character abbreviation (e.g., 'CA', 'NY')")
            
        return v.upper()
    
    @field_validator('search_term')
    @classmethod
    def validate_search_term(cls, v: Optional[str]) -> Optional[str]:
        """Validate and clean search term."""
        if v is None:
            return None
            
        # Basic validation - no special characters that could cause issues
        cleaned = v.strip()
        if any(char in cleaned for char in ['<', '>', '&', '"', "'"]):
            raise ValueError("Search term contains invalid characters")
            
        return cleaned if cleaned else None
    
    def to_fdic_filters(self) -> FDICSearchFilters:
        """
        Convert to FDIC search filters.
        
        Returns:
            FDICSearchFilters object for use with FDIC API
        """
        return FDICSearchFilters(
            name=self.search_term,
            city=self.city,
            county=self.county,
            state=self.state,
            active_only=self.active_only,
            limit=self.max_results * 2  # Get extra for fuzzy filtering
        )
    
    def has_search_criteria(self) -> bool:
        """Check if at least one search criterion is provided."""
        return any([
            self.search_term,
            self.city,
            self.county,
            self.state
        ])


class BankAnalysisInput(BaseModel):
    """
    Enhanced input schema for bank analysis tool with FDIC support.
    
    Extends the existing bank analysis input to support FDIC lookup parameters.
    """
    
    # Existing fields for backward compatibility
    bank_name: Optional[str] = Field(
        None,
        description="Bank name to search for (alternative to rssd_id)"
    )
    rssd_id: Optional[str] = Field(
        None,
        description="Bank RSSD ID (alternative to bank_name)"
    )
    query_type: str = Field(
        "basic_info",
        description="Type of analysis: 'basic_info', 'financial_summary', or 'key_ratios'"
    )
    
    # New FDIC search fields
    city: Optional[str] = Field(
        None,
        description="City to help identify the bank"
    )
    state: Optional[str] = Field(
        None,
        description="State abbreviation to help identify the bank (e.g., 'CA', 'TX')"
    )
    
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid"
    )
    
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
        """Check if bank can be identified with provided parameters."""
        return bool(self.bank_name or self.rssd_id)