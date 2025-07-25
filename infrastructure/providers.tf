# Terraform Provider and Remote State Configuration
# Task 1: Azure provider with remote state backend

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

  # CRITICAL: Remote state configuration
  backend "azurerm" {
    # These values should be provided via backend configuration file
    # or environment variables during terraform init
    resource_group_name  = "tfstate-rg-dev"
    storage_account_name = "tfstatedeveb885f04" # Must be globally unique
    container_name       = "tfstate"
    key                  = "chatbot/terraform.tfstate"

    # CRITICAL: Enable state locking and encryption
    use_azuread_auth = true  # Use Azure AD authentication
    use_msi          = false # Set to true if using Managed Identity
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

# Note: azurerm_client_config data resource is defined in main.tf




