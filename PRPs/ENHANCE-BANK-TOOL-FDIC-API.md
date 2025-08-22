# PRP: FDIC BankFind Suite API Integration

## Goal

Enhance the existing `bank_lookup_tool` and `bank_analysis_tool` to use the FDIC BankFind Suite API for real-time bank identification and data retrieval, replacing the current mock data with live FDIC institution data.

## Why

- **Real Data**: Replace mock bank data with authoritative FDIC institution information
- **Comprehensive Search**: Enable search by institution name, city, and county
- **Enhanced Accuracy**: Provide real FDIC certificate numbers, RSSD IDs, and institution details
- **Future Extensibility**: Foundation for incorporating additional FDIC APIs (Financial, Demographics, etc.)

## What

Transform the banking tools to integrate with FDIC's BankFind Suite API while maintaining LangChain compatibility and existing tool patterns.

### Success Criteria

- [ ] Bank lookup searches real FDIC data via API
- [ ] Support for name, city, county search parameters
- [ ] Enhanced input schemas reflecting FDIC fields
- [ ] Secure API key management
- [ ] Backward compatibility with existing tool interfaces
- [ ] Proper error handling and fallback mechanisms
- [ ] Updated tool descriptions for improved AI usage

## All Needed Context

### Documentation & References

```yaml
- url: https://api.fdic.gov/banks/docs/
  why: Primary FDIC BankFind Suite API documentation and examples

- url: https://api.fdic.gov/banks/docs/swagger.yaml
  why: Complete API schema with endpoints, parameters, and response formats

- file: src/tools/atomic/bank_lookup_tool.py
  why: Current implementation pattern, LangChain integration, async patterns

- file: src/tools/composite/bank_analysis_tool.py
  why: How composite tools use atomic tools, workflow patterns

- file: src/tools/infrastructure/banking/call_report_api.py
  why: API client patterns, error handling, async execution

- file: src/config/settings.py
  why: Secure API key storage patterns, field validation, environment setup

- file: src/tools/dynamic_loader.py
  why: Service availability checking patterns, tool loading logic

- file: tests/tools/call_report/test_langchain_tools.py
  why: Testing patterns for LangChain tools, mocking strategies
```

### Current Codebase Structure

```bash
src/
├── tools/
│   ├── atomic/
│   │   └── bank_lookup_tool.py          # Target for enhancement
│   ├── composite/
│   │   └── bank_analysis_tool.py        # Target for enhancement
│   ├── infrastructure/
│   │   ├── banking/
│   │   │   ├── banking_models.py        # Data models
│   │   │   ├── banking_constants.py     # Constants
│   │   │   └── call_report_api.py       # API pattern reference
│   │   └── toolsets/
│   │       └── banking_toolset.py       # Tool registration
│   ├── dynamic_loader.py                # Service availability
│   └── categories.py                    # Tool categorization
├── config/
│   └── settings.py                      # Settings & API keys
└── tests/
    └── tools/
        ├── call_report/
        │   └── test_langchain_tools.py  # Test patterns
        └── test_enhanced_registry.py
```

### Desired Codebase Structure (New Files)

```bash
src/tools/infrastructure/banking/
├── fdic_api_client.py           # New FDIC API client
├── fdic_models.py              # New FDIC response models
└── fdic_constants.py           # New FDIC field mappings

tests/tools/fdic/
├── __init__.py
├── test_fdic_api_client.py     # FDIC client tests
├── test_fdic_models.py         # FDIC model tests
└── test_enhanced_bank_tools.py # Enhanced tool tests
```

### Known Gotchas & Library Quirks

