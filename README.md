# Context Engineering Template

A comprehensive template for getting started with Context Engineering - the discipline of engineering context for AI coding assistants so they have the information necessary to get the job done end to end.

> **Context Engineering is 10x better than prompt engineering and 100x better than vibe coding.**

## 🚀 Quick Start

### For Context Engineering Development

```bash
# 1. Clone this template
git clone https://github.com/coleam00/Context-Engineering-Intro.git
cd Context-Engineering-Intro

# 2. Set up your project rules (optional - template provided)
# Edit CLAUDE.md to add your project-specific guidelines

# 3. Add examples (highly recommended)
# Place relevant code examples in the examples/ folder

# 4. Create your initial feature request
# Edit INITIAL.md with your feature requirements

# 5. Generate a comprehensive PRP (Product Requirements Prompt)
# In Claude Code, run:
/generate-prp INITIAL.md

# 6. Execute the PRP to implement your feature
# In Claude Code, run:
/execute-prp PRPs/your-feature-name.md
```

### For Azure OpenAI RAG Chatbot Deployment

```powershell
# 1. Prerequisites
# - Azure CLI installed and authenticated (az login)
# - Terraform installed (>= 1.0)
# - PowerShell 5.1+ or PowerShell Core

# 2. First-time setup: Bootstrap the Terraform backend
.\scripts\bootstrap.ps1 -Environment dev -Location "East US"

# 3. Deploy the Azure infrastructure
.\scripts\deploy.ps1 -Environment dev -ForceReinit

# 4. Set up the Python environment and install dependencies
.\scripts\setup-env.ps1

# 5. Activate the virtual environment and install dependencies
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt

# 6. Fix DNS issues if pip fails (corporate network remnants)
.\scripts\fix-dns.ps1 -Force

# 7. Launch the RAG-enabled Streamlit web interface (recommended)
python src\main.py
# Or explicitly: python src\main.py streamlit

# 8. Alternative: Use CLI interface for backwards compatibility
python src\main.py --cli chat
```

## 📚 Table of Contents

