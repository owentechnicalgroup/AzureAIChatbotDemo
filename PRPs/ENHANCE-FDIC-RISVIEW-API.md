name: "FDIC BankFind Suite Financial Data API Integration"
description: |

## Purpose
Integrate FDIC BankFind Suite Financial Data API (/banks/financials endpoint) to enhance bank_analysis_tool with real-time financial metrics, replacing mock Call Report data with over 1,100 actual FDIC financial variables.

## Core Principles
1. **Real Financial Data**: Replace mock data with authoritative FDIC financial metrics
2. **Performance Optimized**: Leverage existing caching and async patterns
3. **Backward Compatible**: Maintain existing tool interfaces while enhancing capabilities
4. **Comprehensive Coverage**: Support wide range of financial analysis use cases
5. **Follow CLAUDE.md**: Adhere to all established codebase patterns and conventions

---

## Goal
Enhance the existing `bank_analysis_tool` to use the FDIC BankFind Suite Financial Data API instead of mock Call Report data, providing real-time access to comprehensive financial metrics for banking institutions.

## Why
- **Real Financial Data**: Replace mock data with authoritative FDIC financial information (assets, deposits, income, ratios)
- **Comprehensive Analysis**: Access over 1,100 Call Report variables for detailed financial analysis
- **Current Data**: Provide up-to-date quarterly financial metrics for accurate analysis
- **Enhanced AI Capabilities**: Enable AI agent to perform sophisticated financial analysis using real data
- **Regional Analysis**: Support geographic and peer analysis using CBSA codes and classifications

## What
Transform the bank_analysis_tool to integrate with FDIC's Financial Data API while maintaining LangChain compatibility and existing architectural patterns.

### Success Criteria
- [ ] Bank analysis uses real FDIC financial data via /financials API endpoint
- [ ] Support for comprehensive financial metrics (assets, deposits, income, ratios, capital)
- [ ] Enhanced financial_summary with multiple real data points
- [ ] Improved key_ratios analysis with calculated ratios from real data  
- [ ] Historical data analysis capability
- [ ] Geographic and peer analysis features
- [ ] Secure API key management using existing patterns
- [ ] Backward compatibility with existing tool interfaces
- [ ] Proper error handling and service availability checking
- [ ] Performance optimization through caching

## All Needed Context

### Documentation & References
```yaml
- url: https://banks.data.fdic.gov/docs/
  why: Primary FDIC BankFind Suite API documentation with interactive examples
  
- url: https://api.fdic.gov/banks/docs/swagger.yaml
  why: Complete OpenAPI specification for /financials endpoint with parameters and responses
  
- url: https://api.fdic.gov/banks/docs/risview_properties.yaml  
  why: Complete field definitions for financial data variables (ASSET, DEP, NETINC, ROA, etc.)
  
- file: src/tools/infrastructure/banking/fdic_api_client.py
  why: Existing FDIC API client pattern, HTTP client implementation, caching patterns
  
- file: src/tools/infrastructure/banking/fdic_models.py
  why: Pydantic model patterns for FDIC data, validation approaches
  
- file: src/tools/infrastructure/banking/banking_models.py
  why: Financial data model patterns, CallReportAPIResponse structure to mirror
  
- file: src/tools/composite/bank_analysis_tool.py
  why: Current implementation using mock data, integration patterns to enhance
  
- file: src/tools/infrastructure/banking/call_report_api.py
  why: API client patterns for financial data, async execution, error handling
  
- file: src/tools/dynamic_loader.py
  why: Service availability checking patterns, tool loading logic
  
- file: tests/tools/fdic/test_fdic_api_client.py
  why: Testing patterns for FDIC API clients using aioresponses
  
- file: src/config/settings.py
  why: API key management patterns, secure configuration handling
```

