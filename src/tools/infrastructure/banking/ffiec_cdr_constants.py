"""
FFIEC CDR API constants, field mappings, and utility functions.

Provides constants and utilities for FFIEC CDR Public Data Distribution SOAP API
with proper authentication, error handling, and caching configuration.
"""

import hashlib
from typing import Dict, List, Tuple, Any, Optional


# FFIEC CDR Public Data Distribution SOAP API Configuration
FFIEC_CDR_API_BASE_URL = "https://cdr.ffiec.gov/public/pws/webservices"
FFIEC_CDR_WSDL_URL = f"{FFIEC_CDR_API_BASE_URL}/retrievalservice.asmx?WSDL"
FFIEC_CDR_ENDPOINT = "/retrievalservice.asmx"

# API Configuration
FFIEC_CDR_API_CONFIG = {
    "wsdl_url": FFIEC_CDR_WSDL_URL,
    "query_timeout_seconds": 30,
    "max_retries": 3,
    "retry_delay_seconds": 1,
    "connection_timeout": 30.0,
    "verify_ssl": True
}

# Cache Configuration - Session-based only
FFIEC_CDR_CACHE_CONFIG = {
    "call_report_data_ttl": 3600,  # 1 hour for call report data
    "discovery_data_ttl": 1800,    # 30 minutes for discovery results
    "error_response_ttl": 300,     # 5 minutes for error responses
    "max_cache_size": 500          # Reasonable limit for session cache
}

# FFIEC CDR Data Series Types
FFIEC_DATA_SERIES = {
    "call_reports": "Call",
    "ubpr": "UBPR",
    "sdi": "SDI"
}

# UBPR Report Types and Periods
FFIEC_UBPR_CONFIG = {
    "data_series": "UBPR",
    "default_format": "XBRL",
    "cache_ttl": 7200,  # 2 hours (UBPR data changes less frequently)
    "description": "Uniform Bank Performance Report - processed financial ratios and peer analysis"
}

# Facsimile Format Options
FFIEC_FACSIMILE_FORMATS = {
    "pdf": "PDF",
    "xbrl": "XBRL", 
    "sdf": "SDF"
}

# Financial Institution ID Types for FFIEC CDR API
FFIEC_FI_ID_TYPES = {
    "rssd": "ID_RSSD",
    "fdic_cert": "FDICCertNumber",
    "occ_charter": "OCCChartNumber",
    "ots_docket": "OTSDockNumber"
}

# FFIEC CDR Error Codes and Messages
FFIEC_CDR_ERROR_CODES = {
    401: "Authentication required or invalid credentials",
    403: "Access forbidden - insufficient permissions", 
    404: "Call report data not found for specified criteria",
    429: "Rate limit exceeded - too many requests",
    500: "FFIEC CDR server error - try again later",
    502: "Bad gateway - FFIEC CDR service temporarily unavailable",
    503: "Service unavailable - FFIEC CDR maintenance in progress",
    504: "Gateway timeout - request took too long"
}

# SOAP Fault Code Mappings
FFIEC_SOAP_FAULT_CODES = {
    "soap:Client": "Client error - invalid request format or parameters",
    "soap:Server": "Server error - FFIEC CDR internal processing error",
    "soap:VersionMismatch": "SOAP version mismatch",
    "soap:MustUnderstand": "Required SOAP header not understood"
}

# Data Quality Indicators for Call Reports
FFIEC_DATA_QUALITY_INDICATORS = {
    "excellent": {"min_size_kb": 100, "has_metadata": True},
    "good": {"min_size_kb": 50, "has_metadata": True},
    "fair": {"min_size_kb": 10, "has_metadata": False},
    "poor": {"min_size_kb": 1, "has_metadata": False}
}

# Common RSSD ID Validation Patterns
FFIEC_RSSD_VALIDATION = {
    "min_length": 1,
    "max_length": 10,
    "pattern": r"^\d+$",  # Only digits allowed
    "description": "RSSD ID must be 1-10 digits"
}

# Period Format Patterns
FFIEC_PERIOD_FORMATS = {
    "quarterly": r"^\d{4}-\d{2}-\d{2}$",  # YYYY-MM-DD
    "description": "Reporting period must be in YYYY-MM-DD format (quarter end date)"
}


def build_ffiec_cache_key(rssd_id: str, reporting_period: str, format_type: str) -> str:
    """
    Build cache key for FFIEC call report data.
    
    Args:
        rssd_id: Bank RSSD identifier
        reporting_period: Reporting period in YYYY-MM-DD format
        format_type: Format type (PDF, XBRL, SDF)
        
    Returns:
        Unique cache key string
    """
    key_components = f"{rssd_id}_{reporting_period}_{format_type}"
    return hashlib.md5(key_components.encode()).hexdigest()


def build_discovery_cache_key(rssd_id: str) -> str:
    """
    Build cache key for FFIEC discovery results.
    
    Args:
        rssd_id: Bank RSSD identifier
        
    Returns:
        Unique cache key for discovery data
    """
    return f"discovery_{rssd_id}"


def validate_rssd_id(rssd_id: str) -> bool:
    """
    Validate RSSD ID format.
    
    Args:
        rssd_id: RSSD ID to validate
        
    Returns:
        True if valid RSSD ID format
    """
    if not rssd_id:
        return False
    
    import re
    pattern = FFIEC_RSSD_VALIDATION["pattern"]
    if not re.match(pattern, rssd_id):
        return False
    
    length = len(rssd_id)
    min_len = FFIEC_RSSD_VALIDATION["min_length"] 
    max_len = FFIEC_RSSD_VALIDATION["max_length"]
    
    return min_len <= length <= max_len


def validate_reporting_period(period: str) -> bool:
    """
    Validate reporting period format.
    
    Args:
        period: Reporting period to validate
        
    Returns:
        True if valid period format
    """
    if not period:
        return False
        
    import re
    pattern = FFIEC_PERIOD_FORMATS["quarterly"]
    return bool(re.match(pattern, period))


def validate_facsimile_format(format_type: str) -> bool:
    """
    Validate facsimile format option.
    
    Args:
        format_type: Format to validate
        
    Returns:
        True if valid format option
    """
    return format_type.upper() in FFIEC_FACSIMILE_FORMATS.values()


def get_ffiec_error_message(error_code: int, default: str = "Unknown FFIEC CDR error") -> str:
    """
    Get human-readable error message for FFIEC CDR error code.
    
    Args:
        error_code: HTTP error code or SOAP fault code
        default: Default message if code not found
        
    Returns:
        Human-readable error message
    """
    return FFIEC_CDR_ERROR_CODES.get(error_code, default)


def assess_call_report_quality(data_size: int, has_metadata: bool = True) -> str:
    """
    Assess call report data quality based on size and metadata.
    
    Args:
        data_size: Size of call report data in bytes
        has_metadata: Whether metadata is present
        
    Returns:
        Quality indicator string
    """
    size_kb = data_size / 1024
    
    for quality, criteria in FFIEC_DATA_QUALITY_INDICATORS.items():
        if size_kb >= criteria["min_size_kb"]:
            if criteria["has_metadata"] and not has_metadata:
                continue
            return quality
    
    return "poor"