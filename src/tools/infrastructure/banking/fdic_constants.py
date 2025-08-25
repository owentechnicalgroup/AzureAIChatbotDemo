"""
FDIC BankFind Suite API constants and field mappings.

Provides standardized API endpoints, field mappings, and constants
for FDIC institution data processing following FDIC API conventions.
"""

from typing import Dict, Set, List

# FDIC BankFind Suite API Configuration
FDIC_API_BASE_URL = "https://api.fdic.gov"
FDIC_INSTITUTIONS_ENDPOINT = "/banks/institutions"

# FDIC API Endpoints
FDIC_ENDPOINTS = {
    "institutions": "/banks/institutions",
    "locations": "/banks/locations", 
    "history": "/banks/history",
    "summary": "/banks/summary",
    "failures": "/banks/failures",
    "sod": "/banks/sod",  # Summary of Deposits
    "financials": "/banks/financials",
    "demographics": "/banks/demographics"
}

# Currently supported endpoints (extensible for future use)
SUPPORTED_ENDPOINTS = {"institutions"}

# FDIC API Field Mappings - Institution Data
FDIC_INSTITUTION_FIELDS = {
    # Core identifiers
    "CERT": "FDIC Certificate number",
    "NAME": "Institution name",
    "RSSD": "RSSD ID (Federal Reserve identifier)",
    "FED_RSSD": "Federal Reserve RSSD identifier",
    
    # Location information
    "CITY": "City",
    "COUNTY": "County", 
    "STNAME": "State name",
    "STALP": "State abbreviation",
    "ZIP": "ZIP code",
    "ADDRESS": "Street address",
    
    # Institution characteristics
    "ACTIVE": "Active status (1=active, 0=inactive)",
    "CHARTER": "Charter type",
    "CHRTAGNT": "Chartering agent",
    "REGAGNT": "Primary federal regulator",
    "INSAGNT1": "Primary deposit insurer",
    "WEBADDR": "Website address",
    
    # Financial data (in thousands)
    "ASSET": "Total assets",
    "DEP": "Total deposits", 
    "OFFICES": "Number of offices",
    "NETINC": "Net income",
    "ROA": "Return on assets",
    "ROE": "Return on equity",
    
    # Important dates
    "DATEOPEN": "Date opened",
    "DATELAST": "Date last updated",
    "CERTDATE": "Date FDIC certificate granted",
    
    # Additional regulatory info
    "FDICREGN": "FDIC region",
    "FED": "Federal Reserve member (Y/N)",
    "SUBCHAPS": "Subchapter S corporation election",
    "CONSERVE": "Under conservatorship",
    "TRUST": "Trust powers"
}

# Field mappings for internal use
FDIC_TO_INTERNAL_MAPPING = {
    # Map FDIC API fields to our internal model fields
    "CERT": "cert",
    "NAME": "name",
    "RSSD": "rssd",
    "FED_RSSD": "fed_rssd",
    "CITY": "city",
    "COUNTY": "county", 
    "STNAME": "stname",
    "STALP": "stalp",
    "ZIP": "zip",
    "ACTIVE": "active",
    "CHARTER": "charter_type",
    "ASSET": "asset",
    "DEP": "dep",
    "OFFICES": "offices",
    "DATEOPEN": "open_date",
    "CERTDATE": "cert_date"
}

# Reverse mapping for API queries
INTERNAL_TO_FDIC_MAPPING = {v: k for k, v in FDIC_TO_INTERNAL_MAPPING.items()}

# FDIC Query Templates and Syntax
FDIC_SEARCH_OPERATORS = {
    "exact_phrase": '"{}"',         # Exact phrase: NAME:"Wells Fargo"
    "wildcard": "{}*",              # Wildcard: NAME:Well*
    "range": "[{} TO {}]",          # Range: ASSET:[1000 TO 5000]
    "exists": "_exists_:{}",        # Field exists: _exists_:WEBADDR
    "not_exists": "NOT _exists_:{}",# Field not exists: NOT _exists_:WEBADDR
}

FDIC_LOGICAL_OPERATORS = {
    "and": " AND ",
    "or": " OR ",
    "not": "NOT "
}

