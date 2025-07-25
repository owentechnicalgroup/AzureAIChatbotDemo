name: "Azure OpenTelemetry Logging Modernization with Separated Concerns PRP"
description: |

## Purpose
Modernize the application logging system by replacing the legacy opencensus-based logging with Azure Monitor OpenTelemetry, while implementing clear separation between **Application Logging** and **AI Chat Observability** as two distinct concerns with dedicated telemetry pipelines.

## Core Principles
1. **Context is King**: Include ALL necessary documentation, examples, and caveats
2. **Validation Loops**: Provide executable tests/lints the AI can run and fix
3. **Information Dense**: Use keywords and patterns from the codebase
4. **Progressive Success**: Start simple, validate, then enhance
5. **Global rules**: Be sure to follow all rules in CLAUDE.md
6. **Separation of Concerns**: Application logging and AI Chat observability are distinct systems

---

## Goal
Replace the legacy opencensus-based Azure Application Insights logging with modern Azure Monitor OpenTelemetry integration while **separating application logging from AI chat observability** as two independent concerns with dedicated configuration, routing, and analysis capabilities.

## Why
- **Modernization**: Move from deprecated opencensus to officially supported Azure Monitor OpenTelemetry Distro
- **Separation of Concerns**: Clear boundaries between application infrastructure logs and AI conversation telemetry
- **Specialized Analysis**: Different log types need different analysis patterns and retention policies
- **Future Portability**: Separate systems enable independent migration and scaling decisions
- **Compliance**: Maintain existing log_type standards while enabling specialized AI observability patterns

## What
Implement two separate observability systems using Azure Monitor OpenTelemetry:

### 1. Application Logging System
- **Purpose**: Infrastructure, performance, security, and system events
- **Log Types**: SYSTEM, SECURITY, PERFORMANCE, AZURE_OPENAI (API-level only)
- **Destination**: Standard Azure Application Insights workspace
- **Retention**: Standard operational log retention
- **Analysis**: Performance monitoring, error tracking, security auditing

### 2. AI Chat Observability System
- **Purpose**: Conversation flow, user interactions, and AI agent behavior
- **Log Types**: CONVERSATION (dedicated pipeline)
- **Destination**: Specialized AI observability workspace or separate log stream
- **Retention**: Extended retention for conversation analysis
- **Analysis**: User experience, conversation quality, AI agent performance

### Shared Infrastructure
- Single OpenTelemetry configuration with multiple exporters
- Common structured logging patterns preserved
- Unified correlation IDs for cross-system tracing

### Success Criteria
- [ ] Azure Monitor OpenTelemetry successfully replaces opencensus integration
- [ ] Application logging (SYSTEM, SECURITY, PERFORMANCE, AZURE_OPENAI) routes to standard workspace
- [ ] AI Chat observability (CONVERSATION) routes to dedicated system
- [ ] Cross-system correlation maintained via operation IDs
- [ ] Independent configuration for each observability concern
- [ ] All existing structured logging helpers work with both systems
- [ ] Tests pass for both application and chat observability
- [ ] Clear separation enables independent analysis and scaling

## All Needed Context

### Documentation & References
```yaml
# MUST READ - Include these in your context window
- url: https://learn.microsoft.com/en-us/azure/azure-monitor/app/opentelemetry-enable?tabs=python
  why: Official Azure OpenTelemetry configuration patterns and environment setup
  
- url: https://learn.microsoft.com/en-us/python/api/overview/azure/monitor-opentelemetry-readme?view=azure-python
  why: Azure Monitor OpenTelemetry Distro client library usage and configuration options
  
- file: src/services/logging_service.py
  why: Current logging implementation with Application Insights formatter and log_type logic
  
- file: src/utils/logging_helpers.py 
  why: Structured logging helpers that must remain compatible
  
- file: src/config/settings.py
  why: Configuration patterns and Application Insights connection string handling
  
- file: CLAUDE.md
  section: "Logging Standards"
  critical: "All logs must include a log_type property with 5 standardized values"

- file: examples/opentelemetry-azure-monitor-python/azure_monitor/examples/traces/trace.py
  why: OpenTelemetry patterns for Azure Monitor integration

- file: examples/opentelemetry-python/docs/getting_started/tracing_example.py
  why: Basic OpenTelemetry instrumentation patterns

```