```python
# CRITICAL: FDIC API uses Elasticsearch query syntax
# Search: NAME:"First Bank" (exact phrase)
# Filter: STALP:IA AND ACTIVE:1 (logical operators)

# CRITICAL: Use aiohttp for HTTP client (standardized choice)
# Follow existing async patterns with proper session management

# CRITICAL: Implement response caching like credential cache pattern
# Bank data changes infrequently - cache for performance

# CRITICAL: Create comprehensive field mappings like banking_constants.py
# Map FDIC response fields to internal representations

# CRITICAL: FDIC-specific error handling required
# Handle 400 (bad request), 401 (unauthorized), 429 (rate limit), 500 (server error)

# CRITICAL: No fallback to mock data on FDIC API failure
# Return clear error: "Bank data not available from FDIC"

# CRITICAL: Validate all FDIC response data against schemas
# Some fields may be missing or null - handle gracefully

# CRITICAL: LangChain tool descriptions are prompts for the AI
# These must be comprehensive and include examples

# CRITICAL: API key is provided - store securely in settings
# API_KEY = "gMeWeAXp4GeNVRB9cN9b3gNV001gqrt3qbhV7KGu"

# GOTCHA: Our codebase uses async/await patterns throughout
# All API calls must be async and use proper error handling

# GOTCHA: Pydantic v2 patterns for data validation
# Use Field() for descriptions, proper type hints

# PATTERN: Follow existing service availability checking
# Add "fdic_api" service to dynamic_loader.py

# TESTING: Mock HTTP responses directly, not API classes
# Use aioresponses or similar for HTTP mocking
```

## Implementation Blueprint

### Data Models and Structure

```python
# FDIC Institution model with key fields
class FDICInstitution(BaseModel):
    cert: Optional[str]          # FDIC Certificate number
    name: str                    # Institution name
    rssd: Optional[str]          # RSSD ID (Federal Reserve)
    city: Optional[str]          # City
    county: Optional[str]        # County
    stname: Optional[str]        # State name
    stalp: Optional[str]         # State abbreviation
    active: Optional[bool]       # Active status
    asset: Optional[Decimal]     # Total assets
    dep: Optional[Decimal]       # Total deposits
    offices: Optional[int]       # Number of offices

# Enhanced input schemas
class BankLookupInput(BaseModel):
    search_term: Optional[str] = Field(description="Bank name to search")
    city: Optional[str] = Field(description="City to filter results")
    county: Optional[str] = Field(description="County to filter results")
    state: Optional[str] = Field(description="State abbreviation (e.g., 'CA', 'TX')")
    active_only: bool = Field(default=True, description="Only show active institutions")
    max_results: int = Field(default=5, description="Maximum results (1-50)")
```

### Task List (In Order)

```yaml
Task 1: Create FDIC API Infrastructure
CREATE src/tools/infrastructure/banking/fdic_models.py:
  - MIRROR pattern from: banking_models.py
  - IMPLEMENT FDICInstitution, FDICAPIResponse pydantic models
  - ADD comprehensive field mappings for FDIC response data

CREATE src/tools/infrastructure/banking/fdic_constants.py:
  - DEFINE FDIC API base URL, endpoints
  - CREATE field mappings for FDIC to internal formats
  - ADD search query templates

CREATE src/tools/infrastructure/banking/fdic_api_client.py:
  - MIRROR pattern from: call_report_api.py
  - IMPLEMENT async HTTP client using aiohttp (standardized choice)
  - ADD search_institutions() method with response caching
  - INCLUDE FDIC-specific error handling (400, 401, 429, 500)
  - ADD response data validation against schemas
  - PRESERVE existing async patterns and logging
  - NO fallback to mock data - return clear FDIC unavailable errors

Task 2: Add FDIC Configuration to Settings
MODIFY src/config/settings.py:
  - FIND: API Keys section (around line 434)
  - ADD: fdic_api_key field with proper Field() description
  - PRESERVE: existing security patterns for API keys

Task 3: Enhance Bank Lookup Tool
MODIFY src/tools/atomic/bank_lookup_tool.py:
  - REPLACE: mock data loading with FDIC API client
  - UPDATE: input schema to enhanced BankLookupInput
`  - ENHANCE: search logic to support city/county/state filters
  - UPDATE: tool description with new capabilities and examples
  - PRESERVE: existing LangChain BaseTool interface
  - MAINTAIN: fuzzy matching and similarity scoring
  - KEEP: backward compatibility for existing parameters

Task 4: Update Bank Analysis Tool
MODIFY src/tools/composite/bank_analysis_tool.py:
  - UPDATE: input schema to support new lookup fields
  - ENHANCE: tool description to reflect FDIC data integration
  - PRESERVE: existing workflow and LangChain integration
  - MAINTAIN: backward compatibility

