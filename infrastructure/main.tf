# Main Infrastructure Configuration
# Task 6: Module instantiation with configuration and dependencies

# Local values for computed configurations
locals {
  # Generate consistent resource names
  name_prefix = "${var.app_name}-${var.environment}"

  # Resource-specific naming with random suffix for global uniqueness
  openai_service_name  = "${local.name_prefix}-openai-${random_id.suffix.hex}"
  openai_subdomain     = "${var.app_name}${var.environment}${random_id.suffix.hex}"
  key_vault_name       = "kv-${var.environment}-${random_id.suffix.hex}"
  log_analytics_name   = "${local.name_prefix}-logs"
  storage_account_name = "${replace(local.name_prefix, "-", "")}st${random_id.suffix.hex}"

  # Combine environment tags with common tags
  tags = merge(var.common_tags, {
    Environment = var.environment
    Deployment  = "Terraform"
    Application = "Azure-OpenAI-Chatbot"
    CreatedBy   = data.azurerm_client_config.current.object_id
    CreatedOn   = formatdate("YYYY-MM-DD", timestamp())
  })
}

# Generate random suffix for globally unique names
resource "random_id" "suffix" {
  byte_length = 4

  keepers = {
    app_name    = var.app_name
    environment = var.environment
  }
}

# Get current Azure configuration for tagging and RBAC
data "azurerm_client_config" "current" {}

# Instantiate the Azure OpenAI module
module "azure_openai" {
  source = "./modules/azure-openai"

  # Resource naming and location
  resource_group_name = var.resource_group_name
  location            = var.location
  app_name            = var.app_name
  environment         = var.environment

  # Azure OpenAI configuration
  openai_service_name = local.openai_service_name
  openai_subdomain    = local.openai_subdomain
  openai_sku          = var.openai_sku

  # GPT-4 model configuration
  gpt4_model_name      = var.gpt4_model_name
  gpt4_model_version   = var.gpt4_model_version
  gpt4_deployment_name = var.gpt4_deployment_name
  gpt4_capacity        = var.gpt4_capacity
  gpt4_scale_type      = var.gpt4_scale_type

  # Key Vault configuration
  key_vault_name = local.key_vault_name
  key_vault_sku  = var.key_vault_sku

  # Log Analytics configuration
  log_analytics_name = local.log_analytics_name
  log_analytics_sku  = var.log_analytics_sku
  log_retention_days = var.log_retention_days

  # Dual Observability configuration
  enable_chat_observability         = var.enable_chat_observability
  chat_observability_retention_days = var.chat_observability_retention_days

  # Storage Account configuration
  storage_account_name = local.storage_account_name

  # RBAC configuration
  developer_object_ids = var.developer_object_ids
  create_app_service   = var.create_app_service

  # FFIEC CDR API configuration
  ffiec_cdr_api_key  = var.ffiec_cdr_api_key
  ffiec_cdr_username = var.ffiec_cdr_username

  # Resource tagging
  common_tags = local.tags

  # Dependencies
  depends_on = [
    random_id.suffix
  ]
}

# Create additional resources that depend on the module
# Example: Network Security Group (if needed for enhanced security)
resource "azurerm_network_security_group" "main" {
  count               = var.create_app_service ? 1 : 0
  name                = "${local.name_prefix}-nsg"
  location            = var.location
  resource_group_name = module.azure_openai.resource_group_name

  # Allow HTTPS traffic
  security_rule {
    name                       = "AllowHTTPS"
    priority                   = 1001
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "443"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  # Allow HTTP traffic (can be removed in production)
  security_rule {
    name                       = "AllowHTTP"
    priority                   = 1002
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "80"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  tags = local.tags

  depends_on = [module.azure_openai]
}

# Create diagnostic settings for monitoring
resource "azurerm_monitor_diagnostic_setting" "key_vault" {
  name                       = "${local.name_prefix}-kv-diagnostics"
  target_resource_id         = module.azure_openai.key_vault_id
  log_analytics_workspace_id = module.azure_openai.log_analytics_workspace_id

  enabled_log {
    category = "AuditEvent"
  }

  enabled_log {
    category = "AzurePolicyEvaluationDetails"
  }

  metric {
    category = "AllMetrics"
    enabled  = true
  }

  depends_on = [module.azure_openai]
}

resource "azurerm_monitor_diagnostic_setting" "openai_service" {
  name                       = "${local.name_prefix}-openai-diagnostics"
  target_resource_id         = module.azure_openai.openai_service_id
  log_analytics_workspace_id = module.azure_openai.log_analytics_workspace_id

  enabled_log {
    category = "Audit"
  }

  enabled_log {
    category = "RequestResponse"
  }

  metric {
    category = "AllMetrics"
    enabled  = true
  }

  depends_on = [module.azure_openai]
}

# Create alerts for monitoring (optional)
resource "azurerm_monitor_metric_alert" "high_token_usage" {
  name                = "${local.name_prefix}-high-token-usage"
  resource_group_name = module.azure_openai.resource_group_name
  scopes              = [module.azure_openai.openai_service_id]

  criteria {
    metric_namespace = "Microsoft.CognitiveServices/accounts"
    metric_name      = "TotalTokens"
    aggregation      = "Total"
    operator         = "GreaterThan"
    threshold        = 100000 # Adjust based on your usage patterns
  }

  action {
    action_group_id = azurerm_monitor_action_group.main.id
  }

  depends_on = [module.azure_openai]
}

# Action group for alerts
resource "azurerm_monitor_action_group" "main" {
  name                = "${local.name_prefix}-alerts"
  resource_group_name = module.azure_openai.resource_group_name
  short_name          = "aoai-alerts"

  # Add email notifications
  email_receiver {
    name          = "admin-email"
    email_address = var.alert_email
  }

  tags = local.tags

  depends_on = [module.azure_openai]
}