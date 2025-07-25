name: "Azure OpenAI CLI Chatbot with LangChain Integration"
description: |
  A comprehensive PRP for implementing a Python-based command-line chatbot application 
  that leverages Azure OpenAI GPT-4 through Azure AI Foundry and LangChain integration.

## Goal
Build a production-ready Python CLI chatbot application that integrates with Azure OpenAI GPT-4 through LangChain, featuring structured logging, conversation memory, configurable system prompts, robust error handling, and extensible architecture supporting future web interface integration. Includes complete Terraform infrastructure provisioning for Azure resources.

## Why
- **Business Value**: Provides a foundational AI assistant that can be extended for customer service, internal knowledge management, or product demos
- **User Impact**: Enables natural language interaction with Azure OpenAI's powerful GPT-4 model through an accessible command-line interface
- **Integration Foundation**: Creates a modular architecture that supports future web interface development and advanced AI capabilities
- **Problems Solved**: 
  - Complex Azure OpenAI service integration through standardized patterns
  - Conversation state management and memory persistence
  - Robust error handling and monitoring for AI applications
  - Configurable prompt engineering capabilities

## What
A complete solution consisting of:

**Infrastructure (Terraform)**:
- Azure Resource Group for organizing resources
- Azure OpenAI Service with GPT-4 model deployment
- Azure Log Analytics Workspace for application monitoring
- Azure Key Vault for secure credential storage
- Proper IAM roles and network security configurations

**Application (Python CLI)**:
- Interactive chat sessions with Azure OpenAI GPT-4
- Persistent conversation history within sessions
- Configurable system prompts via environment variables or CLI arguments
- Structured JSON logging compatible with Azure Application Insights
- Comprehensive error handling with graceful degradation
- Connection pooling and retry logic for reliability
- Clean session management with optional conversation summaries

### Success Criteria
- [ ] Terraform successfully provisions all Azure resources
- [ ] Azure OpenAI service is properly configured with GPT-4 deployment
- [ ] Python application successfully connects to Azure OpenAI GPT-4 service
- [ ] Maintains multi-turn conversation context and memory
- [ ] Implements structured JSON logging to local files and Azure
- [ ] Supports configurable system prompts
- [ ] Provides comprehensive error handling and user feedback
- [ ] Manages conversation history cleanly
- [ ] Includes complete documentation for setup and usage
- [ ] Passes all unit tests and linting checks
- [ ] Demonstrates working CLI interface with rich output formatting
- [ ] Infrastructure can be destroyed and recreated reliably

## All Needed Context

### Documentation & References
```yaml
# MUST READ - Include these in your context window

# Infrastructure & Terraform Documentation
- url: https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs
  why: Azure Resource Manager Terraform provider documentation

- url: https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/cognitive_account
  why: Azure OpenAI service (Cognitive Services) Terraform resource

- url: https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/cognitive_deployment
  why: Azure OpenAI model deployment configuration

- url: https://learn.microsoft.com/en-us/azure/ai-services/openai/how-to/create-resource?pivots=web-portal
  why: Azure OpenAI resource creation patterns and requirements

- url: https://learn.microsoft.com/en-us/azure/key-vault/general/overview
  why: Azure Key Vault for secure credential management

# Application & Integration Documentation
- url: https://learn.microsoft.com/en-us/azure/ai-services/openai/
  why: Main Azure OpenAI documentation for service setup and configuration

- url: https://learn.microsoft.com/en-us/azure/ai-services/openai/quickstart
  why: Python quickstart guide for Azure OpenAI integration patterns

- url: https://learn.microsoft.com/en-us/azure/ai-foundry/openai/references/on-your-data
  why: Latest API reference for Azure OpenAI (2024-05-01-preview)

- url: https://learn.microsoft.com/en-us/azure/ai-foundry/how-to/develop/langchain
  why: LangChain integration patterns with Azure AI Foundry

- url: https://python.langchain.com/docs/integrations/llms/azure_openai/
  why: LangChain Azure OpenAI integration documentation and examples

- url: https://learn.microsoft.com/en-us/azure/developer/python/azure-ai-for-python-developers
  why: Azure AI patterns and best practices for Python developers

# Codebase Examples
- file: examples/azure_openai_langchain_sample/README.md
  why: LangChain integration patterns and examples to follow

- file: examples/sample-app-aoai-chatGPT/README.md  
  why: Azure OpenAI configuration patterns, environment variables setup

- file: examples/sample-app-aoai-chatGPT/infra/
  why: Azure infrastructure patterns using Bicep (convert to Terraform)

- file: examples/openai/Basic_Samples/LangChain/
  why: Basic LangChain implementation patterns and requirements.txt examples

- file: examples/openai/Basic_Samples/Chat/requirements.txt
  why: Dependencies for Azure OpenAI chat implementations
```

### Current Codebase Tree
```bash
context-engineering-intro/
├── .claude/
│   ├── commands/
│   │   ├── generate-prp.md
│   │   └── execute-prp.md
│   └── settings.local.json
├── PRPs/
│   ├── templates/
│   │   └── prp_base.md
│   └── EXAMPLE_multi_agent_prp.md
├── examples/
│   ├── azure_openai_langchain_sample/
│   ├── openai/
│   └── sample-app-aoai-chatGPT/
├── CLAUDE.md
├── INITIAL.md
├── INITIAL_EXAMPLE.md
└── README.md
```