# Common FDIC query templates
FDIC_QUERY_TEMPLATES = {
    "by_name": 'NAME:"{name}"',
    "by_city": 'CITY:"{city}"',
    "by_county": 'COUNTY:"{county}"',
    "by_state": 'STALP:{state}',
    "active_only": 'ACTIVE:1',
    "inactive_only": 'ACTIVE:0',
    "by_charter": 'CHARTER:"{charter}"',
    "minimum_assets": 'ASSET:[{min_assets} TO *]',
    "asset_range": 'ASSET:[{min_assets} TO {max_assets}]',
    "has_website": '_exists_:WEBADDR'
}

# Predefined filter combinations
FDIC_FILTER_COMBINATIONS = {
    "active_banks": "ACTIVE:1",
    "large_banks": "ACTIVE:1 AND ASSET:[1000000 TO *]",  # > $1B in assets
    "community_banks": "ACTIVE:1 AND ASSET:[* TO 1000000]",  # < $1B in assets
    "national_banks": 'ACTIVE:1 AND CHARTER:"N"',
    "state_banks": 'ACTIVE:1 AND CHARTER:"NM"',
    "trust_banks": "ACTIVE:1 AND TRUST:Y"
}

# US State abbreviations for validation
US_STATES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
    "DC", "PR", "VI", "GU", "AS", "MP"  # Include territories
}

# FDIC Charter Type Mappings
FDIC_CHARTER_TYPES = {
    "N": "National Bank",
    "NM": "State Member Bank", 
    "NB": "State Non-Member Bank",
    "SA": "State Savings Association",
    "SB": "Federal Savings Bank",
    "SM": "State Mutual Savings Bank"
}

# FDIC API Response Limits
FDIC_API_LIMITS = {
    "max_results_per_query": 10000,
    "default_limit": 100,
    "recommended_limit": 1000
}

# FDIC Error Code Mappings
FDIC_ERROR_CODES = {
    400: "Bad Request - Invalid query parameters",
    401: "Unauthorized - Invalid or missing API key",
    403: "Forbidden - API key lacks required permissions", 
    404: "Not Found - Endpoint or resource not found",
    429: "Too Many Requests - Rate limit exceeded",
    500: "Internal Server Error - FDIC service unavailable",
    502: "Bad Gateway - FDIC service temporarily unavailable",
    503: "Service Unavailable - FDIC service under maintenance"
}

# Cache configuration
FDIC_CACHE_CONFIG = {
    "default_ttl_seconds": 3600,  # 1 hour
    "institution_data_ttl": 86400,  # 24 hours (institution data changes slowly)
    "search_results_ttl": 1800,  # 30 minutes
    "max_cache_entries": 1000
}

# Valid search fields for validation
VALID_SEARCH_FIELDS = set(FDIC_INSTITUTION_FIELDS.keys())

# Fields that support exact matching
EXACT_MATCH_FIELDS = {
    "CERT", "RSSD", "FED_RSSD", "STALP", "ZIP", "ACTIVE", 
    "CHARTER", "CHRTAGNT", "REGAGNT", "FED", "TRUST"
}

# Fields that support fuzzy/wildcard matching  
FUZZY_MATCH_FIELDS = {
    "NAME", "CITY", "COUNTY", "STNAME", "ADDRESS", "WEBADDR"
}

# Numeric fields that support range queries
NUMERIC_RANGE_FIELDS = {
    "ASSET", "DEP", "OFFICES", "NETINC", "ROA", "ROE"
}

# Date fields that support range queries
DATE_RANGE_FIELDS = {
    "DATEOPEN", "DATELAST", "CERTDATE"
}


