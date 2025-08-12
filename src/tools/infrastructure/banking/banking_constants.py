"""
FFIEC Call Report constants and field mappings.

Provides standardized schedule identifiers, field mappings, and constants
for Call Report data processing following FFIEC conventions.
"""

from typing import Dict, Set

# FFIEC Schedule Mappings
FFIEC_SCHEDULES = {
    "RC": "Balance Sheet",
    "RI": "Income Statement", 
    "RCA": "Cash and Balances Due from Depository Institutions",
    "RCB": "Securities",
    "RCC": "Loans and Lease Financing Receivables",
    "RCD": "Trading Assets and Liabilities",
    "RCE": "Deposit Liabilities",
    "RCF": "Other Assets",
    "RCG": "Other Liabilities",
    "RCH": "Selected Balance Sheet Items for Domestic Offices",
    "RCI": "Unused",
    "RCJ": "Unused", 
    "RCK": "Quarterly Averages",
    "RCL": "Derivatives and Off-Balance Sheet Items",
    "RCM": "Memoranda",
    "RCN": "Past Due and Nonaccrual",
    "RCO": "Other Data for Deposit Insurance and FICO Assessments",
    "RCP": "Unused",
    "RCQ": "Assets and Liabilities Measured at Fair Value",
    "RCR": "Regulatory Capital",
    "RCS": "Servicing, Securitization, and Asset Sale Activities"
}

# Common FFIEC Field Mappings - Balance Sheet (RC Schedule)
RC_BALANCE_SHEET_FIELDS = {
    # Assets
    "RCON0010": "Cash and balances due from depository institutions",
    "RCON0071": "Securities",  
    "RCON1400": "Total loans and leases",
    "RCON2145": "Bank premises and fixed assets",
    "RCON2150": "Other real estate owned",
    "RCON2160": "Investments in unconsolidated subsidiaries",
    "RCON2170": "Total assets",
    
    # Liabilities
    "RCON2200": "Total deposits",
    "RCON2800": "Federal funds purchased and securities sold under agreements to repurchase",
    "RCON3200": "Other borrowed money",
    "RCON2930": "Subordinated notes and debentures", 
    "RCON2948": "Total liabilities",
    
    # Equity
    "RCON3210": "Total bank equity capital",
    "RCON3230": "Common stock",
    "RCON3839": "Retained earnings",
    "RCON3632": "Unrealized gains (losses) on available-for-sale securities"
}

# Income Statement Fields (RI Schedule)  
RI_INCOME_STATEMENT_FIELDS = {
    # Interest Income
    "RIAD4107": "Total interest income",
    "RIAD4115": "Interest income on loans and leases",
    "RIAD4115": "Interest and fee income on loans",
    
    # Interest Expense
    "RIAD4073": "Total interest expense",
    "RIAD4508": "Interest on deposits",
    
    # Net Interest Income
    "RIAD4074": "Net interest income",
    
    # Provision and Noninterest
    "RIAD4230": "Provision for credit losses",
    "RIAD4079": "Total noninterest income",
    "RIAD4093": "Total noninterest expense",
    
    # Net Income
    "RIAD4301": "Income before income taxes",
    "RIAD4302": "Income taxes",
    "RIAD4340": "Net income"
}

# Capital Adequacy Fields (RC-R Schedule)
RCR_CAPITAL_FIELDS = {
    "RCON8274": "Tier 1 capital",
    "RCON8275": "Total capital", 
    "RCON0023": "Risk-weighted assets",
    "RCON7204": "Common equity tier 1 capital ratio",
    "RCON7206": "Tier 1 capital ratio",
    "RCON7205": "Total capital ratio",
    "RCON7219": "Leverage ratio"
}

# Asset Quality Fields (RC-N Schedule)
RCN_ASSET_QUALITY_FIELDS = {
    "RCON5525": "Past due 30-89 days and still accruing",
    "RCON5526": "Past due 90 days or more and still accruing", 
    "RCON5527": "Nonaccrual loans and leases",
    "RCON5612": "Net charge-offs during quarter",
    "RCON1407": "Allowance for credit losses on loans and leases"
}