### Current Codebase tree
```bash
src/
├── __init__.py
├── chatbot/
│   ├── __init__.py
│   ├── agent.py
│   ├── conversation.py
│   └── prompts.py
├── config/
│   ├── __init__.py
│   └── settings.py                 # Configuration with Azure Key Vault integration
├── main.py
├── services/
│   ├── __init__.py
│   ├── azure_client.py
│   └── logging_service.py          # Current opencensus-based logging service
└── utils/
    ├── __init__.py
    ├── console.py
    ├── error_handlers.py
    └── logging_helpers.py           # Structured logging helper classes
```

### Desired Codebase tree with files to be added and responsibility of file
```bash
src/
├── __init__.py
├── chatbot/
│   ├── __init__.py
│   ├── agent.py
│   ├── conversation.py
│   └── prompts.py
├── config/
│   ├── __init__.py
│   └── settings.py                 # Updated with dual observability configuration
├── main.py
├── observability/                  # NEW: Dedicated observability package
│   ├── __init__.py
│   ├── application_logging.py      # NEW: Application infrastructure logging
│   ├── chat_observability.py       # NEW: AI conversation observability
│   └── telemetry_service.py        # NEW: OpenTelemetry configuration and routing
├── services/
│   ├── __init__.py
│   ├── azure_client.py
│   └── logging_service.py          # Legacy compatibility and coordination
└── utils/
    ├── __init__.py
    ├── console.py
    ├── error_handlers.py
    └── logging_helpers.py           # Updated with observability routing logic
tests/
├── __init__.py
├── observability/                  # NEW: Observability-specific tests
│   ├── __init__.py
│   ├── test_application_logging.py # NEW: Application logging tests
│   ├── test_chat_observability.py  # NEW: Chat observability tests
│   └── test_telemetry_service.py   # NEW: OpenTelemetry integration tests
├── test_logging_service.py         # Updated for compatibility layer
└── test_logging_helpers.py         # Updated for dual-system routing
```

### Known Gotchas of our codebase & Library Quirks
```python
# CRITICAL: Azure Monitor OpenTelemetry requires Python 3.8+
# CRITICAL: Multiple exporters require separate connection strings for each destination
# CRITICAL: Existing log_type field must be preserved for Azure Log Analytics queries
# CRITICAL: The current codebase uses both structlog and Python logging - OpenTelemetry integrates with both
# CRITICAL: ConversationContextFilter is duplicated in logging_service.py (lines 29 and 293)
# CRITICAL: Use venv_linux virtual environment for all Python commands
# CRITICAL: Current logging uses opencensus which is being deprecated
# CRITICAL: CONVERSATION logs need dedicated routing logic separate from application logs
# CRITICAL: conversation_id field is used extensively throughout chatbot/agent.py and conversation.py
# CRITICAL: Existing log_conversation_event() function in logging_service.py must be preserved for compatibility
# GOTCHA: Azure Monitor OpenTelemetry is in beta but officially supported
# GOTCHA: Multiple exporters can be configured but require different logger namespaces or routing logic
# GOTCHA: OpenTelemetry collector can be used for advanced routing but adds deployment complexity
# SEPARATION: Application logs (SYSTEM, SECURITY, PERFORMANCE) vs Chat logs (CONVERSATION) need different pipelines
# SEPARATION: chat_observability.py should handle only CONVERSATION logs with conversation_id context
# SEPARATION: application_logging.py should handle SYSTEM, SECURITY, PERFORMANCE, AZURE_OPENAI logs
```

## Implementation Blueprint

### Data models and structure

