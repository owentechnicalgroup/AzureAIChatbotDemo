# Azure Storage Backend Configuration
# Task 8.5: Remote state backend for team collaboration and state safety

# This file documents the backend configuration requirements
# The actual backend configuration is in providers.tf due to Terraform limitations

# Backend Configuration Requirements:
# terraform init -backend-config="resource_group_name=tfstate-rg-dev" \
#                -backend-config="storage_account_name=tfstateXXXXX" \
#                -backend-config="container_name=tfstate" \
#                -backend-config="key=chatbot/terraform.tfstate" \
#                -backend-config="access_key=${STORAGE_ACCESS_KEY}"

# Environment-specific backend configurations
locals {
  backend_configs = {
    dev = {
      key                 = "dev/terraform.tfstate"
      resource_group_name = "tfstate-rg-dev"
      container_name      = "tfstate"
    }
    staging = {
      key                 = "staging/terraform.tfstate"
      resource_group_name = "tfstate-rg-staging"
      container_name      = "tfstate"
    }
    prod = {
      key                 = "prod/terraform.tfstate"
      resource_group_name = "tfstate-rg-prod"
      container_name      = "tfstate"
    }
  }
}

# Backend Security Requirements:
# 1. Storage Account must have:
#    - Minimum TLS version: TLS 1.2
#    - HTTPS traffic only: enabled
#    - Versioning: enabled for state recovery
#    - Soft delete: enabled for accidental deletion protection
#
# 2. Authentication:
#    - Use Azure AD authentication (use_azuread_auth = true)
#    - Avoid storage access keys in production
#    - Use Managed Identity when possible
#
# 3. State Locking:
#    - Automatically enabled with Azure Storage backend
#    - Uses blob lease mechanism
#    - Prevents concurrent modifications
#
# 4. Encryption:
#    - State files encrypted at rest by default
#    - Uses Azure Storage Service Encryption (SSE)
#    - Customer-managed keys optional for enhanced security

# State File Best Practices:
# - Never commit terraform.tfstate to version control
# - Use different state files for each environment
# - Implement backup strategy for state files
# - Monitor state file access and modifications
# - Regularly validate state file integrity

# Workspace isolation (alternative to multiple backend configs):
# terraform workspace new dev
# terraform workspace new staging
# terraform workspace new prod
# terraform workspace select dev

# Recovery Procedures:
# 1. State file corruption:
#    - Restore from backup or version history
#    - Import existing resources if needed
#    - Validate state consistency
#
# 2. State lock issues:
#    - Identify lock holder: terraform force-unlock <lock-id>
#    - Only force unlock if certain no other operation is running
#    - Monitor for abandoned locks
#
# 3. State migration:
#    - terraform init -migrate-state
#    - Verify state after migration
#    - Update team documentation

# Monitoring and Alerts:
# Set up alerts for:
# - State file modifications
# - Lock duration exceeding thresholds  
# - Authentication failures
# - Storage account access patterns