- [What is Context Engineering?](#what-is-context-engineering)
- [RAG-Enabled Azure OpenAI Chatbot](#rag-enabled-azure-openai-chatbot)
- [RAG Features](#rag-features)
- [Streamlit Web Interface](#streamlit-web-interface)
- [Template Structure](#template-structure)
- [What's Included](#whats-included)
- [Step-by-Step Guide](#step-by-step-guide)
- [Writing Effective INITIAL.md Files](#writing-effective-initialmd-files)
- [The PRP Workflow](#the-prp-workflow)
- [Using Examples Effectively](#using-examples-effectively)
- [Best Practices](#best-practices)

## What's Included

### 🎯 Context Engineering Framework

- **PRP Templates**: Structured templates for creating comprehensive Problem Requirement Plans
- **Claude Code Integration**: Pre-configured commands for AI-assisted development
- **Multi-Agent Workflow**: Example showing how to coordinate multiple AI agents

### 🚀 RAG-Enabled Azure OpenAI Chatbot

- **RAG Integration**: Retrieval-Augmented Generation with ChromaDB vector storage
- **Modern Web Interface**: Streamlit-based UI with document upload and chat features
- **Document Processing**: Support for PDF, DOCX, and TXT files with intelligent chunking
- **CLI Interface**: Legacy command-line interface preserved for backwards compatibility
- **Infrastructure as Code**: Complete Terraform configuration for Azure deployment
- **Secure Architecture**: Key Vault integration, managed identities, and RBAC
- **Deployment Automation**: PowerShell scripts for bootstrap and deployment

### 🏗️ Infrastructure Components

- **Bootstrap Infrastructure**: Separate Terraform configuration for backend storage
- **Main Infrastructure**: Modular Azure OpenAI, Key Vault, and monitoring setup
- **Automated Deployment**: Scripts for environment setup and teardown
- **State Management**: Secure Terraform state storage in Azure

### 📚 Examples & Templates

- **Working Examples**: Real implementations you can learn from
- **Reusable Modules**: Terraform modules for common Azure patterns
- **Documentation**: Comprehensive guides and best practices

### 🛠️ Development Tools

- **Python Environment**: Automated setup and dependency management
- **Testing Framework**: Structure for unit and integration tests
- **Logging & Monitoring**: Comprehensive logging and Azure monitoring integration

## 📊 Logging System

The application uses a sophisticated logging system built around **structlog** with multiple output targets and Azure Application Insights integration.

### Configuration

Logging is configured through environment variables in your `.env` file:

```bash
# Core logging settings
LOG_LEVEL=INFO                           # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FORMAT=json                          # json or text
LOG_FILE_PATH=logs/chatbot.log          # Path to log file

# Feature toggles
ENABLE_CONVERSATION_LOGGING=True         # Enable conversation tracking
ENABLE_PERFORMANCE_METRICS=True         # Enable performance monitoring

# Azure integration (optional)
APPLICATIONINSIGHTS_CONNECTION_STRING=InstrumentationKey=...
```

### Key Features

- **Structured Logging**: JSON format with structured data for machine parsing
- **Multiple Handlers**: File rotation (50MB files, 10 backups), console with colors, Azure Application Insights
- **Conversation Tracking**: Context-aware logging with conversation IDs and user interaction tracking
- **Performance Metrics**: Operation timing, success rates, and custom metrics collection
- **Security Events**: Dedicated security event logging with severity levels

### Usage

```python
import structlog
logger = structlog.get_logger(__name__)

# Basic logging
logger.info("Processing message", user_input_length=len(message))

# Conversation context logging
from services.logging_service import ConversationLogger
with ConversationLogger(conversation_id="123") as logger:
    logger.info("User message received", message_type="chat")

# Performance metrics
from services.logging_service import log_performance_metrics
log_performance_metrics("openai_request", duration=1.23, success=True, tokens=150)
```

### File Locations

- **Main Configuration**: `src/services/logging_service.py` - Central logging service (490 lines)
- **Settings**: `src/config/settings.py` - Environment variable configuration
- **Initialization**: `src/main.py:63-64` - Logging setup during app startup

### Azure Log Analytics Queries

The application logs are stored in Azure Application Insights and can be queried through Azure Log Analytics. Your data is primarily in the **AppTraces** table with additional metrics in **AzureMetrics**, **Usage**, and **AzureDiagnostics** tables.

**Key Fields:**

- **AppRoleName**: Set to "aoai-chatbot" (automatically mapped from Application Insights cloud role)
- **Properties.application**: "aoai-chatbot" (explicitly set in custom dimensions)
- **Properties.component**: Component name (azure_client, chatbot, etc.)
- **Properties.operation_type**: Operation type (startup, chat, azure_operation)
- **Measurements**: Numeric metrics (response_time, tokens, etc.)

#### Basic Queries

```kusto
// All application logs (last 24 hours) - using AppRoleName
AppTraces
| where TimeGenerated >= ago(24h)
| where AppRoleName == "aoai-chatbot"
| project TimeGenerated, Message, SeverityLevel, Properties, Measurements
| order by TimeGenerated desc

// Alternative: All application logs using Properties
AppTraces
| where TimeGenerated >= ago(24h)
| where Properties.application == "aoai-chatbot"
| project TimeGenerated, Message, SeverityLevel, Properties, Measurements
| order by TimeGenerated desc

// Events by category
AppTraces
| where TimeGenerated >= ago(24h)
| where Properties.application == "aoai-chatbot"
| where Properties.event_category == "azure_service"  // or "conversation", "performance", "security"
| project TimeGenerated, Message, Properties.event_type, Properties.component
| order by TimeGenerated desc

// Startup events
AppTraces
| where TimeGenerated >= ago(24h)
| where Properties.application == "aoai-chatbot"
| where Properties.operation_type == "startup"
| project TimeGenerated, Message, Properties.component, Properties.resource_type, Properties.success
| order by TimeGenerated desc

// Azure operations
AppTraces
| where TimeGenerated >= ago(24h)
| where Properties.application == "aoai-chatbot"
| where Properties.event_type == "azure_operation"
| project TimeGenerated, Message, Properties.component, Properties.resource_type, Properties.success
| order by TimeGenerated desc

// Conversation events
AppTraces
| where TimeGenerated >= ago(24h)
| where Properties.application == "aoai-chatbot"
| where Properties.event_category == "conversation"
| project TimeGenerated, Message, Properties.conversation_id, Properties.user_id, Properties.turn_number
| order by TimeGenerated desc

// Security events (auth + key vault)
AppTraces
| where TimeGenerated >= ago(24h)
| where Properties.application == "aoai-chatbot"
| where Properties.event_category == "security"
| project TimeGenerated, Message, Properties.event_type, Properties.success, Properties.credential_type
| order by TimeGenerated desc

// Error analysis
AppTraces
| where TimeGenerated >= ago(24h)
| where SeverityLevel >= 2  // Warning level and above
| where Properties.application == "aoai-chatbot"
| project TimeGenerated, Message, SeverityLevel, Properties.logger, Properties.event_category, Properties.error_type
| order by TimeGenerated desc

// Event category analysis
AppTraces
| where TimeGenerated >= ago(24h)
| where Properties.application == "aoai-chatbot"
| summarize Count = count(),
           ErrorCount = countif(Properties.success == "false" or SeverityLevel >= 2),
           SuccessRate = round((count() - countif(Properties.success == "false" or SeverityLevel >= 2)) * 100.0 / count(), 2)
  by Properties.event_category, Properties.event_type
| order by Count desc

// Component analysis
AppTraces
| where TimeGenerated >= ago(24h)
| where Properties.application == "aoai-chatbot"
| summarize Count = count(),
           ErrorCount = countif(Properties.success == "false"),
           LatestEvent = max(TimeGenerated)
  by Properties.component, Properties.event_type
| order by Count desc
```

#### Performance Monitoring

```kusto
// Performance metrics (when customMeasurements are available)
AppTraces
| where TimeGenerated >= ago(24h)
| where Properties.application == "aoai-chatbot"
| where Measurements != "{}" and isnotempty(Measurements)
| extend
    ResponseTime = todouble(Measurements.response_time),
    TokenCount = toint(Measurements.tokens),
    Success = tobool(Measurements.success)
| project TimeGenerated, Message, ResponseTime, TokenCount, Success, Properties.component
| order by TimeGenerated desc

// Azure metrics from AzureMetrics table
AzureMetrics
| where TimeGenerated >= ago(24h)
| where ResourceProvider == "MICROSOFT.COGNITIVESERVICES"
| project TimeGenerated, MetricName, Average, Count, ResourceGroup
| order by TimeGenerated desc
```

## What is Context Engineering?

Context Engineering represents a paradigm shift from traditional prompt engineering:

### Prompt Engineering vs Context Engineering

**Prompt Engineering:**

- Focuses on clever wording and specific phrasing
- Limited to how you phrase a task
- Like giving someone a sticky note

**Context Engineering:**

- A complete system for providing comprehensive context
- Includes documentation, examples, rules, patterns, and validation
- Like writing a full screenplay with all the details

### Why Context Engineering Matters

1. **Reduces AI Failures**: Most agent failures aren't model failures - they're context failures
2. **Ensures Consistency**: AI follows your project patterns and conventions
3. **Enables Complex Features**: AI can handle multi-step implementations with proper context
4. **Self-Correcting**: Validation loops allow AI to fix its own mistakes

## RAG-Enabled Azure OpenAI Chatbot

This repository includes a complete RAG-enabled Azure OpenAI chatbot with both modern web interface and traditional CLI access. The implementation demonstrates best practices for:

- **Retrieval-Augmented Generation** using ChromaDB vector database
- **Modern web interface** using Streamlit with document upload capabilities  
- **Secure Azure OpenAI deployment** with Key Vault integration
- **Infrastructure as Code** using Terraform with proper state management
- **RBAC and security** following Azure best practices
- **Modular architecture** with separation of concerns

## RAG Features

### 🔍 Document Processing & Retrieval

- **Multi-format Support**: Process PDF, DOCX, and TXT documents
- **Intelligent Chunking**: Smart text segmentation with configurable overlap
- **Vector Storage**: ChromaDB integration with persistent local storage
- **Semantic Search**: Azure OpenAI embeddings for document similarity matching
- **Source Attribution**: Track and cite document sources in responses

### 🤖 AI-Powered Chat

- **Context-Aware Responses**: Leverage retrieved document chunks for accurate answers
- **Confidence Scoring**: Assess and display confidence levels for responses
- **Token Management**: Track and optimize token usage across operations
- **Error Handling**: Graceful degradation when documents or services are unavailable
- **Conversation Memory**: Maintain chat history within sessions

### ⚙️ Configuration & Customization

- **Retrieval Parameters**: Adjust chunk count, similarity thresholds, and search filters
- **Processing Limits**: Configure file size limits and chunk sizes
- **UI Customization**: Streamlit theming and component configuration
- **Logging Integration**: Comprehensive structured logging with Azure Application Insights

## Streamlit Web Interface

### 📱 Modern User Experience

- **Document Upload**: Drag-and-drop interface for multiple file types
- **Real-time Processing**: Progress indicators and status updates
- **Interactive Chat**: Modern chat interface with message history
- **Source Display**: Expandable source references with document citations
- **Responsive Design**: Works on desktop and mobile devices

### 🛠️ Management Features

- **Document Library**: View, manage, and delete uploaded documents
- **System Status**: Real-time health monitoring and metrics
- **Settings Panel**: Adjust retrieval parameters and preferences
- **Session Management**: Persistent conversation state
- **Error Handling**: User-friendly error messages and recovery options

### 🎨 Customization Options

- **Theming**: Configurable colors, fonts, and layout options
- **Component Control**: Show/hide sources, adjust sidebar behavior
- **Performance Tuning**: Optimize for different deployment scenarios
- **Authentication**: Ready for future auth integration
- **Configuration**: Flexible settings via TOML files and environment variables

### Architecture Overview

```
Azure Infrastructure:
├── Bootstrap Infrastructure (infrastructure/bootstrap/)
│   ├── Storage account for Terraform state
│   ├── Resource group for backend
│   └── RBAC permissions for deployer
├── Main Infrastructure (infrastructure/)
│   ├── Azure OpenAI service (GPT-4 + embeddings)
│   ├── Key Vault for secure configuration
│   ├── Storage account for conversation history
│   ├── Application Insights for monitoring
│   └── Optional App Service for web deployment
└── RAG-Enabled Application (src/)
    ├── Streamlit Web Interface (ui/)
    │   ├── Document upload and management
    │   ├── Interactive chat interface
    │   └── Real-time status monitoring
    ├── RAG Processing Engine (rag/)
    │   ├── Document processor (PDF/DOCX/TXT)
    │   ├── ChromaDB vector store
    │   └── Retrieval and generation
    ├── Legacy CLI Interface (main.py)
    │   ├── Command-line chatbot
    │   ├── Health monitoring
    │   └── Configuration management
    └── Core Services
        ├── Azure OpenAI client
        ├── Logging and observability
        └── Configuration management

Local Storage:
├── ChromaDB Vector Database (data/chromadb/)
│   ├── Document embeddings
│   ├── Metadata and sources
│   └── Persistent storage
└── Configuration (.streamlit/)
    ├── UI themes and settings
    ├── Security configuration
    └── Performance tuning
```

### Prerequisites

- **Azure CLI** installed and authenticated (`az login`)
- **Terraform** >= 1.0 installed
- **PowerShell** 5.1+ or PowerShell Core
- **Python** 3.8+ (for running the chatbot)
- **Azure subscription** with appropriate permissions

### Deployment Process

The deployment follows a two-phase approach for proper state management:

#### Phase 1: Bootstrap (Run Once)

```powershell
# Creates the Terraform backend storage and permissions
.\scripts\bootstrap.ps1 -Environment dev -Location "East US"
```

This creates:

- Resource group for Terraform state (`tfstate-rg-dev`)
- Storage account for Terraform state files
- Storage container for state files
- RBAC permissions for the deployer

#### Phase 2: Main Infrastructure

```powershell
# Deploys the Azure OpenAI chatbot infrastructure
.\scripts\deploy.ps1 -Environment dev -ForceReinit
```

This creates:

- Azure OpenAI service with GPT-4 deployment
- Key Vault with secure configuration
- Storage account for conversation history
- Application Insights for monitoring
- Managed identity with appropriate RBAC

#### Phase 3: Application Setup

```powershell
# Set up Python environment and dependencies
.\scripts\setup-env.ps1
pip install -r requirements.txt

# Test the deployment
python src\main.py health

# Launch Streamlit web interface (recommended)
python src\main.py
# Interface available at: http://localhost:8501

# Alternative: Start CLI chat (legacy)
python src\main.py --cli chat

# Alternative: Use specific Streamlit command with custom port
python src\main.py streamlit --port 8502 --host 0.0.0.0
```

### Key Features

**🔍 RAG & Document Intelligence**

- Multi-format document processing (PDF, DOCX, TXT)
- ChromaDB vector database with local persistence
- Intelligent text chunking and embedding
- Semantic search with confidence scoring
- Source attribution and citation tracking

**🖥️ Modern Web Interface**

- Streamlit-based responsive web UI
- Real-time document upload and processing
- Interactive chat with message history
- Configurable retrieval parameters
- System health monitoring dashboard

**🔒 Security First**

- All secrets stored in Azure Key Vault
- Managed Identity for secure authentication
- RBAC with least-privilege access
- HTTPS-only storage accounts
- Local vector storage with gitignore protection

**🏗️ Infrastructure as Code**

- Complete Terraform configuration
- Proper state management with remote backend
- Environment-specific configurations
- Modular and reusable components

**📊 Monitoring & Observability**

- Application Insights integration
- Structured logging with log types
- Health check endpoints
- Conversation and performance tracking
- RAG-specific metrics and debugging

**🚀 Production Ready**

- Error handling and graceful degradation
- Conversation persistence and memory
- Rate limiting awareness
- Scalable architecture
- CLI backwards compatibility

### Customization

The infrastructure is highly configurable through Terraform variables:

- **Environment**: `dev`, `staging`, `prod`
- **Azure region**: Any Azure OpenAI supported region
- **OpenAI model**: GPT-4, GPT-3.5-turbo, etc.
- **Capacity**: Token per minute limits
- **Optional components**: App Service, additional storage

### Management Commands

```powershell
# View infrastructure outputs
cd infrastructure
terraform output

# Update environment configuration
.\scripts\setup-env.ps1

# Fix DNS issues (corporate network remnants)
.\scripts\fix-dns.ps1

# Destroy main resources (keeps backend)
.\scripts\destroy.ps1

# Destroy everything including backend
cd infrastructure\bootstrap
terraform destroy
```

### Troubleshooting

#### SSL Handshake Failures During pip install

If you encounter SSL errors like:

```
WARNING: Retrying (Retry(total=0...)) after connection broken by 'SSLError...'
```

This is typically caused by corporate DNS servers persisting after disconnecting from corporate networks. Run the DNS fix script:

```powershell
# Automatically fix corporate DNS settings
.\scripts\fix-dns.ps1 -Force
```

The script will:

- Detect corporate DNS servers on all network interfaces
- Replace them with public DNS servers (Google DNS by default)
- Flush the DNS cache
- Test DNS resolution

#### Other Common Issues

**Terraform Backend Issues:**

```powershell
# Re-initialize Terraform backend
.\scripts\deploy.ps1 -Environment dev -ForceReinit
```

**Environment Variable Issues:**

```powershell
# Regenerate environment variables from Terraform outputs
.\scripts\setup-env.ps1
```

**Permission Issues:**

- Ensure you're running PowerShell as Administrator
- Check Azure CLI authentication: `az account show`

## Template Structure

```
context-engineering-intro/
├── .claude/
│   ├── commands/
│   │   ├── generate-prp.md    # Generates comprehensive PRPs
│   │   └── execute-prp.md     # Executes PRPs to implement features
│   └── settings.local.json    # Claude Code permissions
├── infrastructure/
│   ├── bootstrap/             # Bootstrap Terraform for backend storage
│   │   └── main.tf           # Storage account and RBAC setup
│   ├── modules/
│   │   └── azure-openai/     # Reusable Azure OpenAI module
│   │       ├── main.tf       # Core resources
│   │       ├── variables.tf  # Input variables
│   │       ├── outputs.tf    # Output values
│   │       └── rbac.tf       # RBAC configuration
│   ├── main.tf               # Main infrastructure configuration
│   ├── variables.tf          # Global variables
│   ├── outputs.tf           # Infrastructure outputs
│   └── providers.tf         # Terraform providers and backend
├── scripts/
│   ├── bootstrap.ps1         # Bootstrap backend storage
│   ├── deploy.ps1           # Deploy main infrastructure
│   ├── destroy.ps1          # Destroy infrastructure
│   └── setup-env.ps1        # Set up Python environment
├── src/
│   ├── main.py              # Entry point (Streamlit + CLI)
│   ├── ui/                  # Streamlit web interface
│   │   └── streamlit_app.py # Main Streamlit application
│   ├── rag/                 # RAG processing engine
│   │   ├── document_processor.py  # Document parsing and chunking
│   │   ├── vector_store.py         # ChromaDB integration
│   │   └── retriever.py           # RAG retrieval and generation
│   ├── chatbot/            # Chatbot implementations
│   │   ├── agent.py        # Legacy CLI chatbot
│   │   └── rag_agent.py    # RAG-enabled chatbot
│   ├── config/             # Configuration management
│   ├── services/           # Azure service clients
│   └── utils/              # Utility functions
├── PRPs/
│   ├── templates/
│   │   └── prp_base.md       # Base template for PRPs
│   └── EXAMPLE_multi_agent_prp.md  # Example of a complete PRP
├── data/
│   └── chromadb/            # ChromaDB vector database storage
├── .streamlit/              # Streamlit configuration
│   ├── config.toml          # Main Streamlit settings
│   ├── secrets.toml         # Secrets template (gitignored)
│   └── README.md           # Configuration documentation
├── tests/                   # Comprehensive unit tests
│   ├── test_document_processor.py
│   ├── test_chromadb_manager.py
│   ├── test_rag_retriever.py
│   ├── test_rag_chatbot_agent.py
│   └── test_streamlit_app.py
├── examples/                  # Your code examples (critical!)
├── CLAUDE.md                 # Global rules for AI assistant
├── INITIAL.md               # Template for feature requests
├── INITIAL_EXAMPLE.md       # Example feature request
├── requirements.txt         # Python dependencies (includes RAG deps)
└── README.md                # This file
```

This template now includes a complete RAG implementation demonstrating how Context Engineering principles can be applied to build sophisticated AI-powered document processing systems.

## Step-by-Step Guide

### 1. Set Up Global Rules (CLAUDE.md)

The `CLAUDE.md` file contains project-wide rules that the AI assistant will follow in every conversation. The template includes:

- **Project awareness**: Reading planning docs, checking tasks
- **Code structure**: File size limits, module organization
- **Testing requirements**: Unit test patterns, coverage expectations
- **Style conventions**: Language preferences, formatting rules
- **Documentation standards**: Docstring formats, commenting practices

**You can use the provided template as-is or customize it for your project.**

### 2. Create Your Initial Feature Request

Edit `INITIAL.md` to describe what you want to build:

```markdown
## FEATURE:

[Describe what you want to build - be specific about functionality and requirements]

## EXAMPLES:

[List any example files in the examples/ folder and explain how they should be used]

## DOCUMENTATION:

[Include links to relevant documentation, APIs, or MCP server resources]

## OTHER CONSIDERATIONS:

[Mention any gotchas, specific requirements, or things AI assistants commonly miss]
```

**See `INITIAL_EXAMPLE.md` for a complete example.**

### 3. Generate the PRP

PRPs (Product Requirements Prompts) are comprehensive implementation blueprints that include:

- Complete context and documentation
- Implementation steps with validation
- Error handling patterns
- Test requirements

They are similar to PRDs (Product Requirements Documents) but are crafted more specifically to instruct an AI coding assistant.

Run in Claude Code:

```bash
/generate-prp INITIAL.md
```

**Note:** The slash commands are custom commands defined in `.claude/commands/`. You can view their implementation:

- `.claude/commands/generate-prp.md` - See how it researches and creates PRPs
- `.claude/commands/execute-prp.md` - See how it implements features from PRPs

The `$ARGUMENTS` variable in these commands receives whatever you pass after the command name (e.g., `INITIAL.md` or `PRPs/your-feature.md`).

This command will:

1. Read your feature request
2. Research the codebase for patterns
3. Search for relevant documentation
4. Create a comprehensive PRP in `PRPs/your-feature-name.md`

### 4. Execute the PRP

Once generated, execute the PRP to implement your feature:

```bash
/execute-prp PRPs/your-feature-name.md
```

The AI coding assistant will:

1. Read all context from the PRP
2. Create a detailed implementation plan
3. Execute each step with validation
4. Run tests and fix any issues
5. Ensure all success criteria are met

## Writing Effective INITIAL.md Files

### Key Sections Explained

**FEATURE**: Be specific and comprehensive

- ❌ "Build a web scraper"
- ✅ "Build an async web scraper using BeautifulSoup that extracts product data from e-commerce sites, handles rate limiting, and stores results in PostgreSQL"

**EXAMPLES**: Leverage the examples/ folder

- Place relevant code patterns in `examples/`
- Reference specific files and patterns to follow
- Explain what aspects should be mimicked

**DOCUMENTATION**: Include all relevant resources

- API documentation URLs
- Library guides
- MCP server documentation
- Database schemas

**OTHER CONSIDERATIONS**: Capture important details

- Authentication requirements
- Rate limits or quotas
- Common pitfalls
- Performance requirements

## The PRP Workflow

### How /generate-prp Works

The command follows this process:

1. **Research Phase**

   - Analyzes your codebase for patterns
   - Searches for similar implementations
   - Identifies conventions to follow

2. **Documentation Gathering**

   - Fetches relevant API docs
   - Includes library documentation
   - Adds gotchas and quirks

3. **Blueprint Creation**

   - Creates step-by-step implementation plan
   - Includes validation gates
   - Adds test requirements

4. **Quality Check**
   - Scores confidence level (1-10)
   - Ensures all context is included

### How /execute-prp Works

1. **Load Context**: Reads the entire PRP
2. **Plan**: Creates detailed task list using TodoWrite
3. **Execute**: Implements each component
4. **Validate**: Runs tests and linting
5. **Iterate**: Fixes any issues found
6. **Complete**: Ensures all requirements met

See `PRPs/EXAMPLE_multi_agent_prp.md` for a complete example of what gets generated.

## Using Examples Effectively

The `examples/` folder is **critical** for success. AI coding assistants perform much better when they can see patterns to follow.

### What to Include in Examples

1. **Code Structure Patterns**

   - How you organize modules
   - Import conventions
   - Class/function patterns

2. **Testing Patterns**

   - Test file structure
   - Mocking approaches
   - Assertion styles

3. **Integration Patterns**

   - API client implementations
   - Database connections
   - Authentication flows

4. **CLI Patterns**
   - Argument parsing
   - Output formatting
   - Error handling

### Example Structure

```
examples/
├── README.md           # Explains what each example demonstrates
├── cli.py             # CLI implementation pattern
├── agent/             # Agent architecture patterns
│   ├── agent.py      # Agent creation pattern
│   ├── tools.py      # Tool implementation pattern
│   └── providers.py  # Multi-provider pattern
└── tests/            # Testing patterns
    ├── test_agent.py # Unit test patterns
    └── conftest.py   # Pytest configuration
```

## Best Practices

### 1. Be Explicit in INITIAL.md

- Don't assume the AI knows your preferences
- Include specific requirements and constraints
- Reference examples liberally

### 2. Provide Comprehensive Examples

- More examples = better implementations
- Show both what to do AND what not to do
- Include error handling patterns

### 3. Use Validation Gates

- PRPs include test commands that must pass
- AI will iterate until all validations succeed
- This ensures working code on first try

### 4. Leverage Documentation

- Include official API docs
- Add MCP server resources
- Reference specific documentation sections

### 5. Customize CLAUDE.md

- Add your conventions
- Include project-specific rules
- Define coding standards

## Resources

- [Claude Code Documentation](https://docs.anthropic.com/en/docs/claude-code)
- [Context Engineering Best Practices](https://www.philschmid.de/context-engineering)
