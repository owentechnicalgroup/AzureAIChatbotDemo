name: "AGENT_CALL_REPORT_TOOLING PRP v2 - Context-Rich with Validation Loops"
description: |

## Purpose
Implement a comprehensive Call Report Data API tooling system that provides AI agents with access to FFIEC Call Report data through a mock service API, enabling automated calculation of financial ratios like Return on Assets (ROA) and other metrics based on banking policy documents stored in the RAG system.

## Core Principles
1. **Context is King**: Include ALL necessary documentation, examples, and caveats
2. **Validation Loops**: Provide executable tests/lints the AI can run and fix
3. **Information Dense**: Use keywords and patterns from the codebase
4. **Progressive Success**: Start simple, validate, then enhance
5. **Global rules**: Be sure to follow all rules in CLAUDE.md

---

## Goal
Build a complete Call Report tooling system that:
- Provides mock FFIEC Call Report API service
- Integrates with existing AI agent through LangChain tools
- Enables automated financial ratio calculations
- Cross-references with RAG document information
- Follows project's established patterns for tools, logging, and configuration

## Why
- **Business value**: Enables AI agent to perform quantitative financial analysis by combining policy documents with actual bank data
- **Integration**: Seamlessly works with existing RAG system and Azure OpenAI agent
- **Problems solved**: Eliminates manual Call Report data lookup and ratio calculations for banking analysis workflows
- **User impact**: Provides comprehensive financial analysis combining regulatory data with policy guidance

## What
User-visible behavior: AI agent can look up bank information, retrieve Call Report data, calculate financial ratios, and provide analysis combining quantitative data with policy document guidance.

Technical requirements:
- Mock Call Report API with realistic FFIEC data structure
- LangChain tool wrappers for AI agent integration
- Financial ratio calculation framework
- Bank entity lookup capabilities
- Integration with existing RAG system
- Proper error handling and logging

### Success Criteria
- [ ] AI agent can lookup banks by legal name and get Legal Entity Identifier
- [ ] AI agent can retrieve Call Report data for specific schedules and fields
- [ ] AI agent can calculate ROA and other ratios using retrieved data
- [ ] System integrates with existing RAG documents for policy-driven analysis
- [ ] All tools follow project's logging and error handling patterns
- [ ] Comprehensive test coverage with validation gates

## All Needed Context

### Documentation & References (list all context needed to implement the feature)
```yaml
# MUST READ - Include these in your context window
- url: https://python.langchain.com/docs/how_to/function_calling/
  why: LangChain tool implementation patterns, @tool decorator, binding mechanisms
  
- url: https://python.langchain.com/docs/concepts/tool_calling/
  why: Tool architecture, best practices, error handling patterns

- url: https://github.com/call-report/ffiec-data-connect
  why: Real FFIEC API structure, authentication patterns, data format examples
  
- url: https://bankontology.com/ffiec-031-call-report/
  why: Schedule identifiers (RC, RI, RCA), field naming conventions (RCON, RCONF, RSSD)
  
- url: https://corporatefinanceinstitute.com/resources/accounting/return-on-assets-roa-formula/
  why: ROA calculation formula (Net Income / Total Assets), financial analysis best practices

- file: src/tools/base.py
  why: BaseTool abstract class pattern, ToolExecutionResult, ToolRegistry architecture
  
- file: src/tools/ratings_tool.py
  why: Complete tool implementation example with API integration, error handling, schema definition
  
- file: src/rag/tools_integration.py
  why: RAG integration patterns, hybrid responses, tool execution in agent context
  
- file: src/config/settings.py
  why: Configuration patterns, environment variables, Pydantic field definitions
  
- file: tests/conftest.py
  why: Test fixture patterns, mock implementations, test data structures
  
- file: tests/test_document_processor.py
  why: Testing patterns for async functions, mock usage, assertion patterns

- doc: https://fastapi.tiangolo.com/tutorial/extra-models/
  section: Pydantic model patterns for financial data
  critical: Data validation and schema design for complex financial structures

- docfile: AGENT_CALL_REPORT_TOOLING.md
  why: Feature requirements and specifications
```