### Desired Codebase Tree with Files to be Added
```bash
context-engineering-intro/
├── infrastructure/              # Terraform infrastructure code
│   ├── main.tf                 # Main Terraform configuration
│   ├── variables.tf            # Input variables
│   ├── outputs.tf              # Output values
│   ├── providers.tf            # Provider configurations
│   ├── terraform.tfvars.example # Example variable values
│   └── modules/                # Reusable Terraform modules
│       └── azure-openai/       # Azure OpenAI module
│           ├── main.tf         # OpenAI service and deployment
│           ├── variables.tf    # Module variables
│           ├── outputs.tf      # Module outputs
│           └── versions.tf     # Provider version constraints
├── src/
│   ├── __init__.py
│   ├── main.py                    # CLI entry point with Click
│   ├── chatbot/
│   │   ├── __init__.py
│   │   ├── agent.py              # Main chatbot agent using LangChain
│   │   ├── conversation.py       # Conversation memory management
│   │   └── prompts.py           # System prompt templates
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py          # Configuration management with dotenv
│   ├── services/
│   │   ├── __init__.py
│   │   ├── azure_client.py      # Azure OpenAI client wrapper
│   │   └── logging_service.py   # Structured logging service
│   └── utils/
│       ├── __init__.py
│       ├── error_handlers.py    # Custom exception classes
│       └── console.py          # Rich console utilities
├── tests/
│   ├── __init__.py
│   ├── conftest.py             # Pytest configuration and fixtures
│   ├── test_agent.py          # Unit tests for chatbot agent
│   ├── test_conversation.py   # Unit tests for conversation management
│   ├── test_azure_client.py   # Unit tests for Azure client
│   └── test_settings.py       # Unit tests for configuration
├── scripts/                    # Deployment and utility scripts
│   ├── deploy.sh              # Infrastructure deployment script
│   ├── destroy.sh             # Infrastructure cleanup script
│   └── setup-env.sh           # Environment setup helper
├── requirements.txt            # Project dependencies
├── .env.example               # Environment variables template
├── venv_linux/                # Virtual environment (as per CLAUDE.md)
└── logs/                      # Local log files directory
```

### Known Gotchas & Library Quirks
```python
# CRITICAL: Terraform Azure Provider gotchas
# - Azure OpenAI requires explicit location: "East US" for GPT-4 availability
# - Cognitive Account kind must be "OpenAI" not "CognitiveServices"
# - Model deployment names must be globally unique within the resource
# - GPT-4 requires special approval in many Azure subscriptions

# CRITICAL: Azure OpenAI Terraform resource limitations
# - azurerm_cognitive_deployment requires exact model format: "gpt-4" not "gpt-4-32k"
# - Scale settings must match model capabilities (TPM limits)
# - Some regions don't support all models - check availability first

# CRITICAL: Azure Key Vault integration
# - Key Vault names must be globally unique across all Azure tenants
# - Access policies vs RBAC model - choose one consistently (RBAC recommended)
# - Secret names have character restrictions (alphanumeric and hyphens only)

# CRITICAL: Azure Key Vault authentication patterns
# - DefaultAzureCredential chain: ManagedIdentity → EnvironmentCredential → AzureCLI → etc.
# - For local development: Use Azure CLI (`az login`) or service principal
# - For production: Use Managed Identity (System-assigned or User-assigned)
# - For CI/CD: Use Service Principal with client secret or certificate
# - RBAC roles: "Key Vault Secrets User" (read), "Key Vault Secrets Officer" (manage)
# - Access policies are legacy - use RBAC for new implementations

# CRITICAL: Azure OpenAI requires specific SDK versions for compatibility
# langchain-openai >= 0.1.0 required for Azure OpenAI integration
# openai >= 1.0.0 for latest API compatibility

# CRITICAL: Environment variable naming conventions
# Azure OpenAI uses AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY
# Different from standard OpenAI which uses OPENAI_API_KEY

# CRITICAL: LangChain Azure integration gotchas
# - Must use AzureChatOpenAI not ChatOpenAI for Azure endpoints
# - API version must be specified: api_version="2024-05-01-preview"
# - Deployment name != model name in Azure OpenAI

# CRITICAL: Structured logging with structlog
# - Must configure JSON formatter for Azure Application Insights compatibility
# - Use context binding for conversation tracking: logger.bind(conversation_id=id)
# - Avoid logging sensitive user input or API keys

# CRITICAL: Click CLI framework
# - Use @click.group() for main command with subcommands
# - Environment variables override CLI arguments: auto_envvar_prefix="CHATBOT"
# - Rich integration requires careful handling of click.echo vs rich.print

# CRITICAL: Virtual environment usage per CLAUDE.md
# - Always use venv_linux for Python commands including tests
# - Source activation: source venv_linux/bin/activate before running

# CRITICAL: Terraform remote state management
# - Always use remote state (Azure Storage Account) for team collaboration
# - Never commit terraform.tfstate files to version control
# - Storage Account names must be globally unique across all Azure
# - Enable versioning and soft delete on storage account for state recovery
# - Use different state keys for different environments (dev/staging/prod)
# - Plan before apply, especially for destructive changes
# - State locking prevents concurrent modifications - don't force unlock unless certain

# CRITICAL: Terraform backend initialization
# - Backend configuration cannot use variables - must be hardcoded or passed via -backend-config
# - terraform init must be run with backend configuration before any other commands
# - Changing backend configuration requires terraform init -migrate-state
# - Backend storage account must exist before terraform init - chicken/egg problem requires manual creation
```

## Implementation Blueprint

### Data Models and Structure

Create the core data models to ensure type safety and consistency:
```python
# Pydantic models for configuration and conversation state
- ConfigModel: Azure OpenAI settings, logging config, prompt templates
- ConversationState: Message history, session metadata, user preferences
- MessageModel: Role, content, timestamp, conversation_id
- ErrorResponse: Error type, message, recovery suggestions
```

### List of Tasks to be Completed in Order

