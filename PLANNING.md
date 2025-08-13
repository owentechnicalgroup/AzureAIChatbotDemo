# PLANNING.md

## Project Overview

The **Context Engineering Template** is a comprehensive framework that combines several major components:

1. **Context Engineering Framework** - A discipline for engineering context for AI coding assistants
2. **Azure OpenAI RAG Chatbot** - A production-ready chatbot with both CLI and Streamlit web interface
3. **Banking Tools Integration** - Specialized tools for call report data and banking analysis
4. **Document Management System** - ChromaDB-based RAG implementation with flexible knowledge modes

## Project Architecture

### Core Components

```
context-engineering-intro/
├── infrastructure/           # Terraform IaC for Azure deployment
│   ├── bootstrap/           # Backend storage setup
│   ├── modules/             # Reusable Terraform modules
│   └── main.tf             # Primary infrastructure
├── src/                    # Python application source
│   ├── main.py            # Main entry point (CLI + Streamlit launcher)
│   ├── chatbot/           # AI chatbot agent implementation
│   ├── config/            # Configuration management
│   ├── document_management/ # RAG document processing (ChromaDB)
│   ├── rag_access/        # RAG search and retrieval services
│   ├── tools/             # Modular tool system
│   │   ├── atomic/        # Single-purpose tools (RAG, banking lookups)
│   │   ├── composite/     # Multi-step analysis tools
│   │   └── infrastructure/ # Tool infrastructure (banking APIs, toolsets)
│   ├── ui/                # Streamlit web interface
│   ├── services/          # Core services (logging, formatting)
│   ├── observability/     # Dual logging/telemetry system
│   └── utils/             # Utility functions
├── scripts/               # PowerShell deployment automation
├── data/                  # ChromaDB storage and application data
├── PRPs/                  # Product Requirements Prompts
├── examples/              # Code patterns and examples
└── use-cases/             # Specialized implementations
    ├── mcp-server/        # MCP (Model Context Protocol) server
    ├── pydantic-ai/       # PydanticAI integration examples
    └── template-generator/ # Code template generation tools
```

### Technology Stack

- **Cloud Platform**: Microsoft Azure
- **Infrastructure**: Terraform (Infrastructure as Code)
- **Language**: Python 3.8+
- **AI Integration**: Azure OpenAI + LangChain
- **Authentication**: Azure Identity (Managed Identity, Azure CLI)
- **Security**: Azure Key Vault for secrets management
- **Logging**: Structured logging with structlog + Azure Application Insights (OpenTelemetry)
- **CLI Framework**: Click + Rich (enhanced console output)
- **Web Interface**: Streamlit (primary interface)
- **Document Storage**: ChromaDB for vector search and RAG
- **Configuration**: Pydantic Settings with environment variable support
- **Tool System**: Modular LangChain-compatible tools with categorization
- **Document Processing**: PyPDF, python-docx for document parsing

### Security Architecture

- **RBAC**: Role-based access control with least privilege
- **Secrets Management**: All credentials stored in Azure Key Vault
- **Authentication Chain**: Managed Identity → Azure CLI → Environment → Default
- **Network Security**: HTTPS-only storage accounts and encrypted communications

## Project Goals

### Primary Goals

1. **Context Engineering Excellence**
   - Provide comprehensive context for AI coding assistants
   - Enable complex, multi-step feature implementations
   - Reduce AI failures through better context management

2. **Production-Ready RAG Chatbot**
   - Secure, scalable Azure OpenAI deployment with RAG capabilities
   - Automated infrastructure provisioning and management
   - Enterprise-grade logging and observability with OpenTelemetry
   - Flexible knowledge modes (document-only vs. hybrid)

3. **User Experience**
   - Primary Streamlit web interface for interactive document management
   - Secondary CLI interface for command-line users
   - Modular tool system for extensible functionality
   - Banking domain expertise through specialized tools

4. **Architectural Flexibility**
   - Separated RAG architecture with pluggable components
   - Tool categorization system for dynamic loading
   - Multiple UI modes and deployment options

### Secondary Goals

1. **Educational Value**: Demonstrate best practices for AI-assisted development
2. **Reusability**: Provide templates and modules for other projects
3. **Observability**: Deep insights into application performance and usage

## Architecture Patterns