Task 5: Add Service Availability Checking
MODIFY src/tools/dynamic_loader.py:
  - FIND: _initialize_service_checkers method (around line 60)
  - ADD: "fdic_api" service checker method
  - IMPLEMENT: _check_fdic_api_availability() async method
  - UPDATE: banking tools loading to check fdic_api availability

Task 6: Create Comprehensive Tests
CREATE tests/tools/fdic/ directory and test files:
  - MIRROR: test patterns from tests/tools/call_report/
  - IMPLEMENT: unit tests for FDIC client, models, enhanced tools
  - ADD: integration tests with mocked FDIC API responses
  - INCLUDE: backward compatibility tests

Task 7: Update Tool Registration
MODIFY src/tools/infrastructure/toolsets/banking_toolset.py:
  - UPDATE: tool initialization to use FDIC-enhanced tools
  - PRESERVE: existing LangChain tool registration patterns
```

### Task 1 Pseudocode - FDIC API Client

```python
# src/tools/infrastructure/banking/fdic_api_client.py
class FDICAPIClient:
    def __init__(self, api_key: str, timeout: float = 30.0):
        self.api_key = api_key
        self.base_url = "https://api.fdic.gov"
        self.timeout = aiohttp.ClientTimeout(total=timeout)

    async def search_institutions(
        self,
        name: Optional[str] = None,
        city: Optional[str] = None,
        county: Optional[str] = None,
        state: Optional[str] = None,
        active_only: bool = True,
        limit: int = 50
    ) -> FDICAPIResponse:
        # PATTERN: Build Elasticsearch query like existing APIs
        search_parts = []
        if name:
            search_parts.append(f'NAME:"{name}"')

        filters = []
        if city:
            filters.append(f'CITY:"{city}"')
        if state:
            filters.append(f'STALP:{state}')
        if active_only:
            filters.append('ACTIVE:1')

        # CRITICAL: Use proper query syntax for FDIC API
        query_params = {
            'search': ' '.join(search_parts) if search_parts else None,
            'filters': ' AND '.join(filters) if filters else None,
            'limit': limit,
            'format': 'json'
        }

        # GOTCHA: Add API key if provided
        if self.api_key:
            query_params['api_key'] = self.api_key

        # PATTERN: Async HTTP with proper error handling
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.get(f"{self.base_url}/institutions",
                                 params=query_params) as response:
                # CRITICAL: Handle FDIC-specific error responses
                response.raise_for_status()
                data = await response.json()
                return FDICAPIResponse.parse_obj(data)
```

### Task 3 Pseudocode - Enhanced Bank Lookup

```python
# Enhanced _run method in bank_lookup_tool.py
async def _arun(
    self,
    search_term: Optional[str] = None,
    city: Optional[str] = None,
    county: Optional[str] = None,
    state: Optional[str] = None,
    active_only: bool = True,
    fuzzy_match: bool = True,
    max_results: int = 5
) -> str:
    # PATTERN: Validate inputs first
    if not any([search_term, city, county, state]):
        return "Error: At least one search parameter required"

    # CRITICAL: Use FDIC API client instead of mock data
    try:
        api_response = await self.fdic_client.search_institutions(
            name=search_term,
            city=city,
            county=county,
            state=state,
            active_only=active_only,
            limit=max_results * 2  # Get extra for fuzzy filtering
        )

        institutions = api_response.institutions

        # PRESERVE: Existing fuzzy matching logic for backwards compatibility
        if fuzzy_match and search_term:
            institutions = self._apply_fuzzy_matching(institutions, search_term)

        # PATTERN: Format response like existing implementation
        return self._format_results(institutions[:max_results])

    except Exception as e:
        self.logger.error("FDIC API search failed", error=str(e))
        # FALLBACK: Could fall back to mock data or return error
        return f"Error: Bank search failed - {str(e)}"
```

### Integration Points

```yaml
SETTINGS:
  - add to: src/config/settings.py
  - field: fdic_api_key with proper security handling

SERVICE_AVAILABILITY:
  - add to: src/tools/dynamic_loader.py
  - checker: _check_fdic_api_availability method

TOOL_REGISTRATION:
  - update: src/tools/infrastructure/toolsets/banking_toolset.py
  - preserve: existing LangChain patterns
