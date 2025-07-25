# Bootstrap Infrastructure for Terraform Backend
# This creates the storage account needed for remote state

terraform {
  required_version = ">= 1.0"
  
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.4"
    }
  }
  
  # No backend configuration - uses local state for bootstrap
}

provider "azurerm" {
  features {}
}

# Get current client configuration
data "azurerm_client_config" "current" {}

# Variables
variable "environment" {
  description = "The deployment environment"
  type        = string
  default     = "dev"
}

variable "location" {
  description = "The Azure region"
  type        = string
  default     = "East US"
}

# Generate random suffix for globally unique names
resource "random_id" "suffix" {
  byte_length = 4
}

# Create resource group for Terraform state
resource "azurerm_resource_group" "tfstate" {
  name     = "tfstate-rg-${var.environment}"
  location = var.location

  tags = {
    Environment = var.environment
    Purpose     = "Terraform State"
    ManagedBy   = "Terraform Bootstrap"
  }
}

# Create storage account for Terraform state
resource "azurerm_storage_account" "tfstate" {
  name                     = "tfstate${var.environment}${random_id.suffix.hex}"
  resource_group_name      = azurerm_resource_group.tfstate.name
  location                 = azurerm_resource_group.tfstate.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  
  # Security settings
  https_traffic_only_enabled = true
  min_tls_version            = "TLS1_2"
  
  # Enable versioning for state recovery
  blob_properties {
    versioning_enabled = true
    
    delete_retention_policy {
      days = 30
    }
  }

  tags = {
    Environment = var.environment
    Purpose     = "Terraform State"
    ManagedBy   = "Terraform Bootstrap"
  }
}

# Create storage container for Terraform state
resource "azurerm_storage_container" "tfstate" {
  name                  = "tfstate"
  storage_account_name  = azurerm_storage_account.tfstate.name
  container_access_type = "private"
}

# Grant current user Storage Blob Data Contributor access
resource "azurerm_role_assignment" "deployer_storage_access" {
  scope                = azurerm_storage_account.tfstate.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = data.azurerm_client_config.current.object_id
}

# Outputs
output "resource_group_name" {
  description = "The name of the resource group for Terraform state"
  value       = azurerm_resource_group.tfstate.name
}

output "storage_account_name" {
  description = "The name of the storage account for Terraform state"
  value       = azurerm_storage_account.tfstate.name
}

output "container_name" {
  description = "The name of the storage container for Terraform state"
  value       = azurerm_storage_container.tfstate.name
}

output "backend_config" {
  description = "Backend configuration for main Terraform"
  value = {
    resource_group_name  = azurerm_resource_group.tfstate.name
    storage_account_name = azurerm_storage_account.tfstate.name
    container_name       = azurerm_storage_container.tfstate.name
    key                  = "chatbot/terraform.tfstate"
  }
}