```yaml
Task 1:
CREATE infrastructure/providers.tf:
  - CONFIGURE Terraform Azure provider with required features
  - SET minimum version constraints for azurerm provider
  - INCLUDE backend configuration for remote state in Azure Storage
  - ADD required provider features for Key Vault and Cognitive Services
  - CONFIGURE state locking with Azure Storage Account and container
  - SET encryption at rest for state files

Task 2:
CREATE infrastructure/variables.tf:
  - DEFINE input variables for resource naming and location
  - INCLUDE Azure subscription and tenant configurations
  - ADD OpenAI model and deployment specifications
  - SET default values for resource tags and naming conventions

Task 3:
CREATE infrastructure/modules/azure-openai/main.tf:
  - IMPLEMENT Azure Resource Group creation
  - CREATE Azure OpenAI Cognitive Services account
  - ADD GPT-4 model deployment with appropriate scaling
  - INCLUDE Key Vault for secure credential storage
  - CREATE Log Analytics Workspace for monitoring

Task 4:
CREATE infrastructure/modules/azure-openai/variables.tf:
  - DEFINE module input variables with validation
  - INCLUDE resource naming and location parameters
  - ADD OpenAI model configuration options
  - SET scaling and performance parameters

Task 5:
CREATE infrastructure/modules/azure-openai/outputs.tf:
  - OUTPUT Azure OpenAI endpoint URL
  - EXPOSE API keys and deployment names
  - PROVIDE Key Vault references for application use
  - INCLUDE resource IDs for dependency management
  - OUTPUT Managed Identity principal IDs for RBAC assignments

Task 5.5:
CREATE infrastructure/modules/azure-openai/rbac.tf:
  - CONFIGURE RBAC roles for Key Vault access
  - CREATE system-assigned Managed Identity for application
  - ASSIGN "Key Vault Secrets User" role to application identity
  - CONFIGURE developer access with "Key Vault Secrets Officer" role
  - INCLUDE conditional RBAC assignments for different environments

Task 6:
CREATE infrastructure/main.tf:
  - INSTANTIATE azure-openai module with configuration
  - SET up resource tagging and naming conventions
  - CONFIGURE module dependencies and data flow
  - INCLUDE local values for computed configurations

Task 7:
CREATE infrastructure/outputs.tf:
  - OUTPUT key infrastructure values for application
  - INCLUDE connection strings and endpoints
  - PROVIDE deployment names and resource identifiers
  - ADD Key Vault secret references

Task 8:
CREATE infrastructure/terraform.tfvars.example:
  - DOCUMENT all required variable values
  - INCLUDE example configurations for different environments
  - ADD comments explaining each variable's purpose
  - PROVIDE secure defaults where appropriate

Task 8.5:
CREATE infrastructure/backend.tf:
  - CONFIGURE Azure Storage backend for remote state
  - INCLUDE state locking configuration with lease management
  - ADD encryption settings for state file security
  - SUPPORT multiple environments with workspace isolation
  - DOCUMENT backend initialization requirements

Task 9:
CREATE scripts/deploy.sh:
  - IMPLEMENT Terraform remote state setup and initialization
  - CREATE Azure Storage Account for state backend (if not exists)
  - ADD validation and security checks
  - INCLUDE automated deployment workflow with state verification
  - SUPPORT environment-specific deployments and state isolation
  - CONFIGURE state locking and backup procedures

Task 10:
CREATE scripts/destroy.sh:
  - IMPLEMENT safe infrastructure cleanup
  - ADD confirmation prompts for destructive operations
  - INCLUDE state backup before destruction
  - SUPPORT selective resource cleanup

Task 11:
CREATE src/config/settings.py:
  - IMPLEMENT Pydantic BaseSettings for configuration management
  - INCLUDE Azure OpenAI endpoint, API key, model deployment name
  - SUPPORT environment variables with .env file fallback
  - ADD logging configuration (level, format, file paths)
  - INCLUDE prompt templates and conversation settings
  - INTEGRATE with Terraform outputs for dynamic configuration

Task 12:
CREATE src/utils/error_handlers.py:
  - DEFINE custom exception classes: AzureOpenAIError, ConfigurationError, ConversationError
  - IMPLEMENT error recovery suggestions mapping
  - ADD logging integration for error tracking
  - INCLUDE user-friendly error message formatting

Task 13:
CREATE src/services/logging_service.py:
  - IMPLEMENT structlog configuration for JSON logging
  - SUPPORT Azure Application Insights compatibility
  - ADD conversation ID binding and context management
  - INCLUDE log rotation and file management
  - CREATE performance metrics logging (response times, token usage)

Task 14:
CREATE src/services/azure_client.py:
  - IMPLEMENT Azure OpenAI client wrapper using langchain-openai
  - ADD connection pooling and retry logic with exponential backoff
  - INCLUDE rate limiting awareness and user feedback
  - SUPPORT configurable timeouts and error handling
  - IMPLEMENT token usage tracking and logging
  - INTEGRATE with Terraform-provisioned resources

Task 15:
CREATE src/chatbot/prompts.py:
  - DEFINE system prompt templates using Jinja2 or f-strings
  - SUPPORT configurable prompt parameters (temperature, max_tokens)
  - INCLUDE conversation context injection patterns
  - ADD prompt validation and sanitization
  - CREATE prompt history and versioning support

Task 16:
CREATE src/chatbot/conversation.py:
  - IMPLEMENT conversation memory management with LangChain memory classes
  - SUPPORT persistent conversation history within sessions
  - ADD conversation summarization capabilities
  - INCLUDE conversation state serialization/deserialization
  - CREATE conversation cleanup and archival methods

Task 17:
CREATE src/chatbot/agent.py:
  - IMPLEMENT main chatbot agent using LangChain's ConversationChain
  - INTEGRATE Azure OpenAI client and conversation memory
  - ADD message processing and response generation
  - INCLUDE conversation flow control and user intent handling
  - SUPPORT graceful degradation when services are unavailable

Task 18:
CREATE src/utils/console.py:
  - IMPLEMENT Rich console utilities for enhanced CLI output
  - ADD progress indicators, status messages, and error formatting
  - INCLUDE conversation display formatting with syntax highlighting
  - SUPPORT interactive prompts and user input handling
  - CREATE ASCII art and branding elements

Task 19:
CREATE src/main.py:
  - IMPLEMENT Click-based CLI interface with command groups
  - ADD main chat command with configuration options
  - INCLUDE conversation management commands (list, clear, export)
  - SUPPORT system prompt configuration via CLI arguments
  - INTEGRATE all services and components

Task 20:
CREATE requirements.txt:
  - INCLUDE all necessary dependencies with version constraints
  - FOLLOW examples from examples/openai/Basic_Samples/Chat/requirements.txt
  - ADD Azure Key Vault dependencies (azure-keyvault-secrets, azure-identity)
  - INCLUDE development dependencies (pytest, black, ruff, mypy)
  - ENSURE compatibility with Azure OpenAI and LangChain latest versions
  - ADD Azure SDK core dependencies for authentication

Task 21:
CREATE comprehensive unit tests:
  - tests/conftest.py: Pytest fixtures for mocking Azure OpenAI and Key Vault responses
  - tests/test_settings.py: Configuration validation, environment handling, and Key Vault integration
  - tests/test_azure_client.py: API integration and error scenarios
  - tests/test_conversation.py: Memory management and state persistence
  - tests/test_agent.py: End-to-end conversation flows
  - tests/test_keyvault_auth.py: Key Vault authentication patterns and credential chain testing

Task 22:
CREATE .env.example:
  - DOCUMENT all required environment variables
  - INCLUDE example values and configuration options
  - ADD comments explaining each setting's purpose
  - FOLLOW patterns from examples/sample-app-aoai-chatGPT/.env.sample
  - INTEGRATE with Terraform output values

Task 23:
CREATE scripts/setup-env.sh:
  - IMPLEMENT environment setup automation
  - EXTRACT Terraform outputs to environment variables
  - CREATE .env file from infrastructure values
  - ADD validation for required configurations

Task 24:
CREATE documentation:
  - UPDATE README.md with infrastructure and application setup
  - ADD Terraform deployment guide
  - INCLUDE API documentation for all modules
  - ADD troubleshooting guide for common issues
  - CREATE infrastructure architecture documentation
```

