name: "LANGCHAIN_TOOLS_ARCHITECTURE_ENHANCEMENT PRP v2 - Context-Rich with Validation Loops"
description: |

## Purpose
Enhance the LangChain tools architecture to provide unified tool discovery, domain-based categorization, dynamic tool loading, and comprehensive testing. This solves the current issues with missing RAG tool registration, fragmented tool interfaces, and lack of conversation simulation testing.

## Core Principles
1. **Context is King**: Include ALL necessary documentation, examples, and caveats
2. **Validation Loops**: Provide executable tests/lints the AI can run and fix
3. **Information Dense**: Use keywords and patterns from the codebase
4. **Progressive Success**: Start simple, validate, then enhance
5. **Global rules**: Be sure to follow all rules in CLAUDE.md

---

## Goal
Create a unified LangChain-based tools architecture that:
- Provides unified tool discovery through single interface
- Groups tools by domain (Banking, Documents, Analysis)
- Enables dynamic tool loading based on available data/services
- Registers missing RAG tool for document search
- Includes conversation simulation tests
- Refactors existing Call Report tools to be compliant with enhanced architecture

## Why
- **Business value**: Enables seamless multi-domain AI conversations combining banking data, document analysis, and computational tools
- **Integration**: Eliminates the current dual-architecture confusion between custom BaseTool and LangChain tools
- **Problems solved**: Fixes missing RAG tool registration, provides domain-based tool organization, enables data-driven tool availability
- **User impact**: Users get unified AI assistant that can search documents, analyze financial data, and perform calculations in single conversations

## What
User-visible behavior: AI agent can seamlessly switch between document search, banking data analysis, and other tool categories within a single conversation flow. Tools are automatically available based on data availability.

Technical requirements:
- Enhanced LangChainToolRegistry with category support
- Dynamic tool loading based on service availability
- RAG tool registration for document search
- Tool domain categorization system
- Conversation simulation testing framework
- Refactored Call Report tools for compliance
- Backward compatibility with existing patterns

### Success Criteria
- [ ] RAG tool (document_search) is registered and working with ChatbotAgent
- [ ] Tools are organized into categories (Banking, Documents, Analysis) 
- [ ] Tools load dynamically based on data/service availability
- [ ] Conversation simulation tests cover multi-tool scenarios
- [ ] Single interface for all tool discovery and registration
- [ ] Backward compatibility with existing Call Report tools maintained
- [ ] Agent can use multiple tool categories in single conversation

## All Needed Context

### Documentation & References (list all context needed to implement the feature)
```yaml
# MUST READ - Include these in your context window
- url: https://python.langchain.com/docs/concepts/tools/
  why: LangChain tool architecture, BaseTool patterns, tool creation best practices

- url: https://python.langchain.com/docs/concepts/tool_calling/
  why: OpenAI function calling integration, tool schemas, parameter validation

- url: https://python.langchain.com/docs/concepts/agents/
  why: Agent-tool integration patterns, AgentExecutor usage, multi-step workflows

- url: https://python.langchain.com/docs/how_to/tool_calling/
  why: Practical tool implementation examples, error handling patterns

- file: src/rag/langchain_tools.py
  why: Current LangChainToolRegistry implementation - base for enhancement, existing patterns

- file: src/tools/base.py
  why: Custom BaseTool architecture to understand compatibility requirements

- file: src/rag/rag_tool.py  
  why: RAGSearchTool implementation that needs registration - fully implemented but missing

- file: src/tools/call_report/langchain_tools.py
  why: Call Report tools implementation patterns, toolset organization

- file: src/chatbot/agent.py
  why: ChatbotAgent integration with tools, AgentExecutor setup, multi-step processing

- file: src/ui/streamlit_app.py
  why: Tool initialization in UI, session state management with tools

- file: tests/test_rag_chatbot_agent.py
  why: Testing patterns for agent-tool interactions, async test patterns

- file: use-cases/pydantic-ai/examples/tool_enabled_agent/agent.py
  why: Tool-enabled agent patterns, @agent.tool decorator usage, dependency injection

- doc: https://docs.pydantic.dev/latest/concepts/models/
  section: Model validation and schema generation
  critical: Type safety for tool parameters and responses

- docfile: PRPs/agent-call-report-tooling.md
  why: Previous tool implementation patterns and architectural decisions
```