Separated observability systems with shared data models:
```python
# Application Logging Types - Route to Standard Application Insights
APPLICATION_LOG_TYPES = {
    'SYSTEM': 'Application lifecycle, configuration, health checks, errors',
    'SECURITY': 'Authentication, Key Vault operations, credential management', 
    'PERFORMANCE': 'Response times, throughput metrics, resource usage',
    'AZURE_OPENAI': 'Azure OpenAI API calls, responses, token usage (API-level only)'
}

# AI Chat Observability Types - Route to Specialized Workspace
CHAT_OBSERVABILITY_TYPES = {
    'CONVERSATION': 'Chat interactions, message processing, conversation flow, user experience'
}

# Shared base context for correlation across systems
@dataclass
class BaseObservabilityContext:
    operation_id: str
    timestamp: datetime
    component: str
    environment: str

# Application-specific context
@dataclass  
class ApplicationLogContext(BaseObservabilityContext):
    log_type: Literal['SYSTEM', 'SECURITY', 'PERFORMANCE', 'AZURE_OPENAI']
    resource_type: Optional[str] = None
    duration: Optional[float] = None
    success: Optional[bool] = None

# Chat-specific context with conversation data
@dataclass
class ChatObservabilityContext(BaseObservabilityContext):
    log_type: Literal['CONVERSATION'] = 'CONVERSATION'
    conversation_id: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    turn_number: Optional[int] = None
    message_length: Optional[int] = None
    
# Routing configuration for exporters
@dataclass
class ObservabilityConfig:
    application_connection_string: str  # Standard Application Insights
    chat_connection_string: str        # AI Chat observability workspace
    enable_cross_correlation: bool = True
```

### List of tasks to be completed to fulfill the PRP in the order they should be completed

```yaml
Task 1:
UPDATE requirements.txt and install dependencies:
  - REMOVE: opencensus-ext-azure
  - ADD: azure-monitor-opentelemetry
  - VERIFY: Python 3.8+ compatibility
  - INSTALL: uv add azure-monitor-opentelemetry

Task 2:
CREATE src/observability/ package structure:
  - CREATE: src/observability/__init__.py
  - CREATE: src/observability/telemetry_service.py (OpenTelemetry routing manager)
  - CREATE: src/observability/application_logging.py (SYSTEM, SECURITY, PERFORMANCE, AZURE_OPENAI)
  - CREATE: src/observability/chat_observability.py (CONVERSATION only)
  - DEFINE: Clear interfaces and routing logic between systems

Task 3:
IMPLEMENT src/observability/telemetry_service.py:
  - CONFIGURE: Dual OpenTelemetry exporters (application vs chat)
  - IMPLEMENT: Routing logic based on log_type
  - PATTERN: Multiple exporters with different connection strings
  - PRESERVE: Cross-system correlation via operation_id

Task 4:
IMPLEMENT src/observability/application_logging.py:
  - HANDLE: SYSTEM, SECURITY, PERFORMANCE, AZURE_OPENAI log types
  - DESTINATION: Standard Azure Application Insights workspace
  - PRESERVE: Existing StructuredLogger methods for non-conversation logs
  - INTEGRATE: With existing azure_client.py and error handling

Task 5:
IMPLEMENT src/observability/chat_observability.py:
  - HANDLE: CONVERSATION log type exclusively
  - DESTINATION: Dedicated AI chat observability workspace
  - PRESERVE: conversation_id, user_id, session_id context
  - INTEGRATE: With existing ConversationLogger and log_conversation_event

Task 6:
UPDATE src/config/settings.py:
  - ADD: chat_observability_connection_string field
  - PRESERVE: applicationinsights_connection_string for application logs
  - ADD: Observability routing configuration options
  - MAINTAIN: Existing Key Vault integration patterns

Task 7:
UPDATE src/utils/logging_helpers.py:
  - ADD: Routing logic to determine application vs chat observability
  - PRESERVE: All existing StructuredLogger methods with new routing
  - MAINTAIN: Backward compatibility for existing callers
  - INTEGRATE: With new observability package

Task 8:
UPDATE src/services/logging_service.py:
  - REMOVE: opencensus imports and EnhancedApplicationInsightsFormatter
  - CREATE: Compatibility layer for existing imports
  - DELEGATE: to appropriate observability subsystem
  - PRESERVE: Existing function signatures for backward compatibility

Task 9:
UPDATE src/main.py:
  - INITIALIZE: Dual OpenTelemetry exporters early in startup
  - CONFIGURE: Both application and chat observability systems
  - PRESERVE: Existing logging setup sequence
  - ENSURE: Proper correlation across both systems

Task 10:
CREATE comprehensive separated tests:
  - CREATE: tests/observability/ package
  - CREATE: tests/observability/test_application_logging.py
  - CREATE: tests/observability/test_chat_observability.py  
  - CREATE: tests/observability/test_telemetry_service.py
  - VERIFY: Log routing works correctly for each system
  - VERIFY: Cross-system correlation is maintained
```

### Per task pseudocode as needed added to each task