### Current Codebase Structure
```bash
src/
├── tools/
│   ├── atomic/
│   │   └── bank_lookup_tool.py          # Uses existing FDIC API
│   ├── composite/
│   │   └── bank_analysis_tool.py        # TARGET - needs financial data integration
│   ├── infrastructure/
│   │   ├── banking/
│   │   │   ├── fdic_api_client.py       # Existing FDIC client (institutions)
│   │   │   ├── fdic_models.py           # Existing FDIC models
│   │   │   ├── fdic_constants.py        # Existing FDIC constants
│   │   │   ├── banking_models.py        # Financial data model patterns
│   │   │   └── call_report_api.py       # Mock data client to replace
│   │   └── toolsets/
│   │       └── banking_toolset.py       # Tool registration
│   ├── dynamic_loader.py                # Service availability checking
│   └── categories.py                    # Tool categorization
├── config/
│   └── settings.py                      # API key management
└── tests/
    └── tools/
        ├── fdic/
        │   ├── test_fdic_api_client.py  # Existing FDIC test patterns
        │   └── test_enhanced_bank_tools.py
        └── call_report/
            └── test_langchain_tools.py # Test patterns to mirror
```

### Desired Codebase Structure (New/Modified Files)
```bash
src/tools/infrastructure/banking/
├── fdic_financial_api.py        # NEW - FDIC Financial Data API client
├── fdic_financial_models.py     # NEW - Financial data response models
└── fdic_financial_constants.py  # NEW - Financial field mappings

# Modified existing files:
src/tools/composite/bank_analysis_tool.py  # ENHANCED - integrate financial API
src/tools/dynamic_loader.py                # ENHANCED - add financial API checker
src/config/settings.py                     # ENHANCED - financial API config

tests/tools/fdic/
├── test_fdic_financial_api.py      # NEW - Financial API client tests
├── test_fdic_financial_models.py   # NEW - Financial models tests
└── test_enhanced_bank_analysis.py  # NEW - Enhanced analysis tool tests
```

### Known Gotchas & Library Quirks
```python
# CRITICAL: FDIC BankFind Suite API uses specific endpoint structure
# Financial API: https://banks.data.fdic.gov/api/financials
# NOT https://api.fdic.gov/banks/financials (this is different API)

# CRITICAL: Financial API uses Elasticsearch query syntax
# Filter by certificate: CERT:14
# Filter by date range: REPDTE:[2023-01-01 TO 2023-12-31]
# Filter by asset range: ASSET:[1000000 TO 9999999]

# CRITICAL: API currently doesn't require authentication but may in future
# Use same fdic_api_key from settings as the institution lookup tool

# CRITICAL: Financial data has over 1,100 fields - need field selection
# Common fields: ASSET, DEP, NETINC, ROA, ROE, INTINC, EINTEXP
# Use 'fields' parameter to limit response size and improve performance

# CRITICAL: Response format differs from institution API
# Returns: {metadata: {...}, data: [{CERT: "123", ASSET: 1000, ...}]}
# Need separate models for financial responses vs institution responses

# GOTCHA: Financial data is quarterly - REPDTE field shows report date
# Most recent quarter may not be current quarter (reporting lag)
# Need to handle date filtering for historical vs current analysis

# GOTCHA: Not all banks report all fields - many will be null/missing
# Need robust null handling and graceful degradation for missing data

# GOTCHA: Financial values in thousands - need to convert for display
# ASSET: 1000 = $1 million, not $1,000

# CRITICAL: Maintain existing async patterns and caching
# Follow existing fdic_api_client caching patterns for performance
# Use aiohttp ClientSession with proper timeout handling

# CRITICAL: Error handling for FDIC-specific responses
# API returns 200 with error in response body for some failures
# Check response.data for error messages in addition to HTTP status

# TESTING: Use aioresponses for HTTP mocking consistently
# Mock financial API responses separately from institution API responses
# Include realistic financial data in test fixtures

# INTEGRATION: Remove call_report_api from bank_analysis_tool
# Replace self._api_client (CallReportMockAPI) with new financial API client
# Maintain same interface methods for backward compatibility
```

## Implementation Blueprint