### Current Codebase tree (run `tree` in the root of the project) to get an overview of the codebase
```bash
src/
├── tools/
│   ├── __init__.py
│   ├── base.py              # BaseTool, ToolExecutionResult, ToolRegistry
│   └── ratings_tool.py      # Example tool implementation
├── rag/
│   ├── tools_integration.py # RAG + tools hybrid system
│   ├── vector_store.py      # ChromaDB integration
│   └── retriever.py         # Document retrieval
├── config/
│   └── settings.py          # Pydantic settings with Key Vault
├── observability/
│   └── logging_helpers.py   # Structured logging utilities
└── utils/
    └── error_handlers.py    # Error handling patterns
```

### Desired Codebase tree with files to be added and responsibility of file
```bash
src/tools/call_report/
├── __init__.py                    # Package initialization, exports
├── data_models.py                 # Pydantic models for Call Report data structures
├── mock_api_client.py            # Mock FFIEC Call Report API service implementation
├── langchain_tools.py            # LangChain tool wrappers for AI agent
├── bank_lookup.py                # Bank entity lookup and validation
└── constants.py                  # FFIEC constants, schedules, field mappings

src/rag/
├── prompts/
│   └── call_report_instructions.py # Enhanced system prompts with ratio calculation workflows

tests/tools/call_report/
├── __init__.py
├── test_data_models.py           # Test Pydantic models and validation
├── test_mock_api_client.py       # Test mock API responses and error cases
├── test_langchain_tools.py       # Test tool integration and schemas
└── fixtures.py                   # Test fixtures and sample data
```

### Known Gotchas of our codebase & Library Quirks
```python
# CRITICAL: Project enforces 500-line limit per file - split into modules if approaching
# CRITICAL: All tools must inherit from BaseTool and implement execute() and get_schema()
# CRITICAL: Use structured logging with log_type field: logger.bind(log_type="SYSTEM")
# CRITICAL: All environment variables must be added to 3 places:
#   1. infrastructure/outputs.tf
#   2. scripts/setup-env.ps1 
#   3. src/config/settings.py
# CRITICAL: Use async/await for all tool execution methods
# CRITICAL: LangChain tools use @tool decorator or inherit from BaseTool
# CRITICAL: Tool schemas must follow OpenAI function calling format
# CRITICAL: Mock data should be realistic but clearly not production data
# CRITICAL: Follow existing error handling patterns with ToolExecutionResult
# CRITICAL: Integration with RAG requires ChromaDBManager for document cross-reference
```

## Implementation Blueprint

### Data models and structure

Create the core data models to ensure type safety and consistency.
```python
# Core Pydantic models for Call Report data
class CallReportField(BaseModel):
    field_id: str  # e.g., "RCON2170" 
    field_name: str  # e.g., "Total Assets"
    value: Optional[Decimal]
    schedule: str  # e.g., "RC"
    
class BankIdentification(BaseModel):
    legal_name: str
    rssd_id: str  # Legal Entity Identifier
    fdic_cert_id: Optional[str]
    
class CallReportData(BaseModel):
    bank_id: str
    report_date: date
    fields: List[CallReportField]
    
class FinancialRatio(BaseModel):
    ratio_name: str
    value: Optional[Decimal]
    components: Dict[str, Decimal]  # Source fields used
    calculation_method: str
```

### list of tasks to be completed to fullfill the PRP in the order they should be completed

