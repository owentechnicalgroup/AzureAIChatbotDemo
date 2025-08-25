# PRP: FFIEC Call Report Data Tool Integration

**name:** "FFIEC_CALL_REPORT_TOOL_INTEGRATION PRP v1 - Real FFIEC CDR API with SOAP Integration"

**description:** |

## Purpose
Implement a production-ready FFIEC Call Report data retrieval tool that integrates with the real FFIEC CDR Public Data Distribution web service, providing AI agents with access to actual call report data through SOAP API integration with comprehensive caching and error handling.

## Core Principles
1. **Context is King**: Include ALL necessary documentation, examples, and caveats
2. **Validation Loops**: Provide executable tests/lints the AI can run and fix
3. **Information Dense**: Use keywords and patterns from the codebase
4. **Progressive Success**: Start simple, validate, then enhance
5. **Global rules**: Follow all rules in CLAUDE.md

---

## Goal
Build a complete FFIEC Call Report atomic tool that:
- Integrates with real FFIEC CDR SOAP web service using authentication
- Provides discovery services to find latest call reports by bank RSSD ID
- Retrieves and caches call report facsimile data 
- Follows established atomic tool patterns from existing FDIC tools
- Integrates with the existing bank_analysis_tool for comprehensive analysis
- Handles SOAP-specific challenges with async/await patterns

## Why
- **Business value**: Enables AI agent to access real regulatory call report data for comprehensive financial analysis
- **Integration**: Seamlessly works with existing bank analysis workflows and FDIC data
- **Problems solved**: Eliminates need for manual call report lookup and provides current regulatory filing data
- **User impact**: Provides complete financial picture combining FDIC data with detailed call report information

## What
User-visible behavior: AI agent can retrieve the latest call report data for any bank by name or RSSD ID, combining this with existing FDIC financial data for comprehensive analysis.

Technical requirements:
- Real FFIEC CDR SOAP API integration with authentication
- Intelligent discovery of latest available filings by bank
- Session-based caching of retrieved call report data
- Secure API key storage in Azure Key Vault
- Integration with existing bank_analysis_tool
- Comprehensive error handling for SOAP faults and API issues
- Async/await patterns with proper WSDL handling

### Success Criteria
- [ ] AI agent can discover and retrieve latest call reports for banks by RSSD ID
- [ ] Tool integrates with real FFIEC CDR web service using provided API credentials
- [ ] Call report data is cached for current session to avoid redundant API calls
- [ ] Tool follows existing atomic tool patterns and integrates with bank_analysis_tool
- [ ] All SOAP-specific challenges are handled (sync WSDL loading, async execution)
- [ ] Comprehensive error handling for API failures, missing data, and authentication issues
- [ ] API key is stored securely in Azure Key Vault following existing patterns

## All Needed Context

