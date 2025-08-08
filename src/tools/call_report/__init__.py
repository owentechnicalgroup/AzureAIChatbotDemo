"""
Call Report tooling package for FFIEC banking data.

Provides tools and models for accessing, processing, and analyzing
FFIEC Call Report data through mock API services and AI agent integration.
"""

from .constants import (
    FFIEC_SCHEDULES,
    RC_BALANCE_SHEET_FIELDS,
    RI_INCOME_STATEMENT_FIELDS,
    RCR_CAPITAL_FIELDS,
    RCN_ASSET_QUALITY_FIELDS,
    ALL_FIELD_MAPPINGS,
    RATIO_FIELD_REQUIREMENTS,
    VALID_SCHEDULES,
    VALID_FIELD_IDS,
    get_field_info,
    validate_schedule,
    validate_field_id,
    get_ratio_requirements
)

from .data_models import (
    CallReportField,
    BankIdentification, 
    CallReportData,
    FinancialRatio,
    CallReportAPIResponse,
    BankSearchRequest
)

__all__ = [
    # Constants and utilities
    "FFIEC_SCHEDULES",
    "RC_BALANCE_SHEET_FIELDS",
    "RI_INCOME_STATEMENT_FIELDS", 
    "RCR_CAPITAL_FIELDS",
    "RCN_ASSET_QUALITY_FIELDS",
    "ALL_FIELD_MAPPINGS",
    "RATIO_FIELD_REQUIREMENTS",
    "VALID_SCHEDULES",
    "VALID_FIELD_IDS",
    "get_field_info",
    "validate_schedule",
    "validate_field_id",
    "get_ratio_requirements",
    
    # Data models
    "CallReportField",
    "BankIdentification",
    "CallReportData", 
    "FinancialRatio",
    "CallReportAPIResponse",
    "BankSearchRequest",
]

# Package metadata
__version__ = "1.0.0"
__author__ = "Context Engineering Team"
__description__ = "FFIEC Call Report tooling for AI agent financial analysis"