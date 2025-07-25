#!/bin/bash
# Azure OpenAI Chatbot Destruction Script
# Task 10: Safe infrastructure cleanup with confirmation prompts

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
FORCE_DESTROY=false
BACKUP_STATE=true
DESTROY_STATE_RESOURCES=false

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "${SCRIPT_DIR}")"
INFRA_DIR="${PROJECT_ROOT}/infrastructure"

# Resource naming for state resources
RESOURCE_GROUP_NAME="tfstate-rg-${ENVIRONMENT}"
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
    
    # Check Azure CLI login
    if ! az account show &> /dev/null; then
        print_error "Not logged into Azure. Please run 'az login' first."
        exit 1
    fi
    
    # Check if in infrastructure directory
    if [[ ! -f "${INFRA_DIR}/main.tf" ]]; then
        print_error "Terraform configuration not found in ${INFRA_DIR}"
        exit 1
    fi
    
    print_success "Prerequisites check passed"
}

# Function to get current Terraform state info
get_terraform_state_info() {
    print_status "Getting Terraform state information..."
    
    cd "${INFRA_DIR}"
    
    # Check if Terraform is initialized
    if [[ ! -d ".terraform" ]]; then
        print_error "Terraform not initialized. Please run deploy.sh first."
        exit 1
    fi
    
    # Get state storage account name from Terraform backend config
    if [[ -f ".terraform/terraform.tfstate" ]]; then
        local backend_config
        backend_config=$(jq -r '.backend.config' .terraform/terraform.tfstate 2>/dev/null || echo "{}")
        STORAGE_ACCOUNT_NAME=$(echo "${backend_config}" | jq -r '.storage_account_name // empty')
    fi
    
    if [[ -z "${STORAGE_ACCOUNT_NAME:-}" ]]; then
        print_warning "Could not determine storage account name from Terraform state"
        print_status "Please provide the storage account name or run with --destroy-state-resources"
    fi
}

# Function to backup Terraform state
backup_terraform_state() {
    if [[ "${BACKUP_STATE}" == "false" ]]; then
        print_warning "Skipping state backup as requested"
        return 0
    fi
    
    print_status "Backing up Terraform state..."
    
    cd "${INFRA_DIR}"
    
    # Create backup directory
    local backup_dir="${PROJECT_ROOT}/backups"
    local timestamp=$(date +%Y%m%d-%H%M%S)
    local backup_file="${backup_dir}/terraform-state-${ENVIRONMENT}-${timestamp}.tfstate"
    
    mkdir -p "${backup_dir}"
    
    # Download current state
    if terraform state pull > "${backup_file}"; then
        print_success "State backed up to: ${backup_file}"
    else
        print_warning "Could not backup state file"
    fi
    
    # Also backup tfvars
    if [[ -f "terraform.tfvars" ]]; then
        cp "terraform.tfvars" "${backup_dir}/terraform-${ENVIRONMENT}-${timestamp}.tfvars"
        print_success "Variables backed up to: ${backup_dir}/terraform-${ENVIRONMENT}-${timestamp}.tfvars"
    fi
}

# Function to confirm destruction
confirm_destruction() {
    if [[ "${FORCE_DESTROY}" == "true" ]]; then
        print_warning "Force destroy mode - skipping confirmation"
        return 0
    fi
    
    print_warning "========================================="
    print_warning "WARNING: DESTRUCTIVE OPERATION"
    print_warning "========================================="
    print_warning "This will permanently destroy all resources in the ${ENVIRONMENT} environment."
    print_warning "This action cannot be undone!"
    echo
    
    # Show what will be destroyed
    cd "${INFRA_DIR}"
    print_status "Resources that will be destroyed:"
    terraform state list 2>/dev/null || print_warning "Could not list resources"
    echo
    
    # Multiple confirmations for safety
    read -p "Are you sure you want to destroy the ${ENVIRONMENT} environment? (yes/no): " -r
    if [[ ! "$REPLY" =~ ^[Yy][Ee][Ss]$ ]]; then
        print_status "Destruction cancelled by user"
        exit 0
    fi
    
    read -p "Type the environment name '${ENVIRONMENT}' to confirm: " -r
    if [[ "$REPLY" != "${ENVIRONMENT}" ]]; then
        print_error "Environment name mismatch. Destruction cancelled."
        exit 1
    fi
    
    print_warning "Proceeding with destruction in 10 seconds..."
    for i in {10..1}; do
        echo -n "${i}... "
        sleep 1
    done
    echo
}

# Function to destroy Terraform resources
destroy_terraform_resources() {
    print_status "Destroying Terraform resources..."
    
    cd "${INFRA_DIR}"
    
    # Create a destruction plan first
    print_status "Creating destruction plan..."
    terraform plan -destroy -var-file="terraform.tfvars" -out="destroy-plan-${ENVIRONMENT}"
    
    # Apply the destruction plan
    print_status "Applying destruction plan..."
    terraform apply "destroy-plan-${ENVIRONMENT}"
    
    # Clean up plan file
    rm -f "destroy-plan-${ENVIRONMENT}"
    
    print_success "Terraform resources destroyed"
}