### Documentation & References (Critical Context for Implementation)
```yaml
# MUST READ - Include these in your context window

# FFIEC CDR API Documentation
- url: https://cdr.ffiec.gov/public/PWS/PWSPage.aspx
  why: FFIEC CDR Public Data Distribution overview, account requirements, authentication
  
- url: https://cdr.ffiec.gov/public/pws/webservices/retrievalservice.asmx?WSDL
  why: Complete WSDL definition with method signatures, parameters, and data types
  critical: RetrieveFacsimile, RetrieveReportingPeriods, RetrieveFilersSinceDate methods

# SOAP Client Implementation
- url: https://docs.python-zeep.org/en/master/client.html
  why: Zeep AsyncClient patterns, authentication, transport configuration
  critical: AsyncClient setup with synchronous WSDL loading caveat
  
- url: https://docs.python-zeep.org/en/master/transports.html
  why: Authentication setup, httpx integration for async operations
  critical: Separate sync/async clients for authentication scenarios

# Existing Codebase Patterns
- file: src/tools/atomic/fdic_financial_data_tool.py
  why: Complete atomic tool implementation pattern, async methods, input validation
  critical: Tool structure, _arun implementation, error handling patterns
  
- file: src/tools/infrastructure/banking/fdic_financial_api.py  
  why: API client implementation with caching, error handling, async patterns
  critical: Cache implementation, HTTP client patterns, response processing
  
- file: src/tools/infrastructure/banking/fdic_financial_models.py
  why: Pydantic model patterns for financial data, validation, field handling
  critical: Data modeling for complex financial structures
  
- file: src/tools/infrastructure/banking/fdic_financial_constants.py
  why: Constants organization, field mappings, configuration patterns
  critical: API configuration, field templates, error codes

- file: src/tools/composite/bank_analysis_tool.py
  why: Composite tool integration pattern, multiple API client coordination
  critical: Tool initialization, client management, integration approach
  
- file: src/config/settings.py
  why: Secure API key storage patterns, Azure Key Vault integration
  critical: Field definitions, Key Vault patterns, environment variable handling

# Financial Domain Knowledge  
- url: https://www.ffiec.gov/pdf/FFIEC_forms/FFIEC031_202403_f.pdf
  why: FFIEC 031 Call Report form structure, schedules, field definitions
  critical: Understanding data structure and field relationships

- url: https://corporatefinanceinstitute.com/resources/accounting/call-report/
  why: Call report business context, regulatory requirements, data interpretation
  critical: Understanding the business value and usage patterns of call report data

# Testing Patterns
- file: tests/tools/call_report/fixtures.py
  why: Existing test fixture patterns for call report data structures
  critical: Test data models, mock patterns, fixture organization
  
- file: tests/tools/fdic/test_fdic_api_client.py
  why: API client testing patterns, async test setup, mock response handling
  critical: Testing HTTP clients, error scenarios, validation approaches
```

### Current Codebase Architecture
```bash
# Existing atomic tools structure
src/tools/atomic/
├── fdic_financial_data_tool.py    # Pattern for atomic tool implementation
├── fdic_institution_search_tool.py # Pattern for search/lookup tools  
└── rag_search_tool.py             # Pattern for data retrieval tools

# Existing infrastructure patterns  
src/tools/infrastructure/banking/
├── fdic_api_client.py             # HTTP API client with caching
├── fdic_financial_api.py          # Specialized API client  
├── fdic_models.py                 # Pydantic data models
├── fdic_constants.py              # API constants and configuration
├── fdic_financial_models.py       # Complex financial data models
└── fdic_financial_constants.py    # Field mappings and templates

# Existing composite tool integration
src/tools/composite/
└── bank_analysis_tool.py          # Multi-API coordination pattern

# Configuration and security
src/config/
└── settings.py                    # Secure API key storage with Key Vault
```

### Desired Implementation Architecture
```bash
# New FFIEC Call Report atomic tool
src/tools/atomic/
└── ffiec_call_report_data_tool.py # Main atomic tool following FDIC patterns

# New FFIEC infrastructure components
src/tools/infrastructure/banking/
├── ffiec_cdr_api_client.py        # SOAP API client with authentication  
├── ffiec_cdr_models.py            # Pydantic models for call report data
├── ffiec_cdr_constants.py         # FFIEC constants, endpoints, error codes
└── ffiec_cdr_cache.py             # Session-based caching implementation

# Enhanced composite tool
src/tools/composite/
└── bank_analysis_tool.py          # Updated to include FFIEC call report data

# Updated configuration  
src/config/
└── settings.py                    # Add ffiec_cdr_api_key configuration

# Test implementation
tests/tools/ffiec/
├── test_ffiec_cdr_api_client.py   # SOAP API client tests with mocks
├── test_ffiec_call_report_tool.py # Atomic tool integration tests  
└── fixtures.py                    # Test fixtures for FFIEC data
```

