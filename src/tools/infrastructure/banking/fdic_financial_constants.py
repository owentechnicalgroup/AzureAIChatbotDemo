"""
FDIC Financial Data API constants, field mappings, and utility functions.

Provides constants and utilities for FDIC BankFind Suite Financial Data API
(/financials endpoint) following established patterns and best practices.
"""

import hashlib
from typing import Dict, List, Tuple, Any, Optional


# CRITICAL: FDIC BankFind Suite API uses specific endpoint structure
# Financial API: https://banks.data.fdic.gov/api/financials
# NOT https://api.fdic.gov/banks/financials (this is different API)
FDIC_FINANCIAL_API_BASE_URL = "https://banks.data.fdic.gov/api"
FDIC_FINANCIAL_ENDPOINT = "/financials"

# API Configuration
FDIC_FINANCIAL_API_CONFIG = {
    "max_results_per_query": 100,
    "default_fields_limit": 20,
    "query_timeout_seconds": 30,
    "max_retries": 3,
    "retry_delay_seconds": 1
}

# Cache Configuration
FDIC_FINANCIAL_CACHE_CONFIG = {
    "financial_data_ttl": 1800,  # 30 minutes for financial data
    "field_metadata_ttl": 3600,  # 1 hour for field definitions
    "error_response_ttl": 300,   # 5 minutes for error responses
    "max_cache_size": 1000
}

# Common Financial Fields - over 1,100 fields available, these are most important
# Format: field_name -> (description, data_type, typical_range)
FINANCIAL_FIELD_MAPPINGS = {
    # Asset Fields
    "ASSET": ("Total assets", "decimal", "thousands"),
    "DEP": ("Total deposits", "decimal", "thousands"),
    "LNLS": ("Total loans and leases", "decimal", "thousands"),
    "NETINC": ("Net income", "decimal", "thousands"),
    "EQ": ("Total equity capital", "decimal", "thousands"),
    
    # Income Statement Fields
    "INTINC": ("Total interest income", "decimal", "thousands"),
    "EINTEXP": ("Total interest expense", "decimal", "thousands"),
    "NETINTINC": ("Net interest income", "decimal", "thousands"),
    "NONII": ("Total noninterest income", "decimal", "thousands"),
    "NONIX": ("Total noninterest expense", "decimal", "thousands"),
    
    # Capital Fields
    "TIER1CAP": ("Tier 1 capital", "decimal", "thousands"),
    "TOTCAP": ("Total capital", "decimal", "thousands"),
    "RWAJCET1": ("Risk-weighted assets for CET1", "decimal", "thousands"),
    
    # Ratio Fields (already calculated by FDIC)
    "ROA": ("Return on assets", "decimal", "percentage"),
    "ROE": ("Return on equity", "decimal", "percentage"),
    "NIM": ("Net interest margin", "decimal", "percentage"),
    "EFFRATIO": ("Efficiency ratio", "decimal", "percentage"),
    
    # Capital Ratio Fields
    "CET1R": ("Common equity tier 1 ratio", "decimal", "percentage"),
    "TIER1R": ("Tier 1 capital ratio", "decimal", "percentage"),
    "TOTCAPR": ("Total capital ratio", "decimal", "percentage"),
    
    # Asset Quality Fields
    "NPTLA": ("Nonperforming loans to total loans", "decimal", "percentage"),
    "ALLL": ("Allowance for loan and lease losses", "decimal", "thousands"),
    "CHARGEOFFS": ("Net charge-offs", "decimal", "thousands"),
    
    # Key Identifiers
    "CERT": ("FDIC certificate number", "string", "identifier"),
    "REPDTE": ("Report date", "date", "yyyy-mm-dd"),
    "RSSD": ("RSSD identifier", "string", "identifier")
}