```yaml
Task 1: Create Call Report Data Models
CREATE src/tools/call_report/__init__.py:
  - IMPORT and expose main classes
  - FOLLOW pattern from: src/tools/__init__.py

CREATE src/tools/call_report/constants.py:
  - DEFINE FFIEC schedule mappings (RC, RI, RCA, etc.)
  - DEFINE field name to ID mappings (RCON, RCONF, RSSD)
  - MIRROR pattern from existing constants in codebase

CREATE src/tools/call_report/data_models.py:
  - IMPLEMENT Pydantic models for Call Report structures
  - USE Decimal for financial values (not float)
  - FOLLOW validation patterns from src/config/settings.py

Task 2: Implement Mock API Client
CREATE src/tools/call_report/mock_api_client.py:
  - INHERIT from BaseTool architecture
  - IMPLEMENT realistic mock data generation
  - FOLLOW async patterns from src/tools/ratings_tool.py
  - INCLUDE proper error handling with ToolExecutionResult

Task 3: Implement Bank Lookup Service
CREATE src/tools/call_report/bank_lookup.py:
  - IMPLEMENT legal name to RSSD ID mapping
  - USE realistic but fake bank data
  - FOLLOW error handling patterns from existing tools
  - INCLUDE fuzzy matching for bank names

Task 4: Create Enhanced AI System Prompts with Ratio Workflows
CREATE src/rag/prompts/call_report_instructions.py:
  - IMPLEMENT system prompt templates with financial ratio calculation workflows
  - DEFINE step-by-step procedures for ROA and other ratio calculations
  - INCLUDE field mapping guidance (Net Income -> RI schedule, Total Assets -> RC schedule)
  - CREATE workflow templates that instruct AI to use Call Report tools sequentially
  - INTEGRATE with RAG document context for policy-driven ratio selection
  - FOLLOW existing prompt pattern from src/rag/tools_integration.py

MODIFY src/rag/tools_integration.py:
  - ENHANCE _create_system_prompt() method with call report ratio workflows
  - INCLUDE ratio calculation instructions and field mapping guidance
  - ADD context-aware prompting for financial analysis scenarios

Task 5: Implement LangChain Tool Wrappers
CREATE src/tools/call_report/langchain_tools.py:
  - INHERIT from BaseTool class
  - IMPLEMENT @tool decorators for each function
  - CREATE OpenAI function schemas for each tool
  - FOLLOW integration patterns from src/rag/tools_integration.py
  - REGISTER tools with ToolRegistry

Task 6: Update Configuration and Registration
MODIFY src/config/settings.py:
  - ADD call_report_enabled: bool setting
  - ADD call_report_timeout_seconds: int setting
  - FOLLOW existing patterns for tool configuration

MODIFY src/tools/__init__.py:
  - IMPORT CallReportTools
  - REGISTER with ToolRegistry if enabled

Task 7: Create Comprehensive Test Suite
CREATE tests/tools/call_report/fixtures.py:
  - GENERATE realistic test data
  - FOLLOW patterns from tests/conftest.py

CREATE test files for each module:
  - MIRROR testing patterns from existing tests
  - INCLUDE happy path, edge cases, and error scenarios
  - USE pytest fixtures and async test patterns
  - CREATE tests for AI prompt workflow effectiveness (integration tests)
```

### Per task pseudocode as needed added to each task

