#!/bin/bash
# Azure OpenAI Chatbot Deployment Script
# Task 9: Automated Terraform remote state setup and infrastructure deployment

set -e  # Exit on any error
set -u  # Exit on undefined variable

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
ENVIRONMENT=${1:-dev}
LOCATION=${2:-"East US"}
SUBSCRIPTION_ID=""
TENANT_ID=""
FORCE_REINIT=false

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "${SCRIPT_DIR}")"
INFRA_DIR="${PROJECT_ROOT}/infrastructure"

# Resource naming
RESOURCE_GROUP_NAME="tfstate-rg-${ENVIRONMENT}"
STORAGE_ACCOUNT_NAME="tfstate$(openssl rand -hex 4)${ENVIRONMENT}"
CONTAINER_NAME="tfstate"
STATE_KEY="${ENVIRONMENT}/terraform.tfstate"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check if Azure CLI is installed
    if ! command -v az &> /dev/null; then
        print_error "Azure CLI not found. Please install Azure CLI first."
        exit 1
    fi
    
    # Check if Terraform is installed
    if ! command -v terraform &> /dev/null; then
        print_error "Terraform not found. Please install Terraform first."
        exit 1
    fi
    
    # Check if jq is installed
    if ! command -v jq &> /dev/null; then
        print_error "jq not found. Please install jq first."
        exit 1
    fi
    
    # Check Azure CLI login
    if ! az account show &> /dev/null; then
        print_error "Not logged into Azure. Please run 'az login' first."
        exit 1
    fi
    
    print_success "Prerequisites check passed"
}

# Function to get Azure context
get_azure_context() {
    print_status "Getting Azure context..."
    
    # Get current subscription and tenant
    SUBSCRIPTION_ID=$(az account show --query id -o tsv)
    TENANT_ID=$(az account show --query tenantId -o tsv)
    
    print_status "Using subscription: ${SUBSCRIPTION_ID}"
    print_status "Using tenant: ${TENANT_ID}"
}

# Function to create resource group for Terraform state
create_state_resource_group() {
    print_status "Creating resource group for Terraform state..."
    
    # Check if resource group exists
    if az group show --name "${RESOURCE_GROUP_NAME}" &> /dev/null; then
        print_warning "Resource group ${RESOURCE_GROUP_NAME} already exists"
    else
        az group create \
            --name "${RESOURCE_GROUP_NAME}" \
            --location "${LOCATION}" \
            --tags Environment="${ENVIRONMENT}" \
                   Purpose="TerraformState" \
                   ManagedBy="DeployScript" \
                   CreatedOn="$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
        > /dev/null
        
        print_success "Created resource group: ${RESOURCE_GROUP_NAME}"
    fi
}

# Function to create storage account for Terraform state
create_state_storage_account() {
    print_status "Creating storage account for Terraform state..."
    
    # Check if storage account name is available
    local availability
    availability=$(az storage account check-name --name "${STORAGE_ACCOUNT_NAME}" --query nameAvailable -o tsv)
    
    if [[ "${availability}" == "false" ]]; then
        print_warning "Storage account name ${STORAGE_ACCOUNT_NAME} not available, generating new name..."
        STORAGE_ACCOUNT_NAME="tfstate$(openssl rand -hex 6)${ENVIRONMENT}"
    fi
    
    # Create storage account
    az storage account create \
        --name "${STORAGE_ACCOUNT_NAME}" \
        --resource-group "${RESOURCE_GROUP_NAME}" \
        --location "${LOCATION}" \
        --sku Standard_LRS \
        --encryption-services blob \
        --https-only true \
        --min-tls-version TLS1_2 \
        --allow-blob-public-access false \
        --tags Environment="${ENVIRONMENT}" \
               Purpose="TerraformState" \
               ManagedBy="DeployScript" \
    > /dev/null
    
    print_success "Created storage account: ${STORAGE_ACCOUNT_NAME}"
}