```python
# Task 2: Create telemetry_service.py
from azure.monitor.opentelemetry import configure_azure_monitor
from config.settings import Settings

def initialize_opentelemetry(settings: Settings) -> bool:
    """
    Initialize Azure Monitor OpenTelemetry with proper configuration.
    
    CRITICAL: Must be called before other imports that use logging
    PATTERN: Use settings.applicationinsights_connection_string
    GOTCHA: Logger namespace controls telemetry collection scope
    """
    if not settings.applicationinsights_connection_string:
        return False
    
    # PATTERN: Configure with connection string from settings
    configure_azure_monitor(
        connection_string=settings.applicationinsights_connection_string,
        logger_name="src",  # Match our source code namespace
    )
    
    # PATTERN: Log successful initialization with structured data
    logger = structlog.get_logger(__name__).bind(log_type="SYSTEM")
    logger.info(
        "OpenTelemetry initialized successfully", 
        component="telemetry_service",
        connection_configured=True
    )
    return True

# Task 3: Update logging_service.py
def setup_logging(settings: Optional[Settings] = None) -> None:
    """
    MODIFY existing function to remove opencensus, preserve all other functionality
    REMOVE: AzureLogHandler and EnhancedApplicationInsightsFormatter
    PRESERVE: structlog configuration and log_type processing
    PRESERVE: File and console logging setup
    """
    # ... existing structlog configuration preserved
    
    # REMOVE this section:
    # try:
    #     ai_handler = setup_application_insights_logging(settings)
    # except Exception as e:
    #     logging.error(f"Failed to setup Application Insights logging: {e}")
    
    # OpenTelemetry now handles Azure Monitor integration automatically

# Task 4: Verify logging_helpers.py compatibility
class StructuredLogger:
    """
    PRESERVE: All existing methods and log_type logic
    VERIFY: Works correctly with OpenTelemetry instrumentation
    """
    def log_conversation_event(self, message: str, conversation_id: str, **kwargs):
        # PRESERVE: Existing implementation - OpenTelemetry will instrument automatically
        extra = {
            'log_type': 'CONVERSATION',  # CRITICAL: Preserve for Azure Log Analytics
            'conversation_id': conversation_id,
            # ... rest of implementation unchanged
        }
        
# Task 6: Update main.py startup sequence
def main():
    """
    CRITICAL: Initialize OpenTelemetry BEFORE other imports
    """
    # Load settings first
    from config.settings import get_settings
    settings = get_settings()
    
    # Initialize OpenTelemetry EARLY - before logging setup
    from services.telemetry_service import initialize_opentelemetry
    initialize_opentelemetry(settings)
    
    # PRESERVE: Existing logging setup
    from services.logging_service import setup_logging
    setup_logging(settings)
    
    # ... rest of application startup unchanged
```

### Integration Points
```yaml
DEPENDENCIES:
  - remove: opencensus-ext-azure
  - add: azure-monitor-opentelemetry
  - verify: Python 3.8+ compatibility
  
CONFIGURATION:
  - preserve: APPLICATIONINSIGHTS_CONNECTION_STRING environment variable
  - preserve: All existing logging configuration options
  - add: OpenTelemetry logger namespace configuration
  
STARTUP_SEQUENCE:
  - modify: main.py to initialize OpenTelemetry before logging setup
  - preserve: Existing settings loading and validation
  - preserve: Structured logging configuration sequence

AZURE_LOG_ANALYTICS:
  - preserve: All existing log_type values and field mappings
  - preserve: customDimensions and customMeasurements structure
  - verify: Existing queries continue to work unchanged
```

## Validation Loop

### Level 1: Syntax & Style
```bash
# Run these FIRST - fix any errors before proceeding
ruff check src/services/telemetry_service.py --fix
ruff check src/services/logging_service.py --fix
mypy src/services/telemetry_service.py
mypy src/services/logging_service.py

# Expected: No errors. If errors, READ the error message and fix.
```