### Data Models and Structure
```python
# Financial data response models mirroring existing patterns
class FDICFinancialData(BaseModel):
    cert: str                           # FDIC Certificate number
    repdte: date                        # Report date
    asset: Optional[Decimal]            # Total assets (in thousands)
    dep: Optional[Decimal]              # Total deposits
    netinc: Optional[Decimal]           # Net income
    roa: Optional[Decimal]              # Return on assets
    roe: Optional[Decimal]              # Return on equity
    intinc: Optional[Decimal]           # Interest income
    eintexp: Optional[Decimal]          # Interest expense
    eq: Optional[Decimal]               # Equity capital
    lnls: Optional[Decimal]             # Loans and leases

class FDICFinancialAPIResponse(BaseModel):
    success: bool
    data: List[FDICFinancialData]
    metadata: Optional[Dict]
    error_message: Optional[str]
    
# Enhanced input schemas for financial analysis
class BankFinancialAnalysisInput(BaseModel):
    cert_id: Optional[str] = Field(description="FDIC Certificate number")
    analysis_type: str = Field(description="Type of analysis: basic_info, financial_summary, key_ratios")
    report_date: Optional[str] = Field(description="Specific report date (YYYY-MM-DD)")
    historical_quarters: int = Field(default=1, description="Number of quarters of historical data")
```

### Task List (In Order)

```yaml
Task 1: Create FDIC Financial Data Infrastructure
CREATE src/tools/infrastructure/banking/fdic_financial_constants.py:
  - DEFINE FDIC Financial API base URL: https://banks.data.fdic.gov/api/financials
  - CREATE field mappings for common financial metrics
  - ADD query templates for different analysis types
  - DEFINE financial field display formats (thousands to millions/billions)

CREATE src/tools/infrastructure/banking/fdic_financial_models.py:
  - MIRROR pattern from: banking_models.py and fdic_models.py
  - IMPLEMENT FDICFinancialData with comprehensive field definitions
  - IMPLEMENT FDICFinancialAPIResponse following existing response patterns
  - ADD validation for financial values and date ranges
  - INCLUDE field conversion helpers (thousands to display values)

CREATE src/tools/infrastructure/banking/fdic_financial_api.py:
  - MIRROR pattern from: fdic_api_client.py and call_report_api.py
  - IMPLEMENT async HTTP client using aiohttp (existing pattern)
  - ADD get_financial_data() method with filtering and field selection
  - INCLUDE response caching using existing cache patterns
  - IMPLEMENT FDIC-specific error handling (200 responses with errors)
  - ADD financial field selection optimization (limit to requested metrics)
  - PRESERVE existing logging and async patterns

Task 2: Enhance Configuration
MODIFY src/config/settings.py:
  - FIND: FDIC API configuration section (around fdic_api_key)
  - ENSURE: fdic_api_key supports both institution and financial endpoints
  - ADD: fdic_financial_api_timeout and fdic_financial_cache_ttl if needed
  - PRESERVE: existing security patterns for API keys

Task 3: Update Service Availability Checking
MODIFY src/tools/dynamic_loader.py:
  - FIND: _initialize_service_checkers method (around line 60-72)
  - ADD: "fdic_financial_api" to service checkers mapping
  - IMPLEMENT: _check_fdic_financial_api_availability() async method
  - TEST: financial API endpoint connectivity and response validation

Task 4: Enhance Bank Analysis Tool with Real Financial Data
MODIFY src/tools/composite/bank_analysis_tool.py:
  - REPLACE: CallReportMockAPI import with FDICFinancialAPI
  - UPDATE: __init__ method to use FDICFinancialAPI instead of CallReportMockAPI
  - ENHANCE: _get_basic_info to include real asset data and basic metrics
  - TRANSFORM: _get_financial_summary to query multiple real financial fields
  - UPGRADE: _get_key_ratios to calculate actual ratios from FDIC data
  - ADD: historical data analysis capability
  - PRESERVE: existing LangChain BaseTool interface and async patterns
  - MAINTAIN: backward compatibility for existing parameters

Task 5: Implement Financial Data Analysis Methods
ENHANCE src/tools/composite/bank_analysis_tool.py methods:
  - _get_basic_info: Query ASSET, DEP, basic identification data
  - _get_financial_summary: Query ASSET, DEP, NETINC, INTINC, EINTEXP, EQ
  - _get_key_ratios: Calculate ROA, ROE, Net Interest Margin, Efficiency Ratio
  - ADD: _get_historical_analysis for multi-quarter trend analysis
  - ADD: _format_financial_value helper for thousands/millions/billions display
  - ADD: _calculate_financial_ratios for derived metrics

Task 6: Create Comprehensive Tests
CREATE tests/tools/fdic/test_fdic_financial_api.py:
  - MIRROR: test patterns from test_fdic_api_client.py
  - IMPLEMENT: HTTP response mocking using aioresponses
  - TEST: financial data retrieval with various filters
  - TEST: error handling for API failures and invalid responses
  - TEST: caching behavior and performance optimization

CREATE tests/tools/fdic/test_fdic_financial_models.py:
  - TEST: financial data model validation and field conversion
  - TEST: date range validation and financial value bounds
  - TEST: null value handling for missing financial data

CREATE tests/tools/fdic/test_enhanced_bank_analysis.py:
  - TEST: enhanced bank analysis tool with real financial data
  - TEST: all analysis types (basic_info, financial_summary, key_ratios)
  - TEST: backward compatibility with existing interfaces
  - TEST: historical analysis and trend calculations

Task 7: Update Tool Registration and Documentation
MODIFY src/tools/infrastructure/toolsets/banking_toolset.py:
  - UPDATE: tool descriptions to reflect real financial data capabilities
  - PRESERVE: existing LangChain tool registration patterns
  - ENHANCE: tool metadata to indicate financial data availability

UPDATE tool description in bank_analysis_tool.py:
  - EMPHASIZE: real FDIC financial data capabilities
  - INCLUDE: examples of financial analysis use cases
  - SPECIFY: supported financial metrics and ratios
  - MENTION: historical analysis and trend capabilities
```