### Configuration Management

**Pattern**: Layered configuration with secure fallbacks
- **Environment Variables** → **Azure Key Vault** → **Defaults**
- **Validation**: Pydantic models with field validation
- **Settings**: Singleton pattern with reload capability
- **Environment Setup**: Automated PowerShell scripts for Terraform integration

### Logging Architecture

**Pattern**: Dual observability system with OpenTelemetry
- **Application Logging**: General application events and errors
- **Chat Observability**: Specialized AI interaction telemetry
- **Structured Logging**: JSON format with consistent field schemas
- **Multiple Handlers**: Console, File, Azure Application Insights
- **OpenTelemetry Integration**: Modern telemetry collection and export

### Document Management

**Pattern**: Separated RAG architecture
- **Document Manager**: High-level document operations and lifecycle
- **ChromaDB Service**: Vector storage and similarity search
- **Document Processor**: File parsing and text chunking
- **Database Manager**: Metadata storage and relationship management
- **RAG Access Layer**: Search services and retrieval tools

### Tool System Architecture

**Pattern**: Modular tool system with dynamic loading
- **Atomic Tools**: Single-purpose tools (RAG search, banking lookups)
- **Composite Tools**: Multi-step analysis and complex workflows  
- **Infrastructure Layer**: API clients and service integrations
- **Toolsets**: Domain-specific tool collections (banking, analysis)
- **Category System**: Tool classification and dependency management

### User Interface Architecture

**Pattern**: Multi-modal interface with consistent backend
- **Primary Interface**: Streamlit web application with real-time document management
- **Secondary Interface**: Click CLI with rich console output
- **Shared Agent**: Common ChatbotAgent for consistent behavior
- **Flexible Knowledge Modes**: User-controlled document-only vs. hybrid modes

### Error Handling

**Pattern**: Graceful degradation with rich error reporting
- **Structured Exceptions**: Custom error types with context
- **User-Friendly Messages**: Technical details hidden from end users
- **Debug Mode**: Detailed stacktraces and diagnostic information
- **Response Formatting**: Consistent error formatting across interfaces

## Style Guidelines

### Code Organization

- **File Size Limit**: Maximum 500 lines per file
- **Module Structure**: Clear separation by feature/responsibility
- **Import Style**: Relative imports within packages, absolute for external
- **Naming**: Snake_case for variables/functions, PascalCase for classes

### Python Conventions

- **Type Hints**: Required for all function signatures
- **Docstrings**: Google-style docstrings for all functions
- **Formatting**: Black formatter with PEP8 compliance
- **Validation**: Pydantic for data validation and settings

### Infrastructure Conventions

- **Resource Naming**: Consistent prefixes and environment suffixes
- **Modularity**: Reusable modules with clear interfaces
- **State Management**: Remote backend with proper locking
- **Documentation**: Inline comments explaining business logic

## Development Constraints

### Technical Constraints

1. **Python Version**: 3.8+ (Azure Functions compatibility)
2. **Azure Regions**: Limited to Azure OpenAI supported regions
3. **Authentication**: Must support multiple Azure credential types
4. **Logging**: Must integrate with Azure Application Insights and OpenTelemetry
5. **Configuration**: Environment-specific with secure secret management
6. **RAG Performance**: ChromaDB vector search response times under 2 seconds
7. **Tool Loading**: Dynamic tool loading based on service availability

### Business Constraints

1. **Security**: No secrets in code or version control
2. **Compliance**: Structured logging for audit trails
3. **Scalability**: Stateless design for horizontal scaling
4. **Cost**: Efficient resource usage and proper cleanup
5. **Maintainability**: Clear separation of concerns and documentation
6. **Domain Expertise**: Banking/financial tools require regulatory awareness

### Operational Constraints

1. **Deployment**: Automated with rollback capability
2. **Monitoring**: Health checks and observability requirements
3. **Error Recovery**: Graceful failure handling and retry logic
4. **Documentation**: Self-documenting code with comprehensive README
5. **Multi-Interface**: Consistent behavior across CLI and Streamlit interfaces
6. **Document Storage**: Persistent document storage across sessions

## Environment Configuration

### Required Environment Variables