```python
# Task 2: Mock API Client Architecture
class CallReportMockAPI(BaseTool):
    def __init__(self):
        super().__init__(name="call_report_api", description="Mock FFIEC Call Report API")
        # PATTERN: Load mock data from constants
        self.mock_data = self._load_mock_data()
    
    async def execute(self, rssd_id: str, schedule: str, field_id: str) -> ToolExecutionResult:
        # PATTERN: Always validate input first
        validated = self._validate_inputs(rssd_id, schedule, field_id)
        
        # CRITICAL: Check if bank exists in mock data
        if rssd_id not in self.mock_data:
            return ToolExecutionResult(
                status=ToolStatus.ERROR,
                error=f"Bank with RSSD ID {rssd_id} not found"
            )
        
        # PATTERN: Use existing error handling
        try:
            field_data = self._get_field_data(rssd_id, schedule, field_id)
            return ToolExecutionResult(
                status=ToolStatus.SUCCESS,
                data=field_data
            )
        except Exception as e:
            return ToolExecutionResult(
                status=ToolStatus.ERROR,
                error=str(e)
            )

# Task 4: Enhanced AI System Prompts with Financial Ratio Workflows
class CallReportInstructions:
    """System prompt templates for Call Report financial analysis workflows."""
    
    @staticmethod
    def get_ratio_calculation_workflow() -> str:
        return """
FINANCIAL RATIO CALCULATION WORKFLOW:

When asked to calculate financial ratios for banks, follow this step-by-step process:

1. IDENTIFY THE BANK:
   - Use bank_lookup tool to find the Legal Entity Identifier (RSSD ID) from the bank's legal name
   - If bank not found, inform user and suggest similar bank names if available

2. DETERMINE REQUIRED FIELDS:
   - ROA (Return on Assets): Need Net Income (RIAD4340 from RI schedule) and Total Assets (RCON2170 from RC schedule)
   - ROE (Return on Equity): Need Net Income (RIAD4340) and Total Equity (RCON3210 from RC schedule)
   - Tier 1 Capital Ratio: Need Tier 1 Capital (RCON8274) and Risk-Weighted Assets (RCON0023)

3. RETRIEVE CALL REPORT DATA:
   - Use call_report_data tool with bank's RSSD ID, schedule, and field ID
   - Always check if data retrieval was successful before proceeding
   - Handle missing data gracefully - inform user which fields are unavailable

4. PERFORM CALCULATIONS:
   - ROA = (Net Income / Total Assets) × 100
   - ROE = (Net Income / Total Equity) × 100  
   - Always check for division by zero
   - Round results to appropriate decimal places (typically 2 for percentages)

5. CONTEXTUALIZE WITH POLICY DOCUMENTS:
   - Reference retrieved banking policy documents for ratio interpretation
   - Include regulatory benchmarks and thresholds from RAG context
   - Explain what the calculated ratios indicate about bank performance

6. ERROR HANDLING:
   - If API is unavailable: "Cannot retrieve Call Report data at this time"
   - If data missing: "Required data for [ratio] calculation is not available for [bank]"
   - If calculation invalid: "Cannot calculate [ratio]: [specific reason]"

EXAMPLE WORKFLOW EXECUTION:
User: "Calculate ROA for Wells Fargo"
1. bank_lookup("Wells Fargo") → RSSD ID: 451965
2. call_report_data(rssd_id="451965", schedule="RI", field_id="RIAD4340") → Net Income: $22,183M
3. call_report_data(rssd_id="451965", schedule="RC", field_id="RCON2170") → Total Assets: $1,948,934M  
4. Calculate: ROA = (22,183 / 1,948,934) × 100 = 1.14%
5. Context: "According to banking regulations, ROA above 1.0% is considered healthy..."
"""

    @staticmethod  
    def get_field_mapping_guide() -> str:
        return """
FFIEC CALL REPORT FIELD MAPPING GUIDE:

BALANCE SHEET (RC Schedule):
- Total Assets: RCON2170
- Total Liabilities: RCON2948  
- Total Equity: RCON3210
- Cash and Due from Banks: RCON0010
- Securities: RCON0009 + RCON1773

INCOME STATEMENT (RI Schedule):  
- Net Income: RIAD4340
- Interest Income: RIAD4107
- Interest Expense: RIAD4073
- Provision for Loan Losses: RIAD4230
- Noninterest Income: RIAD4079

CAPITAL ADEQUACY (RC-R Schedule):
- Tier 1 Capital: RCON8274
- Total Capital: RCON8275
- Risk-Weighted Assets: RCON0023

ASSET QUALITY (RC-N Schedule):
- Past Due 30-89 Days: RCON5525
- Past Due 90+ Days: RCON5526
- Nonaccrual Loans: RCON5527
"""

# Task 5: LangChain Tool Integration Pattern
class CallReportToolset:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.api_client = CallReportMockAPI()
        
    def get_tools(self) -> List[BaseTool]:
        """Get all Call Report tools for LangChain integration."""
        # Note: No dedicated calculation tool - AI uses workflow instructions
        return [
            BankLookupTool(),
            CallReportDataTool(self.api_client),
        ]
    
    def register_with_agent(self, tool_registry: ToolRegistry):
        """Register tools with the agent's tool registry."""
        if not self.settings.enable_tools:
            return
            
        for tool in self.get_tools():
            tool_registry.register_tool(tool)

# Task 5: Enhanced System Prompt Integration  
class EnhancedRAGRetriever(ToolsIntegratedRAGRetriever):  
    def _create_system_prompt(self) -> str:
        """Enhanced system prompt with Call Report workflow instructions."""
        base_prompt = super()._create_system_prompt()
        
        call_report_instructions = CallReportInstructions.get_ratio_calculation_workflow()
        field_mapping = CallReportInstructions.get_field_mapping_guide()
        
        enhanced_prompt = f"""{base_prompt}

SPECIALIZED CALL REPORT ANALYSIS CAPABILITIES:
You have access to FFIEC Call Report data through specialized tools. When performing financial analysis:

{call_report_instructions}

{field_mapping}

IMPORTANT: You do NOT have a dedicated ratio calculation tool. Instead:
1. Use the bank_lookup and call_report_data tools to retrieve raw data
2. Perform calculations manually following the workflows above
3. Always show your calculation steps to the user
4. Cross-reference results with policy documents from RAG when available
"""
        return enhanced_prompt
```

