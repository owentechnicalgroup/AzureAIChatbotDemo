# Input Variables for Infrastructure Configuration
# Task 2: Define all required variables for resource provisioning

# Resource Naming and Location
variable "resource_group_name" {
  description = "The name of the resource group"
  type        = string
  default     = "rg-azure-openai-chatbot"

  validation {
    condition     = length(var.resource_group_name) >= 1 && length(var.resource_group_name) <= 90
    error_message = "Resource group name must be between 1 and 90 characters."
  }
}

variable "location" {
  description = "The Azure region where resources will be created"
  type        = string
  default     = "East US"

  validation {
    condition = contains([
      "East US", "East US 2", "West US", "West US 2", "Central US",
      "North Central US", "South Central US", "West Central US",
      "Canada Central", "Canada East",
      "Brazil South",
      "North Europe", "West Europe", "France Central", "Germany West Central",
      "UK South", "UK West", "Switzerland North",
      "Southeast Asia", "East Asia", "Australia East", "Japan East",
      "Korea Central", "Central India", "South India"
    ], var.location)
    error_message = "Location must be a valid Azure region that supports Azure OpenAI."
  }
}

# Application Configuration
variable "app_name" {
  description = "The base name for the application resources"
  type        = string
  default     = "aoai-chatbot"

  validation {
    condition     = length(var.app_name) >= 2 && length(var.app_name) <= 20
    error_message = "App name must be between 2 and 20 characters."
  }
}

variable "environment" {
  description = "The deployment environment (dev, staging, prod)"
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod."
  }
}

# Azure OpenAI Configuration
variable "openai_sku" {
  description = "The SKU for the Azure OpenAI service"
  type        = string
  default     = "S0"

  validation {
    condition     = contains(["S0"], var.openai_sku)
    error_message = "OpenAI SKU must be S0 (Standard)."
  }
}

variable "gpt4_model_name" {
  description = "The GPT-4 model name to deploy"
  type        = string
  default     = "gpt-4.1"

  validation {
    condition     = contains(["gpt-4", "gpt-4-32k", "gpt-4-1106-Preview", "gpt-4-0125-Preview", "gpt-4.1"], var.gpt4_model_name)
    error_message = "GPT-4 model must be one of: gpt-4, gpt-4-32k, gpt-4-1106-Preview, gpt-4-0125-Preview, gpt-4.1."
  }
}

variable "gpt4_model_version" {
  description = "The GPT-4 model version to deploy"
  type        = string
  default     = "2025-04-14"

  validation {
    condition     = length(var.gpt4_model_version) > 0
    error_message = "Model version must be specified (e.g., 2025-04-14, 1106-Preview, 0125-Preview)."
  }
}

variable "gpt4_deployment_name" {
  description = "The name for the GPT-4 deployment"
  type        = string
  default     = "gpt-4-deployment"

  validation {
    condition     = length(var.gpt4_deployment_name) >= 2 && length(var.gpt4_deployment_name) <= 64
    error_message = "Deployment name must be between 2 and 64 characters."
  }
}

variable "gpt4_capacity" {
  description = "The capacity (TPM) for the GPT-4 deployment"
  type        = number
  default     = 10

  validation {
    condition     = var.gpt4_capacity >= 1 && var.gpt4_capacity <= 1000
    error_message = "GPT-4 capacity must be between 1 and 1000 TPM."
  }
}

variable "gpt4_scale_type" {
  description = "The scale type for the GPT-4 deployment"
  type        = string
  default     = "GlobalStandard"
  
  validation {
    condition     = contains(["Standard", "GlobalStandard", "ProvisionedManaged"], var.gpt4_scale_type)
    error_message = "Scale type must be one of: Standard, GlobalStandard, ProvisionedManaged."
  }
}

# Key Vault Configuration
variable "key_vault_sku" {
  description = "The SKU for the Key Vault"
  type        = string
  default     = "standard"

  validation {
    condition     = contains(["standard", "premium"], var.key_vault_sku)
    error_message = "Key Vault SKU must be standard or premium."
  }
}

# RBAC Configuration
variable "developer_object_ids" {
  description = "List of Azure AD object IDs for developers who need Key Vault access"
  type        = list(string)
  default     = []
}

variable "create_app_service" {
  description = "Whether to create an App Service for web deployment"
  type        = bool
  default     = false
}

# Log Analytics Configuration
variable "log_analytics_sku" {
  description = "The SKU for the Log Analytics workspace"
  type        = string
  default     = "PerGB2018"

  validation {
    condition     = contains(["Free", "Standalone", "PerNode", "PerGB2018"], var.log_analytics_sku)
    error_message = "Log Analytics SKU must be one of: Free, Standalone, PerNode, PerGB2018."
  }
}

variable "log_retention_days" {
  description = "Number of days to retain logs in Log Analytics"
  type        = number
  default     = 30

  validation {
    condition     = var.log_retention_days >= 7 && var.log_retention_days <= 730
    error_message = "Log retention must be between 7 and 730 days."
  }
}

# Dual Observability Configuration
variable "enable_chat_observability" {
  description = "Whether to create a separate Application Insights workspace for chat observability"
  type        = bool
  default     = true
}

variable "chat_observability_retention_days" {
  description = "Number of days to retain chat observability logs (separate from application logs)"
  type        = number
  default     = 90

  validation {
    condition     = var.chat_observability_retention_days >= 7 && var.chat_observability_retention_days <= 730
    error_message = "Chat observability retention must be between 7 and 730 days."
  }
}

# Monitoring Configuration
variable "alert_email" {
  description = "Email address for monitoring alerts"
  type        = string
  default     = "admin@example.com"

  validation {
    condition     = can(regex("^[^@]+@[^@]+\\.[^@]+$", var.alert_email))
    error_message = "Alert email must be a valid email address."
  }
}

# Resource Tagging
variable "common_tags" {
  description = "Common tags to apply to all resources"
  type        = map(string)
  default = {
    Environment = "dev"
    Project     = "Azure-OpenAI-Chatbot"
    ManagedBy   = "Terraform"
    Owner       = "DevOps-Team"
    CostCenter  = "Engineering"
  }
}

# Azure Subscription and Tenant Configuration (optional overrides)
variable "subscription_id" {
  description = "Azure subscription ID (optional, uses default if not specified)"
  type        = string
  default     = null
}

variable "tenant_id" {
  description = "Azure tenant ID (optional, uses default if not specified)"
  type        = string
  default     = null
}