# Function to configure storage account for state management
configure_state_storage() {
    print_status "Configuring storage account for state management..."
    
    # Enable versioning for state recovery
    az storage account blob-service-properties update \
        --account-name "${STORAGE_ACCOUNT_NAME}" \
        --resource-group "${RESOURCE_GROUP_NAME}" \
        --enable-versioning true \
        --enable-change-feed true \
        --change-feed-retention-days 30 \
    > /dev/null
    
    # Get storage account key
    STORAGE_KEY=$(az storage account keys list \
        --resource-group "${RESOURCE_GROUP_NAME}" \
        --account-name "${STORAGE_ACCOUNT_NAME}" \
        --query '[0].value' -o tsv)
    
    # Create container for Terraform state
    if ! az storage container exists \
        --name "${CONTAINER_NAME}" \
        --account-name "${STORAGE_ACCOUNT_NAME}" \
        --account-key "${STORAGE_KEY}" \
        --query exists -o tsv | grep -q true; then
        
        az storage container create \
            --name "${CONTAINER_NAME}" \
            --account-name "${STORAGE_ACCOUNT_NAME}" \
            --account-key "${STORAGE_KEY}" \
            --public-access off \
        > /dev/null
        
        print_success "Created container: ${CONTAINER_NAME}"
    else
        print_warning "Container ${CONTAINER_NAME} already exists"
    fi
}

# Function to create terraform.tfvars file
create_tfvars_file() {
    print_status "Creating terraform.tfvars file..."
    
    local tfvars_file="${INFRA_DIR}/terraform.tfvars"
    
    cat > "${tfvars_file}" <<EOF
# Terraform Variables for ${ENVIRONMENT} Environment
# Generated by deploy.sh on $(date -u +%Y-%m-%dT%H:%M:%SZ)

# Resource Configuration
resource_group_name = "rg-azure-openai-chatbot-${ENVIRONMENT}"
location            = "${LOCATION}"
app_name           = "aoai-chatbot"
environment        = "${ENVIRONMENT}"

# Azure OpenAI Configuration
openai_sku               = "S0"
gpt4_model_name          = "gpt-4"
gpt4_model_version       = "0613"
gpt4_deployment_name     = "gpt-4-deployment"
gpt4_capacity            = 10

# Key Vault Configuration
key_vault_sku = "standard"

# Log Analytics Configuration
log_analytics_sku    = "PerGB2018"
log_retention_days   = 30

# RBAC Configuration
developer_object_ids = []
create_app_service   = false

# Subscription Configuration (optional)
# subscription_id = "${SUBSCRIPTION_ID}"
# tenant_id       = "${TENANT_ID}"

# Resource Tagging
common_tags = {
  Environment = "${ENVIRONMENT}"
  Project     = "Azure-OpenAI-Chatbot"
  ManagedBy   = "Terraform"
  Owner       = "DevOps-Team"
  CostCenter  = "Engineering"
  CreatedBy   = "$(az account show --query user.name -o tsv)"
  CreatedOn   = "$(date -u +%Y-%m-%d)"
}
EOF

    print_success "Created terraform.tfvars file"
}

# Function to initialize Terraform with remote state
init_terraform() {
    print_status "Initializing Terraform with remote state..."
    
    cd "${INFRA_DIR}"
    
    # Check if we need to reinitialize
    if [[ "${FORCE_REINIT}" == "true" ]] || [[ ! -d ".terraform" ]]; then
        # Remove existing Terraform state if forcing reinit
        if [[ "${FORCE_REINIT}" == "true" ]]; then
            rm -rf .terraform .terraform.lock.hcl
            print_warning "Forced reinitialization - removed existing Terraform state"
        fi
        
        # Initialize with remote backend
        terraform init \
            -backend-config="resource_group_name=${RESOURCE_GROUP_NAME}" \
            -backend-config="storage_account_name=${STORAGE_ACCOUNT_NAME}" \
            -backend-config="container_name=${CONTAINER_NAME}" \
            -backend-config="key=${STATE_KEY}" \
            -backend-config="access_key=${STORAGE_KEY}"
        
        print_success "Terraform initialized with remote state"
    else
        print_warning "Terraform already initialized, skipping initialization"
    fi
}

# Function to validate Terraform configuration
validate_terraform() {
    print_status "Validating Terraform configuration..."
    
    cd "${INFRA_DIR}"
    
    # Validate configuration
    terraform validate
    
    # Format check
    if ! terraform fmt -check -diff; then
        print_warning "Terraform formatting issues found. Running terraform fmt..."
        terraform fmt -recursive
    fi
    
    print_success "Terraform configuration validated"
}