### Current Codebase tree (run `tree src/` to get current structure)
```bash
src/
├── chatbot/
│   ├── agent.py                    # ChatbotAgent with AgentExecutor and tool support
│   └── prompts.py
├── rag/
│   ├── langchain_tools.py          # LangChainToolRegistry - needs enhancement
│   ├── rag_tool.py                 # RAGSearchTool - exists but not registered!
│   ├── retriever.py                # RAG retrieval logic
│   └── chromadb_manager.py         # Document storage
├── tools/
│   ├── base.py                     # Custom BaseTool architecture (dual-architecture issue)
│   ├── __init__.py                 # Tool exports and imports
│   ├── call_report/                # Call Report toolset
│   │   ├── langchain_tools.py      # LangChain wrappers for Call Report
│   │   ├── mock_api_client.py      # Mock banking data API
│   │   └── bank_lookup.py          # Bank identification service
│   └── ratings_tool.py             # Example tool (currently unused)
├── ui/
│   └── streamlit_app.py            # Tool initialization and agent setup
└── config/
    └── settings.py                 # Configuration management
```

### Desired Codebase tree with files to be added and responsibility of file
```bash
src/
├── rag/
│   ├── langchain_tools.py          # ENHANCED: Categorized registry with dynamic loading
│   └── rag_tool.py                 # UNCHANGED: RAGSearchTool (will be registered)
├── tools/
│   ├── categories.py               # NEW: Tool category system and enums
│   ├── dynamic_loader.py           # NEW: Dynamic tool loading based on availability
│   ├── base.py                     # ENHANCED: Bridge for backward compatibility
│   └── call_report/
│       └── langchain_tools.py      # REFACTORED: Enhanced for category compliance
├── chatbot/
│   └── agent.py                    # ENHANCED: Category-aware tool integration
└── ui/
    └── streamlit_app.py            # ENHANCED: Dynamic tool loading in UI

tests/tools/
├── __init__.py                     # NEW: Test package initialization
├── test_tool_categories.py         # NEW: Category system tests
├── test_dynamic_loading.py         # NEW: Dynamic loading tests
├── test_langchain_registry.py      # NEW: Enhanced registry tests
└── conversation_simulations/       # NEW: Conversation simulation tests
    ├── __init__.py
    ├── test_multi_tool_scenarios.py # NEW: Multi-tool conversation tests
    ├── test_banking_document_flow.py # NEW: Banking + document search tests
    └── fixtures/                   # NEW: Test conversation fixtures
        └── conversation_data.py
```

### Known Gotchas of our codebase & Library Quirks
```python
# CRITICAL: Project enforces 500-line limit per file - split enhanced registry if needed
# CRITICAL: All tools must work with ChatbotAgent's AgentExecutor pattern
# CRITICAL: Use structured logging with log_type field: logger.bind(log_type="SYSTEM")
# CRITICAL: RAG tool exists at src/rag/rag_tool.py but is NOT registered - this is the key issue
# CRITICAL: LangChain tools use different signatures than custom BaseTool
# CRITICAL: AsyncCallbackManagerForToolRun vs CallbackManagerForToolRun patterns
# CRITICAL: Tool schemas must follow OpenAI function calling format exactly
# CRITICAL: Agent memory management with ConversationBufferWindowMemory in agent.py:194-199
# CRITICAL: Streamlit session state management for tools in streamlit_app.py:75-86
# CRITICAL: Multi-step agent mode is enabled by default in streamlit_app.py:85
# CRITICAL: Tool execution happens in async context - all tools must support async patterns
# CRITICAL: Error handling must return ToolExecutionResult format for compatibility
# CRITICAL: ChromaDB availability affects RAG tool availability - check in dynamic loader
# CRITICAL: Call Report tools use mock data - must maintain this pattern for testing
```

## Implementation Blueprint

### Data models and structure