### Known Gotchas & Critical Implementation Details
```python
# CRITICAL: Zeep SOAP client async caveat
# WSDL loading must be synchronous, but execution is async
from zeep import AsyncClient
from zeep.transports import AsyncTransport
import httpx

# Pattern for authenticated SOAP client setup
def create_ffiec_client(api_key: str) -> AsyncClient:
    # Synchronous client for WSDL loading with auth
    wsdl_client = httpx.Client(
        auth=(username, api_key),
        verify=True,
        timeout=30.0
    )
    
    # Async client for request execution  
    async_client = httpx.AsyncClient(
        auth=(username, api_key),
        verify=True,
        timeout=30.0
    )
    
    transport = AsyncTransport(
        client=async_client,
        wsdl_client=wsdl_client
    )
    
    return AsyncClient(
        "https://cdr.ffiec.gov/public/pws/webservices/retrievalservice.asmx?WSDL",
        transport=transport
    )

# CRITICAL: Project conventions from CLAUDE.md  
# - Never create files longer than 500 lines - split into modules
# - Use async/await for all tool execution methods
# - Use structured logging with log_type field
# - Store API keys securely in Azure Key Vault
# - Use Decimal for financial values, never float
# - Follow existing error handling patterns with detailed messages

# CRITICAL: FFIEC API specific requirements
# - API requires account credentials (username/PIN)  
# - RetrieveFacsimile returns Base64 encoded data
# - Discovery pattern: Check recent periods for latest filing
# - Handle "filer not found" scenarios gracefully
# - Cache responses for session duration only (don't persist)

# CRITICAL: Integration with existing tools
# - Bank analysis tool needs RSSD ID from FDIC institution search
# - Combine FFIEC call report data with FDIC financial data
# - Maintain consistent data formatting and error handling
# - Use existing logging patterns with log_type="SYSTEM"
```

## Implementation Blueprint

### Data Models and Structure
Create type-safe models following existing banking infrastructure patterns:

```python
# Core Pydantic models for FFIEC Call Report data
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import date, datetime
from decimal import Decimal

class FFIECCallReportRequest(BaseModel):
    """Input model for call report data requests."""
    rssd_id: str = Field(
        ..., 
        description="Bank RSSD ID for call report retrieval",
        min_length=1,
        max_length=10
    )
    reporting_period: Optional[str] = Field(
        None,
        description="Specific reporting period (YYYY-MM-DD) or None for latest"
    )
    facsimile_format: str = Field(
        "PDF", 
        description="Output format: PDF, XBRL, or SDF"
    )

class FFIECCallReportData(BaseModel):
    """Model for retrieved call report data."""
    rssd_id: str
    reporting_period: date
    report_format: str
    data: bytes  # Base64 decoded facsimile data
    retrieval_timestamp: datetime
    data_source: str = "FFIEC CDR Public Data Distribution"

class FFIECDiscoveryResult(BaseModel):
    """Model for filing discovery results."""
    rssd_id: str
    available_periods: List[str]
    latest_period: Optional[str] = None
    discovery_timestamp: datetime
```

### List of Tasks (Implementation Order)

