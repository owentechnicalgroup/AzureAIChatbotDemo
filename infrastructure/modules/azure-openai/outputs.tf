# Azure OpenAI Module Outputs
# Task 5: Expose key infrastructure values for application use

# Resource Group Information
output "resource_group_name" {
  description = "The name of the resource group"
  value       = azurerm_resource_group.main.name
}

output "resource_group_id" {
  description = "The ID of the resource group"
  value       = azurerm_resource_group.main.id
}

output "location" {
  description = "The Azure region where resources are deployed"
  value       = azurerm_resource_group.main.location
}

# Azure OpenAI Service Outputs
output "openai_service_name" {
  description = "The name of the Azure OpenAI service"
  value       = azurerm_cognitive_account.openai.name
}

output "openai_service_id" {
  description = "The ID of the Azure OpenAI service"
  value       = azurerm_cognitive_account.openai.id
}

output "openai_endpoint" {
  description = "The endpoint URL for the Azure OpenAI service"
  value       = azurerm_cognitive_account.openai.endpoint
}

output "openai_primary_key" {
  description = "The primary API key for the Azure OpenAI service"
  value       = azurerm_cognitive_account.openai.primary_access_key
  sensitive   = true
}

output "openai_secondary_key" {
  description = "The secondary API key for the Azure OpenAI service"
  value       = azurerm_cognitive_account.openai.secondary_access_key
  sensitive   = true
}

# GPT-4 Deployment Information
output "gpt4_deployment_name" {
  description = "The name of the GPT-4 deployment"
  value       = azurerm_cognitive_deployment.gpt4.name
}

output "gpt4_deployment_id" {
  description = "The ID of the GPT-4 deployment"
  value       = azurerm_cognitive_deployment.gpt4.id
}

output "gpt4_model_name" {
  description = "The GPT-4 model name"
  value       = azurerm_cognitive_deployment.gpt4.model[0].name
}

output "gpt4_model_version" {
  description = "The GPT-4 model version"
  value       = azurerm_cognitive_deployment.gpt4.model[0].version
}

# Text Embedding Deployment Information
output "embedding_deployment_name" {
  description = "The name of the text embedding deployment"
  value       = azurerm_cognitive_deployment.embedding.name
}

output "embedding_deployment_id" {
  description = "The ID of the text embedding deployment"
  value       = azurerm_cognitive_deployment.embedding.id
}

output "embedding_model_name" {
  description = "The text embedding model name"
  value       = azurerm_cognitive_deployment.embedding.model[0].name
}

output "embedding_model_version" {
  description = "The text embedding model version"
  value       = azurerm_cognitive_deployment.embedding.model[0].version
}

# Key Vault Information
output "key_vault_name" {
  description = "The name of the Key Vault"
  value       = azurerm_key_vault.main.name
}

output "key_vault_id" {
  description = "The ID of the Key Vault"
  value       = azurerm_key_vault.main.id
}

output "key_vault_url" {
  description = "The URL of the Key Vault"
  value       = azurerm_key_vault.main.vault_uri
}

# Key Vault Secret References (for application configuration)
output "openai_key_secret_id" {
  description = "The Key Vault secret ID for the OpenAI API key"
  value       = azurerm_key_vault_secret.openai_key.id
}

output "openai_endpoint_secret_id" {
  description = "The Key Vault secret ID for the OpenAI endpoint"
  value       = azurerm_key_vault_secret.openai_endpoint.id
}

output "gpt4_deployment_secret_id" {
  description = "The Key Vault secret ID for the GPT-4 deployment name"
  value       = azurerm_key_vault_secret.gpt4_deployment.id
}

output "embedding_deployment_secret_id" {
  description = "The Key Vault secret ID for the embedding deployment name"
  value       = azurerm_key_vault_secret.embedding_deployment.id
}

output "application_insights_connection_string_secret_id" {
  description = "The Key Vault secret ID for the Application Insights connection string"
  value       = azurerm_key_vault_secret.application_insights_connection_string.id
}

# Log Analytics and Application Insights
output "log_analytics_workspace_id" {
  description = "The ID of the Log Analytics workspace"
  value       = azurerm_log_analytics_workspace.main.id
}