# Function to plan Terraform deployment
plan_terraform() {
    print_status "Planning Terraform deployment..."
    
    cd "${INFRA_DIR}"
    
    # Create plan file
    terraform plan \
        -var-file="terraform.tfvars" \
        -out="tfplan-${ENVIRONMENT}" \
        -detailed-exitcode || {
        local exit_code=$?
        if [[ ${exit_code} -eq 2 ]]; then
            print_status "Changes detected in Terraform plan"
        elif [[ ${exit_code} -eq 1 ]]; then
            print_error "Terraform plan failed"
            exit 1
        fi
    }
    
    print_success "Terraform plan created: tfplan-${ENVIRONMENT}"
}

# Function to apply Terraform deployment
apply_terraform() {
    print_status "Applying Terraform deployment..."
    
    cd "${INFRA_DIR}"
    
    # Check if plan file exists
    if [[ ! -f "tfplan-${ENVIRONMENT}" ]]; then
        print_error "Plan file not found. Please run plan first."
        exit 1
    fi
    
    # Apply the plan
    terraform apply "tfplan-${ENVIRONMENT}"
    
    print_success "Terraform deployment completed"
}

# Function to output deployment information
output_deployment_info() {
    print_status "Deployment information:"
    
    cd "${INFRA_DIR}"
    
    echo
    echo "=== Terraform State Information ==="
    echo "Resource Group:    ${RESOURCE_GROUP_NAME}"
    echo "Storage Account:   ${STORAGE_ACCOUNT_NAME}"
    echo "Container:         ${CONTAINER_NAME}"
    echo "State Key:         ${STATE_KEY}"
    echo
    
    echo "=== Terraform Outputs ==="
    terraform output
    echo
    
    echo "=== Next Steps ==="
    echo "1. Review the outputs above"
    echo "2. Run: ./scripts/setup-env.sh ${ENVIRONMENT}"
    echo "3. Set up your Python environment"
    echo "4. Test the application"
    echo
    
    print_success "Deployment completed successfully!"
}

# Function to show usage
show_usage() {
    cat <<EOF
Usage: $0 [ENVIRONMENT] [LOCATION]

Arguments:
    ENVIRONMENT    Deployment environment (dev/staging/prod) [default: dev]
    LOCATION       Azure region [default: East US]

Options:
    --force-reinit Force Terraform reinitialization
    --plan-only    Only run terraform plan, don't apply
    --help         Show this help message

Examples:
    $0 dev "East US"
    $0 prod "West Europe" --force-reinit
    $0 staging --plan-only

Environment Variables:
    AZURE_SUBSCRIPTION_ID    Override Azure subscription
    AZURE_TENANT_ID         Override Azure tenant
    
Prerequisites:
    - Azure CLI installed and logged in (az login)
    - Terraform installed (>= 1.0)
    - jq installed for JSON processing
    - Appropriate Azure permissions for resource creation
EOF
}

# Main execution flow
main() {
    local plan_only=false
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --force-reinit)
                FORCE_REINIT=true
                shift
                ;;
            --plan-only)
                plan_only=true
                shift
                ;;
            --help|-h)
                show_usage
                exit 0
                ;;
            -*)
                print_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
            *)
                if [[ -z "${ENVIRONMENT:-}" ]] || [[ "${ENVIRONMENT}" == "dev" ]]; then
                    ENVIRONMENT="$1"
                elif [[ -z "${LOCATION:-}" ]] || [[ "${LOCATION}" == "East US" ]]; then
                    LOCATION="$1"
                fi
                shift
                ;;
        esac
    done
    
    # Validate environment
    if [[ ! "${ENVIRONMENT}" =~ ^(dev|staging|prod)$ ]]; then
        print_error "Invalid environment: ${ENVIRONMENT}. Must be dev, staging, or prod."
        exit 1
    fi
    
    print_status "Starting deployment for environment: ${ENVIRONMENT}"
    print_status "Target location: ${LOCATION}"
    
    # Execute deployment steps
    check_prerequisites
    get_azure_context
    create_state_resource_group
    create_state_storage_account
    configure_state_storage
    create_tfvars_file
    init_terraform
    validate_terraform
    plan_terraform
    
    if [[ "${plan_only}" == "false" ]]; then
        apply_terraform
        output_deployment_info
    else
        print_success "Plan-only mode completed. Review the plan and run without --plan-only to apply."
    fi
}

# Handle script interruption
trap 'print_error "Script interrupted"; exit 130' INT TERM

# Run main function with all arguments
main "$@"