Create core models for tool categorization and dynamic loading.
```python
# Tool category system for domain organization
from enum import Enum
from typing import List, Dict, Any, Optional, Set
from pydantic import BaseModel, Field
from langchain.tools import BaseTool

class ToolCategory(str, Enum):
    """Tool categories for domain-based organization."""
    DOCUMENTS = "documents"      # RAG document search, file processing
    BANKING = "banking"          # Call Report, financial analysis
    ANALYSIS = "analysis"        # Calculations, data processing  
    WEB = "web"                  # Web search, external APIs
    UTILITIES = "utilities"      # Time, formatting, general tools

class ToolMetadata(BaseModel):
    """Enhanced metadata for categorized tools."""
    name: str
    description: str
    category: ToolCategory
    requires_data: Optional[List[str]] = None  # Data dependencies for dynamic loading
    priority: int = 0  # Loading priority within category
    tags: List[str] = Field(default_factory=list)
    
class CategoryConfig(BaseModel):
    """Configuration for tool category behavior."""
    category: ToolCategory
    enabled: bool = True
    max_tools: Optional[int] = None
    load_order: int = 0
```

### List of tasks to be completed to fulfill the PRP in the order they should be completed

```yaml
Task 1: Create Tool Category System
CREATE src/tools/categories.py:
  - IMPLEMENT ToolCategory enum with domain classifications
  - IMPLEMENT ToolMetadata model for enhanced tool information
  - IMPLEMENT CategoryConfig for category-level configuration
  - FOLLOW patterns from: src/tools/base.py and existing Pydantic models

Task 2: Create Dynamic Tool Loader
CREATE src/tools/dynamic_loader.py:
  - IMPLEMENT service availability detection (ChromaDB, Call Report API)
  - IMPLEMENT dynamic tool registration based on data availability
  - IMPLEMENT dependency checking for tool requirements
  - FOLLOW async patterns from: src/rag/retriever.py

Task 3: Enhance LangChainToolRegistry with Categories
MODIFY src/rag/langchain_tools.py:
  - EXTEND LangChainToolRegistry to support ToolCategory system
  - IMPLEMENT get_tools_by_category() method
  - IMPLEMENT dynamic tool loading integration
  - ADD RAG tool registration (CRITICAL FIX)
  - PRESERVE existing Call Report tool integration patterns

Task 4: Refactor Call Report Tools for Category Compliance
MODIFY src/tools/call_report/langchain_tools.py:
  - ADD category metadata to CallReportDataTool and BankLookupTool
  - IMPLEMENT ToolCategory.BANKING classification
  - ENHANCE availability detection for dynamic loading
  - PRESERVE all existing functionality and schemas

Task 5: Enhance ChatbotAgent for Category-Aware Tool Integration
MODIFY src/chatbot/agent.py:
  - IMPLEMENT category-based tool filtering
  - ENHANCE system prompt with category-specific instructions
  - ADD tool usage statistics by category
  - PRESERVE existing AgentExecutor patterns and multi-step functionality

Task 6: Update UI for Dynamic Tool Loading
MODIFY src/ui/streamlit_app.py:
  - IMPLEMENT dynamic tool initialization based on data availability
  - ADD tool category display in system status
  - ENHANCE tool registry initialization with category support
  - PRESERVE existing session state management patterns

Task 7: Create Comprehensive Test Suite
CREATE tests/tools/test_tool_categories.py:
  - TEST ToolCategory system and metadata validation
  - TEST tool categorization accuracy

CREATE tests/tools/test_dynamic_loading.py:
  - TEST dynamic tool loading based on service availability
  - TEST tool dependency checking and resolution

CREATE tests/tools/test_langchain_registry.py:
  - TEST enhanced LangChainToolRegistry with category support
  - TEST RAG tool registration (critical validation)
  - TEST tool discovery by category

Task 8: Create Conversation Simulation Tests
CREATE tests/tools/conversation_simulations/test_multi_tool_scenarios.py:
  - SIMULATE conversations that trigger multiple tool categories
  - TEST seamless switching between document search and banking tools
  - VALIDATE tool selection logic and execution flow

CREATE tests/tools/conversation_simulations/test_banking_document_flow.py:
  - SIMULATE "analyze Bank of America's ROA using our policy documents" scenarios
  - TEST integration between banking tools and document search
  - VALIDATE multi-step workflows combining tool categories

CREATE tests/tools/conversation_simulations/fixtures/conversation_data.py:
  - DEFINE realistic conversation scenarios with tool triggers
  - CREATE mock responses for conversation flow testing
  - FOLLOW patterns from: tests/conftest.py
```