### Per Task Pseudocode (Selected Critical Tasks)

```hcl
# Task 1: Terraform Provider and Remote State Configuration
# infrastructure/providers.tf

terraform {
  required_version = ">= 1.0"
  
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
  }
  
  # CRITICAL: Remote state configuration
  backend "azurerm" {
    # These values should be provided via backend configuration file
    # or environment variables during terraform init
    resource_group_name  = "tfstate-rg"
    storage_account_name = "tfstateXXXXX"  # Must be globally unique
    container_name       = "tfstate"
    key                  = "chatbot/terraform.tfstate"
    
    # CRITICAL: Enable state locking and encryption
    use_azuread_auth = true  # Use Azure AD authentication
    use_msi         = false  # Set to true if using Managed Identity
  }
}

provider "azurerm" {
  features {
    # CRITICAL: Required for Key Vault operations
    key_vault {
      purge_soft_delete_on_destroy    = true
      recover_soft_deleted_key_vaults = true
    }
    
    # CRITICAL: Required for Cognitive Services
    cognitive_account {
      purge_soft_delete_on_destroy = true
    }
  }
}

# Get current Azure configuration
data "azurerm_client_config" "current" {}
```

```bash
# Task 9: Deployment Script with Remote State Setup
# scripts/deploy.sh

#!/bin/bash
set -e

ENVIRONMENT=${1:-dev}
RESOURCE_GROUP_NAME="tfstate-rg-${ENVIRONMENT}"
STORAGE_ACCOUNT_NAME="tfstate$(openssl rand -hex 4)"
CONTAINER_NAME="tfstate"

echo "🏗️  Setting up Terraform remote state for environment: ${ENVIRONMENT}"

# Create resource group for Terraform state if it doesn't exist
echo "Creating resource group for Terraform state..."
az group create \
  --name "${RESOURCE_GROUP_NAME}" \
  --location "East US" \
  --tags Environment="${ENVIRONMENT}" Purpose="TerraformState"

# Create storage account for Terraform state
echo "Creating storage account for Terraform state..."
az storage account create \
  --name "${STORAGE_ACCOUNT_NAME}" \
  --resource-group "${RESOURCE_GROUP_NAME}" \
  --location "East US" \
  --sku Standard_LRS \
  --encryption-services blob \
  --https-only true \
  --min-tls-version TLS1_2

# Get storage account key
ACCOUNT_KEY=$(az storage account keys list \
  --resource-group "${RESOURCE_GROUP_NAME}" \
  --account-name "${STORAGE_ACCOUNT_NAME}" \
  --query '[0].value' -o tsv)

# Create container for Terraform state
echo "Creating container for Terraform state..."
az storage container create \
  --name "${CONTAINER_NAME}" \
  --account-name "${STORAGE_ACCOUNT_NAME}" \
  --account-key "${ACCOUNT_KEY}"

# Initialize Terraform with remote state
echo "Initializing Terraform with remote state..."
cd infrastructure

terraform init \
  -backend-config="resource_group_name=${RESOURCE_GROUP_NAME}" \
  -backend-config="storage_account_name=${STORAGE_ACCOUNT_NAME}" \
  -backend-config="container_name=${CONTAINER_NAME}" \
  -backend-config="key=${ENVIRONMENT}/terraform.tfstate" \
  -backend-config="access_key=${ACCOUNT_KEY}"

# CRITICAL: Validate configuration before applying
terraform validate
terraform fmt -check

# Plan deployment
terraform plan -var-file="terraform.tfvars" -out="tfplan"

echo "✅ Terraform state configured. Review the plan above."
echo "To apply: terraform apply tfplan"
echo "State location: ${STORAGE_ACCOUNT_NAME}/${CONTAINER_NAME}/${ENVIRONMENT}/terraform.tfstate"
```