### Level 2: Unit Tests each new feature/file/function use existing test patterns
```python
# CREATE tests/test_telemetry_service.py
def test_initialize_opentelemetry_success():
    """OpenTelemetry initializes with valid connection string"""
    settings = Settings(applicationinsights_connection_string="InstrumentationKey=test-key")
    result = initialize_opentelemetry(settings)
    assert result is True

def test_initialize_opentelemetry_no_connection_string():
    """OpenTelemetry initialization fails gracefully without connection string"""
    settings = Settings(applicationinsights_connection_string=None)
    result = initialize_opentelemetry(settings)
    assert result is False

# CREATE tests/test_logging_service.py
def test_setup_logging_preserves_log_types():
    """Verify all 5 log_type categories still work"""
    settings = Settings()
    setup_logging(settings)
    
    logger = structlog.get_logger(__name__)
    # Test each log_type category
    for log_type in ['CONVERSATION', 'AZURE_OPENAI', 'PERFORMANCE', 'SECURITY', 'SYSTEM']:
        bound_logger = logger.bind(log_type=log_type)
        bound_logger.info(f"Test {log_type} logging")

def test_conversation_context_preserved():
    """Conversation logging maintains required fields"""
    from utils.logging_helpers import StructuredLogger
    logger = StructuredLogger(__name__)
    
    # This should not raise exceptions and should preserve all fields
    logger.log_conversation_event(
        message="Test conversation",
        conversation_id="test-123",
        user_id="user-456"
    )

# CREATE tests/test_logging_helpers.py  
def test_structured_logger_compatibility():
    """All existing StructuredLogger methods work with OpenTelemetry"""
    logger = StructuredLogger(__name__)
    
    # Test each method preserves log_type
    logger.log_azure_operation("Test", "openai", "test-resource", "api_call")
    logger.log_performance_metrics("Test", 1.5, tokens_total=100)
    logger.log_authentication_event("Test", "managed_identity", True)
```

```bash
# Run and iterate until passing:
uv run pytest tests/test_telemetry_service.py -v
uv run pytest tests/test_logging_service.py -v  
uv run pytest tests/test_logging_helpers.py -v

# If failing: Read error, understand root cause, fix code, re-run
```

### Level 3: Integration Test
```bash
# Test full application startup with OpenTelemetry
uv run python -m src.main

# Expected logs should show:
# - "OpenTelemetry initialized successfully" with log_type="SYSTEM"
# - "Logging configured" with application_insights_enabled=true
# - No opencensus-related errors
# - All existing log_type categories working

# Test structured logging still works:
uv run python -c "
from src.utils.logging_helpers import StructuredLogger
logger = StructuredLogger(__name__)
logger.log_conversation_event('Integration test', 'test-conversation-123')
print('Structured logging test completed')
"

# Expected: No errors, telemetry sent to Azure Application Insights
```

## Final validation Checklist
- [ ] All tests pass: `uv run pytest tests/ -v`
- [ ] No linting errors: `uv run ruff check src/`
- [ ] No type errors: `uv run mypy src/`
- [ ] Application starts without OpenTelemetry errors
- [ ] All 5 log_type categories work in Azure Log Analytics
- [ ] Conversation logging preserves all required fields
- [ ] Performance metrics still captured correctly
- [ ] Azure Application Insights receives telemetry data
- [ ] Existing Log Analytics queries continue to work
- [ ] No regression in structured logging functionality

---

## Anti-Patterns to Avoid
- ❌ Don't remove existing log_type logic - Azure Log Analytics depends on it
- ❌ Don't change existing structured logging field names
- ❌ Don't initialize OpenTelemetry after other logging setup
- ❌ Don't skip testing each log_type category individually
- ❌ Don't ignore OpenTelemetry configuration failures
- ❌ Don't modify conversation logging fields without testing
- ❌ Don't assume OpenTelemetry will automatically preserve custom formatters

## Confidence Score: 9/10

This PRP provides comprehensive context for migrating from opencensus to Azure Monitor OpenTelemetry while preserving all existing logging functionality. The score of 9/10 reflects high confidence in one-pass implementation success due to:

**Strengths:**
- Complete codebase analysis with specific file references
- Detailed preservation of existing log_type categorization
- Step-by-step migration plan with clear validation gates
- Comprehensive testing strategy covering all log categories
- Integration with existing configuration and Key Vault patterns

**Risk Mitigation:**
- Explicit preservation of Azure Log Analytics compatibility
- Detailed gotchas section covering OpenTelemetry specifics
- Progressive validation approach with executable tests
- Clear rollback strategy (keep opencensus imports until verified)

The implementation should succeed in one pass with this level of context and validation planning.