### Per task pseudocode as needed added to each task

```python
# Task 1: Tool Category System
class ToolCategory(str, Enum):
    """Domain-based tool categorization."""
    DOCUMENTS = "documents"  # RAG search, file operations
    BANKING = "banking"      # Financial data, Call Report
    ANALYSIS = "analysis"    # Calculations, data processing
    WEB = "web"             # External APIs, search
    UTILITIES = "utilities"  # Time, format, general

class ToolMetadata(BaseModel):
    """Enhanced tool metadata with category support."""
    name: str
    description: str  
    category: ToolCategory
    requires_data: Optional[List[str]] = None  # ["chromadb", "call_report_api"]
    priority: int = 0
    enabled: bool = True

# Task 2: Dynamic Tool Loader
class DynamicToolLoader:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.availability_cache = {}
    
    async def check_service_availability(self, service_name: str) -> bool:
        """Check if required service is available for tool loading."""
        # PATTERN: Cache availability checks to avoid repeated calls
        if service_name in self.availability_cache:
            return self.availability_cache[service_name]
        
        availability = False
        
        if service_name == "chromadb":
            # CRITICAL: Check ChromaDB connection for RAG tool
            try:
                from src.rag.chromadb_manager import ChromaDBManager
                manager = ChromaDBManager(self.settings)
                doc_count = await manager.get_document_count()
                availability = doc_count >= 0  # Connection successful
            except Exception:
                availability = False
                
        elif service_name == "call_report_api":
            # Check Call Report mock API availability
            try:
                from src.tools.call_report.mock_api_client import CallReportMockAPI
                api = CallReportMockAPI()
                availability = api.is_available()
            except Exception:
                availability = False
        
        # PATTERN: Cache with TTL for performance
        self.availability_cache[service_name] = availability
        return availability
    
    async def load_tools_by_category(
        self, 
        category: ToolCategory
    ) -> List[BaseTool]:
        """Dynamically load tools for a category based on availability."""
        tools = []
        
        if category == ToolCategory.DOCUMENTS:
            # CRITICAL: Load RAG tool if ChromaDB available
            if await self.check_service_availability("chromadb"):
                from src.rag.rag_tool import RAGSearchTool
                from src.rag.retriever import RAGRetriever
                
                retriever = RAGRetriever(self.settings)
                rag_tool = RAGSearchTool(retriever)
                tools.append(rag_tool)
                
        elif category == ToolCategory.BANKING:
            # Load Call Report tools if API available
            if await self.check_service_availability("call_report_api"):
                from src.tools.call_report.langchain_tools import CallReportToolset
                toolset = CallReportToolset(self.settings)
                tools.extend(toolset.get_tools())
        
        return tools

# Task 3: Enhanced LangChainToolRegistry
class EnhancedLangChainToolRegistry(LangChainToolRegistry):
    """Enhanced registry with category support and dynamic loading."""
    
    def __init__(self, settings: Settings):
        super().__init__(settings)
        self.dynamic_loader = DynamicToolLoader(settings)
        self.tools_by_category: Dict[ToolCategory, List[BaseTool]] = {}
        self.category_config: Dict[ToolCategory, CategoryConfig] = {}
    
    async def initialize_dynamic_tools(self):
        """Initialize tools dynamically based on service availability."""
        for category in ToolCategory:
            if self._is_category_enabled(category):
                tools = await self.dynamic_loader.load_tools_by_category(category)
                self.tools_by_category[category] = tools
                
                # CRITICAL: Register each tool with base class
                for tool in tools:
                    self._register_tool_with_metadata(tool, category)
    
    def get_tools_by_category(
        self, 
        category: ToolCategory
    ) -> List[BaseTool]:
        """Get tools filtered by category."""
        return self.tools_by_category.get(category, [])
    
    def get_available_categories(self) -> List[ToolCategory]:
        """Get list of categories with available tools."""
        return [
            cat for cat, tools in self.tools_by_category.items()
            if tools and self._is_category_enabled(cat)
        ]

# Task 8: Conversation Simulation Tests
class ConversationSimulator:
    """Simulate realistic conversations for tool testing."""
    
    def __init__(self, agent: ChatbotAgent):
        self.agent = agent
        self.conversation_history = []
    
    async def simulate_conversation(
        self, 
        scenario: ConversationScenario
    ) -> ConversationResult:
        """Simulate a multi-turn conversation with tool usage."""
        results = []
        
        for turn in scenario.turns:
            # PATTERN: Track tool usage across conversation
            response = await self.agent.process_message(
                user_message=turn.user_message,
                conversation_id=scenario.conversation_id
            )
            
            # Analyze which tools were used
            tools_used = self._extract_tools_from_response(response)
            
            turn_result = TurnResult(
                user_message=turn.user_message,
                agent_response=response,
                tools_used=tools_used,
                expected_tools=turn.expected_tools
            )
            
            results.append(turn_result)
            
            # VALIDATION: Check if expected tools were used
            if not self._validate_tool_usage(turn_result):
                return ConversationResult(
                    success=False,
                    error=f"Expected tools {turn.expected_tools}, got {tools_used}",
                    turns=results
                )
        
        return ConversationResult(success=True, turns=results)

# Example test scenarios for banking + document integration
BANKING_DOCUMENT_SCENARIOS = [
    ConversationScenario(
        name="ROA Analysis with Policy Reference",
        turns=[
            ConversationTurn(
                user_message="What's Wells Fargo's Return on Assets?",
                expected_tools=["bank_lookup", "call_report_data"]
            ),
            ConversationTurn(
                user_message="What do our policy documents say about acceptable ROA levels?",
                expected_tools=["document_search"]
            ),
            ConversationTurn(
                user_message="Is Wells Fargo's ROA within our acceptable range?",
                expected_tools=[]  # Analysis based on previous data
            )
        ]
    )
]
```