```hcl
# Task 3: Azure OpenAI Infrastructure Module
# infrastructure/modules/azure-openai/main.tf

# Resource Group
resource "azurerm_resource_group" "main" {
  name     = var.resource_group_name
  location = var.location
  
  tags = var.common_tags
}

# Azure OpenAI Cognitive Services Account
resource "azurerm_cognitive_account" "openai" {
  name                = var.openai_service_name
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  kind                = "OpenAI"  # CRITICAL: Must be "OpenAI" not "CognitiveServices"
  sku_name            = var.openai_sku
  
  # CRITICAL: Custom subdomain required for Azure OpenAI
  custom_subdomain_name = var.openai_subdomain
  
  tags = var.common_tags
}

# GPT-4 Model Deployment  
resource "azurerm_cognitive_deployment" "gpt4" {
  name                 = var.gpt4_deployment_name
  cognitive_account_id = azurerm_cognitive_account.openai.id
  
  model {
    format  = "OpenAI"
    name    = "gpt-4"  # CRITICAL: Exact model name required
    version = "0613"   # CRITICAL: Must match available versions
  }
  
  scale {
    type     = "Standard"
    capacity = var.gpt4_capacity  # TPM (Tokens Per Minute) limit
  }
  
  depends_on = [azurerm_cognitive_account.openai]
}

# Key Vault for Secrets
resource "azurerm_key_vault" "main" {
  name                = var.key_vault_name
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tenant_id           = data.azurerm_client_config.current.tenant_id
  
  sku_name = "standard"
  
  # CRITICAL: Choose access model consistently
  enable_rbac_authorization = true
  
  tags = var.common_tags
}

# Store OpenAI API Key in Key Vault
resource "azurerm_key_vault_secret" "openai_key" {
  name         = "openai-api-key"
  value        = azurerm_cognitive_account.openai.primary_access_key
  key_vault_id = azurerm_key_vault.main.id
  
  depends_on = [azurerm_key_vault.main]
}

# Store additional configuration secrets
resource "azurerm_key_vault_secret" "openai_endpoint" {
  name         = "openai-endpoint"
  value        = azurerm_cognitive_account.openai.endpoint
  key_vault_id = azurerm_key_vault.main.id
}

resource "azurerm_key_vault_secret" "gpt4_deployment" {
  name         = "gpt4-deployment-name"
  value        = azurerm_cognitive_deployment.gpt4.name
  key_vault_id = azurerm_key_vault.main.id
}
```

```hcl
# Task 5.5: RBAC Configuration for Key Vault Access
# infrastructure/modules/azure-openai/rbac.tf

# Get current Azure AD context
data "azurerm_client_config" "current" {}

# Create User-Assigned Managed Identity for the application
resource "azurerm_user_assigned_identity" "app_identity" {
  name                = "${var.app_name}-identity"
  location            = var.location
  resource_group_name = azurerm_resource_group.main.name
  
  tags = var.common_tags
}

# CRITICAL: RBAC role assignment for Key Vault access
# Grant "Key Vault Secrets User" role to the application identity
resource "azurerm_role_assignment" "app_keyvault_secrets_user" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.app_identity.principal_id
}

# Grant "Key Vault Secrets Officer" role to developers (optional)
resource "azurerm_role_assignment" "dev_keyvault_secrets_officer" {
  count                = length(var.developer_object_ids)
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Secrets Officer"
  principal_id         = var.developer_object_ids[count.index]
}

# Grant current user (deployer) access to Key Vault
resource "azurerm_role_assignment" "deployer_keyvault_access" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Secrets Officer"
  principal_id         = data.azurerm_client_config.current.object_id
}

# Optional: Create App Service with Managed Identity enabled
resource "azurerm_linux_web_app" "chatbot" {
  count               = var.create_app_service ? 1 : 0
  name                = "${var.app_name}-webapp"
  location            = var.location
  resource_group_name = azurerm_resource_group.main.name
  service_plan_id     = azurerm_service_plan.main[0].id
  
  # Enable system-assigned managed identity
  identity {
    type = "SystemAssigned"
  }
  
  # App settings with Key Vault references
  app_settings = {
    # CRITICAL: Use Key Vault references for secure config
    "AZURE_OPENAI_ENDPOINT"    = "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault_secret.openai_endpoint.id})"
    "AZURE_OPENAI_API_KEY"     = "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault_secret.openai_key.id})"
    "AZURE_OPENAI_DEPLOYMENT" = "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault_secret.gpt4_deployment.id})"
    
    # Enable Managed Identity for Key Vault access
    "AZURE_CLIENT_ID" = azurerm_user_assigned_identity.app_identity.client_id
  }
  
  tags = var.common_tags
}

# Grant Key Vault access to App Service system-assigned identity (if created)
resource "azurerm_role_assignment" "webapp_keyvault_access" {
  count                = var.create_app_service ? 1 : 0
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_linux_web_app.chatbot[0].identity[0].principal_id
}
```