### Task 4 Pseudocode - Enhanced Financial Analysis
```python
# Enhanced bank_analysis_tool.py with real FDIC financial data
class BankAnalysisTool(BaseTool):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # REPLACE mock API with real FDIC financial API
        object.__setattr__(self, '_financial_client', FDICFinancialAPI())
        object.__setattr__(self, '_bank_lookup', BankLookupTool())

    async def _get_financial_summary(self, bank_info: Dict, cert_id: str) -> str:
        """Get comprehensive financial summary with real FDIC data."""
        try:
            # PATTERN: Query multiple financial fields efficiently
            financial_fields = [
                "ASSET",     # Total assets
                "DEP",       # Total deposits  
                "NETINC",    # Net income
                "INTINC",    # Interest income
                "EINTEXP",   # Interest expense
                "EQ",        # Equity capital
                "LNLS"       # Loans and leases
            ]
            
            # CRITICAL: Use efficient field selection to limit response size
            financial_data = await self.financial_client.get_financial_data(
                cert_id=cert_id,
                fields=financial_fields,
                quarters=1  # Most recent quarter
            )
            
            if not financial_data.success or not financial_data.data:
                return f"Error: Financial data not available for certificate {cert_id}"
            
            # Get most recent quarter data
            latest_data = financial_data.data[0]  # Sorted by date desc
            
            # PATTERN: Convert thousands to display format
            def format_financial(value_in_thousands):
                if value_in_thousands is None:
                    return "Not available"
                if value_in_thousands >= 1_000_000:
                    return f"${value_in_thousands/1_000_000:.1f}B"
                elif value_in_thousands >= 1_000:
                    return f"${value_in_thousands/1_000:.1f}M"
                else:
                    return f"${value_in_thousands}K"
            
            return f"""Bank Analysis - Financial Summary:

Bank: {bank_info.get('name', 'Unknown')}
FDIC Certificate: {cert_id}
Report Date: {latest_data.repdte}

Financial Metrics:
- Total Assets: {format_financial(latest_data.asset)}
- Total Deposits: {format_financial(latest_data.dep)}
- Total Loans & Leases: {format_financial(latest_data.lnls)}
- Equity Capital: {format_financial(latest_data.eq)}

Income Statement:
- Net Income: {format_financial(latest_data.netinc)}
- Interest Income: {format_financial(latest_data.intinc)}
- Interest Expense: {format_financial(latest_data.eintexp)}

Data Source: FDIC BankFind Suite Financial API
Analysis Type: Financial Summary"""
            
        except Exception as e:
            self.logger.error("Financial summary failed", error=str(e))
            return f"Error retrieving financial summary: {str(e)}"

    async def _get_key_ratios(self, bank_info: Dict, cert_id: str) -> str:
        """Calculate key financial ratios from real FDIC data."""
        try:
            # Query specific fields needed for ratio calculations
            ratio_fields = ["ASSET", "EQ", "NETINC", "INTINC", "EINTEXP"]
            
            financial_data = await self.financial_client.get_financial_data(
                cert_id=cert_id,
                fields=ratio_fields,
                quarters=1
            )
            
            if not financial_data.success or not financial_data.data:
                return f"Error: Financial data not available for ratio calculation"
                
            data = financial_data.data[0]
            
            # CRITICAL: Handle null values gracefully
            def calculate_ratio(numerator, denominator, format_as_percent=True):
                if numerator is None or denominator is None or denominator == 0:
                    return "Not available"
                ratio = float(numerator) / float(denominator)
                if format_as_percent:
                    return f"{ratio * 100:.2f}%"
                return f"{ratio:.4f}"
            
            # Calculate key ratios
            roa = calculate_ratio(data.netinc, data.asset)  # Return on Assets
            roe = calculate_ratio(data.netinc, data.eq)     # Return on Equity
            nim = calculate_ratio(
                (data.intinc or 0) - (data.eintexp or 0), 
                data.asset
            )  # Net Interest Margin
            
            return f"""Bank Analysis - Key Financial Ratios:

Bank: {bank_info.get('name', 'Unknown')}
FDIC Certificate: {cert_id}
Report Date: {data.repdte}

Profitability Ratios:
- Return on Assets (ROA): {roa}
- Return on Equity (ROE): {roe}
- Net Interest Margin (NIM): {nim}

Capital Ratios:
- Equity to Assets: {calculate_ratio(data.eq, data.asset)}

Data Source: FDIC BankFind Suite Financial API
Analysis Type: Key Financial Ratios"""
            
        except Exception as e:
            return f"Error calculating financial ratios: {str(e)}"
```