### Integration Points
```yaml
DATABASE:
  - No database changes required (mock data in memory)
  
CONFIG:
  - add to: src/config/settings.py
  - pattern: "call_report_enabled: bool = Field(True, env='ENABLE_CALL_REPORT_TOOLS')"
  - pattern: "call_report_timeout_seconds: int = Field(30, env='CALL_REPORT_TIMEOUT')"
  
ENVIRONMENT:
  - add to: scripts/setup-env.ps1
  - add to: infrastructure/outputs.tf if needed for API keys
  
TOOL_REGISTRY:
  - modify: src/tools/__init__.py
  - pattern: "if settings.call_report_enabled: registry.register_tool(CallReportTools())"
  
RAG_INTEGRATION:
  - modify: src/rag/tools_integration.py 
  - pattern: "register call report tools in _register_tools() method"
```

## Validation Loop

### Level 1: Syntax & Style
```bash
# Run these FIRST - fix any errors before proceeding
ruff check src/tools/call_report/ --fix  # Auto-fix what's possible
mypy src/tools/call_report/            # Type checking

# Expected: No errors. If errors, READ the error and fix.
```

### Level 2: Unit Tests each new feature/file/function use existing test patterns
```python
# CREATE comprehensive test suite following existing patterns

# tests/tools/call_report/test_data_models.py
def test_call_report_field_validation():
    """Test Pydantic model validation for Call Report fields"""
    field = CallReportField(
        field_id="RCON2170",
        field_name="Total Assets", 
        value=Decimal("1000000.00"),
        schedule="RC"
    )
    assert field.field_id == "RCON2170"
    assert field.value == Decimal("1000000.00")

def test_invalid_decimal_raises_error():
    """Test that invalid decimal values raise ValidationError"""
    with pytest.raises(ValidationError):
        CallReportField(
            field_id="RCON2170",
            field_name="Total Assets",
            value="invalid_decimal",  # Should fail
            schedule="RC"
        )

# tests/tools/call_report/test_mock_api_client.py
@pytest.mark.asyncio
async def test_api_client_success():
    """Test successful API client call"""
    client = CallReportMockAPI()
    result = await client.execute(
        rssd_id="123456",
        schedule="RC", 
        field_id="RCON2170"
    )
    assert result.success
    assert "value" in result.data

@pytest.mark.asyncio
async def test_api_client_bank_not_found():
    """Test API client with non-existent bank"""
    client = CallReportMockAPI()
    result = await client.execute(
        rssd_id="999999",
        schedule="RC",
        field_id="RCON2170"
    )
    assert not result.success
    assert "not found" in result.error

# tests/tools/call_report/test_prompt_integration.py
@pytest.mark.asyncio
async def test_ai_workflow_roa_calculation():
    """Test AI agent following ROA calculation workflow"""
    # Mock API responses for realistic workflow test
    with patch('call_report.mock_api_client.CallReportMockAPI') as mock_api:
        # Mock bank lookup
        mock_api.return_value.bank_lookup.return_value = ToolExecutionResult(
            status=ToolStatus.SUCCESS, 
            data={"rssd_id": "123456", "legal_name": "Test Bank"}
        )
        
        # Mock Call Report data retrieval
        mock_api.return_value.execute.side_effect = [
            ToolExecutionResult(status=ToolStatus.SUCCESS, data={"value": Decimal("50000")}),  # Net Income
            ToolExecutionResult(status=ToolStatus.SUCCESS, data={"value": Decimal("1000000")}), # Total Assets
        ]
        
        # Test that AI can follow workflow to calculate ROA
        retriever = EnhancedRAGRetriever(mock_settings)
        response = await retriever.generate_response("Calculate ROA for Test Bank")
        
        # Verify workflow steps were followed
        assert "1.14%" in response.answer or "5.0%" in response.answer  # Expected ROA result
        assert "Net Income" in response.answer
        assert "Total Assets" in response.answer
        assert "RSSD ID" in response.answer or "123456" in response.answer

@pytest.mark.asyncio  
async def test_ai_workflow_missing_data_handling():
    """Test AI agent handling missing Call Report data"""
    with patch('call_report.mock_api_client.CallReportMockAPI') as mock_api:
        # Mock failed data retrieval
        mock_api.return_value.execute.return_value = ToolExecutionResult(
            status=ToolStatus.ERROR,
            error="Required data not available"
        )
        
        retriever = EnhancedRAGRetriever(mock_settings)
        response = await retriever.generate_response("Calculate ROA for Test Bank")
        
        # Verify proper error handling
        assert "not available" in response.answer.lower()
        assert "cannot calculate" in response.answer.lower() or "unable to calculate" in response.answer.lower()
```