```yaml
Task 1: Create FFIEC CDR Infrastructure Components
CREATE src/tools/infrastructure/banking/ffiec_cdr_constants.py:
  - DEFINE FFIEC CDR API endpoints and configuration
  - DEFINE error codes and messages specific to FFIEC CDR  
  - DEFINE facsimile format options and validation
  - FOLLOW pattern from: src/tools/infrastructure/banking/fdic_financial_constants.py

CREATE src/tools/infrastructure/banking/ffiec_cdr_models.py:
  - IMPLEMENT Pydantic models for FFIEC call report data structures  
  - USE Decimal for financial values, datetime for timestamps
  - INCLUDE proper validation and field descriptions
  - FOLLOW pattern from: src/tools/infrastructure/banking/fdic_financial_models.py

Task 2: Implement SOAP API Client with Authentication  
CREATE src/tools/infrastructure/banking/ffiec_cdr_api_client.py:
  - IMPLEMENT AsyncClient pattern with zeep library
  - HANDLE synchronous WSDL loading with async execution
  - IMPLEMENT authentication using provided API credentials
  - INCLUDE comprehensive error handling for SOAP faults
  - FOLLOW async patterns from: src/tools/infrastructure/banking/fdic_financial_api.py
  - ADD session-based caching for retrieved call report data

Task 3: Create Atomic Call Report Tool
CREATE src/tools/atomic/ffiec_call_report_data_tool.py:
  - INHERIT from BaseTool following LangChain patterns
  - IMPLEMENT discovery logic for latest filings  
  - USE smart filing discovery from feature examples
  - INTEGRATE with FFIEC CDR API client
  - FOLLOW tool structure from: src/tools/atomic/fdic_financial_data_tool.py
  - INCLUDE proper input validation and error handling

Task 4: Update Security Configuration
MODIFY src/config/settings.py:
  - ADD ffiec_cdr_api_key: Optional[str] field
  - ADD ffiec_cdr_username: Optional[str] field  
  - ADD ffiec_cdr_timeout_seconds: int field
  - ADD ffiec_cdr_cache_ttl: int field
  - FOLLOW existing API key patterns for secure storage

UPDATE infrastructure/outputs.tf:
  - ADD ffiec-cdr-api-key to Key Vault secrets
  - ADD ffiec-cdr-username to Key Vault secrets
  - FOLLOW existing secret management patterns

UPDATE scripts/setup-env.ps1:
  - ADD FFIEC_CDR_API_KEY environment variable mapping
  - ADD FFIEC_CDR_USERNAME environment variable mapping  
  - FOLLOW existing environment setup patterns

Task 5: Register Tool and Update System Prompts
MODIFY src/tools/atomic/__init__.py:
  - ADD FFIECCallReportDataTool import and export
  - FOLLOW existing atomic tool registration pattern
  
MODIFY src/chatbot/agent.py:
  - UPDATE _build_system_prompt method to include FFIEC call report routing
  - ADD "🏛️ CALL REPORT DATA" routing pattern for RSSD/bank regulatory data queries
  - INCLUDE examples and keywords for call report data requests
  - FOLLOW existing tool routing patterns in multi-step addition section

MODIFY src/tools/infrastructure/toolsets/banking_toolset.py:
  - IMPORT and initialize FFIECCallReportDataTool
  - ADD to tools list when ffiec_cdr_enabled setting is True
  - FOLLOW existing FDIC tool integration pattern

Task 6: Integrate with Bank Analysis Tool  
MODIFY src/tools/composite/bank_analysis_tool.py:
  - IMPORT FFIECCallReportDataTool
  - INITIALIZE FFIEC client alongside existing FDIC clients
  - ENHANCE analysis to include call report data when available
  - MAINTAIN existing functionality while adding call report capabilities
  - FOLLOW integration pattern from existing FDIC tool integration

Task 7: Create Comprehensive Test Suite
CREATE tests/tools/ffiec/test_ffiec_cdr_api_client.py:
  - TEST SOAP client initialization and authentication
  - MOCK WSDL responses and API calls using aioresponses patterns
  - TEST error handling for authentication failures and API errors
  - FOLLOW async testing patterns from: tests/tools/fdic/test_fdic_api_client.py

CREATE tests/tools/ffiec/test_ffiec_call_report_tool.py:
  - TEST atomic tool functionality with mocked API responses
  - TEST discovery logic for finding latest filings
  - TEST integration with LangChain tool framework
  - FOLLOW tool testing patterns from existing FDIC tool tests

CREATE tests/tools/ffiec/fixtures.py:
  - PROVIDE realistic FFIEC test data fixtures
  - MOCK SOAP response data structures
  - FOLLOW fixture patterns from: tests/tools/call_report/fixtures.py

Task 8: Integration Testing and Validation
CREATE integration test for full workflow:
  - TEST bank lookup -> RSSD ID -> call report retrieval  
  - TEST integration with bank analysis tool
  - TEST error handling for missing data scenarios
  - VALIDATE caching behavior and session management
```

### Per Task Pseudocode