### Task 1 Pseudocode - FDIC Financial API Client
```python
# src/tools/infrastructure/banking/fdic_financial_api.py
class FDICFinancialAPI:
    def __init__(self, api_key: Optional[str] = None, timeout: float = 30.0):
        self.api_key = api_key
        self.base_url = "https://banks.data.fdic.gov/api"
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        # PATTERN: Use existing cache pattern from fdic_api_client.py
        self.cache = FDICAPICache(default_ttl_seconds=1800)  # 30 min cache
    
    async def get_financial_data(
        self,
        cert_id: Optional[str] = None,
        filters: Optional[str] = None,
        fields: Optional[List[str]] = None,
        quarters: int = 1,
        report_date: Optional[str] = None
    ) -> FDICFinancialAPIResponse:
        """
        Get financial data from FDIC BankFind Suite Financial API.
        
        Args:
            cert_id: FDIC certificate number for specific bank
            filters: Additional Elasticsearch query filters
            fields: Specific fields to retrieve (performance optimization)
            quarters: Number of recent quarters (default 1)
            report_date: Specific report date filter
            
        Returns:
            FDICFinancialAPIResponse with financial data
        """
        # PATTERN: Build query parameters using existing patterns
        params = {
            "format": "json",
            "sort_by": "REPDTE", 
            "sort_order": "DESC",
            "limit": min(quarters * 10, 100)  # Multiple quarters, multiple institutions
        }
        
        # Build filters
        filter_parts = []
        if cert_id:
            filter_parts.append(f"CERT:{cert_id}")
        if report_date:
            filter_parts.append(f"REPDTE:{report_date}")
        if filters:
            filter_parts.append(filters)
            
        if filter_parts:
            params["filters"] = " AND ".join(filter_parts)
        
        # CRITICAL: Optimize field selection for performance
        if fields:
            # Always include key identification fields
            required_fields = ["CERT", "REPDTE"]
            all_fields = list(set(required_fields + fields))
            params["fields"] = ",".join(all_fields)
        
        # Add API key if available
        if self.api_key:
            params["api_key"] = self.api_key
        
        # PATTERN: Check cache first using existing cache patterns
        cache_key = build_cache_key("financial", params)
        cached_response = self.cache.get(cache_key)
        if cached_response:
            return cached_response
        
        # CRITICAL: Use async HTTP with proper error handling
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            try:
                async with session.get(
                    f"{self.base_url}/financials", 
                    params=params
                ) as response:
                    # GOTCHA: FDIC API can return 200 with error in body
                    response.raise_for_status()
                    data = await response.json()
                    
                    # Check for API-level errors in response
                    if "error" in data:
                        raise ValueError(f"FDIC API error: {data['error']}")
                    
                    # CRITICAL: Validate response structure
                    validated_response = FDICFinancialAPIResponse(
                        success=True,
                        data=[FDICFinancialData.model_validate(item) for item in data.get("data", [])],
                        metadata=data.get("metadata", {})
                    )
                    
                    # Cache successful response
                    self.cache.put(cache_key, validated_response)
                    return validated_response
                    
            except aiohttp.ClientError as e:
                logger.error("FDIC Financial API HTTP error", error=str(e))
                return FDICFinancialAPIResponse(
                    success=False,
                    error_message=f"Failed to connect to FDIC Financial API: {str(e)}"
                )
            except Exception as e:
                logger.error("FDIC Financial API unexpected error", error=str(e))
                return FDICFinancialAPIResponse(
                    success=False,
                    error_message=f"Financial data retrieval failed: {str(e)}"
                )
```