# Function to destroy Terraform state resources
destroy_state_resources() {
    if [[ "${DESTROY_STATE_RESOURCES}" == "false" ]]; then
        print_status "Keeping Terraform state resources (use --destroy-state-resources to remove)"
        return 0
    fi
    
    print_warning "Destroying Terraform state resources..."
    
    # Confirm state resource destruction
    if [[ "${FORCE_DESTROY}" == "false" ]]; then
        print_warning "This will destroy the Terraform state storage account and all state history!"
        read -p "Are you absolutely sure? Type 'DELETE STATE' to confirm: " -r
        if [[ "$REPLY" != "DELETE STATE" ]]; then
            print_status "State resource destruction cancelled"
            return 0
        fi
    fi
    
    # Delete storage account (this will delete all state files)
    if [[ -n "${STORAGE_ACCOUNT_NAME:-}" ]]; then
        print_status "Deleting storage account: ${STORAGE_ACCOUNT_NAME}"
        az storage account delete \
            --name "${STORAGE_ACCOUNT_NAME}" \
            --resource-group "${RESOURCE_GROUP_NAME}" \
            --yes \
        2>/dev/null || print_warning "Could not delete storage account (may already be deleted)"
    fi
    
    # Delete resource group for state resources
    if az group show --name "${RESOURCE_GROUP_NAME}" &> /dev/null; then
        print_status "Deleting resource group: ${RESOURCE_GROUP_NAME}"
        az group delete \
            --name "${RESOURCE_GROUP_NAME}" \
            --yes --no-wait \
        2>/dev/null || print_warning "Could not delete resource group"
        
        print_success "Resource group deletion initiated: ${RESOURCE_GROUP_NAME}"
    fi
}

# Function to cleanup local Terraform files
cleanup_local_files() {
    print_status "Cleaning up local Terraform files..."
    
    cd "${INFRA_DIR}"
    
    # Remove Terraform state directory
    if [[ -d ".terraform" ]]; then
        rm -rf .terraform
        print_success "Removed .terraform directory"
    fi
    
    # Remove lock file
    if [[ -f ".terraform.lock.hcl" ]]; then
        rm -f .terraform.lock.hcl
        print_success "Removed .terraform.lock.hcl"
    fi
    
    # Remove plan files
    rm -f *.tfplan destroy-plan-* tfplan-*
    
    # Optionally remove tfvars (ask user)
    if [[ -f "terraform.tfvars" ]] && [[ "${FORCE_DESTROY}" == "false" ]]; then
        read -p "Remove terraform.tfvars file? (y/n): " -r
        if [[ "$REPLY" =~ ^[Yy]$ ]]; then
            rm -f terraform.tfvars
            print_success "Removed terraform.tfvars"
        fi
    elif [[ "${FORCE_DESTROY}" == "true" ]]; then
        rm -f terraform.tfvars
        print_success "Removed terraform.tfvars"
    fi
}

# Function to show destruction summary
show_destruction_summary() {
    print_success "========================================="
    print_success "DESTRUCTION COMPLETED"
    print_success "========================================="
    
    echo
    echo "Environment: ${ENVIRONMENT}"
    echo "Timestamp:   $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo
    
    if [[ "${BACKUP_STATE}" == "true" ]]; then
        echo "✓ State backed up before destruction"
    fi
    
    if [[ "${DESTROY_STATE_RESOURCES}" == "true" ]]; then
        echo "✓ State resources destroyed"
    else
        echo "⚠ State resources preserved"
    fi
    
    echo "✓ Application resources destroyed"
    echo "✓ Local Terraform files cleaned"
    echo
    
    print_status "Resources in other environments (if any) are unaffected"
    
    if [[ "${DESTROY_STATE_RESOURCES}" == "false" ]]; then
        echo
        print_warning "State storage account preserved: ${STORAGE_ACCOUNT_NAME:-unknown}"
        print_warning "You can redeploy using the same state by running deploy.sh"
    fi
}

# Function to show usage
show_usage() {
    cat <<EOF
Usage: $0 [ENVIRONMENT] [OPTIONS]

Arguments:
    ENVIRONMENT    Deployment environment to destroy (dev/staging/prod) [default: dev]

Options:
    --force-destroy              Skip all confirmation prompts
    --no-backup                  Skip state backup before destruction
    --destroy-state-resources    Also destroy Terraform state storage resources
    --help                       Show this help message

Examples:
    $0 dev                       # Destroy dev environment with confirmations
    $0 prod --force-destroy      # Destroy prod environment without prompts
    $0 staging --destroy-state-resources  # Destroy staging and its state storage

WARNING:
    This script will permanently destroy all resources in the specified environment.
    This action cannot be undone. Always ensure you have backups of important data.

State Resources:
    By default, Terraform state storage resources (storage account, resource group)
    are preserved to allow redeployment. Use --destroy-state-resources to remove them.

Prerequisites:
    - Azure CLI installed and logged in (az login)
    - Terraform installed (>= 1.0)
    - Appropriate Azure permissions for resource deletion
EOF
}

# Main execution flow
main() {
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --force-destroy)
                FORCE_DESTROY=true
                shift
                ;;
            --no-backup)
                BACKUP_STATE=false
                shift
                ;;
            --destroy-state-resources)
                DESTROY_STATE_RESOURCES=true
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
                ENVIRONMENT="$1"
                shift
                ;;
        esac
    done
    
    # Validate environment
    if [[ ! "${ENVIRONMENT}" =~ ^(dev|staging|prod)$ ]]; then
        print_error "Invalid environment: ${ENVIRONMENT}. Must be dev, staging, or prod."
        exit 1
    fi
    
    print_status "Starting destruction for environment: ${ENVIRONMENT}"
    
    # Execute destruction steps
    check_prerequisites
    get_terraform_state_info
    backup_terraform_state
    confirm_destruction
    destroy_terraform_resources
    destroy_state_resources
    cleanup_local_files
    show_destruction_summary
}

# Handle script interruption
trap 'print_error "Script interrupted"; exit 130' INT TERM

# Run main function with all arguments
main "$@"