```python
# Task 12: Enhanced Settings with Key Vault Integration
# src/config/settings.py

from pydantic import BaseSettings, validator
from azure.identity import DefaultAzureCredential, ChainedTokenCredential, AzureCliCredential, ManagedIdentityCredential
from azure.keyvault.secrets import SecretClient
import os
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    # Key Vault configuration
    key_vault_url: Optional[str] = None
    azure_client_id: Optional[str] = None  # For user-assigned managed identity
    
    # Azure OpenAI configuration (can be overridden by Key Vault)
    azure_openai_endpoint: Optional[str] = None
    azure_openai_api_key: Optional[str] = None
    azure_openai_deployment: Optional[str] = None
    
    # Other settings...
    temperature: float = 0.7
    max_tokens: int = 1000
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # If Key Vault is configured, fetch secrets
        if self.key_vault_url:
            self._load_from_keyvault()
    
    def _load_from_keyvault(self) -> None:
        """Load configuration from Azure Key Vault using multiple authentication methods."""
        try:
            # CRITICAL: Create authentication credential chain
            credential_chain = []
            
            # 1. Try Managed Identity (production)
            if self.azure_client_id:
                # User-assigned managed identity
                credential_chain.append(ManagedIdentityCredential(client_id=self.azure_client_id))
            else:
                # System-assigned managed identity
                credential_chain.append(ManagedIdentityCredential())
            
            # 2. Try Azure CLI (local development)
            credential_chain.append(AzureCliCredential())
            
            # 3. Fallback to DefaultAzureCredential
            credential = ChainedTokenCredential(*credential_chain)
            
            # Create Key Vault client
            client = SecretClient(vault_url=self.key_vault_url, credential=credential)
            
            # PATTERN: Load secrets with fallback to environment variables
            self.azure_openai_endpoint = self._get_secret_or_env(
                client, "openai-endpoint", self.azure_openai_endpoint
            )
            self.azure_openai_api_key = self._get_secret_or_env(
                client, "openai-api-key", self.azure_openai_api_key
            )
            self.azure_openai_deployment = self._get_secret_or_env(
                client, "gpt4-deployment-name", self.azure_openai_deployment
            )
            
            logger.info("Successfully loaded configuration from Key Vault")
            
        except Exception as e:
            logger.warning(f"Failed to load from Key Vault, using environment variables: {e}")
            # Continue with environment variables/defaults
    
    def _get_secret_or_env(self, client: SecretClient, secret_name: str, fallback_value: Optional[str]) -> Optional[str]:
        """Get secret from Key Vault with fallback to current value."""
        try:
            secret = client.get_secret(secret_name)
            return secret.value
        except Exception as e:
            logger.debug(f"Could not retrieve secret '{secret_name}': {e}")
            return fallback_value
    
    @validator('azure_openai_endpoint')
    def validate_endpoint(cls, v):
        if v and not v.startswith('https://'):
            raise ValueError('Azure OpenAI endpoint must start with https://')
        return v
```

```python
# Task 14: Azure OpenAI Client Implementation
class AzureOpenAIClient:
    def __init__(self, config: Settings):
        # PATTERN: Use LangChain's AzureChatOpenAI for proper Azure integration
        self.client = AzureChatOpenAI(
            azure_endpoint=config.azure_openai_endpoint,
            api_key=config.azure_openai_api_key,
            api_version="2024-05-01-preview",  # Latest stable version
            deployment_name=config.azure_openai_deployment,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            request_timeout=config.request_timeout,
        )
        
        # CRITICAL: Implement retry logic with exponential backoff
        self.retry_config = Retry(
            total=3,
            backoff_factor=2,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        
    async def generate_response(self, messages: List[Dict], **kwargs) -> str:
        # PATTERN: Use structured logging with conversation context
        logger.bind(conversation_id=kwargs.get('conversation_id')).info(
            "Generating response", 
            message_count=len(messages),
            model=self.deployment_name
        )
        
        try:
            # CRITICAL: Handle rate limiting gracefully
            response = await self._retry_request(messages)
            
            # PATTERN: Log performance metrics
            logger.bind(conversation_id=kwargs.get('conversation_id')).info(
                "Response generated successfully",
                token_usage=response.usage,
                response_time=response.response_metadata.get('response_time')
            )
            
            return response.content
            
        except Exception as e:
            # PATTERN: Structured error logging with context
            logger.bind(conversation_id=kwargs.get('conversation_id')).error(
                "Failed to generate response",
                error_type=type(e).__name__,
                error_message=str(e)
            )
            raise AzureOpenAIError(f"Service unavailable: {str(e)}")

# Task 6: Conversation Memory Management
class ConversationManager:
    def __init__(self, max_history: int = 10):
        # PATTERN: Use LangChain's ConversationBufferWindowMemory
        self.memory = ConversationBufferWindowMemory(
            k=max_history,
            return_messages=True,
            memory_key="chat_history"
        )
        
    def add_message(self, role: str, content: str, conversation_id: str):
        # PATTERN: Validate and sanitize user input
        if not content.strip():
            raise ConversationError("Empty message content")
            
        # CRITICAL: Log conversation events for debugging
        logger.bind(conversation_id=conversation_id).debug(
            "Adding message to conversation",
            role=role,
            content_length=len(content)
        )
        
        # PATTERN: Use structured message format
        if role == "user":
            self.memory.chat_memory.add_user_message(content)
        else:
            self.memory.chat_memory.add_ai_message(content)

# Task 9: CLI Interface Implementation
@click.group()
@click.option('--config-file', envvar='CHATBOT_CONFIG_FILE', default='.env')
@click.option('--log-level', envvar='CHATBOT_LOG_LEVEL', default='INFO')
@click.pass_context
def cli(ctx, config_file, log_level):
    """Azure OpenAI CLI Chatbot"""
    # PATTERN: Initialize configuration and logging early
    ctx.ensure_object(dict)
    ctx.obj['config'] = Settings(_env_file=config_file)
    setup_logging(log_level)

@cli.command()
@click.option('--system-prompt', help='Custom system prompt')
@click.option('--max-turns', default=50, help='Maximum conversation turns')
@click.pass_context
def chat(ctx, system_prompt, max_turns):
    """Start interactive chat session"""
    # PATTERN: Initialize all services with dependency injection
    config = ctx.obj['config']
    azure_client = AzureOpenAIClient(config)
    conversation = ConversationManager()
    agent = ChatbotAgent(azure_client, conversation, config)
    
    # PATTERN: Rich console for enhanced UX
    console = Console()
    console.print(f"[bold green]🤖 Azure OpenAI Chatbot Ready![/bold green]")
    
    # CRITICAL: Graceful error handling and recovery
    try:
        agent.run_interactive_session(max_turns=max_turns)
    except KeyboardInterrupt:
        console.print("\n[yellow]Chat session ended by user[/yellow]")
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        logger.error("Chat session failed", error=str(e))
```