### Integration Points
```yaml
CONFIGURATION:
  - use: existing fdic_api_key from settings.py
  - add: financial API specific timeout and cache settings if needed
  
SERVICE_AVAILABILITY:
  - add to: src/tools/dynamic_loader.py
  - checker: _check_fdic_financial_api_availability method
  - test: /financials endpoint connectivity
  
TOOL_ENHANCEMENT:
  - modify: src/tools/composite/bank_analysis_tool.py
  - replace: CallReportMockAPI with FDICFinancialAPI
  - preserve: existing LangChain BaseTool interface
```

## Validation Loop

### Level 1: Syntax & Style  
```bash
# Run these FIRST - fix any errors before proceeding
cd src/tools/infrastructure/banking/
ruff check fdic_financial_*.py --fix        # Auto-fix style issues
mypy fdic_financial_*.py                    # Type checking

cd ../../composite/
ruff check bank_analysis_tool.py --fix
mypy bank_analysis_tool.py

# Expected: No errors. If errors occur, read and fix them.
```

### Level 2: Unit Tests
```python
# tests/tools/fdic/test_fdic_financial_api.py
import pytest
from aioresponses import aioresponses
from decimal import Decimal
from datetime import date

@pytest.mark.asyncio
async def test_financial_data_retrieval():
    """Test basic financial data retrieval with real FDIC response format."""
    from src.tools.infrastructure.banking.fdic_financial_api import FDICFinancialAPI
    
    client = FDICFinancialAPI("test_api_key")
    
    # Mock realistic FDIC financial response
    mock_response = {
        "metadata": {"total": 1},
        "data": [
            {
                "CERT": "14",
                "REPDTE": "2023-12-31",
                "ASSET": 2500000,  # $2.5B in thousands
                "DEP": 2100000,    # $2.1B in deposits  
                "NETINC": 25000,   # $25M net income
                "ROA": 1.25,       # 1.25% ROA
                "ROE": 15.5        # 15.5% ROE
            }
        ]
    }
    
    with aioresponses() as mock_http:
        mock_http.get(
            'https://banks.data.fdic.gov/api/financials',
            payload=mock_response,
            status=200
        )
        
        result = await client.get_financial_data(
            cert_id="14",
            fields=["ASSET", "DEP", "NETINC", "ROA", "ROE"]
        )
        
        assert result.success == True
        assert len(result.data) == 1
        assert result.data[0].cert == "14"
        assert result.data[0].asset == Decimal("2500000")
        assert result.data[0].netinc == Decimal("25000")

@pytest.mark.asyncio
async def test_enhanced_bank_analysis_financial_summary():
    """Test enhanced bank analysis with real financial data integration."""
    from src.tools.composite.bank_analysis_tool import BankAnalysisTool
    
    # Mock FDIC financial API response
    with aioresponses() as mock_http:
        mock_http.get(
            'https://banks.data.fdic.gov/api/financials',
            payload={
                "data": [{
                    "CERT": "14",
                    "REPDTE": "2023-12-31", 
                    "ASSET": 1500000,
                    "DEP": 1200000,
                    "NETINC": 18000,
                    "INTINC": 45000,
                    "EINTEXP": 12000
                }]
            }
        )
        
        tool = BankAnalysisTool()
        result = await tool._get_financial_summary(
            {"name": "Test Bank"}, 
            "14"
        )
        
        # Verify real financial data in response
        assert "$1.5B" in result  # Assets formatted correctly
        assert "$1.2B" in result  # Deposits formatted correctly  
        assert "$18.0M" in result # Net income formatted correctly
        assert "2023-12-31" in result  # Report date included

def test_financial_ratio_calculations():
    """Test financial ratio calculation accuracy."""
    from src.tools.composite.bank_analysis_tool import BankAnalysisTool
    
    tool = BankAnalysisTool()
    
    # Test ROA calculation: Net Income / Total Assets
    # $20M / $2B = 1.0%
    mock_data = type('MockData', (), {
        'netinc': Decimal('20000'),    # $20M in thousands
        'asset': Decimal('2000000'),   # $2B in thousands  
        'eq': Decimal('200000'),       # $200M equity
        'repdte': date(2023, 12, 31)
    })()
    
    # Test the ratio calculation logic
    roa = float(mock_data.netinc) / float(mock_data.asset) * 100
    assert abs(roa - 1.0) < 0.01  # 1.0% ROA
    
    roe = float(mock_data.netinc) / float(mock_data.eq) * 100  
    assert abs(roe - 10.0) < 0.01  # 10.0% ROE

@pytest.mark.asyncio
async def test_error_handling_financial_api():
    """Test error handling for FDIC Financial API failures."""
    from src.tools.infrastructure.banking.fdic_financial_api import FDICFinancialAPI
    
    client = FDICFinancialAPI("test_api_key")
    
    # Test server error handling
    with aioresponses() as mock_http:
        mock_http.get(
            'https://banks.data.fdic.gov/api/financials',
            status=500
        )
        
        result = await client.get_financial_data(cert_id="999")
        
        assert result.success == False
        assert "Financial data retrieval failed" in result.error_message
        
    # Test API response with error in body (FDIC-specific pattern)
    with aioresponses() as mock_http:
        mock_http.get(
            'https://banks.data.fdic.gov/api/financials',
            payload={"error": "Invalid certificate number"},
            status=200
        )
        
        result = await client.get_financial_data(cert_id="invalid")
        
        assert result.success == False
        assert "FDIC API error" in result.error_message
```

