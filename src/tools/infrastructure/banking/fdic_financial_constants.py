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

# Field Selection Templates for Different Analysis Types Based on FDIC RISView Sections
FIELD_SELECTION_TEMPLATES = {
    "institution_profile": [
        "CERT", "REPDTE", "ACTIVE", "BKCLASS", "INSTTYPE", "CB", 
        "CHRTAGNT", "INSFDIC", "ASSET", "OFFDOM", "OFFFOR"
    ],
    "balance_sheet_assets": [
        "CERT", "REPDTE", "ASSET", "CHBAL", "LNLS", "LNLSNET", "BKPREM", 
        "INTAN", "FREPO", "LNCI", "LNRE", "LNCON", "LNAG"
    ],
    "balance_sheet_liabilities": [
        "CERT", "REPDTE", "LIAB", "DEP", "DEPDOM", "DEPNI", "DEPI", 
        "BRO", "FREPP", "EQCS", "EQSUR", "EQ"
    ],
    "deposit_composition": [
        "CERT", "REPDTE", "DEP", "DEPDOM", "DEPFOR", "DEPNI", "DEPI",
        "DDT", "CD3LES", "CD3T12", "CD1T3", "CDOV3", "BRO", "IRAKEOGH"
    ],
    "loan_portfolio": [
        "CERT", "REPDTE", "LNLS", "LNLSNET", "LNCI", "LNAG", "LNRE", 
        "LNRECONS", "LNRELOC", "LNREMULT", "LNCON", "LNAUTO", "LNCRCD"
    ],
    "credit_quality": [
        "CERT", "REPDTE", "LNLS", "LNATRES", "NPTLA", "ELNATR", 
        "DRLNLS", "CRLNLS", "ELNLOS"
    ],
    "interest_income": [
        "CERT", "REPDTE", "INTINC", "ILNDOM", "ILNFOR", "ILS", 
        "ISC", "ICHBAL", "IFREPO", "IOTHII"
    ],
    "interest_expense": [
        "CERT", "REPDTE", "EINTEXP", "EDEPDOM", "EDEPFOR", "EFREPP", 
        "EFHLBADV", "EMTGLS", "ESUBND"
    ],
    "noninterest_income_expense": [
        "CERT", "REPDTE", "ISERCHG", "IOTHFEE", "IGLSEC", "ESAL", 
        "EPREMAGG", "EOTHNINT", "EAMINTAN"
    ],
    "profitability": [
        "CERT", "REPDTE", "ASSET", "EQ", "NETINC", "INTINC", "EINTEXP", 
        "NETINTINC", "ELNATR", "ROA", "ROE", "ROAPTX"
    ],
    "capital_ratios": [
        "CERT", "REPDTE", "EQ", "ASSET", "TIER1CAP", "TOTCAP", "RWAJCET1",
        "CET1R", "TIER1R", "TOTCAPR", "EQCS", "EQSUR"
    ],
    "efficiency_metrics": [
        "CERT", "REPDTE", "ASSET", "NETINC", "EINTEXP", "INTINC", 
        "ESAL", "EPREMAGG", "EOTHNINT", "INTEXPY"
    ],
    "institution_identification": [
        "CERT", "REPDTE", "REPDTE_RAW", "L_REPDTE", "REPYEAR", "RISDATE", 
        "CALLYM", "CALLFORM", "ACTEVT"
    ],
    "institution_classification": [
        "CERT", "REPDTE", "ACTIVE", "CLOSED", "FAILED", "BKCLASS", 
        "CLCODE", "ENTTYPE", "INSTTYPE"
    ],
    "charter_regulatory": [
        "CERT", "REPDTE", "CHRTAGNT", "FEDCHRTR", "FORCHRTR", "CONSERVE", 
        "FRSMEM", "FORMCFR"
    ],
    "insurance_classification": [
        "CERT", "REPDTE", "INSALL", "INSFDIC", "INSDIF", "INSBIF", "INSSAIF", 
        "INSCOML", "INSSAVE", "INSNONE", "INSTCOML", "INSTSAVE"
    ],
    "specialized_institution_types": [
        "CERT", "REPDTE", "CB", "CBLRIND", "DENOVO", "IBA", "INSTAG", 
        "INSTCRCD", "MINORITY", "MUTUAL", "TRUST", "TRACT", "SUBCHAPS"
    ],
    "geographic_information": [
        "CERT", "REPDTE", "ADDRESS", "CNTRYALP", "CNTRYNUM", "CNTYNUM", 
        "CBSANAME", "CBSADIV", "DIVISION", "CSA", "STMULT"
    ],
    "fdic_administrative": [
        "CERT", "REPDTE", "FDICDBS", "FDICDBSDESC", "FDICSUPV", "FDICSUPVDESC", 
        "FED", "FEDDESC", "FLDOFF", "FDICAREA", "FDICTERR", "FLDOFDCA"
    ],
    "securities_investments": [
        "CERT", "REPDTE", "FREPO", "FREPOR", "FREPP", "FREPPR"
    ],
    "allowance_credit_losses": [
        "CERT", "REPDTE", "LNATRES", "LNATRESJ", "LNATRESRR"
    ],
    "borrowings_liabilities": [
        "CERT", "REPDTE", "LIAB", "LIABR", "LIABEQ", "LIABEQR", 
        "LIPMTG", "CUSLI", "ACEPT"
    ],
    "equity_capital_components": [
        "CERT", "REPDTE", "EQ", "EQ2", "EQR", "EQCS", "EQCSR", "EQSUR", 
        "EQSURR", "EQPP", "EQPPR", "LLPFDSTK", "EQCONSUB", "EQNWCERT", 
        "EQOTHCC", "EQUP", "EQUPTOT", "EQUPTOTR", "EQCFCTA"
    ],
    "provision_credit_losses": [
        "CERT", "REPDTE", "ELNATR", "ELNATRR", "ELNATQ", "ELNATQR", 
        "ELNATQA", "ELNLOS", "ELNLOSQ", "NTTOTQ"
    ],
    "charge_offs_recoveries": [
        "CERT", "REPDTE", "DRLNLS", "DRLNLSR", "DRLNLSQ", "DRLNLSQR", 
        "CRLNLS", "CRLNLSR", "CRLNLSQ", "CRLNLSQR"
    ],
    "net_income_components": [
        "CERT", "REPDTE", "IBEFTAX", "ITAX", "ITAXR", "ITAXQ", "ITAXQR", 
        "NETINC", "NETINCR", "NETINCQ", "NETINCQA", "NETINCQR", 
        "EXTRA", "EXTRAR", "EXTRAQ", "EXTRAQR"
    ],
    "performance_ratios": [
        "CERT", "REPDTE", "ROA", "ROAQ", "ROAPTX", "ROAPTXQ", "ROE", "ROEQ", 
        "INTEXPY", "INTEXPYQ"
    ],
    "dividend_information": [
        "CERT", "REPDTE", "EQCDIV", "EQCDIVR", "EQCDIVC", "EQCDIVCR", 
        "EQCDIVP", "EQCDIVPR", "EQCDIVQ", "EQCDIVQR"
    ],
    "office_branch_information": [
        "CERT", "REPDTE", "BRANCH", "OFFDOM", "OFFFOR", "OFFOA"
    ],
    "holding_company_information": [
        "CERT", "REPDTE", "HCTMULT", "HCTONE", "HCTNONE", "NAMEHCR", 
        "CITYHCR", "STALPHCR", "RSSDHCR", "CERTCONS", "PARCERT"
    ],
    "specialized_business": [
        "CERT", "REPDTE", "EDGECODE", "SPECGRP", "SPECGRPDESC"
    ],
    "call_report_information": [
        "CERT", "REPDTE", "FORM31", "DOCKET"
    ]
}