### Integration Points
```yaml
CHATBOT_AGENT:
  - modify: src/chatbot/agent.py
  - pattern: "Enhanced tool initialization with category support"
  - integrate: "Dynamic tool loading in _setup_agent_executor()"

STREAMLIT_UI:
  - modify: src/ui/streamlit_app.py  
  - pattern: "Dynamic tool initialization in session state"
  - integrate: "Category-based tool status display"

SETTINGS:
  - modify: src/config/settings.py
  - pattern: "tool_categories_enabled: Dict[str, bool]"
  - add: "max_tools_per_category: int = 10"

RAG_SYSTEM:
  - critical: "Register RAGSearchTool in LangChainToolRegistry"
  - pattern: "Ensure document search capability in multi-step agent"

BACKWARD_COMPATIBILITY:
  - maintain: "All existing Call Report tool functionality"
  - preserve: "Existing tool schemas and OpenAI function calling patterns"
```

## Validation Loop

### Level 1: Syntax & Style
```bash
# Run these FIRST - fix any errors before proceeding
ruff check src/tools/ src/rag/langchain_tools.py src/chatbot/agent.py --fix
mypy src/tools/ src/rag/langchain_tools.py src/chatbot/agent.py

# Expected: No errors. If errors, READ the error and fix.
```

### Level 2: Unit Tests each new feature/file/function use existing test patterns
```python
# tests/tools/test_tool_categories.py
def test_tool_category_enum():
    """Test ToolCategory enum values and coverage."""
    assert ToolCategory.DOCUMENTS == "documents"
    assert ToolCategory.BANKING == "banking"
    assert ToolCategory.ANALYSIS == "analysis"
    
    # Ensure all expected categories exist
    expected_categories = {"documents", "banking", "analysis", "web", "utilities"}
    actual_categories = {cat.value for cat in ToolCategory}
    assert actual_categories >= expected_categories

def test_tool_metadata_validation():
    """Test ToolMetadata model validation."""
    metadata = ToolMetadata(
        name="test_tool",
        description="Test tool description",
        category=ToolCategory.DOCUMENTS,
        requires_data=["chromadb"],
        priority=1
    )
    assert metadata.category == ToolCategory.DOCUMENTS
    assert "chromadb" in metadata.requires_data

# tests/tools/test_dynamic_loading.py
@pytest.mark.asyncio
async def test_dynamic_tool_loading_with_available_services():
    """Test dynamic tool loading when services are available."""
    settings = get_test_settings()
    loader = DynamicToolLoader(settings)
    
    # Mock service availability
    with patch.object(loader, 'check_service_availability', return_value=True):
        tools = await loader.load_tools_by_category(ToolCategory.DOCUMENTS)
        
        # Should load RAG tool when ChromaDB available
        assert len(tools) > 0
        tool_names = [tool.name for tool in tools]
        assert "document_search" in tool_names

@pytest.mark.asyncio
async def test_rag_tool_registration_fix():
    """CRITICAL: Test that RAG tool is now properly registered."""
    settings = get_test_settings()
    
    # Mock ChromaDB availability
    with patch('src.rag.chromadb_manager.ChromaDBManager') as mock_chromadb:
        mock_chromadb.return_value.get_document_count.return_value = 5
        
        registry = EnhancedLangChainToolRegistry(settings)
        await registry.initialize_dynamic_tools()
        
        # RAG tool should now be registered
        tools = registry.get_tools()
        tool_names = [tool.name for tool in tools]
        
        assert "document_search" in tool_names, "RAG tool registration failed - this was the critical issue"

# tests/tools/conversation_simulations/test_multi_tool_scenarios.py
@pytest.mark.asyncio
async def test_banking_document_integration_conversation():
    """Test conversation using both banking tools and document search."""
    settings = get_test_settings()
    
    # Setup agent with all tool categories
    registry = EnhancedLangChainToolRegistry(settings)
    await registry.initialize_dynamic_tools()
    
    tools = registry.get_tools()
    agent = ChatbotAgent(
        settings=settings,
        tools=tools,
        enable_multi_step=True
    )
    
    simulator = ConversationSimulator(agent)
    
    # Test scenario: Banking analysis with policy reference
    scenario = ConversationScenario(
        name="ROA Analysis with Policy Context",
        conversation_id="test-banking-docs-001",
        turns=[
            ConversationTurn(
                user_message="Find Wells Fargo's RSSD ID and get their ROA data",
                expected_tools=["bank_lookup", "call_report_data"]
            ),
            ConversationTurn(
                user_message="What do our banking policy documents say about ROA thresholds?",
                expected_tools=["document_search"]
            )
        ]
    )
    
    result = await simulator.simulate_conversation(scenario)
    
    assert result.success, f"Conversation simulation failed: {result.error}"
    assert len(result.turns) == 2
    
    # Validate tool usage in conversation
    turn1_tools = result.turns[0].tools_used
    turn2_tools = result.turns[1].tools_used
    
    # First turn should use banking tools
    assert any("bank" in tool.lower() or "call_report" in tool.lower() for tool in turn1_tools)
    
    # Second turn should use document search
    assert "document_search" in turn2_tools or any("document" in tool.lower() for tool in turn2_tools)

@pytest.mark.asyncio
async def test_tool_category_filtering():
    """Test that tools are properly filtered by category."""
    settings = get_test_settings()
    registry = EnhancedLangChainToolRegistry(settings)
    await registry.initialize_dynamic_tools()
    
    # Test category filtering
    banking_tools = registry.get_tools_by_category(ToolCategory.BANKING)
    document_tools = registry.get_tools_by_category(ToolCategory.DOCUMENTS)
    
    assert len(banking_tools) >= 2  # At least bank_lookup and call_report_data
    assert len(document_tools) >= 1  # At least document_search (RAG tool)
    
    # Verify no overlap (tools in correct categories)
    banking_names = {tool.name for tool in banking_tools}
    document_names = {tool.name for tool in document_tools}
    
    assert banking_names.isdisjoint(document_names), "Tools should not appear in multiple categories"
```