```python
# Task 2: SOAP API Client Implementation
class FFIECCDRAPIClient:
    """FFIEC CDR SOAP API client with authentication and caching."""
    
    def __init__(self, api_key: str, username: str, cache_ttl: int = 3600):
        self.api_key = api_key
        self.username = username
        self.cache = {}  # Session-based cache
        self.cache_ttl = cache_ttl
        
        # CRITICAL: Handle zeep async caveat
        self._setup_soap_client()
    
    def _setup_soap_client(self):
        """Setup SOAP client with proper auth and async handling."""
        # Synchronous client for WSDL loading
        wsdl_client = httpx.Client(
            auth=(self.username, self.api_key),
            verify=True,
            timeout=30.0
        )
        
        # Async client for execution
        async_client = httpx.AsyncClient(
            auth=(self.username, self.api_key), 
            verify=True,
            timeout=30.0
        )
        
        transport = AsyncTransport(
            client=async_client,
            wsdl_client=wsdl_client
        )
        
        self.client = AsyncClient(
            "https://cdr.ffiec.gov/public/pws/webservices/retrievalservice.asmx?WSDL",
            transport=transport
        )
    
    async def discover_latest_filing(self, rssd_id: str) -> Optional[str]:
        """Implement smart discovery from feature examples."""
        try:
            # Get available reporting periods
            periods = await self.client.service.RetrieveReportingPeriods(
                dataSeries="Call"
            )
            
            # Sort newest to oldest
            sorted_periods = sorted(periods, reverse=True)
            
            # Check recent periods for this bank
            for period in sorted_periods[:4]:
                filers = await self.client.service.RetrieveFilersSinceDate(
                    dataSeries="Call",
                    reportingPeriodEndDate=period,
                    lastUpdateDateTime=period  
                )
                
                if int(rssd_id) in filers:
                    return period
                    
            return None
            
        except Exception as e:
            logger.error("Discovery failed", error=str(e), rssd_id=rssd_id)
            return None
    
    async def retrieve_facsimile(self, rssd_id: str, reporting_period: str, 
                                format: str = "PDF") -> Optional[bytes]:
        """Retrieve call report facsimile data."""
        cache_key = f"{rssd_id}_{reporting_period}_{format}"
        
        # Check cache first
        if cache_key in self.cache:
            cached_data, timestamp = self.cache[cache_key]
            if datetime.now() - timestamp < timedelta(seconds=self.cache_ttl):
                return cached_data
        
        try:
            # Call FFIEC API
            result = await self.client.service.RetrieveFacsimile(
                dataSeries="Call",
                reportingPeriodEndDate=reporting_period,
                fiIDType="ID_RSSD",
                fiID=int(rssd_id),
                facsimileFormat=format
            )
            
            # Decode base64 result
            decoded_data = base64.b64decode(result)
            
            # Cache for session
            self.cache[cache_key] = (decoded_data, datetime.now())
            
            return decoded_data
            
        except Exception as e:
            logger.error("Facsimile retrieval failed", error=str(e), 
                        rssd_id=rssd_id, period=reporting_period)
            return None

# Task 3: Atomic Tool Implementation  
class FFIECCallReportDataTool(BaseTool):
    """Atomic tool for FFIEC Call Report data retrieval."""
    
    name: str = "ffiec_call_report_data"
    description: str = """Retrieve FFIEC Call Report data for banking institutions.
    
This tool provides access to official FFIEC Call Report filings through the 
FFIEC CDR Public Data Distribution service.

Required Input:
- rssd_id: Bank's RSSD identifier (from institution search)

Optional Parameters:  
- reporting_period: Specific reporting period (YYYY-MM-DD) or None for latest
- format: Output format - PDF, XBRL, or SDF (default: PDF)

Data Provided:
- Latest available Call Report filing for the specified bank
- Official regulatory data directly from FFIEC CDR
- Multiple format options for different analysis needs

Use Cases:
1. Latest filing: Get most recent Call Report for analysis
2. Historical data: Retrieve specific period filings  
3. Regulatory compliance: Access official FFIEC data
4. Multi-format: Choose appropriate format for analysis needs"""

    args_schema: Type[BaseModel] = FFIECCallReportRequest
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        from src.config.settings import get_settings
        settings = kwargs.get('settings') or get_settings()
        
        # Initialize FFIEC CDR API client
        object.__setattr__(self, '_ffiec_client', FFIECCDRAPIClient(
            api_key=settings.ffiec_cdr_api_key,
            username=settings.ffiec_cdr_username,
            cache_ttl=settings.ffiec_cdr_cache_ttl
        ))
        
        logger.info("FFIEC Call Report data tool initialized")
    
    async def _arun(self, rssd_id: str, reporting_period: Optional[str] = None,
                   format: str = "PDF") -> str:
        """Retrieve FFIEC Call Report data."""
        try:
            # Discover latest filing if no period specified
            if not reporting_period:
                reporting_period = await self._ffiec_client.discover_latest_filing(rssd_id)
                if not reporting_period:
                    return self._format_error(f"No recent filings found for RSSD ID {rssd_id}")
            
            # Retrieve facsimile data
            data = await self._ffiec_client.retrieve_facsimile(
                rssd_id=rssd_id,
                reporting_period=reporting_period,
                format=format
            )
            
            if not data:
                return self._format_error(f"Call Report data not available for RSSD ID {rssd_id}")
            
            # Format successful response
            return self._format_success(rssd_id, reporting_period, format, len(data))
            
        except Exception as e:
            logger.error("Call report retrieval failed", error=str(e), rssd_id=rssd_id)
            return self._format_error(f"Call report retrieval failed: {str(e)}")

# Task 5: System Prompt Integration and Tool Registration
class EnhancedSystemPrompt:
    """System prompt enhancement for FFIEC call report awareness."""
    
    @staticmethod
    def get_call_report_routing_addition() -> str:
        """Get the routing pattern for FFIEC call report queries."""
        return """
🏛️ CALL REPORT DATA → ffiec_call_report_data
Intent: User requesting official FFIEC Call Report regulatory filings
Keywords: "call report", "FFIEC", "regulatory filing", "bank filing", "quarterly report", "RSSD", "facsimile", "official data"
Examples:
- "Get the call report for Wells Fargo"
- "What is the latest FFIEC filing for RSSD 451965?"
- "Show me the call report data for JPMorgan Chase"
- "Retrieve the quarterly regulatory filing for Bank of America"
- "I need the official FFIEC call report for this bank"

ROUTING LOGIC: If query involves official FFIEC regulatory filings or call reports → ffiec_call_report_data
"""

# Enhanced agent system prompt integration
def _build_enhanced_system_prompt(self, custom_prompt: Optional[str], prompt_type: Optional[str]) -> str:
    """Enhanced system prompt with FFIEC call report routing."""
    base_prompt = self._build_original_system_prompt(custom_prompt, prompt_type)
    
    # Add FFIEC routing if tools include call report tool
    if self.enable_multi_step and any(hasattr(tool, 'name') and 'ffiec' in tool.name.lower() for tool in self.tools):
        call_report_routing = EnhancedSystemPrompt.get_call_report_routing_addition()
        
        # Insert after existing routing patterns
        routing_insertion_point = base_prompt.find("🏛️ BANK POLICIES & PROCESSES")
        if routing_insertion_point != -1:
            enhanced_prompt = (
                base_prompt[:routing_insertion_point] + 
                call_report_routing + 
                "\n" + 
                base_prompt[routing_insertion_point:]
            )
            return enhanced_prompt
    
    return base_prompt

# Task 5: Tool Registration Pattern  
class FFIECToolRegistration:
    """Tool registration following existing patterns."""
    
    @staticmethod
    def update_atomic_tools_init():
        """Update src/tools/atomic/__init__.py pattern."""
        # ADD to imports:
        from .ffiec_call_report_data_tool import FFIECCallReportDataTool
        
        # ADD to __all__:
        __all__ = [
            "FDICFinancialDataTool",
            "FDICInstitutionSearchTool", 
            "RAGSearchTool",
            "FFIECCallReportDataTool",  # NEW
        ]
    
    @staticmethod 
    def update_banking_toolset():
        """Update banking toolset registration."""
        from ..atomic.ffiec_call_report_data_tool import FFIECCallReportDataTool
        
        def get_banking_tools(settings: Settings) -> List[BaseTool]:
            """Get all banking tools based on configuration."""
            tools = []
            
            # Existing FDIC tools
            if settings.fdic_api_enabled:
                tools.extend([
                    FDICInstitutionSearchTool(settings=settings),
                    FDICFinancialDataTool(settings=settings)
                ])
            
            # NEW: FFIEC call report tool
            if getattr(settings, 'ffiec_cdr_enabled', False) and settings.ffiec_cdr_api_key:
                tools.append(FFIECCallReportDataTool(settings=settings))
            
            return tools
```