```bash
# Run and iterate until passing:
python -m pytest tests/tools/call_report/ -v
# If failing: Read error, understand root cause, fix code, re-run
```

### Level 3: Integration Test
```bash
# Test LangChain tool integration
python -c "
from src.tools.call_report import CallReportToolset
from src.config.settings import get_settings

settings = get_settings()
toolset = CallReportToolset(settings)
tools = toolset.get_tools()
print(f'Registered {len(tools)} Call Report tools')

# Test tool schema generation
for tool in tools:
    schema = tool.get_schema()
    print(f'Tool: {tool.name}, Schema valid: {\"function\" in schema}')
"

# Test RAG integration
python -c "
from src.rag.tools_integration import ToolsIntegratedRAGRetriever
from src.config.settings import get_settings

settings = get_settings()
retriever = ToolsIntegratedRAGRetriever(settings)
response = await retriever.generate_response('Calculate ROA for Wells Fargo')
print(f'Response generated: {len(response.answer) > 0}')
"
```

## Final validation Checklist
- [ ] All tests pass: `python -m pytest tests/tools/call_report/ -v`
- [ ] No linting errors: `ruff check src/tools/call_report/`
- [ ] No type errors: `mypy src/tools/call_report/`
- [ ] Tools register correctly with ToolRegistry
- [ ] Tools integrate with RAG system for hybrid responses
- [ ] Mock API provides realistic Call Report data
- [ ] AI agent follows ratio calculation workflows correctly (integration tests)
- [ ] AI agent performs calculations manually and shows work
- [ ] Error messages are clear and actionable for missing data scenarios
- [ ] System prompts include comprehensive field mapping and workflow guidance
- [ ] Logging follows project's structured logging patterns
- [ ] Configuration variables added to all required files

---

## Anti-Patterns to Avoid
- ❌ Don't use float for financial calculations - use Decimal
- ❌ Don't hardcode bank data - use realistic mock data patterns
- ❌ Don't skip input validation - always validate before processing
- ❌ Don't ignore FFIEC naming conventions - use proper field IDs
- ❌ Don't create tools without proper OpenAI function schemas
- ❌ Don't bypass existing error handling patterns
- ❌ Don't exceed 500-line file limit - split into multiple modules
- ❌ Don't skip RAG integration - tools should work with document context
- ❌ Don't create synchronous tools - use async/await patterns
- ❌ Don't forget to register tools with the agent's ToolRegistry
- ❌ Don't create dedicated calculation tools - let AI perform calculations following workflows
- ❌ Don't hide calculation steps from users - always show the work
- ❌ Don't create vague system prompts - provide detailed step-by-step workflows

## PRP Confidence Score: 9/10

This PRP provides comprehensive context including:
✅ Complete codebase analysis with existing patterns
✅ External API research with real FFIEC structure
✅ Financial calculation formulas and best practices  
✅ LangChain tool implementation patterns
✅ Detailed task breakdown with validation gates
✅ Realistic mock data approaches
✅ Integration points with existing systems
✅ Comprehensive test coverage strategy
✅ Clear error handling requirements
✅ Configuration management patterns

The high confidence score reflects thorough research into both the existing codebase patterns and external requirements, providing a clear implementation path with validation loops.