```bash
# Run and iterate until passing:
python -m pytest tests/tools/ -v --tb=short
# If failing: Read error, understand root cause, fix code, re-run
```

### Level 3: Integration Test
```bash
# Test dynamic tool loading and category system
python -c "
import asyncio
from src.config.settings import get_settings
from src.rag.langchain_tools import LangChainToolRegistry

async def test_integration():
    settings = get_settings()
    registry = LangChainToolRegistry(settings)
    
    # This should now include RAG tool (the critical fix)
    tools = registry.get_tools()
    tool_names = [tool.name for tool in tools]
    
    print(f'Registered tools: {tool_names}')
    
    # Critical validation - RAG tool should be present
    if 'document_search' in tool_names:
        print('SUCCESS: RAG tool registration fixed!')
    else:
        print('FAILURE: RAG tool still not registered')
        
    # Test categories if enhanced registry available
    try:
        categories = registry.get_available_categories() 
        print(f'Available categories: {categories}')
    except AttributeError:
        print('Categories not yet implemented')

asyncio.run(test_integration())
"

# Test ChatbotAgent with enhanced tools
python -c "
import asyncio
from src.chatbot.agent import ChatbotAgent
from src.rag.langchain_tools import LangChainToolRegistry
from src.config.settings import get_settings

async def test_agent():
    settings = get_settings()
    registry = LangChainToolRegistry(settings)
    tools = registry.get_tools()
    
    agent = ChatbotAgent(
        settings=settings,
        tools=tools,
        enable_multi_step=True
    )
    
    # Test multi-tool capability
    response = agent.process_message(
        'Can you search for bank information and documents about ROA?'
    )
    
    print(f'Agent response: {response.get(\"content\", \"No response\")}')
    print(f'Processing mode: {response.get(\"processing_mode\", \"unknown\")}')

asyncio.run(test_agent())
"
```