# Detailed Analysis Type Descriptions for AI Guidance
ANALYSIS_TYPE_DESCRIPTIONS = {
    "institution_profile": {
        "description": "Basic institution information, charter details, and classification",
        "use_cases": ["Bank identification", "Institution overview", "Charter and regulatory status"],
        "key_fields": ["CERT", "BKCLASS", "INSTTYPE", "CHRTAGNT", "INSFDIC", "CB", "ACTIVE"],
        "field_details": {
            "CERT": "FDIC Certificate Number - unique institution identifier",
            "BKCLASS": "Institution Class (N=National, SM=State Member, NM=State Non-Member, etc.)",
            "INSTTYPE": "Descriptive institution type",
            "CHRTAGNT": "Charter granting authority",
            "INSFDIC": "FDIC insurance indicator",
            "CB": "Community bank classification",
            "ACTIVE": "Institution active status flag"
        }
    },
    "balance_sheet_assets": {
        "description": "Asset composition including loans, cash, premises, and investments",
        "use_cases": ["Asset analysis", "Portfolio composition", "Asset quality assessment"],
        "key_fields": ["ASSET", "CHBAL", "LNLS", "LNLSNET", "BKPREM", "INTAN", "LNCI", "LNRE", "LNCON"],
        "field_details": {
            "ASSET": "Total assets (in thousands USD)",
            "CHBAL": "Cash and due from depository institutions",
            "LNLS": "Total loans and leases with unearned income",
            "LNLSNET": "Net loans and leases (after allowance for losses)",
            "BKPREM": "Bank premises and fixed assets",
            "INTAN": "Intangible assets including goodwill",
            "LNCI": "Commercial and industrial loans",
            "LNRE": "Real estate loans total",
            "LNCON": "Consumer loans total"
        }
    },
    "balance_sheet_liabilities": {
        "description": "Liability structure including deposits, borrowings, and equity capital",
        "use_cases": ["Funding analysis", "Capital structure", "Liability composition"],
        "key_fields": ["LIAB", "DEP", "DEPDOM", "DEPNI", "DEPI", "BRO", "EQ", "EQCS", "EQSUR"],
        "field_details": {
            "LIAB": "Total liabilities",
            "DEP": "Total deposits",
            "DEPDOM": "Deposits in domestic offices",
            "DEPNI": "Noninterest-bearing deposits",
            "DEPI": "Interest-bearing deposits",
            "BRO": "Brokered deposits",
            "EQ": "Total equity capital",
            "EQCS": "Common stock",
            "EQSUR": "Capital surplus"
        }
    },
    "deposit_composition": {
        "description": "Detailed deposit mix by type, maturity, and interest-bearing status",
        "use_cases": ["Funding stability analysis", "Interest rate sensitivity", "Deposit concentration"],
        "key_fields": ["DEP", "DEPNI", "DEPI", "DDT", "CD3LES", "CD3T12", "CD1T3", "BRO", "IRAKEOGH"],
        "field_details": {
            "DEP": "Total deposits",
            "DEPNI": "Noninterest-bearing deposits (demand)",
            "DEPI": "Interest-bearing deposits",
            "DDT": "Total demand deposit accounts",
            "CD3LES": "Time deposits $250K+ maturing in 3 months or less",
            "CD3T12": "Time deposits $250K+ maturing 3-12 months",
            "CD1T3": "Time deposits $250K+ maturing 1-3 years",
            "BRO": "Brokered deposits",
            "IRAKEOGH": "IRA and Keogh retirement deposits"
        }
    },
    "loan_portfolio": {
        "description": "Loan composition by type including commercial, real estate, and consumer",
        "use_cases": ["Credit portfolio analysis", "Loan concentration", "Business focus assessment"],
        "key_fields": ["LNLS", "LNLSNET", "LNCI", "LNAG", "LNRE", "LNRECONS", "LNRELOC", "LNCON", "LNAUTO", "LNCRCD"],
        "field_details": {
            "LNLS": "Total loans and leases (gross)",
            "LNLSNET": "Net loans and leases (after allowance)",
            "LNCI": "Commercial and industrial loans",
            "LNAG": "Agricultural loans",
            "LNRE": "Total real estate loans",
            "LNRECONS": "Real estate construction and land development",
            "LNRELOC": "1-4 family residential real estate",
            "LNCON": "Total consumer loans",
            "LNAUTO": "Automobile loans",
            "LNCRCD": "Credit card loans"
        }
    },
    "credit_quality": {
        "description": "Asset quality metrics including allowances, nonperforming loans, and charge-offs",
        "use_cases": ["Credit risk assessment", "Asset quality trends", "Loss provision analysis"],
        "key_fields": ["LNATRES", "NPTLA", "ELNATR", "DRLNLS", "CRLNLS", "ELNLOS"],
        "field_details": {
            "LNATRES": "Allowance for loan and lease losses (adjusted)",
            "NPTLA": "Nonperforming loans to total loans ratio (%)",
            "ELNATR": "Provisions for credit losses",
            "DRLNLS": "Total loan and lease charge-offs",
            "CRLNLS": "Total loan and lease recoveries",
            "ELNLOS": "Provisions for loan and lease losses"
        }
    },
    "interest_income": {
        "description": "Interest income by source including loans, securities, and fed funds",
        "use_cases": ["Revenue analysis", "Yield analysis", "Income source diversification"],
        "key_fields": ["INTINC", "ILNDOM", "ILNFOR", "ILS", "ISC", "ICHBAL", "IFREPO", "IOTHII"],
        "field_details": {
            "INTINC": "Total interest income",
            "ILNDOM": "Interest income on domestic loans",
            "ILNFOR": "Interest income on foreign loans", 
            "ILS": "Lease financing income",
            "ISC": "Securities interest income",
            "ICHBAL": "Interest on deposits at other institutions",
            "IFREPO": "Fed funds sold and repo interest income",
            "IOTHII": "Other interest income"
        }
    },
    "interest_expense": {
        "description": "Interest expense by source including deposits and borrowings",
        "use_cases": ["Cost of funds analysis", "Interest rate sensitivity", "Funding cost management"],
        "key_fields": ["EINTEXP", "EDEPDOM", "EDEPFOR", "EFREPP", "EFHLBADV", "EMTGLS", "ESUBND"],
        "field_details": {
            "EINTEXP": "Total interest expense",
            "EDEPDOM": "Interest expense on domestic deposits",
            "EDEPFOR": "Interest expense on foreign deposits",
            "EFREPP": "Fed funds purchased and repo interest expense",
            "EFHLBADV": "FHLB advances interest expense",
            "EMTGLS": "Mortgage debt interest expense",
            "ESUBND": "Subordinated notes interest expense"
        }
    },
    "noninterest_income_expense": {
        "description": "Fee income and operating expenses excluding interest",
        "use_cases": ["Operating efficiency", "Fee income analysis", "Expense management"],
        "key_fields": ["ISERCHG", "IOTHFEE", "IGLSEC", "ESAL", "EPREMAGG", "EOTHNINT", "EAMINTAN"],
        "field_details": {
            "ISERCHG": "Service charges on deposit accounts",
            "IOTHFEE": "Other fee income",
            "IGLSEC": "Securities gains and losses",
            "ESAL": "Salaries and employee benefits",
            "EPREMAGG": "Premises and equipment expense",
            "EOTHNINT": "Other noninterest expense",
            "EAMINTAN": "Amortization of intangible assets"
        }
    },
    "profitability": {
        "description": "Earnings metrics and profitability ratios",
        "use_cases": ["Performance analysis", "Return metrics", "Profitability trends"],
        "key_fields": ["NETINC", "INTINC", "EINTEXP", "NETINTINC", "ELNATR", "ROA", "ROE", "ROAPTX"],
        "field_details": {
            "NETINC": "Net income after taxes",
            "INTINC": "Total interest income",
            "EINTEXP": "Total interest expense",
            "NETINTINC": "Net interest income",
            "ELNATR": "Provision for credit losses",
            "ROA": "Return on assets (%)",
            "ROE": "Return on equity (%)",
            "ROAPTX": "Pre-tax return on assets (%)"
        }
    },
    "capital_ratios": {
        "description": "Regulatory capital ratios and capital components",
        "use_cases": ["Capital adequacy", "Regulatory compliance", "Capital strength assessment"],
        "key_fields": ["EQ", "TIER1CAP", "TOTCAP", "RWAJCET1", "CET1R", "TIER1R", "TOTCAPR"],
        "field_details": {
            "EQ": "Total equity capital",
            "TIER1CAP": "Tier 1 capital",
            "TOTCAP": "Total capital",
            "RWAJCET1": "Risk-weighted assets for CET1 ratio",
            "CET1R": "Common Equity Tier 1 capital ratio (%)",
            "TIER1R": "Tier 1 capital ratio (%)",
            "TOTCAPR": "Total capital ratio (%)"
        }
    },
    "efficiency_metrics": {
        "description": "Operating efficiency and productivity ratios",
        "use_cases": ["Operational efficiency", "Cost management", "Productivity analysis"],
        "key_fields": ["ASSET", "NETINC", "EINTEXP", "INTINC", "ESAL", "EPREMAGG", "INTEXPY"],
        "field_details": {
            "ASSET": "Total assets for efficiency calculations",
            "NETINC": "Net income for productivity ratios",
            "EINTEXP": "Interest expense for spread analysis",
            "INTINC": "Interest income for margin calculations",
            "ESAL": "Personnel costs",
            "EPREMAGG": "Premises and equipment costs",
            "INTEXPY": "Interest expense to earning assets ratio (%)"
        }
    },
    "institution_identification": {
        "description": "Core identification and reporting date information",
        "use_cases": ["Data validation", "Report period verification", "Institution tracking"],
        "key_fields": ["CERT", "REPDTE", "REPYEAR", "CALLYM", "CALLFORM"],
        "field_details": {
            "CERT": "FDIC Certificate Number - unique institution identifier",
            "REPDTE": "Report date - last day of financial reporting period",
            "REPDTE_RAW": "Report date in raw format",
            "REPYEAR": "Four-digit report year",
            "RISDATE": "Report date in CCYYMM format",
            "CALLYM": "Call report year-month (CCYYMM)",
            "CALLFORM": "Call form number - type of regulatory form filed",
            "ACTEVT": "Activity event code (merger/closing codes)"
        }
    },
    "institution_classification": {
        "description": "Institution status and classification codes",
        "use_cases": ["Institution categorization", "Status verification", "Regulatory classification"],
        "key_fields": ["ACTIVE", "BKCLASS", "INSTTYPE", "CLOSED", "FAILED"],
        "field_details": {
            "ACTIVE": "Active institution flag (1=active, 0=inactive)",
            "CLOSED": "Closed institution flag (1=closed, 0=open)",
            "FAILED": "Failed institution flag (includes assisted mergers)",
            "BKCLASS": "Institution class (N=National, SM=State Member, etc.)",
            "CLCODE": "Detailed numeric classification code (3-93 range)",
            "ENTTYPE": "Entity type - major category indicator",
            "INSTTYPE": "Descriptive institution type"
        }
    },
    "charter_regulatory": {
        "description": "Charter authority and regulatory oversight information",
        "use_cases": ["Regulatory oversight analysis", "Charter authority identification", "Federal vs state regulation"],
        "key_fields": ["CHRTAGNT", "FEDCHRTR", "FRSMEM", "CONSERVE"],
        "field_details": {
            "CHRTAGNT": "Charter agent - entity that granted the charter",
            "FEDCHRTR": "Federal charter flag (1=federal, 0=state)",
            "FORCHRTR": "Foreign charter flag",
            "CONSERVE": "RTC conservatorship flag",
            "FRSMEM": "Federal Reserve System membership",
            "FORMCFR": "Commercial Financial Report filing requirement"
        }
    },
    "insurance_classification": {
        "description": "Deposit insurance status and fund membership",
        "use_cases": ["Insurance coverage verification", "Fund membership analysis", "Risk assessment"],
        "key_fields": ["INSFDIC", "INSDIF", "INSCOML", "INSSAVE"],
        "field_details": {
            "INSALL": "General insured institution flag",
            "INSFDIC": "FDIC insured flag",
            "INSDIF": "Deposit Insurance Fund membership",
            "INSBIF": "Former Bank Insurance Fund membership",
            "INSSAIF": "Former SAIF membership",
            "INSCOML": "Insured commercial bank flag",
            "INSSAVE": "Insured savings institution flag",
            "INSNONE": "Not federally insured flag"
        }
    },
    "specialized_institution_types": {
        "description": "Special institution designations and business focus indicators",
        "use_cases": ["Community bank identification", "Specialty classification", "Business model analysis"],
        "key_fields": ["CB", "MINORITY", "MUTUAL", "INSTAG", "INSTCRCD"],
        "field_details": {
            "CB": "Community bank classification",
            "CBLRIND": "Community bank ratio indicator",
            "DENOVO": "De novo institution flag (new, not recharter)",
            "IBA": "International Banking Act entity flag",
            "INSTAG": "Agricultural lending specialization",
            "INSTCRCD": "Credit card specialization indicator",
            "MINORITY": "Minority owned institution flag",
            "MUTUAL": "Mutual vs stock ownership (1=mutual)",
            "TRUST": "Trust powers codes (00-31 range)",
            "SUBCHAPS": "Subchapter S corporation election"
        }
    },
    "geographic_information": {
        "description": "Location and geographic market information",
        "use_cases": ["Market analysis", "Geographic concentration", "Regional studies"],
        "key_fields": ["ADDRESS", "CBSANAME", "STMULT", "CNTYNUM"],
        "field_details": {
            "ADDRESS": "Physical street address",
            "CNTRYALP": "FIPS country code (alphabetic)",
            "CNTRYNUM": "FIPS country number",
            "CNTYNUM": "FIPS county number",
            "CBSANAME": "Core Based Statistical Area name",
            "CBSADIV": "CBSA division number",
            "CSA": "Combined Statistical Area designation",
            "STMULT": "Multi-state operations flag"
        }
    },
    "fdic_administrative": {
        "description": "FDIC administrative regions and supervisory assignments",
        "use_cases": ["Supervisory analysis", "Regional grouping", "FDIC organization structure"],
        "key_fields": ["FDICDBS", "FDICSUPV", "FED", "FLDOFF"],
        "field_details": {
            "FDICDBS": "FDIC geographic region number",
            "FDICDBSDESC": "FDIC geographic region name",
            "FDICSUPV": "FDIC supervisory region number",
            "FDICSUPVDESC": "FDIC supervisory region name",
            "FED": "Federal Reserve district number (1-12)",
            "FEDDESC": "Federal Reserve district name",
            "FLDOFF": "FDIC Risk Management field office",
            "FDICAREA": "FDIC compliance area identifier"
        }
    },
    "securities_investments": {
        "description": "Securities holdings and short-term investment activities",
        "use_cases": ["Liquidity analysis", "Investment portfolio", "Short-term funding"],
        "key_fields": ["FREPO", "FREPOR", "FREPP", "FREPPR"],
        "field_details": {
            "FREPO": "Federal funds sold and repurchase agreements",
            "FREPOR": "Fed funds & repos sold ratio (% of assets)",
            "FREPP": "Federal funds purchased and repos",
            "FREPPR": "Fed funds & repos purchased ratio (% of assets)"
        }
    },
    "allowance_credit_losses": {
        "description": "Allowance for credit losses and risk reserves",
        "use_cases": ["Credit risk assessment", "Loss reserve analysis", "CECL implementation"],
        "key_fields": ["LNATRES", "LNATRESJ", "LNATRESRR"],
        "field_details": {
            "LNATRES": "Allowance for loan losses (adjusted)",
            "LNATRESJ": "Allowance for loans plus allocated transfer risk",
            "LNATRESRR": "Allowance plus transfer risk ratio"
        }
    },
    "borrowings_liabilities": {
        "description": "Non-deposit liabilities and borrowing arrangements",
        "use_cases": ["Funding diversification", "Liability composition", "Borrowing analysis"],
        "key_fields": ["LIAB", "LIPMTG", "CUSLI", "ACEPT"],
        "field_details": {
            "LIAB": "Total liabilities",
            "LIABR": "Total liabilities ratio",
            "LIABEQ": "Total liabilities and capital",
            "LIPMTG": "Mortgage loans in process",
            "CUSLI": "Customer acceptances outstanding",
            "ACEPT": "Bank's liability on acceptances"
        }
    },
    "equity_capital_components": {
        "description": "Detailed breakdown of equity capital components",
        "use_cases": ["Capital structure analysis", "Equity composition", "Capital adequacy details"],
        "key_fields": ["EQ", "EQCS", "EQSUR", "EQPP", "EQUPTOT"],
        "field_details": {
            "EQ": "Total equity capital",
            "EQCS": "Common stock issued",
            "EQSUR": "Capital surplus",
            "EQPP": "Perpetual preferred stock",
            "LLPFDSTK": "Limited-life preferred stock",
            "EQCONSUB": "Minority interest in subsidiaries",
            "EQUPTOT": "Undivided profits and other capital",
            "EQCFCTA": "Cumulative foreign currency adjustments"
        }
    },
    "provision_credit_losses": {
        "description": "Credit loss provisions and expense recognition",
        "use_cases": ["Credit cost analysis", "Loss provisioning trends", "Earnings impact"],
        "key_fields": ["ELNATR", "ELNLOS", "ELNATQ"],
        "field_details": {
            "ELNATR": "Provisions for credit losses",
            "ELNATRR": "Provisions for credit losses ratio",
            "ELNATQ": "Provisions for credit losses quarterly",
            "ELNLOS": "Provisions for loan and lease losses",
            "ELNLOSQ": "Loan loss provisions quarterly ratio"
        }
    },
    "charge_offs_recoveries": {
        "description": "Actual charge-offs and recoveries on loans",
        "use_cases": ["Credit loss realization", "Recovery analysis", "Net charge-off trends"],
        "key_fields": ["DRLNLS", "CRLNLS", "DRLNLSQ", "CRLNLSQ"],
        "field_details": {
            "DRLNLS": "Total loan and lease charge-offs (YTD)",
            "DRLNLSR": "Charge-offs ratio (% of assets)",
            "DRLNLSQ": "Charge-offs quarterly",
            "CRLNLS": "Total loan and lease recoveries (YTD)",
            "CRLNLSR": "Recoveries ratio (% of assets)",
            "CRLNLSQ": "Recoveries quarterly"
        }
    },
    "net_income_components": {
        "description": "Detailed net income components and tax information",
        "use_cases": ["Earnings analysis", "Tax efficiency", "Pre/post-tax performance"],
        "key_fields": ["NETINC", "IBEFTAX", "ITAX", "EXTRA"],
        "field_details": {
            "IBEFTAX": "Income before taxes and discontinued operations",
            "ITAX": "Applicable income taxes",
            "NETINC": "Net income after taxes",
            "NETINCQ": "Net income quarterly",
            "EXTRA": "Net discontinued operations",
            "EXTRAQ": "Discontinued operations quarterly"
        }
    },
    "performance_ratios": {
        "description": "Key performance and profitability ratios",
        "use_cases": ["Performance benchmarking", "Profitability analysis", "Return metrics"],
        "key_fields": ["ROA", "ROE", "ROAPTX", "INTEXPY"],
        "field_details": {
            "ROA": "Return on assets (%)",
            "ROAQ": "Quarterly return on assets",
            "ROAPTX": "Pre-tax return on assets",
            "ROE": "Return on equity (%)",
            "ROEQ": "Quarterly return on equity",
            "INTEXPY": "Interest expense to earning assets ratio"
        }
    },
    "dividend_information": {
        "description": "Dividend payments and distribution policies",
        "use_cases": ["Capital distribution analysis", "Dividend policy", "Shareholder returns"],
        "key_fields": ["EQCDIV", "EQCDIVC", "EQCDIVP"],
        "field_details": {
            "EQCDIV": "Total cash dividends on common and preferred",
            "EQCDIVC": "Cash dividends on common stock",
            "EQCDIVP": "Cash dividends on preferred stock",
            "EQCDIVQ": "Quarterly dividends total",
            "EQCDIVR": "Dividend ratio"
        }
    },
    "office_branch_information": {
        "description": "Branch network and office distribution",
        "use_cases": ["Market presence", "Branch network analysis", "Geographic coverage"],
        "key_fields": ["BRANCH", "OFFDOM", "OFFFOR", "OFFOA"],
        "field_details": {
            "BRANCH": "Branching flag (1=has branches, 0=single office)",
            "OFFDOM": "Number of domestic offices",
            "OFFFOR": "Number of foreign offices",
            "OFFOA": "Number of US territory offices"
        }
    },
    "holding_company_information": {
        "description": "Bank holding company relationships and structure",
        "use_cases": ["Corporate structure", "Holding company analysis", "Ownership chains"],
        "key_fields": ["NAMEHCR", "RSSDHCR", "HCTMULT", "HCTONE"],
        "field_details": {
            "HCTMULT": "Multi-bank holding company flag",
            "HCTONE": "One-bank holding company member",
            "HCTNONE": "Not a holding company member",
            "NAMEHCR": "Regulatory top holder name",
            "CITYHCR": "Holding company headquarters city",
            "RSSDHCR": "RSSD ID of regulatory holding company"
        }
    },
    "specialized_business": {
        "description": "Specialized business activities and focus areas",
        "use_cases": ["Business model analysis", "Specialization identification", "Activity classification"],
        "key_fields": ["EDGECODE", "SPECGRP", "SPECGRPDESC"],
        "field_details": {
            "EDGECODE": "International activity flag (Edge Act operations)",
            "SPECGRP": "Asset concentration hierarchy indicator",
            "SPECGRPDESC": "Asset concentration description"
        }
    },
    "call_report_information": {
        "description": "Call report filing information and regulatory form details",
        "use_cases": ["Regulatory compliance", "Filing verification", "Report type identification"],
        "key_fields": ["FORM31", "DOCKET"],
        "field_details": {
            "FORM31": "FFIEC Call Report 31 filer indicator",
            "DOCKET": "OTS docket number (legacy)"
        }
    }
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
    return FIELD_SELECTION_TEMPLATES.get(analysis_type, FIELD_SELECTION_TEMPLATES["institution_profile"])


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
    analysis_requirements = {
        "institution_profile": {
            "required": ["CERT", "REPDTE", "ACTIVE", "BKCLASS"],
            "recommended": ["INSTTYPE", "CB", "CHRTAGNT", "ASSET", "OFFDOM"]
        },
        "balance_sheet_assets": {
            "required": ["CERT", "REPDTE", "ASSET", "LNLS", "DEP"],
            "recommended": ["CHBAL", "LNLSNET", "BKPREM", "INTAN", "FREPO"]
        },
        "balance_sheet_liabilities": {
            "required": ["CERT", "REPDTE", "LIAB", "DEP", "EQ"],
            "recommended": ["DEPDOM", "DEPNI", "DEPI", "BRO", "FREPP"]
        },
        "deposit_composition": {
            "required": ["CERT", "REPDTE", "DEP", "DEPDOM", "DEPNI"],
            "recommended": ["DEPI", "DDT", "CD3LES", "CD3T12", "BRO"]
        },
        "loan_portfolio": {
            "required": ["CERT", "REPDTE", "LNLS", "LNLSNET", "LNCI"],
            "recommended": ["LNAG", "LNRE", "LNCON", "LNAUTO", "LNCRCD"]
        },
        "credit_quality": {
            "required": ["CERT", "REPDTE", "LNLS", "LNATRES", "NPTLA"],
            "recommended": ["ELNATR", "DRLNLS", "CRLNLS", "ELNLOS"]
        },
        "interest_income": {
            "required": ["CERT", "REPDTE", "INTINC", "ILNDOM"],
            "recommended": ["ILNFOR", "ILS", "ISC", "ICHBAL", "IFREPO"]
        },
        "interest_expense": {
            "required": ["CERT", "REPDTE", "EINTEXP", "EDEPDOM"],
            "recommended": ["EDEPFOR", "EFREPP", "EFHLBADV", "EMTGLS"]
        },
        "noninterest_income_expense": {
            "required": ["CERT", "REPDTE", "ISERCHG", "ESAL"],
            "recommended": ["IOTHFEE", "IGLSEC", "EPREMAGG", "EOTHNINT"]
        },
        "profitability": {
            "required": ["CERT", "REPDTE", "ASSET", "EQ", "NETINC"],
            "recommended": ["INTINC", "EINTEXP", "ROA", "ROE", "ROAPTX"]
        },
        "capital_ratios": {
            "required": ["CERT", "REPDTE", "EQ", "ASSET", "CET1R"],
            "recommended": ["TIER1CAP", "TOTCAP", "TIER1R", "TOTCAPR"]
        },
        "efficiency_metrics": {
            "required": ["CERT", "REPDTE", "ASSET", "NETINC", "EINTEXP"],
            "recommended": ["INTINC", "ESAL", "EPREMAGG", "INTEXPY"]
        },
        "institution_identification": {
            "required": ["CERT", "REPDTE", "REPYEAR"],
            "recommended": ["CALLYM", "CALLFORM", "ACTEVT", "RISDATE"]
        },
        "institution_classification": {
            "required": ["CERT", "REPDTE", "ACTIVE", "BKCLASS"],
            "recommended": ["INSTTYPE", "CLCODE", "ENTTYPE", "CLOSED", "FAILED"]
        },
        "charter_regulatory": {
            "required": ["CERT", "REPDTE", "CHRTAGNT", "FEDCHRTR"],
            "recommended": ["FORCHRTR", "CONSERVE", "FRSMEM", "FORMCFR"]
        },
        "insurance_classification": {
            "required": ["CERT", "REPDTE", "INSFDIC", "INSDIF"],
            "recommended": ["INSALL", "INSCOML", "INSSAVE", "INSNONE"]
        },
        "specialized_institution_types": {
            "required": ["CERT", "REPDTE", "CB", "MINORITY"],
            "recommended": ["MUTUAL", "INSTAG", "INSTCRCD", "TRUST", "DENOVO"]
        },
        "geographic_information": {
            "required": ["CERT", "REPDTE", "ADDRESS", "CNTYNUM"],
            "recommended": ["CBSANAME", "STMULT", "CSA", "CBSADIV"]
        },
        "fdic_administrative": {
            "required": ["CERT", "REPDTE", "FDICDBS", "FED"],
            "recommended": ["FDICSUPV", "FLDOFF", "FDICAREA", "FDICTERR"]
        },
        "securities_investments": {
            "required": ["CERT", "REPDTE", "FREPO", "FREPP"],
            "recommended": ["FREPOR", "FREPPR"]
        },
        "allowance_credit_losses": {
            "required": ["CERT", "REPDTE", "LNATRES"],
            "recommended": ["LNATRESJ", "LNATRESRR"]
        },
        "borrowings_liabilities": {
            "required": ["CERT", "REPDTE", "LIAB", "LIABEQ"],
            "recommended": ["LIPMTG", "CUSLI", "ACEPT", "LIABR"]
        },
        "equity_capital_components": {
            "required": ["CERT", "REPDTE", "EQ", "EQCS", "EQSUR"],
            "recommended": ["EQPP", "EQUPTOT", "EQCONSUB", "EQCFCTA"]
        },
        "provision_credit_losses": {
            "required": ["CERT", "REPDTE", "ELNATR", "ELNLOS"],
            "recommended": ["ELNATQ", "ELNLOSQ", "ELNATRR", "ELNATQA"]
        },
        "charge_offs_recoveries": {
            "required": ["CERT", "REPDTE", "DRLNLS", "CRLNLS"],
            "recommended": ["DRLNLSQ", "CRLNLSQ", "DRLNLSR", "CRLNLSR"]
        },
        "net_income_components": {
            "required": ["CERT", "REPDTE", "NETINC", "IBEFTAX", "ITAX"],
            "recommended": ["NETINCQ", "EXTRA", "EXTRAQ", "NETINCR"]
        },
        "performance_ratios": {
            "required": ["CERT", "REPDTE", "ROA", "ROE"],
            "recommended": ["ROAQ", "ROEQ", "ROAPTX", "INTEXPY"]
        },
        "dividend_information": {
            "required": ["CERT", "REPDTE", "EQCDIV"],
            "recommended": ["EQCDIVC", "EQCDIVP", "EQCDIVQ", "EQCDIVR"]
        },
        "office_branch_information": {
            "required": ["CERT", "REPDTE", "OFFDOM", "BRANCH"],
            "recommended": ["OFFFOR", "OFFOA"]
        },
        "holding_company_information": {
            "required": ["CERT", "REPDTE", "HCTMULT", "HCTONE"],
            "recommended": ["NAMEHCR", "RSSDHCR", "CITYHCR", "HCTNONE"]
        },
        "specialized_business": {
            "required": ["CERT", "REPDTE", "SPECGRP"],
            "recommended": ["SPECGRPDESC", "EDGECODE"]
        },
        "call_report_information": {
            "required": ["CERT", "REPDTE", "FORM31"],
            "recommended": ["DOCKET"]
        }
    }
    
    # Get specific requirements or default to basic requirements
    requirements = analysis_requirements.get(analysis_type, {
        "required": ["CERT", "REPDTE"],
        "recommended": fields[2:] if len(fields) > 2 else []
    })
    
    return {
        "required": requirements["required"],
        "recommended": requirements["recommended"],
        "all_fields": fields
    }