```bash
# Install required test dependencies
uv add --dev aioresponses pytest-asyncio

# Run unit tests and iterate until passing:
cd tests/tools/fdic/
uv run pytest test_fdic_financial_api.py -v
uv run pytest test_fdic_financial_models.py -v  
uv run pytest test_enhanced_bank_analysis.py -v

# If failing: Read error, understand root cause, fix implementation, re-run
```

### Level 3: Integration Test
```bash
# Test with real FDIC Financial API (if available)
uv run python -c "
import asyncio
from src.tools.composite.bank_analysis_tool import BankAnalysisTool

async def test():
    tool = BankAnalysisTool()
    
    # Test financial summary with real data
    result = await tool._arun(
        rssd_id='480228',  # JPMorgan Chase
        query_type='financial_summary'
    )
    print('Financial Summary:')
    print(result)
    print()
    
    # Test key ratios calculation
    result = await tool._arun(
        rssd_id='480228',
        query_type='key_ratios'  
    )
    print('Key Ratios:')
    print(result)

asyncio.run(test())
"

# Expected: Real financial data with proper formatting
# Assets in billions, ratios as percentages, current report dates
# If error: Check FDIC_API_KEY configuration and API connectivity
```

### Level 4: Service Integration Test
```bash
# Test service availability checking
uv run python -c "
import asyncio
from src.tools.dynamic_loader import ServiceAvailabilityChecker  
from src.config.settings import get_settings

async def test():
    settings = get_settings()
    checker = ServiceAvailabilityChecker(settings)
    
    # Test FDIC financial API availability
    available = await checker.check_service_availability('fdic_financial_api')
    print(f'FDIC Financial API Available: {available}')
    
    # Test tool loading with financial API dependency
    if available:
        from src.tools.composite.bank_analysis_tool import BankAnalysisTool
        tool = BankAnalysisTool()
        print(f'Bank Analysis Tool Available: {tool.is_available()}')

asyncio.run(test())
"
```