### Integration Points
```yaml
INFRASTRUCTURE:
  - terraform: Provision Azure resources before application deployment
  - pattern: "cd infrastructure && terraform apply"
  - output: Extract resource values to environment configuration
  
ENVIRONMENT:
  - create: .env file from Terraform outputs
  - pattern: "scripts/setup-env.sh generates from terraform output"
  - values: "AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY from infrastructure"
  
LOGGING:
  - add to: logs/ directory for local file logging
  - pattern: "logs/chatbot_{date}.json for daily rotation"
  - azure: Log Analytics Workspace integration via Application Insights
  
VIRTUAL_ENVIRONMENT:
  - use: venv_linux as specified in CLAUDE.md
  - pattern: "source venv_linux/bin/activate && python src/main.py chat"
  
DEPENDENCIES:
  - add to: requirements.txt
  - pattern: "langchain-openai>=0.1.0, structlog>=23.1.0, click>=8.1.0, rich>=13.0.0"
  
KEY_VAULT:
  - integration: Azure Key Vault for secure credential retrieval
  - pattern: "Azure SDK for Python with DefaultAzureCredential"
```

## Validation Loop

### Level 0: Infrastructure Validation
```bash
# STEP 1: Remote State Setup and Validation
# Run deployment script to set up remote state backend
./scripts/deploy.sh dev

# Verify remote state is configured
terraform state list
terraform show

# Check that state is stored remotely (not locally)
ls -la terraform.tfstate*  # Should show no local state files

# Verify state locking is working
# (In another terminal) terraform plan  # Should show lock acquisition

# STEP 2: Infrastructure Validation
cd infrastructure

# Validate Terraform configuration
terraform validate
terraform fmt -check

# Plan infrastructure changes with remote state
terraform plan -var-file="terraform.tfvars" -out="tfplan"

# Apply infrastructure (after review)
terraform apply "tfplan"

# STEP 3: Resource Verification
# Verify Azure OpenAI resources are created
az cognitiveservices account list --query "[?kind=='OpenAI']"
az cognitiveservices deployment list --name <openai-service-name> --resource-group <rg-name>

# Verify Key Vault and secrets
az keyvault list --query "[?name=='<keyvault-name>']"
az keyvault secret list --vault-name <keyvault-name>

# STEP 4: Authentication Testing
# Test different authentication methods for Key Vault access

# Test Azure CLI authentication (local development)
az login
az keyvault secret show --name "openai-api-key" --vault-name <keyvault-name>

# Test Managed Identity authentication (if on Azure VM/App Service)
curl "http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01&resource=https://vault.azure.net" -H Metadata:true

# Verify RBAC assignments
az role assignment list --scope "/subscriptions/<sub-id>/resourceGroups/<rg>/providers/Microsoft.KeyVault/vaults/<kv-name>"

# Expected: 
# - Remote state stored in Azure Storage with proper locking
# - Azure OpenAI resource with GPT-4 deployment ready
# - Key Vault with OpenAI API key stored securely
# - RBAC roles properly assigned to identities
# - Authentication chain works for both local development and production scenarios
```

### Level 1: Syntax & Style  
```bash
# Run these FIRST - fix any errors before proceeding
source venv_linux/bin/activate  # CRITICAL: Use project virtual environment
ruff check src/ --fix           # Auto-fix code style issues
mypy src/                       # Type checking with strict mode
black src/                      # Code formatting

# Expected: No errors. If errors exist, READ and fix before continuing.
```

### Level 2: Unit Tests
```python
# CREATE comprehensive test suite covering all major components
def test_azure_client_connection():
    """Test successful Azure OpenAI connection"""
    client = AzureOpenAIClient(test_config)
    response = client.generate_response([{"role": "user", "content": "Hello"}])
    assert response is not None
    assert len(response) > 0

def test_conversation_memory():
    """Test conversation history persistence"""
    conv = ConversationManager()
    conv.add_message("user", "Hello", "test-123")
    conv.add_message("assistant", "Hi there!", "test-123")
    history = conv.get_history()
    assert len(history) == 2

def test_configuration_validation():
    """Test environment variable validation"""
    with pytest.raises(ValidationError):
        Settings(azure_openai_endpoint="invalid-url")

def test_keyvault_authentication_chain():
    """Test Key Vault authentication with multiple credential types"""
    from unittest.mock import Mock, patch
    from azure.identity import ChainedTokenCredential
    
    # Mock Key Vault client
    mock_client = Mock()
    mock_secret = Mock()
    mock_secret.value = "test-api-key"
    mock_client.get_secret.return_value = mock_secret
    
    with patch('azure.keyvault.secrets.SecretClient', return_value=mock_client):
        settings = Settings(
            key_vault_url="https://test-kv.vault.azure.net/",
            azure_client_id="test-client-id"
        )
        
        # Verify Key Vault integration worked
        assert settings.azure_openai_api_key == "test-api-key"
        mock_client.get_secret.assert_called()

def test_keyvault_fallback_to_env():
    """Test fallback to environment variables when Key Vault fails"""
    import os
    
    # Set environment variable
    os.environ['AZURE_OPENAI_API_KEY'] = 'env-api-key'
    
    # Mock Key Vault failure
    with patch('azure.keyvault.secrets.SecretClient') as mock_client:
        mock_client.side_effect = Exception("Key Vault unavailable")
        
        settings = Settings(key_vault_url="https://test-kv.vault.azure.net/")
        
        # Should fallback to environment variable
        assert settings.azure_openai_api_key == 'env-api-key'

def test_managed_identity_authentication():
    """Test Managed Identity credential creation"""
    from azure.identity import ManagedIdentityCredential
    
    with patch('azure.identity.ManagedIdentityCredential') as mock_mi:
        settings = Settings(
            key_vault_url="https://test-kv.vault.azure.net/",
            azure_client_id="test-client-id"
        )
        
        # Verify user-assigned managed identity is used
        mock_mi.assert_called_with(client_id="test-client-id")

def test_error_handling():
    """Test graceful error handling"""
    with mock.patch('azure_client.generate_response', side_effect=Exception("API Error")):
        result = agent.process_message("Hello")
        assert "Error" in result or "unavailable" in result
```