# Field Selection Templates for Different Analysis Types
FIELD_SELECTION_TEMPLATES = {
    "basic_info": [
        "CERT", "REPDTE", "ASSET", "DEP", "EQ"
    ],
    "financial_summary": [
        "CERT", "REPDTE", "ASSET", "DEP", "LNLS", "EQ", 
        "NETINC", "INTINC", "EINTEXP", "NETINTINC"
    ],
    "key_ratios": [
        "CERT", "REPDTE", "ASSET", "EQ", "NETINC",
        "NETINTINC", "INTINC", "EINTEXP",  # Added for NIM calculation
        "ROA", "ROE", "NIM", "CET1R", "TIER1R", "TOTCAPR"
    ],
    "asset_quality": [
        "CERT", "REPDTE", "ASSET", "LNLS", "NPTLA", 
        "ALLL", "CHARGEOFFS"
    ],
    "comprehensive": [
        "CERT", "REPDTE", "ASSET", "DEP", "LNLS", "EQ",
        "NETINC", "INTINC", "EINTEXP", "NETINTINC",
        "NONII", "NONIX", "ROA", "ROE", "NIM",
        "CET1R", "TIER1R", "TOTCAPR", "NPTLA", "ALLL"
    ]
}

# Query Templates for Different Use Cases
QUERY_TEMPLATES = {
    "single_bank_latest": {
        "filters": "CERT:{cert_id}",
        "sort_by": "REPDTE",
        "sort_order": "DESC",
        "limit": "1"
    },
    "single_bank_historical": {
        "filters": "CERT:{cert_id} AND REPDTE:[{start_date} TO {end_date}]",
        "sort_by": "REPDTE", 
        "sort_order": "DESC",
        "limit": "{quarters}"
    },
    "peer_group_comparison": {
        "filters": "ASSET:[{min_assets} TO {max_assets}] AND REPDTE:{report_date}",
        "sort_by": "ASSET",
        "sort_order": "DESC",
        "limit": "{peer_count}"
    },
    "geographic_analysis": {
        "filters": "STALPBR:{state} AND REPDTE:{report_date}",
        "sort_by": "ASSET",
        "sort_order": "DESC", 
        "limit": "{bank_count}"
    }
}

# Financial Value Display Formatting
FINANCIAL_DISPLAY_FORMATS = {
    "thousands": {
        "divisor": 1,
        "suffix": "K",
        "decimal_places": 0
    },
    "millions": {
        "divisor": 1000,
        "suffix": "M", 
        "decimal_places": 1
    },
    "billions": {
        "divisor": 1000000,
        "suffix": "B",
        "decimal_places": 2
    }
}

# Financial Value Thresholds for Auto-Formatting
FINANCIAL_FORMAT_THRESHOLDS = {
    "billions_threshold": 1000000,      # >= 1B (in thousands)
    "millions_threshold": 1000,         # >= 1M (in thousands)
    "thousands_threshold": 1            # >= 1K (in thousands)
}

# Error Codes and Messages (FDIC-specific)
FDIC_FINANCIAL_ERROR_CODES = {
    400: "Invalid query parameters or malformed request",
    401: "Authentication required or invalid API key",
    403: "Access forbidden - insufficient permissions",
    404: "Financial data not found for specified criteria",
    429: "Rate limit exceeded - too many requests",
    500: "FDIC server error - try again later",
    502: "Bad gateway - FDIC service temporarily unavailable",
    503: "Service unavailable - FDIC maintenance in progress",
    504: "Gateway timeout - request took too long"
}

# Data Quality Indicators
DATA_QUALITY_INDICATORS = {
    "excellent": {"min_fields": 18, "required_fields": ["CERT", "REPDTE", "ASSET", "DEP", "NETINC"]},
    "good": {"min_fields": 12, "required_fields": ["CERT", "REPDTE", "ASSET"]},
    "fair": {"min_fields": 6, "required_fields": ["CERT", "REPDTE"]},
    "poor": {"min_fields": 3, "required_fields": ["CERT"]}
}


