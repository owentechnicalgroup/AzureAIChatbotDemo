# Azure OpenAI Infrastructure Module
# Task 3: Main resources for Azure OpenAI chatbot infrastructure

# Get current Azure AD configuration
data "azurerm_client_config" "current" {}

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
    name    = var.gpt4_model_name  # Using variable for flexibility
    version = var.gpt4_model_version   # Using variable for flexibility
  }
  
  scale {
    type     = var.gpt4_scale_type
    capacity = var.gpt4_capacity  # TPM (Tokens Per Minute) limit
  }
  
  depends_on = [azurerm_cognitive_account.openai]
}

# Text Embedding Model Deployment
resource "azurerm_cognitive_deployment" "embedding" {
  name                 = var.embedding_deployment_name
  cognitive_account_id = azurerm_cognitive_account.openai.id
  
  model {
    format  = "OpenAI"
    name    = var.embedding_model_name
    version = var.embedding_model_version
  }
  
  scale {
    type     = var.embedding_scale_type
    capacity = var.embedding_capacity  # TPM (Tokens Per Minute) limit
  }
  
  depends_on = [azurerm_cognitive_account.openai]
}

# Log Analytics Workspace for monitoring
resource "azurerm_log_analytics_workspace" "main" {
  name                = var.log_analytics_name
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = var.log_analytics_sku
  retention_in_days   = var.log_retention_days
  
  tags = var.common_tags
}

# Application Insights for infrastructure/application monitoring
resource "azurerm_application_insights" "main" {
  name                = "${var.app_name}-app-insights"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  workspace_id        = azurerm_log_analytics_workspace.main.id
  application_type    = "other"
  
  tags = merge(var.common_tags, {
    Purpose = "ApplicationLogging"
    LogTypes = "SYSTEM,SECURITY,PERFORMANCE,AZURE_OPENAI"
  })
}

# Dedicated Log Analytics workspace for chat observability (optional)
resource "azurerm_log_analytics_workspace" "chat" {
  count               = var.enable_chat_observability ? 1 : 0
  name                = "${var.app_name}-chat-logs"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = var.log_analytics_sku
  retention_in_days   = var.chat_observability_retention_days
  
  tags = merge(var.common_tags, {
    Purpose = "ChatObservability"
    LogTypes = "CONVERSATION"
    DataRetention = "${var.chat_observability_retention_days}days"
  })
}

# Application Insights for chat observability (optional)
resource "azurerm_application_insights" "chat" {
  count               = var.enable_chat_observability ? 1 : 0
  name                = "${var.app_name}-chat-insights"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  workspace_id        = azurerm_log_analytics_workspace.chat[0].id
  application_type    = "other"
  
  tags = merge(var.common_tags, {
    Purpose = "ChatObservability"
    LogTypes = "CONVERSATION"
    DataAnalysis = "UserExperience,ConversationQuality,AIPerformance"
  })
}

# Key Vault for Secrets
resource "azurerm_key_vault" "main" {
  name                = var.key_vault_name
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tenant_id           = data.azurerm_client_config.current.tenant_id
  
  sku_name = var.key_vault_sku
  
  # CRITICAL: Choose access model consistently - use RBAC
  enable_rbac_authorization = true
  
  # Security settings
  purge_protection_enabled   = false  # Set to true for production
  soft_delete_retention_days = 7
  
  tags = var.common_tags
}

# Wait for RBAC propagation before creating secrets
resource "null_resource" "rbac_propagation_wait" {
  provisioner "local-exec" {
    command = "Start-Sleep -Seconds 30"
    interpreter = ["powershell", "-Command"]
  }
  
  depends_on = [azurerm_role_assignment.deployer_keyvault_access]
}

# Store OpenAI API Key in Key Vault
resource "azurerm_key_vault_secret" "openai_key" {
  name         = "openai-api-key"
  value        = azurerm_cognitive_account.openai.primary_access_key
  key_vault_id = azurerm_key_vault.main.id
  
  depends_on = [
    azurerm_key_vault.main,
    azurerm_role_assignment.deployer_keyvault_access,
    null_resource.rbac_propagation_wait
  ]
}

# Store additional configuration secrets
resource "azurerm_key_vault_secret" "openai_endpoint" {
  name         = "openai-endpoint"
  value        = azurerm_cognitive_account.openai.endpoint
  key_vault_id = azurerm_key_vault.main.id
  
  depends_on = [
    azurerm_key_vault.main,
    azurerm_role_assignment.deployer_keyvault_access,
    null_resource.rbac_propagation_wait
  ]
}

resource "azurerm_key_vault_secret" "gpt4_deployment" {
  name         = "gpt4-deployment-name"
  value        = azurerm_cognitive_deployment.gpt4.name
  key_vault_id = azurerm_key_vault.main.id
  
  depends_on = [
    azurerm_key_vault.main,
    azurerm_role_assignment.deployer_keyvault_access,
    null_resource.rbac_propagation_wait
  ]
}

resource "azurerm_key_vault_secret" "embedding_deployment" {
  name         = "embedding-deployment-name"
  value        = azurerm_cognitive_deployment.embedding.name
  key_vault_id = azurerm_key_vault.main.id
  
  depends_on = [
    azurerm_key_vault.main,
    azurerm_role_assignment.deployer_keyvault_access,
    null_resource.rbac_propagation_wait
  ]
}

# Store Application Insights connection string in Key Vault
resource "azurerm_key_vault_secret" "application_insights_connection_string" {
  name         = "applicationinsights-connection-string"
  value        = azurerm_application_insights.main.connection_string
  key_vault_id = azurerm_key_vault.main.id
  
  depends_on = [
    azurerm_key_vault.main,
    azurerm_role_assignment.deployer_keyvault_access,
    null_resource.rbac_propagation_wait
  ]
}

# Store Chat Observability connection string in Key Vault (if enabled)
resource "azurerm_key_vault_secret" "chat_observability_connection_string" {
  count        = var.enable_chat_observability ? 1 : 0
  name         = "chat-observability-connection-string"
  value        = azurerm_application_insights.chat[0].connection_string
  key_vault_id = azurerm_key_vault.main.id
  
  depends_on = [
    azurerm_key_vault.main,
    azurerm_role_assignment.deployer_keyvault_access,
    null_resource.rbac_propagation_wait,
    azurerm_application_insights.chat
  ]
}

# Optional: Storage Account for logs and conversation history
resource "azurerm_storage_account" "main" {
  name                     = var.storage_account_name
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  
  # Security settings
  https_traffic_only_enabled = true
  min_tls_version            = "TLS1_2"
  
  # Enable blob versioning for conversation history
  blob_properties {
    versioning_enabled = true
  }
  
  tags = var.common_tags
}

# Storage Container for conversation history
resource "azurerm_storage_container" "conversations" {
  name                  = "conversations"
  storage_account_name  = azurerm_storage_account.main.name
  container_access_type = "private"
}