## Final validation Checklist
- [ ] All tests pass: `python -m pytest tests/tools/ -v`
- [ ] No linting errors: `ruff check src/tools/ src/rag/langchain_tools.py`
- [ ] No type errors: `mypy src/tools/ src/rag/langchain_tools.py`
- [ ] RAG tool (document_search) is registered and discoverable
- [ ] Tools are properly categorized by domain
- [ ] Dynamic tool loading works based on service availability
- [ ] Conversation simulation tests pass for multi-tool scenarios
- [ ] ChatbotAgent can use tools from multiple categories in single conversation
- [ ] Backward compatibility maintained for existing Call Report tools
- [ ] Tool discovery through single unified interface works
- [ ] System status shows tool categories and availability
- [ ] Error handling graceful for missing services/data

---

## Anti-Patterns to Avoid
- ❌ Don't break existing Call Report tool functionality - preserve all schemas
- ❌ Don't ignore the critical RAG tool registration issue - this is the main fix needed
- ❌ Don't create synchronous tools in async context - maintain async patterns
- ❌ Don't hardcode tool availability - use dynamic loading based on actual services
- ❌ Don't skip conversation simulation testing - this validates real user scenarios
- ❌ Don't forget OpenAI function calling schema compliance - tools must work with AgentExecutor
- ❌ Don't exceed 500-line file limit - split enhanced registry if needed
- ❌ Don't ignore backward compatibility - existing tool patterns must continue working
- ❌ Don't skip error handling for tool category/loading failures
- ❌ Don't forget structured logging patterns - use log_type consistently
- ❌ Don't mix LangChain tools with custom BaseTool patterns - consolidate on LangChain
- ❌ Don't skip service availability caching - avoid repeated expensive checks

## PRP Confidence Score: 9/10

This PRP provides comprehensive context including:
✅ Complete analysis of current dual-architecture tool problem
✅ Identification of critical RAG tool registration issue 
✅ Clear categorization system with domain-based organization
✅ Dynamic loading strategy based on service availability
✅ Detailed task breakdown with clear validation gates
✅ Conversation simulation testing for real-world validation
✅ Integration points with existing ChatbotAgent and UI systems
✅ Comprehensive test coverage strategy including edge cases
✅ Clear error handling and backward compatibility requirements
✅ Structured logging and configuration management patterns

The high confidence score reflects:
- **Critical Issue Identification**: RAG tool registration gap clearly identified and addressed
- **Architectural Enhancement**: Clear path from dual-architecture to unified LangChain approach  
- **Real-world Testing**: Conversation simulations test actual user interaction patterns
- **Comprehensive Coverage**: All integration points and compatibility requirements addressed
- **Validation Gates**: Executable tests ensure quality at each development phase

This provides a clear path to achieving the goal of unified tool discovery, domain categorization, and dynamic loading while fixing the critical missing RAG tool issue.