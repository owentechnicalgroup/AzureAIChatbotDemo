# PLANNING.md

## Project Overview

The **Context Engineering Template** is a comprehensive framework that combines two major components:

1. **Context Engineering Framework** - A discipline for engineering context for AI coding assistants
2. **Azure OpenAI Chatbot** - A production-ready CLI chatbot with Infrastructure as Code

## Project Architecture

### Core Components

```
context-engineering-intro/
├── infrastructure/           # Terraform IaC for Azure deployment
│   ├── bootstrap/           # Backend storage setup
│   ├── modules/             # Reusable Terraform modules
│   └── main.tf             # Primary infrastructure
├── src/                    # Python application source
│   ├── chatbot/           # AI chatbot implementation
│   ├── config/            # Configuration management
│   ├── services/          # Azure service clients
│   ├── observability/     # Dual logging/telemetry system
│   └── utils/             # Utility functions
├── scripts/               # PowerShell deployment automation
├── PRPs/                  # Product Requirements Prompts
├── examples/              # Code patterns and examples
└── use-cases/             # Specialized implementations
```

### Technology Stack

- **Cloud Platform**: Microsoft Azure
- **Infrastructure**: Terraform (Infrastructure as Code)
- **Language**: Python 3.8+
- **AI Integration**: Azure OpenAI + LangChain
- **Authentication**: Azure Identity (Managed Identity, Azure CLI)
- **Security**: Azure Key Vault for secrets management
- **Logging**: Structured logging with structlog + Azure Application Insights
- **CLI Framework**: Click + Rich (enhanced console output)
- **Configuration**: Pydantic Settings with environment variable support

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

2. **Production-Ready Infrastructure**
   - Secure, scalable Azure OpenAI deployment
   - Automated infrastructure provisioning and management
   - Enterprise-grade logging and observability

3. **Developer Experience**
   - Intuitive CLI interface with rich output
   - Comprehensive error handling and debugging
   - Clear documentation and examples

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

### Logging Architecture

**Pattern**: Dual observability system
- **Application Logging**: General application events and errors
- **Chat Observability**: Specialized AI interaction telemetry
- **Structured Logging**: JSON format with consistent field schemas
- **Multiple Handlers**: Console, File, Azure Application Insights

### Error Handling

**Pattern**: Graceful degradation with rich error reporting
- **Structured Exceptions**: Custom error types with context
- **User-Friendly Messages**: Technical details hidden from end users
- **Debug Mode**: Detailed stacktraces and diagnostic information

### CLI Design

**Pattern**: Command groups with rich interactive elements
- **Click Framework**: Hierarchical command structure
- **Rich Console**: Enhanced output with colors, tables, and progress bars
- **Context Passing**: Shared state across command hierarchy

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
4. **Logging**: Must integrate with Azure Application Insights
5. **Configuration**: Environment-specific with secure secret management

### Business Constraints

1. **Security**: No secrets in code or version control
2. **Compliance**: Structured logging for audit trails
3. **Scalability**: Stateless design for horizontal scaling
4. **Cost**: Efficient resource usage and proper cleanup
5. **Maintainability**: Clear separation of concerns and documentation

### Operational Constraints

1. **Deployment**: Automated with rollback capability
2. **Monitoring**: Health checks and observability requirements
3. **Error Recovery**: Graceful failure handling and retry logic
4. **Documentation**: Self-documenting code with comprehensive README

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

### Example Management

- **Placement**: All examples in `examples/` directory
- **Documentation**: Clear explanation of patterns demonstrated
- **Maintenance**: Keep examples current with codebase evolution

## Deployment Architecture

### Bootstrap Phase

1. **Backend Storage**: Terraform state management
2. **RBAC Setup**: Initial permissions and service accounts
3. **Resource Groups**: Environment-specific organization

### Main Deployment

1. **Azure OpenAI**: Service deployment with security configuration
2. **Key Vault**: Secret storage with access policies
3. **Application Insights**: Monitoring and telemetry setup
4. **Storage**: Conversation history and file storage

### Application Setup

1. **Environment Configuration**: Variable extraction from Terraform
2. **Virtual Environment**: Python dependency management
3. **Service Validation**: Health checks and connectivity tests

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
- **Load Balancing**: Multiple instance support
- **Resource Optimization**: Auto-scaling based on demand

### Feature Expansion

- **Web Interface**: Potential web UI addition
- **Multi-Model**: Support for additional AI models
- **Advanced Features**: Function calling, RAG integration

### Integration Points

- **CI/CD**: GitHub Actions or Azure DevOps integration
- **Monitoring**: Advanced APM solutions
- **Security**: Enhanced security scanning and compliance