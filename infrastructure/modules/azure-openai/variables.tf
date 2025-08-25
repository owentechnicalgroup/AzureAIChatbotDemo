# Azure OpenAI Module Variables
# Task 4: Define module input variables with validation

# Resource Naming
variable "resource_group_name" {
  description = "The name of the resource group to create"
  type        = string
  
  validation {
    condition     = length(var.resource_group_name) >= 1 && length(var.resource_group_name) <= 90
    error_message = "Resource group name must be between 1 and 90 characters."
  }
}

variable "location" {
  description = "The Azure region where resources will be deployed"
  type        = string
}

variable "app_name" {
  description = "The base name for the application resources"
  type        = string
}

# Azure OpenAI Configuration
variable "openai_service_name" {
  description = "The name of the Azure OpenAI service"
  type        = string
  
  validation {
    condition     = can(regex("^[a-z0-9-]{2,64}$", var.openai_service_name))
    error_message = "OpenAI service name must be 2-64 characters, lowercase letters, numbers, and hyphens only."
  }
}

variable "openai_subdomain" {
  description = "The custom subdomain name for Azure OpenAI service"
  type        = string
  
  validation {
    condition     = can(regex("^[a-z0-9-]{3,24}$", var.openai_subdomain))
    error_message = "OpenAI subdomain must be 3-24 characters, lowercase letters, numbers, and hyphens only."
  }
}

variable "openai_sku" {
  description = "The SKU for the Azure OpenAI service"
  type        = string
  default     = "S0"
  
  validation {
    condition     = contains(["S0"], var.openai_sku)
    error_message = "OpenAI SKU must be S0 (Standard)."
  }
}

# GPT-4 Model Configuration
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

# Text Embedding Model Configuration
variable "embedding_model_name" {
  description = "The text embedding model name to deploy"
  type        = string
  default     = "text-embedding-ada-002"
  
  validation {
    condition     = contains(["text-embedding-ada-002", "text-embedding-3-small", "text-embedding-3-large"], var.embedding_model_name)
    error_message = "Embedding model must be one of: text-embedding-ada-002, text-embedding-3-small, text-embedding-3-large."
  }
}

variable "embedding_model_version" {
  description = "The text embedding model version to deploy"
  type        = string
  default     = "2"
  
  validation {
    condition     = length(var.embedding_model_version) > 0
    error_message = "Embedding model version must be specified (e.g., 2, 1)."
  }
}

variable "embedding_deployment_name" {
  description = "The name for the text embedding deployment"
  type        = string
  default     = "text-embedding-ada-002"
  
  validation {
    condition     = length(var.embedding_deployment_name) >= 2 && length(var.embedding_deployment_name) <= 64
    error_message = "Embedding deployment name must be between 2 and 64 characters."
  }
}

variable "embedding_capacity" {
  description = "The capacity (TPM) for the embedding deployment"
  type        = number
  default     = 10
  
  validation {
    condition     = var.embedding_capacity >= 1 && var.embedding_capacity <= 1000
    error_message = "Embedding capacity must be between 1 and 1000 TPM."
  }
}

variable "embedding_scale_type" {
  description = "The scale type for the embedding deployment"
  type        = string
  default     = "GlobalStandard"
  
  validation {
    condition     = contains(["Standard", "GlobalStandard", "ProvisionedManaged"], var.embedding_scale_type)
    error_message = "Embedding scale type must be one of: Standard, GlobalStandard, ProvisionedManaged."
  }
}

# Key Vault Configuration
variable "key_vault_name" {
  description = "The name of the Key Vault"
  type        = string
  
  validation {
    condition     = can(regex("^[a-zA-Z][a-zA-Z0-9-]{1,22}[a-zA-Z0-9]$", var.key_vault_name))
    error_message = "Key Vault name must be 3-24 characters, start with a letter, and contain only letters, numbers, and hyphens."
  }
}

variable "key_vault_sku" {
  description = "The SKU for the Key Vault"
  type        = string
  default     = "standard"
  
  validation {
    condition     = contains(["standard", "premium"], var.key_vault_sku)
    error_message = "Key Vault SKU must be standard or premium."
  }
}

# Log Analytics Configuration
variable "log_analytics_name" {
  description = "The name of the Log Analytics workspace"
  type        = string
  
  validation {
    condition     = can(regex("^[a-zA-Z0-9][a-zA-Z0-9-]{2,61}[a-zA-Z0-9]$", var.log_analytics_name))
    error_message = "Log Analytics name must be 4-63 characters, start and end with alphanumeric, and contain only letters, numbers, and hyphens."
  }
}

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

# Storage Account Configuration
variable "storage_account_name" {
  description = "The name of the storage account for logs and conversation history"
  type        = string
  
  validation {
    condition     = can(regex("^[a-z0-9]{3,24}$", var.storage_account_name))
    error_message = "Storage account name must be 3-24 characters, lowercase letters and numbers only."
  }
}

# RBAC Configuration
variable "developer_object_ids" {
  description = "List of Azure AD object IDs for developers who need Key Vault access"
  type        = list(string)
  default     = []
  
  validation {
    condition = alltrue([
      for id in var.developer_object_ids : can(regex("^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$", id))
    ])
    error_message = "All developer object IDs must be valid UUIDs."
  }
}

variable "create_app_service" {
  description = "Whether to create an App Service for web deployment"
  type        = bool
  default     = false
}

# Resource Tagging
variable "common_tags" {
  description = "Common tags to apply to all resources"
  type        = map(string)
  default     = {}
}

# Environment Configuration
variable "environment" {
  description = "The deployment environment (dev, staging, prod)"
  type        = string
  default     = "dev"
  
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod."
  }
}

# FFIEC CDR API Configuration
variable "ffiec_cdr_api_key" {
  description = "FFIEC CDR API key (PIN) for Call Report data access"
  type        = string
  default     = ""
  sensitive   = true
}

variable "ffiec_cdr_username" {
  description = "FFIEC CDR username for authentication"
  type        = string
  default     = ""
  sensitive   = true
}