### Integration Points
```yaml
CONFIGURATION:
  - add to: src/config/settings.py
  - pattern: "ffiec_cdr_enabled: bool = Field(True, env='FFIEC_CDR_ENABLED')"
  - pattern: "ffiec_cdr_api_key: Optional[str] = Field(None, env='FFIEC_CDR_API_KEY')"
  - pattern: "ffiec_cdr_username: Optional[str] = Field(None, env='FFIEC_CDR_USERNAME')"
  - pattern: "ffiec_cdr_timeout_seconds: int = Field(30, env='FFIEC_CDR_TIMEOUT')"
  - pattern: "ffiec_cdr_cache_ttl: int = Field(3600, env='FFIEC_CDR_CACHE_TTL')"
  
SECURITY:
  - add to: infrastructure/outputs.tf  
  - add to: scripts/setup-env.ps1
  - pattern: Key Vault secret storage for API credentials
  
DEPENDENCIES:
  - add: zeep[async] for SOAP client support
  - add: httpx for HTTP client functionality  
  - pattern: Add to requirements.txt and pyproject.toml

TOOL_REGISTRATION:
  - modify: src/tools/atomic/__init__.py
  - pattern: "from .ffiec_call_report_data_tool import FFIECCallReportDataTool"
  - pattern: Add to __all__ exports list
  
BANKING_TOOLSET:
  - modify: src/tools/infrastructure/toolsets/banking_toolset.py
  - pattern: Import and initialize FFIECCallReportDataTool when settings.ffiec_cdr_enabled is True
  - pattern: Add to banking tools list with proper settings check

SYSTEM_PROMPTS:
  - modify: src/chatbot/agent.py 
  - pattern: Update _build_system_prompt to include FFIEC call report routing
  - pattern: Add "🏛️ CALL REPORT DATA → ffiec_call_report_data" routing pattern
  - pattern: Include keywords and examples for call report queries

BANK_ANALYSIS_INTEGRATION:
  - modify: src/tools/composite/bank_analysis_tool.py
  - pattern: Initialize FFIEC client alongside FDIC clients  
  - pattern: Enhance analysis output to include call report availability
```