def get_financial_field_info(field_name: str) -> Optional[Dict[str, str]]:
    """
    Get information about a financial field.
    
    Args:
        field_name: FDIC financial field name
        
    Returns:
        Dictionary with field information or None if not found
    """
    field_info = FINANCIAL_FIELD_MAPPINGS.get(field_name.upper())
    if field_info:
        return {
            "field_name": field_name.upper(),
            "description": field_info[0],
            "data_type": field_info[1],
            "unit": field_info[2]
        }
    return None


def get_fields_for_analysis_type(analysis_type: str) -> List[str]:
    """
    Get the recommended fields for a specific analysis type.
    
    Args:
        analysis_type: Type of analysis (basic_info, financial_summary, etc.)
        
    Returns:
        List of field names for the analysis type
    """
    return FIELD_SELECTION_TEMPLATES.get(analysis_type, FIELD_SELECTION_TEMPLATES["basic_info"])


def build_financial_query_params(
    cert_id: Optional[str] = None,
    filters: Optional[str] = None,
    fields: Optional[List[str]] = None,
    sort_by: str = "REPDTE",
    sort_order: str = "DESC",
    limit: int = 10
) -> Dict[str, str]:
    """
    Build query parameters for FDIC Financial API.
    
    Args:
        cert_id: FDIC certificate number for specific bank
        filters: Additional Elasticsearch query filters
        fields: Specific fields to retrieve
        sort_by: Field to sort by
        sort_order: Sort order (ASC or DESC)
        limit: Maximum results
        
    Returns:
        Dictionary of query parameters
    """
    params = {
        "format": "json",
        "sort_by": sort_by,
        "sort_order": sort_order,
        "limit": str(min(limit, FDIC_FINANCIAL_API_CONFIG["max_results_per_query"]))
    }
    
    # Build filters
    filter_parts = []
    if cert_id:
        filter_parts.append(f"CERT:{cert_id}")
    if filters:
        filter_parts.append(filters)
        
    if filter_parts:
        params["filters"] = " AND ".join(filter_parts)
    
    # Add field selection for performance optimization
    if fields:
        # Always include key identification fields
        required_fields = ["CERT", "REPDTE"]
        all_fields = list(set(required_fields + fields))
        params["fields"] = ",".join(all_fields)
    
    return params


def format_financial_value(
    value_in_thousands: Optional[float],
    auto_scale: bool = True,
    force_format: Optional[str] = None,
    include_currency: bool = True
) -> str:
    """
    Format financial values for display with appropriate scaling.
    
    Args:
        value_in_thousands: Value in thousands of dollars
        auto_scale: Automatically choose best scale (millions/billions)
        force_format: Force specific format ('thousands', 'millions', 'billions')
        include_currency: Include dollar sign in output
        
    Returns:
        Formatted string representation of the value
    """
    if value_in_thousands is None:
        return "Not available"
    
    # Handle negative values
    is_negative = value_in_thousands < 0
    abs_value = abs(value_in_thousands)
    
    # Determine format
    if force_format:
        format_info = FINANCIAL_DISPLAY_FORMATS.get(force_format)
    elif auto_scale:
        if abs_value >= FINANCIAL_FORMAT_THRESHOLDS["billions_threshold"]:
            format_info = FINANCIAL_DISPLAY_FORMATS["billions"]
        elif abs_value >= FINANCIAL_FORMAT_THRESHOLDS["millions_threshold"]:
            format_info = FINANCIAL_DISPLAY_FORMATS["millions"]
        else:
            format_info = FINANCIAL_DISPLAY_FORMATS["thousands"]
    else:
        format_info = FINANCIAL_DISPLAY_FORMATS["thousands"]
    
    if not format_info:
        return f"${value_in_thousands}K" if include_currency else f"{value_in_thousands}K"
    
    # Calculate scaled value
    scaled_value = abs_value / format_info["divisor"]
    
    # Format with appropriate decimal places
    if format_info["decimal_places"] == 0:
        formatted_number = f"{scaled_value:.0f}"
    else:
        formatted_number = f"{scaled_value:.{format_info['decimal_places']}f}"
    
    # Add negative sign back if needed
    if is_negative:
        formatted_number = f"-{formatted_number}"
    
    # Construct final string
    currency_prefix = "$" if include_currency else ""
    return f"{currency_prefix}{formatted_number}{format_info['suffix']}"