All environment variables must be configured in three places:
1. `infrastructure/outputs.tf` - Terraform output section
2. `scripts/setup-env.ps1` - PowerShell environment setup
3. `src/config/settings.py` - Pydantic settings fields

### Development vs Production

- **Development**: Azure CLI authentication, local file logging
- **Production**: Managed Identity, Azure Application Insights
- **Settings Validation**: Environment-specific validation rules

## Testing Strategy

### Unit Testing

- **Framework**: Pytest with fixtures and mocks
- **Coverage**: Minimum coverage for new features
- **Structure**: Mirror source structure in `tests/` directory
- **Patterns**: Arrange-Act-Assert with clear test names

### Integration Testing

- **Azure Services**: Test against live Azure resources
- **Configuration**: Separate test configurations
- **Cleanup**: Automated resource cleanup after tests

## Context Engineering Workflow

### PRP (Product Requirements Prompt) Process

1. **Initial Requirements**: Define in `INITIAL.md`
2. **Context Research**: Analyze codebase patterns
3. **PRP Generation**: Create comprehensive implementation plan
4. **Execution**: Implement with validation gates
5. **Testing**: Automated testing and validation

### Use Case Management

- **MCP Server**: Model Context Protocol server implementation
- **PydanticAI**: Integration examples with PydanticAI framework
- **Template Generator**: Automated code template generation
- **Banking Tools**: Financial data analysis and call report processing

### Example Management

- **Placement**: All examples in `examples/` directory
- **Documentation**: Clear explanation of patterns demonstrated
- **Maintenance**: Keep examples current with codebase evolution
- **Use Cases**: Specialized implementations in `use-cases/` directory

## Deployment Architecture

### Bootstrap Phase

1. **Backend Storage**: Terraform state management
2. **RBAC Setup**: Initial permissions and service accounts
3. **Resource Groups**: Environment-specific organization

### Main Deployment

1. **Azure OpenAI**: Service deployment with security configuration
2. **Key Vault**: Secret storage with access policies
3. **Application Insights**: Monitoring and telemetry setup with OpenTelemetry
4. **Storage**: Conversation history and document storage

### Application Setup

1. **Environment Configuration**: Variable extraction from Terraform
2. **Virtual Environment**: Python dependency management with venv_linux
3. **Service Validation**: Health checks and connectivity tests
4. **Document Storage**: ChromaDB initialization and data directory setup
5. **Tool Loading**: Dynamic tool initialization based on available services

## Observability Strategy

### Logging Categories (log_type field)

- **CONVERSATION**: Chat interactions and message processing
- **AZURE_OPENAI**: API calls, responses, token usage
- **PERFORMANCE**: Response times, throughput, resource usage
- **SECURITY**: Authentication, Key Vault operations
- **SYSTEM**: Application lifecycle, configuration, health checks

### Metrics Collection

- **Azure OpenAI**: Token usage, response times, error rates
- **Application**: Request counts, success rates, user activity
- **Infrastructure**: Resource utilization, availability

### Alerting

- **Error Rates**: Threshold-based alerts for failure rates
- **Performance**: Response time degradation alerts
- **Security**: Authentication failure and anomaly detection

## Future Considerations

### Scalability

- **Horizontal Scaling**: Stateless design enables scaling
- **Load Balancing**: Multiple instance support for Streamlit interface
- **Resource Optimization**: Auto-scaling based on demand
- **ChromaDB Scaling**: Distributed vector search for large document collections

### Feature Expansion

- **Advanced RAG Features**: Multi-modal document support, advanced chunking strategies
- **Multi-Model Support**: Integration with additional LLM providers
- **Enhanced Banking Tools**: Real-time market data integration, regulatory compliance monitoring
- **Collaborative Features**: Multi-user document sharing and chat history

### Tool System Evolution

- **Plugin Architecture**: External tool plugin system
- **Tool Marketplace**: Community-contributed tools
- **Advanced Orchestration**: Multi-agent workflows and tool chaining
- **Performance Optimization**: Tool caching and parallel execution

### Integration Points

- **CI/CD**: GitHub Actions or Azure DevOps integration
- **Monitoring**: Advanced APM solutions beyond OpenTelemetry
- **Security**: Enhanced security scanning and compliance
- **Enterprise Integration**: SAML/SSO, enterprise document systems
- **API Gateway**: RESTful API for headless integration