```

## Validation Loop

### Level 1: Syntax & Style

```bash
# Run these FIRST - fix any errors before proceeding
cd src/tools/infrastructure/banking/
ruff check fdic_*.py --fix         # Auto-fix style issues
mypy fdic_*.py                     # Type checking

cd ../../atomic/
ruff check bank_lookup_tool.py --fix
mypy bank_lookup_tool.py

# Expected: No errors. If errors occur, read and fix them.
```

### Level 2: Unit Tests

```python
# tests/tools/fdic/test_fdic_api_client.py
import pytest
from unittest.mock import AsyncMock, Mock
from src.tools.infrastructure.banking.fdic_api_client import FDICAPIClient

@pytest.mark.asyncio
async def test_search_institutions_by_name():
    """Test basic institution search by name"""
    client = FDICAPIClient("test_api_key")

    # Mock successful API response
    mock_response = {
        "institutions": [
            {
                "cert": "123",
                "name": "Test Bank",
                "city": "Test City",
                "stname": "California",
                "active": True
            }
        ]
    }

    with patch('aiohttp.ClientSession') as mock_session:
        mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value.json.return_value = mock_response

        result = await client.search_institutions(name="Test Bank")

        assert result.institutions[0].name == "Test Bank"
        assert result.institutions[0].cert == "123"

@pytest.mark.asyncio
async def test_enhanced_bank_lookup_tool():
    """Test enhanced bank lookup with FDIC integration"""
    from src.tools.atomic.bank_lookup_tool import BankLookupTool

    tool = BankLookupTool()

    result = await tool._arun(
        search_term="Wells Fargo",
        state="CA",
        max_results=3
    )

    assert "Found" in result
    assert "Wells Fargo" in result or "No banks found" in result

def test_backward_compatibility():
    """Ensure existing tool interface still works"""
    from src.tools.atomic.bank_lookup_tool import BankLookupInput

    # Old interface should still work
    old_input = BankLookupInput(
        search_term="Bank of America",
        fuzzy_match=True,
        max_results=5
    )

    assert old_input.search_term == "Bank of America"
    assert old_input.fuzzy_match == True
```

```bash
# Run and iterate until passing:
cd tests/tools/fdic/
uv run pytest test_fdic_api_client.py -v
uv run pytest test_enhanced_bank_tools.py -v

# Test backward compatibility
uv run pytest ../call_report/ -k "test_bank" -v

# If failing: Read error, fix code, re-run (don't mock to pass - fix the implementation)
```

### Level 3: Integration Test

```bash
# Test with actual FDIC API (if key configured)
uv run python -c "
from src.tools.atomic.bank_lookup_tool import BankLookupTool
import asyncio

async def test():
    tool = BankLookupTool()
    result = await tool._arun(search_term='Wells Fargo', state='CA', max_results=3)
    print(f'Result: {result}')

asyncio.run(test())
"

# Expected output: List of Wells Fargo institutions in California
# If error: Check FDIC_API_KEY in .env and API connectivity
```

## Final Validation Checklist

- [ ] All tests pass: `uv run pytest tests/tools/ -v`
- [ ] No linting errors: `ruff check src/tools/ --fix`
- [ ] No type errors: `mypy src/tools/`
- [ ] FDIC API integration working: Manual test with real API key
- [ ] Backward compatibility maintained: Old tool interfaces still work
- [ ] Enhanced search capabilities: Name, city, county, state searches work
- [ ] Tool descriptions updated: AI gets better guidance for tool usage
- [ ] Error handling robust: Network failures handled gracefully
- [ ] Logs informative: Structured logging for debugging

## Anti-Patterns to Avoid

- ❌ Don't hardcode the API key - use settings pattern
- ❌ Don't break backward compatibility - existing interfaces must work
- ❌ Don't ignore FDIC API rate limits or error responses
- ❌ Don't use sync HTTP calls - maintain async patterns
- ❌ Don't skip comprehensive tool descriptions - AI needs good prompts
- ❌ Don't forget fallback mechanisms for API failures
- ❌ Don't skip validation of FDIC response data structure

---

## Confidence Score: 8/10

**Strong points**: Comprehensive context, clear task breakdown, existing patterns to follow, executable validation gates

**Risk areas**: FDIC API reliability, rate limiting behavior, response format changes - mitigated by robust error handling and fallback mechanisms