output "log_analytics_workspace_name" {
  description = "The name of the Log Analytics workspace"
  value       = azurerm_log_analytics_workspace.main.name
}

output "application_insights_name" {
  description = "The name of the Application Insights instance"
  value       = azurerm_application_insights.main.name
}

output "application_insights_instrumentation_key" {
  description = "The instrumentation key for Application Insights"
  value       = azurerm_application_insights.main.instrumentation_key
  sensitive   = true
}

output "application_insights_connection_string" {
  description = "The connection string for Application Insights"
  value       = azurerm_application_insights.main.connection_string
  sensitive   = true
}

# Chat Observability Outputs (if enabled)
output "chat_observability_enabled" {
  description = "Whether chat observability is enabled"
  value       = var.enable_chat_observability
}

output "chat_log_analytics_workspace_id" {
  description = "The ID of the Chat Observability Log Analytics workspace (if enabled)"
  value       = var.enable_chat_observability ? azurerm_log_analytics_workspace.chat[0].id : null
}

output "chat_log_analytics_workspace_name" {
  description = "The name of the Chat Observability Log Analytics workspace (if enabled)"
  value       = var.enable_chat_observability ? azurerm_log_analytics_workspace.chat[0].name : null
}

output "chat_application_insights_name" {
  description = "The name of the Chat Observability Application Insights instance (if enabled)"
  value       = var.enable_chat_observability ? azurerm_application_insights.chat[0].name : null
}

output "chat_application_insights_instrumentation_key" {
  description = "The instrumentation key for Chat Observability Application Insights (if enabled)"
  value       = var.enable_chat_observability ? azurerm_application_insights.chat[0].instrumentation_key : null
  sensitive   = true
}

output "chat_observability_connection_string" {
  description = "The connection string for Chat Observability Application Insights (if enabled)"
  value       = var.enable_chat_observability ? azurerm_application_insights.chat[0].connection_string : null
  sensitive   = true
}

output "chat_observability_connection_string_secret_id" {
  description = "The Key Vault secret ID for the Chat Observability connection string (if enabled)"
  value       = var.enable_chat_observability ? azurerm_key_vault_secret.chat_observability_connection_string[0].id : null
}

# Storage Account Information
output "storage_account_name" {
  description = "The name of the storage account"
  value       = azurerm_storage_account.main.name
}

output "storage_account_id" {
  description = "The ID of the storage account"
  value       = azurerm_storage_account.main.id
}

output "storage_account_primary_key" {
  description = "The primary access key for the storage account"
  value       = azurerm_storage_account.main.primary_access_key
  sensitive   = true
}

output "storage_account_connection_string" {
  description = "The primary connection string for the storage account"
  value       = azurerm_storage_account.main.primary_connection_string
  sensitive   = true
}

output "conversations_container_name" {
  description = "The name of the conversations storage container"
  value       = azurerm_storage_container.conversations.name
}

# App Service Information (conditionally created)
output "app_service_name" {
  description = "The name of the App Service (if created)"
  value       = var.create_app_service ? azurerm_linux_web_app.chatbot[0].name : null
}

output "app_service_default_hostname" {
  description = "The default hostname of the App Service (if created)"
  value       = var.create_app_service ? azurerm_linux_web_app.chatbot[0].default_hostname : null
}

# Managed Identity Information  
output "managed_identity_client_id" {
  description = "The client ID of the user-assigned managed identity"
  value       = azurerm_user_assigned_identity.app_identity.client_id
}

output "managed_identity_principal_id" {
  description = "The principal ID of the user-assigned managed identity"
  value       = azurerm_user_assigned_identity.app_identity.principal_id
}

# Configuration for Application Environment Variables
output "app_config" {
  description = "Configuration values for application environment"
  value = {
    azure_openai_endpoint      = azurerm_cognitive_account.openai.endpoint
    azure_openai_deployment   = azurerm_cognitive_deployment.gpt4.name
    azure_embedding_deployment = azurerm_cognitive_deployment.embedding.name
    key_vault_url             = azurerm_key_vault.main.vault_uri
    app_insights_key          = azurerm_application_insights.main.instrumentation_key
    storage_account_name      = azurerm_storage_account.main.name
    resource_group_name       = azurerm_resource_group.main.name
    location                  = azurerm_resource_group.main.location
  }
  sensitive = true
}