```bash
# Run and iterate until all tests pass:
source venv_linux/bin/activate
uv run pytest tests/ -v --tb=short
# If failing: Read error output, understand root cause, fix code, re-run
```

### Level 3: Integration Test
```bash
# Test the complete CLI workflow
source venv_linux/bin/activate

# Set up test environment
export AZURE_OPENAI_ENDPOINT="your-test-endpoint"
export AZURE_OPENAI_API_KEY="your-test-key"
export AZURE_OPENAI_DEPLOYMENT="your-deployment"

# Start interactive chat session
python src/main.py chat --system-prompt "You are a helpful assistant"

# Expected: 
# - Welcome message with Rich formatting
# - Successful connection to Azure OpenAI
# - Interactive prompt ready for user input
# - Graceful error handling if credentials are invalid

# Test CLI configuration
python src/main.py --help

# Expected: Complete help output with all commands and options
```

## Final Validation Checklist
- [ ] Terraform remote state backend configured: `./scripts/deploy.sh dev`
- [ ] Remote state locking works: `terraform state list` shows remote state
- [ ] No local state files present: `ls terraform.tfstate*` returns empty
- [ ] Terraform infrastructure deploys successfully: `terraform apply "tfplan"`
- [ ] Azure OpenAI service is accessible: `az cognitiveservices account show`
- [ ] GPT-4 deployment is ready: `az cognitiveservices deployment list`
- [ ] Key Vault stores secrets properly: `az keyvault secret list`
- [ ] RBAC roles assigned correctly: `az role assignment list --scope <keyvault-scope>`
- [ ] Key Vault authentication works locally: `az keyvault secret show --name "openai-api-key"`
- [ ] Managed Identity authentication configured (if using App Service/VM)
- [ ] Application loads secrets from Key Vault successfully
- [ ] Environment setup script works: `scripts/setup-env.sh`
- [ ] All Python tests pass: `uv run pytest tests/ -v`
- [ ] No linting errors: `ruff check src/`
- [ ] No type errors: `mypy src/`
- [ ] Manual CLI test successful: `python src/main.py chat`
- [ ] Azure OpenAI connection established successfully
- [ ] Conversation memory persists across multiple exchanges
- [ ] Structured JSON logging writes to logs/ directory
- [ ] Error cases handled gracefully with user-friendly messages
- [ ] Configuration loads properly from .env file (generated from Terraform)
- [ ] Rich console output displays correctly
- [ ] Documentation is complete and accurate
- [ ] Virtual environment setup works as documented
- [ ] Infrastructure can be destroyed cleanly: `terraform destroy`

---

## Anti-Patterns to Avoid
- ❌ Don't use openai library directly - use langchain-openai for better integration
- ❌ Don't hardcode API keys or endpoints in source code
- ❌ Don't ignore Azure OpenAI rate limits - implement proper retry logic
- ❌ Don't use print() statements - use Rich console for output and structlog for logging
- ❌ Don't create files longer than 500 lines (per CLAUDE.md requirements)
- ❌ Don't skip error handling for external API calls
- ❌ Don't log sensitive user input or API responses containing personal data
- ❌ Don't use sync code for potentially slow operations - implement async patterns where appropriate

## PRP Confidence Score: 10/10

**Reasoning**: This PRP provides comprehensive context including:
✅ Complete Terraform infrastructure provisioning with Azure OpenAI
✅ Detailed remote state configuration with Azure Storage backend
✅ Automated deployment scripts with state setup and validation
✅ Detailed Azure provider configuration and resource dependencies
✅ Complete Azure OpenAI and LangChain integration documentation
✅ 26 sequential tasks with specific implementation patterns
✅ Real examples from the codebase to follow
✅ Multi-level validation (remote state → infrastructure → application → integration)
✅ Known gotchas and library-specific quirks documented
✅ Clear success criteria and testing strategy
✅ Infrastructure as Code with reproducible deployments
✅ Secure credential management via Azure Key Vault
✅ Production-ready remote state management with locking and encryption
✅ **Comprehensive Key Vault authentication patterns**:
  - Multiple authentication methods (Managed Identity, Azure CLI, Service Principal)
  - ChainedTokenCredential implementation with proper fallbacks
  - RBAC configuration with proper role assignments
  - Both user-assigned and system-assigned Managed Identity support
  - Local development and production deployment patterns
  - Comprehensive unit tests for authentication scenarios

**No gaps remaining**: All major implementation aspects are covered with production-ready patterns, comprehensive authentication methods, and detailed validation procedures.

The PRP should enable one-pass implementation with maximum confidence due to the complete infrastructure-to-application context, enterprise-grade security patterns, and comprehensive multi-tier validation loops provided.