## Validation Loop

### Level 1: Syntax & Style
```bash
# Run these FIRST - fix any errors before proceeding
ruff check src/tools/atomic/ffiec_call_report_data_tool.py --fix
ruff check src/tools/infrastructure/banking/ffiec_cdr_*.py --fix  
mypy src/tools/atomic/ffiec_call_report_data_tool.py
mypy src/tools/infrastructure/banking/ffiec_cdr_api_client.py

# Expected: No errors. If errors exist, READ and fix them.
```

### Level 2: Unit Tests
```bash  
# Test SOAP API client functionality
python -m pytest tests/tools/ffiec/test_ffiec_cdr_api_client.py -v

# Test atomic tool integration  
python -m pytest tests/tools/ffiec/test_ffiec_call_report_tool.py -v

# Test all FFIEC components
python -m pytest tests/tools/ffiec/ -v

# Expected: All tests pass. If failing, read errors and fix code.
```

### Level 3: Integration Test
```bash
# Test tool registration and schema generation
python -c "
from src.tools.atomic.ffiec_call_report_data_tool import FFIECCallReportDataTool
from src.config.settings import get_settings

settings = get_settings()
if settings.ffiec_cdr_api_key:
    tool = FFIECCallReportDataTool(settings=settings)
    print(f'Tool initialized: {tool.name}')
    print(f'Schema valid: {\"function\" in tool.get_schema()}')
else:
    print('FFIEC API key not configured - skipping tool test')
"

# Test bank analysis tool integration
python -c "
from src.tools.composite.bank_analysis_tool import BankAnalysisTool
from src.config.settings import get_settings

settings = get_settings()  
tool = BankAnalysisTool(settings=settings)
print(f'Bank analysis tool includes FFIEC: {hasattr(tool, \"_ffiec_client\")}')
"
```

