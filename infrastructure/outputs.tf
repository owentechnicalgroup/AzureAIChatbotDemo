# Infrastructure Outputs
# Task 7: Expose key infrastructure values for application use

# Pass through all module outputs for application consumption
output "resource_group_name" {
  description = "The name of the resource group containing all resources"
  value       = module.azure_openai.resource_group_name
}

output "location" {
  description = "The Azure region where resources are deployed"
  value       = module.azure_openai.location
}

# Azure OpenAI Service Configuration
output "azure_openai_endpoint" {
  description = "The endpoint URL for the Azure OpenAI service"
  value       = module.azure_openai.openai_endpoint
}

output "azure_openai_deployment_name" {
  description = "The name of the GPT-4 deployment"
  value       = module.azure_openai.gpt4_deployment_name
}

output "azure_openai_model_name" {
  description = "The GPT-4 model name"
  value       = module.azure_openai.gpt4_model_name
}

output "azure_openai_model_version" {
  description = "The GPT-4 model version"
  value       = module.azure_openai.gpt4_model_version
}

# Key Vault Configuration for Application
output "key_vault_name" {
  description = "The name of the Key Vault containing secrets"
  value       = module.azure_openai.key_vault_name
}

output "key_vault_url" {
  description = "The URL of the Key Vault for application configuration"
  value       = module.azure_openai.key_vault_url
}

# Managed Identity Information
output "managed_identity_client_id" {
  description = "The client ID of the user-assigned managed identity for authentication"
  value       = module.azure_openai.managed_identity_client_id
}

output "managed_identity_principal_id" {
  description = "The principal ID of the user-assigned managed identity"
  value       = module.azure_openai.managed_identity_principal_id
}

# Application Insights Configuration
output "application_insights_connection_string" {
  description = "The connection string for Application Insights logging"
  value       = module.azure_openai.application_insights_connection_string
  sensitive   = true
}

output "application_insights_instrumentation_key" {
  description = "The instrumentation key for Application Insights"
  value       = module.azure_openai.application_insights_instrumentation_key
  sensitive   = true
}

# Chat Observability Configuration
output "chat_observability_enabled" {
  description = "Whether chat observability is enabled with separate Application Insights"
  value       = module.azure_openai.chat_observability_enabled
}

output "chat_observability_connection_string" {
  description = "The connection string for Chat Observability Application Insights (if enabled)"
  value       = module.azure_openai.chat_observability_connection_string
  sensitive   = true
}

# Storage Account Configuration
output "storage_account_name" {
  description = "The name of the storage account for conversation history"
  value       = module.azure_openai.storage_account_name
}

output "conversations_container_name" {
  description = "The name of the storage container for conversations"
  value       = module.azure_openai.conversations_container_name
}

# App Service Configuration (if created)
output "app_service_name" {
  description = "The name of the App Service (if created)"
  value       = module.azure_openai.app_service_name
}

output "app_service_url" {
  description = "The URL of the App Service (if created)"
  value       = module.azure_openai.app_service_name != null ? "https://${module.azure_openai.app_service_default_hostname}" : null
}

# Complete Application Configuration
output "application_config" {
  description = "Complete configuration object for the Python application"
  value = {
    # Azure OpenAI Configuration
    azure_openai_endpoint   = module.azure_openai.openai_endpoint
    azure_openai_deployment = module.azure_openai.gpt4_deployment_name
    azure_openai_model      = module.azure_openai.gpt4_model_name
    azure_openai_version    = module.azure_openai.gpt4_model_version

    # Authentication Configuration
    azure_client_id = module.azure_openai.managed_identity_client_id
    key_vault_url   = module.azure_openai.key_vault_url

    # Logging Configuration
    application_insights_connection_string = module.azure_openai.application_insights_connection_string
    chat_observability_connection_string   = module.azure_openai.chat_observability_connection_string
    log_analytics_workspace_id             = module.azure_openai.log_analytics_workspace_id

    # Storage Configuration
    storage_account_name    = module.azure_openai.storage_account_name
    conversations_container = module.azure_openai.conversations_container_name

    # Environment Configuration
    environment         = var.environment
    resource_group_name = module.azure_openai.resource_group_name
    location            = module.azure_openai.location
    app_name            = var.app_name
  }
  sensitive = true
}

# Environment Variables Template for Application
output "environment_variables" {
  description = "Environment variables template for the Python application"
  value = {
    # Core Azure OpenAI Configuration (will be overridden by Key Vault)
    AZURE_OPENAI_ENDPOINT    = module.azure_openai.openai_endpoint
    AZURE_OPENAI_DEPLOYMENT  = module.azure_openai.gpt4_deployment_name
    AZURE_OPENAI_API_VERSION = "2024-05-01-preview"

    # Authentication Configuration
    AZURE_CLIENT_ID = module.azure_openai.managed_identity_client_id
    KEY_VAULT_URL   = module.azure_openai.key_vault_url

    # Logging Configuration
    APPLICATIONINSIGHTS_CONNECTION_STRING = module.azure_openai.application_insights_connection_string
    CHAT_OBSERVABILITY_CONNECTION_STRING  = module.azure_openai.chat_observability_connection_string
    ENABLE_CHAT_OBSERVABILITY            = tostring(module.azure_openai.chat_observability_enabled)
    ENABLE_CROSS_CORRELATION             = "true"
    LOG_LEVEL                             = var.environment == "prod" ? "INFO" : "DEBUG"

    # Application Configuration
    ENVIRONMENT    = var.environment
    APP_NAME       = var.app_name
    AZURE_LOCATION = module.azure_openai.location

    # Storage Configuration
    AZURE_STORAGE_ACCOUNT_NAME = module.azure_openai.storage_account_name
    CONVERSATIONS_CONTAINER    = module.azure_openai.conversations_container_name

    # Feature Flags
    ENABLE_CONVERSATION_HISTORY = "true"
    ENABLE_STRUCTURED_LOGGING   = "true"
    ENABLE_METRICS_COLLECTION   = "true"

    # Performance Configuration
    OPENAI_MAX_TOKENS        = "1000"
    OPENAI_TEMPERATURE       = "0.7"
    CONVERSATION_MAX_HISTORY = "10"
  }
  sensitive = true
}

# Development and Deployment Information
output "deployment_info" {
  description = "Information about the deployment for documentation and scripts"
  value = {
    terraform_workspace = terraform.workspace
    deployment_time     = timestamp()
    random_suffix       = random_id.suffix.hex

    # Resource URLs for quick access
    azure_portal_url  = "https://portal.azure.com/#@${data.azurerm_client_config.current.tenant_id}/resource${module.azure_openai.resource_group_id}"
    key_vault_url     = "https://portal.azure.com/#@${data.azurerm_client_config.current.tenant_id}/resource${module.azure_openai.key_vault_id}"
    openai_studio_url = "https://oai.azure.com/resource/${module.azure_openai.openai_service_name}"

    # Validation Commands
    validation_commands = [
      "az cognitiveservices account show --name ${module.azure_openai.openai_service_name} --resource-group ${module.azure_openai.resource_group_name}",
      "az keyvault secret list --vault-name ${module.azure_openai.key_vault_name}",
      "az role assignment list --scope ${module.azure_openai.key_vault_id}"
    ]
  }
}