def build_financial_cache_key(query_params: Dict[str, Any]) -> str:
    """
    Build cache key for financial API queries.
    
    Args:
        query_params: Query parameters dictionary
        
    Returns:
        SHA-256 hash string for cache key
    """
    # Sort parameters for consistent cache keys
    sorted_params = sorted(query_params.items())
    cache_string = "&".join(f"{k}={v}" for k, v in sorted_params)
    return hashlib.sha256(cache_string.encode()).hexdigest()[:16]


def get_financial_error_message(status_code: int, default_message: str = "Unknown error") -> str:
    """
    Get human-readable error message for FDIC Financial API status codes.
    
    Args:
        status_code: HTTP status code
        default_message: Default message if code not recognized
        
    Returns:
        Human-readable error message
    """
    return FDIC_FINANCIAL_ERROR_CODES.get(status_code, default_message)


def assess_data_quality(available_fields: List[str]) -> Tuple[str, Dict[str, Any]]:
    """
    Assess the quality of available financial data based on field count and coverage.
    
    Args:
        available_fields: List of available field names
        
    Returns:
        Tuple of (quality_level, assessment_details)
    """
    field_count = len(available_fields)
    available_set = set(field.upper() for field in available_fields)
    
    # Check each quality level (from highest to lowest)
    for level in ["excellent", "good", "fair", "poor"]:
        criteria = DATA_QUALITY_INDICATORS[level]
        required_set = set(criteria["required_fields"])
        
        # Check if meets minimum field count and has required fields
        if field_count >= criteria["min_fields"] and required_set.issubset(available_set):
            return level, {
                "quality_level": level,
                "field_count": field_count,
                "required_fields_present": len(required_set),
                "required_fields_missing": list(required_set - available_set),
                "coverage_percentage": round((field_count / 25) * 100, 1)  # Assume 25 is good coverage
            }
    
    # If none match, return poor quality
    return "poor", {
        "quality_level": "poor",
        "field_count": field_count,
        "required_fields_present": 0,
        "required_fields_missing": DATA_QUALITY_INDICATORS["poor"]["required_fields"],
        "coverage_percentage": 0
    }


def validate_financial_field_name(field_name: str) -> bool:
    """
    Validate if a field name is a known FDIC financial field.
    
    Args:
        field_name: Field name to validate
        
    Returns:
        True if field is known, False otherwise
    """
    return field_name.upper() in FINANCIAL_FIELD_MAPPINGS


def get_analysis_field_requirements(analysis_type: str) -> Dict[str, List[str]]:
    """
    Get field requirements for a specific analysis type.
    
    Args:
        analysis_type: Type of analysis
        
    Returns:
        Dictionary with required and recommended fields
    """
    fields = get_fields_for_analysis_type(analysis_type)
    
    # Separate into required vs recommended based on analysis type
    if analysis_type == "basic_info":
        required = ["CERT", "REPDTE", "ASSET"]
        recommended = ["DEP", "EQ"]
    elif analysis_type == "financial_summary":
        required = ["CERT", "REPDTE", "ASSET", "DEP", "NETINC"]
        recommended = ["LNLS", "EQ", "INTINC", "EINTEXP"]
    elif analysis_type == "key_ratios":
        required = ["CERT", "REPDTE", "ASSET", "EQ", "NETINC"]
        recommended = ["ROA", "ROE", "NIM", "CET1R"]
    else:
        required = ["CERT", "REPDTE"]
        recommended = fields[2:]  # All except required
    
    return {
        "required": required,
        "recommended": recommended,
        "all_fields": fields
    }