### Level 4: End-to-End Validation
```bash
# Test actual API connectivity (requires API key)
python -c "
import asyncio
from src.tools.atomic.ffiec_call_report_data_tool import FFIECCallReportDataTool
from src.config.settings import get_settings

async def test_api():
    settings = get_settings()
    if not settings.ffiec_cdr_api_key:
        print('FFIEC API key not configured')
        return
        
    tool = FFIECCallReportDataTool(settings=settings) 
    
    # Test with Wells Fargo RSSD ID
    result = await tool._arun('451965')
    print(f'API test result: {len(result) > 100}')  # Should have substantial response
    
asyncio.run(test_api())
"
```

## Final Validation Checklist
- [ ] All tests pass: `python -m pytest tests/tools/ffiec/ -v`
- [ ] No linting errors: `ruff check src/tools/ --fix`
- [ ] No type errors: `mypy src/tools/atomic/ffiec_call_report_data_tool.py`
- [ ] SOAP client handles authentication correctly
- [ ] Discovery logic finds latest filings for test banks  
- [ ] Caching prevents redundant API calls during session
- [ ] **Tool is registered**: FFIECCallReportDataTool appears in atomic tools __init__.py
- [ ] **Banking toolset integration**: Tool loads when ffiec_cdr_enabled is True
- [ ] **System prompts updated**: Call report routing pattern appears in agent system prompt
- [ ] **AI agent awareness**: Agent recognizes call report queries and routes to correct tool  
- [ ] Tool integrates with bank analysis workflow
- [ ] Error handling covers SOAP faults and API failures
- [ ] API credentials are stored securely in Key Vault
- [ ] Integration with existing FDIC tools works seamlessly
- [ ] All file sizes are under 500 lines (split if needed)
- [ ] Structured logging follows project patterns

---

## Anti-Patterns to Avoid
- ❌ Don't use synchronous SOAP calls - handle zeep async caveat properly
- ❌ Don't store API credentials in code - use Key Vault integration  
- ❌ Don't ignore SOAP fault handling - implement comprehensive error handling
- ❌ Don't cache call report data permanently - use session-based caching only
- ❌ Don't bypass discovery logic - always check for latest filings intelligently
- ❌ Don't use float for financial data - use Decimal and proper data types
- ❌ Don't skip input validation - validate RSSD IDs and parameters
- ❌ Don't create oversized files - split into focused modules under 500 lines
- ❌ Don't ignore existing patterns - follow established atomic tool architecture
- ❌ Don't skip integration testing - ensure composite tool integration works

## PRP Confidence Score: 9.5/10

This PRP provides comprehensive context including:
✅ Complete FFIEC CDR API research with WSDL analysis  
✅ Thorough existing codebase pattern analysis  
✅ SOAP client implementation strategy with async handling
✅ Security configuration following Key Vault patterns
✅ Integration approach with existing bank analysis tools
✅ **Tool registration and system prompt integration patterns**
✅ **AI agent awareness through routing pattern updates**
✅ Comprehensive error handling and edge case coverage
✅ Detailed task breakdown with validation gates
✅ Test strategy covering unit, integration, and E2E scenarios  
✅ Clear implementation path with progressive complexity
✅ Anti-patterns and gotchas clearly identified

The high confidence score reflects extensive research into both FFIEC API requirements and existing codebase patterns, with complete tool registration and AI agent integration, providing a clear implementation path with multiple validation checkpoints for success.

<function_calls>
<invoke name="TodoWrite">
<parameter name="todos">[{"content": "Research existing codebase patterns for atomic tools and infrastructure", "status": "completed"}, {"content": "Analyze FFIEC CDR API structure and capabilities", "status": "completed"}, {"content": "Research SOAP client best practices with asyncio", "status": "completed"}, {"content": "Examine existing call report test fixtures and infrastructure", "status": "completed"}, {"content": "Create comprehensive PRP with all necessary context and validation gates", "status": "completed"}]