def build_fdic_query(search_params: Dict) -> Dict[str, str]:
    """
    Build FDIC API query parameters from search criteria.
    
    Args:
        search_params: Dictionary with search criteria
        
    Returns:
        Dictionary of FDIC API query parameters
    """
    query_params = {}
    
    # Build search query
    search_parts = []
    if "name" in search_params and search_params["name"]:
        search_parts.append(FDIC_QUERY_TEMPLATES["by_name"].format(
            name=search_params["name"]
        ))
    
    if search_parts:
        query_params["search"] = " ".join(search_parts)
    
    # Build filters
    filters = []
    
    if "city" in search_params and search_params["city"]:
        filters.append(FDIC_QUERY_TEMPLATES["by_city"].format(
            city=search_params["city"]
        ))
    
    if "county" in search_params and search_params["county"]:
        filters.append(FDIC_QUERY_TEMPLATES["by_county"].format(
            county=search_params["county"]
        ))
    
    if "state" in search_params and search_params["state"]:
        filters.append(FDIC_QUERY_TEMPLATES["by_state"].format(
            state=search_params["state"]
        ))
    
    # Add active filter by default unless explicitly disabled
    active_only = search_params.get("active_only", True)
    if active_only:
        filters.append(FDIC_QUERY_TEMPLATES["active_only"])
    
    if filters:
        query_params["filters"] = FDIC_LOGICAL_OPERATORS["and"].join(filters)
    
    # Add limit and format
    limit = search_params.get("limit", FDIC_API_LIMITS["default_limit"])
    query_params["limit"] = str(min(limit, FDIC_API_LIMITS["max_results_per_query"]))
    query_params["format"] = "json"
    
    # Add field selection to ensure we get RSSD identifiers
    # Request key fields including both RSSD and FED_RSSD
    requested_fields = [
        "CERT", "NAME", "RSSD", "FED_RSSD", "CITY", "COUNTY", 
        "STNAME", "STALP", "ZIP", "ACTIVE", "ASSET", "DEP", "OFFICES"
    ]
    query_params["fields"] = ",".join(requested_fields)
    
    return query_params


def validate_fdic_field(field_name: str) -> bool:
    """
    Validate if field name is supported by FDIC API.
    
    Args:
        field_name: FDIC field name to validate
        
    Returns:
        True if valid field name, False otherwise
    """
    return field_name.upper() in VALID_SEARCH_FIELDS


def validate_state_code(state: str) -> bool:
    """
    Validate if state code is a valid US state/territory.
    
    Args:
        state: State abbreviation to validate
        
    Returns:
        True if valid state code, False otherwise
    """
    return state.upper() in US_STATES


def get_charter_type_description(charter_code: str) -> str:
    """
    Get description for FDIC charter type code.
    
    Args:
        charter_code: FDIC charter type code
        
    Returns:
        Human-readable charter type description
    """
    return FDIC_CHARTER_TYPES.get(charter_code.upper(), f"Unknown ({charter_code})")


def map_fdic_response_field(fdic_field: str, fdic_value) -> tuple[str, any]:
    """
    Map FDIC API response field to internal model field.
    
    Args:
        fdic_field: FDIC API field name
        fdic_value: FDIC API field value
        
    Returns:
        Tuple of (internal_field_name, processed_value)
    """
    internal_field = FDIC_TO_INTERNAL_MAPPING.get(fdic_field.upper())
    
    if not internal_field:
        return fdic_field.lower(), fdic_value
    
    # Process specific field types
    if internal_field == "active" and isinstance(fdic_value, (str, int)):
        # Convert FDIC active flag (1/0 or "1"/"0") to boolean
        processed_value = str(fdic_value) == "1"
    elif internal_field in ["cert", "rssd", "fed_rssd"] and fdic_value is not None:
        # Convert numeric IDs to strings
        processed_value = str(fdic_value)
    elif internal_field in ["asset", "dep"] and fdic_value is not None:
        # Keep financial values as-is (will be processed by Pydantic validator)
        processed_value = fdic_value
    else:
        processed_value = fdic_value
    
    return internal_field, processed_value


def get_error_message(status_code: int) -> str:
    """
    Get human-readable error message for FDIC API status code.
    
    Args:
        status_code: HTTP status code
        
    Returns:
        Human-readable error message
    """
    return FDIC_ERROR_CODES.get(status_code, f"Unknown error (HTTP {status_code})")


def build_cache_key(query_params: Dict) -> str:
    """
    Build a cache key from FDIC query parameters.
    
    Args:
        query_params: FDIC API query parameters
        
    Returns:
        Cache key string
    """
    # Sort parameters for consistent cache keys
    sorted_params = sorted(query_params.items())
    key_parts = [f"{k}:{v}" for k, v in sorted_params]
    return "fdic_" + "_".join(key_parts).replace(" ", "_")