# All Field Mappings Combined
ALL_FIELD_MAPPINGS = {
    **RC_BALANCE_SHEET_FIELDS,
    **RI_INCOME_STATEMENT_FIELDS,
    **RCR_CAPITAL_FIELDS,
    **RCN_ASSET_QUALITY_FIELDS
}

# Rename this to avoid conflict with the constant above
CALL_REPORT_FIELDS = ALL_FIELD_MAPPINGS

# Field to Schedule Mapping
FIELD_TO_SCHEDULE = {
    # RC Schedule fields
    **{field_id: "RC" for field_id in RC_BALANCE_SHEET_FIELDS.keys()},
    # RI Schedule fields  
    **{field_id: "RI" for field_id in RI_INCOME_STATEMENT_FIELDS.keys()},
    # RC-R Schedule fields
    **{field_id: "RCR" for field_id in RCR_CAPITAL_FIELDS.keys()},
    # RC-N Schedule fields
    **{field_id: "RCN" for field_id in RCN_ASSET_QUALITY_FIELDS.keys()}
}

# Financial Ratio Field Requirements
RATIO_FIELD_REQUIREMENTS = {
    "ROA": {
        "numerator": {"field_id": "RIAD4340", "name": "Net Income", "schedule": "RI"},
        "denominator": {"field_id": "RCON2170", "name": "Total Assets", "schedule": "RC"}
    },
    "ROE": {
        "numerator": {"field_id": "RIAD4340", "name": "Net Income", "schedule": "RI"},
        "denominator": {"field_id": "RCON3210", "name": "Total Equity", "schedule": "RC"}
    },
    "TIER1_CAPITAL_RATIO": {
        "numerator": {"field_id": "RCON8274", "name": "Tier 1 Capital", "schedule": "RCR"},
        "denominator": {"field_id": "RCON0023", "name": "Risk-Weighted Assets", "schedule": "RCR"}
    },
    "NET_INTEREST_MARGIN": {
        "numerator": {"field_id": "RIAD4074", "name": "Net Interest Income", "schedule": "RI"},
        "denominator": {"field_id": "RCON2170", "name": "Total Assets", "schedule": "RC"}
    }
}

# Valid Schedules Set
VALID_SCHEDULES: Set[str] = set(FFIEC_SCHEDULES.keys())

# Valid Field IDs Set
VALID_FIELD_IDS: Set[str] = set(ALL_FIELD_MAPPINGS.keys())

def get_field_info(field_id: str) -> Dict[str, str]:
    """
    Get field information including name and schedule.
    
    Args:
        field_id: FFIEC field identifier (e.g., "RCON2170")
        
    Returns:
        Dictionary with field_name and schedule, or empty dict if not found
    """
    if field_id not in ALL_FIELD_MAPPINGS:
        return {}
    
    return {
        "field_name": ALL_FIELD_MAPPINGS[field_id],
        "schedule": FIELD_TO_SCHEDULE.get(field_id, "UNKNOWN"),
        "field_id": field_id
    }

def validate_schedule(schedule: str) -> bool:
    """
    Validate if schedule is a known FFIEC schedule.
    
    Args:
        schedule: Schedule identifier to validate
        
    Returns:
        True if valid schedule, False otherwise
    """
    return schedule in VALID_SCHEDULES

def validate_field_id(field_id: str) -> bool:
    """
    Validate if field_id is a known FFIEC field.
    
    Args:
        field_id: Field identifier to validate
        
    Returns:
        True if valid field ID, False otherwise
    """
    return field_id in VALID_FIELD_IDS

def get_ratio_requirements(ratio_name: str) -> Dict:
    """
    Get field requirements for calculating a financial ratio.
    
    Args:
        ratio_name: Name of the ratio (ROA, ROE, etc.)
        
    Returns:
        Dictionary with numerator and denominator field requirements
    """
    return RATIO_FIELD_REQUIREMENTS.get(ratio_name.upper(), {})