## Final Validation Checklist
- [ ] All tests pass: `uv run pytest tests/tools/fdic/ -v`
- [ ] All tests pass: `uv run pytest tests/tools/call_report/ -v` (backward compatibility)
- [ ] No linting errors: `ruff check src/tools/ --fix`
- [ ] No type errors: `mypy src/tools/`
- [ ] FDIC Financial API integration working: Manual test with real API
- [ ] Enhanced financial_summary shows real data: Multiple metrics displayed
- [ ] Key ratios calculated correctly: ROA, ROE, NIM calculations accurate
- [ ] Service availability checking works: Financial API dependency detected
- [ ] Backward compatibility maintained: Existing tool interfaces unchanged
- [ ] Error handling robust: Network failures and API errors handled gracefully
- [ ] Performance optimized: Field selection and caching implemented
- [ ] Logs informative: Financial API calls and errors properly logged

## Anti-Patterns to Avoid
- ❌ Don't hardcode API endpoints - use constants and configuration
- ❌ Don't break backward compatibility - existing interfaces must work
- ❌ Don't ignore null financial values - handle missing data gracefully
- ❌ Don't skip field selection optimization - limit API response size
- ❌ Don't cache error responses - only cache successful financial data
- ❌ Don't forget financial value conversion - thousands to display format
- ❌ Don't use sync HTTP calls - maintain async patterns throughout
- ❌ Don't skip comprehensive error handling - API can fail in multiple ways
- ❌ Don't assume all banks have all financial fields - robust null handling
- ❌ Don't hardcode financial calculations - make them configurable/extensible

---

## Confidence Score: 9.2/10

**Strong points**: 
- Comprehensive existing FDIC infrastructure provides solid foundation
- Clear API documentation and field specifications available
- Established patterns for async HTTP clients, caching, and error handling
- Extensive test coverage approach with realistic financial data mocking
- Backward compatibility preservation ensures no breaking changes
- Performance optimization through field selection and caching
- Real financial data will dramatically improve tool capabilities

**Minor risk areas**: 
- FDIC API response time variability (mitigated by caching and timeouts)
- Financial data availability inconsistencies across institutions (handled by null checking)
- Date range handling for historical analysis (addressed in implementation)

The implementation leverages substantial existing infrastructure while adding significant real-world financial analysis capabilities.