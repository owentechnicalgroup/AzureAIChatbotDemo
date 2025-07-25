# Task 5.5: Configure RBAC roles and Managed Identity for secure access

# Create User-Assigned Managed Identity for the application
resource "azurerm_user_assigned_identity" "app_identity" {
  name                = "${var.app_name}-identity"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  
  tags = var.common_tags
}

# CRITICAL: RBAC role assignment for Key Vault access
# Grant "Key Vault Secrets User" role to the application identity
resource "azurerm_role_assignment" "app_keyvault_secrets_user" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.app_identity.principal_id
  
  depends_on = [
    azurerm_key_vault.main,
    azurerm_user_assigned_identity.app_identity
  ]
}

# Grant "Key Vault Secrets Officer" role to developers (optional)
resource "azurerm_role_assignment" "dev_keyvault_secrets_officer" {
  count                = length(var.developer_object_ids)
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Secrets Officer"
  principal_id         = var.developer_object_ids[count.index]
  
  depends_on = [azurerm_key_vault.main]
}

# Grant current user (deployer) access to Key Vault
resource "azurerm_role_assignment" "deployer_keyvault_access" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Secrets Officer"
  principal_id         = data.azurerm_client_config.current.object_id
  
  depends_on = [azurerm_key_vault.main]
}

# Optional: Service Plan for App Service deployment
resource "azurerm_service_plan" "main" {
  count               = var.create_app_service ? 1 : 0
  name                = "${var.app_name}-plan"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  
  os_type  = "Linux"
  sku_name = "B1"  # Basic tier for development
  
  tags = var.common_tags
}

# Optional: Create App Service with Managed Identity enabled
resource "azurerm_linux_web_app" "chatbot" {
  count               = var.create_app_service ? 1 : 0
  name                = "${var.app_name}-webapp"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  service_plan_id     = azurerm_service_plan.main[0].id
  
  # Enable system-assigned managed identity
  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.app_identity.id]
  }
  
  # Site configuration for Python apps
  site_config {
    always_on = true
    
    application_stack {
      python_version = "3.11"
    }
  }
  
  # App settings with Key Vault references
  app_settings = {
    # CRITICAL: Use Key Vault references for secure config
    "AZURE_OPENAI_ENDPOINT"    = "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault_secret.openai_endpoint.id})"
    "AZURE_OPENAI_API_KEY"     = "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault_secret.openai_key.id})"
    "AZURE_OPENAI_DEPLOYMENT" = "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault_secret.gpt4_deployment.id})"
    
    # Enable Managed Identity for Key Vault access
    "AZURE_CLIENT_ID" = azurerm_user_assigned_identity.app_identity.client_id
    "KEY_VAULT_URL"   = azurerm_key_vault.main.vault_uri
    
    # Application Insights configuration  
    "APPLICATIONINSIGHTS_CONNECTION_STRING" = azurerm_application_insights.main.connection_string
    "CHAT_OBSERVABILITY_CONNECTION_STRING"  = var.enable_chat_observability ? azurerm_application_insights.chat[0].connection_string : ""
    "ENABLE_CHAT_OBSERVABILITY"            = tostring(var.enable_chat_observability)
    
    # Other application settings
    "ENVIRONMENT"     = var.environment
    "LOG_LEVEL"      = var.environment == "prod" ? "INFO" : "DEBUG"
  }
  
  tags = var.common_tags
  
  depends_on = [
    azurerm_key_vault_secret.openai_key,
    azurerm_key_vault_secret.openai_endpoint,
    azurerm_key_vault_secret.gpt4_deployment,
    azurerm_key_vault_secret.application_insights_connection_string,
    azurerm_role_assignment.app_keyvault_secrets_user
  ]
}

# Grant Storage Blob Data Contributor role to the application identity (for conversation storage)
resource "azurerm_role_assignment" "app_storage_contributor" {
  scope                = azurerm_storage_account.main.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_user_assigned_identity.app_identity.principal_id
  
  depends_on = [
    azurerm_storage_account.main,
    azurerm_user_assigned_identity.app_identity
  ]
}

# Grant Application Insights Component Contributor role (optional, for custom metrics)
resource "azurerm_role_assignment" "app_insights_contributor" {
  scope                = azurerm_application_insights.main.id
  role_definition_name = "Application Insights Component Contributor"
  principal_id         = azurerm_user_assigned_identity.app_identity.principal_id
  
  depends_on = [
    azurerm_application_insights.main,
    azurerm_user_assigned_identity.app_identity
  ]
}

# Environment-specific RBAC assignments
# Production: More restrictive access
resource "azurerm_role_assignment" "prod_monitoring_reader" {
  count                = var.environment == "prod" ? 1 : 0
  scope                = azurerm_resource_group.main.id
  role_definition_name = "Monitoring Reader"
  principal_id         = azurerm_user_assigned_identity.app_identity.principal_id
  
  depends_on = [azurerm_user_assigned_identity.app_identity]
}

# Development: More permissive access for debugging
resource "azurerm_role_assignment" "dev_log_analytics_reader" {
  count                = var.environment == "dev" ? 1 : 0
  scope                = azurerm_log_analytics_workspace.main.id
  role_definition_name = "Log Analytics Reader"
  principal_id         = azurerm_user_assigned_identity.app_identity.principal_id
  
  depends_on = [
    azurerm_log_analytics_workspace.main,
    azurerm_user_assigned_identity.app_identity
  ]
}

# Note: All outputs moved to outputs.tf to avoid duplication