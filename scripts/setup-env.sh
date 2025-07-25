#!/bin/bash

# Azure OpenAI CLI Chatbot - Environment Setup Script
# Task 20: Extract Terraform outputs to environment variables for application configuration
#
# This script extracts infrastructure values from Terraform and populates
# environment variables for the Python application.

set -euo pipefail

# Script configuration
readonly SCRIPT_NAME="$(basename "$0")"
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
readonly INFRASTRUCTURE_DIR="$PROJECT_ROOT/infrastructure"
readonly ENV_FILE="$PROJECT_ROOT/.env"
readonly ENV_EXAMPLE_FILE="$PROJECT_ROOT/.env.example"

# Color output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

# Configuration
TERRAFORM_WORKSPACE="${TF_WORKSPACE:-default}"
FORCE_OVERWRITE=false
BACKUP_EXISTING=true
VERBOSE=false
DRY_RUN=false

# Function to print colored output
print_color() {
    local color=$1
    shift
    echo -e "${color}$*${NC}"
}

print_info() { print_color "$BLUE" "ℹ️  $*"; }
print_success() { print_color "$GREEN" "✅ $*"; }
print_warning() { print_color "$YELLOW" "⚠️  $*"; }
print_error() { print_color "$RED" "❌ $*"; }

# Function to show usage
usage() {
    cat << EOF
Usage: $SCRIPT_NAME [OPTIONS]

Extract Terraform infrastructure outputs to application environment variables.

OPTIONS:
    -f, --force              Force overwrite existing .env file without backup
    -n, --no-backup         Don't create backup of existing .env file
    -v, --verbose           Enable verbose output
    -d, --dry-run           Show what would be done without making changes
    -w, --workspace WORKSPACE   Terraform workspace to use (default: current)
    -h, --help              Show this help message

EXAMPLES:
    $SCRIPT_NAME                    # Extract outputs to .env file
    $SCRIPT_NAME --dry-run          # Preview what would be done
    $SCRIPT_NAME --force            # Overwrite existing .env without backup
    $SCRIPT_NAME -w production      # Use production workspace

DESCRIPTION:
    This script connects your deployed Azure infrastructure with the Python
    application by extracting key configuration values from Terraform outputs
    and populating them in a .env file for the application to use.

    The script will extract the following configuration:
    • Azure OpenAI endpoint and deployment settings
    • Azure Key Vault URL for secure credential storage
    • Application Insights connection string for logging
    • Managed Identity client ID for authentication
    • Environment-specific configuration values

PREREQUISITES:
    • Terraform must be installed and configured
    • Azure CLI must be logged in with appropriate permissions
    • Infrastructure must be deployed using the included Terraform configuration
    • Current directory must be the project root or scripts directory

EOF
}

# Function to parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -f|--force)
                FORCE_OVERWRITE=true
                shift
                ;;
            -n|--no-backup)
                BACKUP_EXISTING=false
                shift
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            -d|--dry-run)
                DRY_RUN=true
                shift
                ;;
            -w|--workspace)
                TERRAFORM_WORKSPACE="$2"
                shift 2
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                usage >&2
                exit 1
                ;;
        esac
    done
}

# Function to check prerequisites
check_prerequisites() {
    local errors=()

    print_info "Checking prerequisites..."

    # Check if we're in the right directory
    if [[ ! -f "$PROJECT_ROOT/src/main.py" ]]; then
        errors+=("Not in project root directory. Expected to find src/main.py")
    fi

    # Check if Terraform is installed
    if ! command -v terraform &> /dev/null; then
        errors+=("Terraform is not installed or not in PATH")
    fi

    # Check if Azure CLI is installed
    if ! command -v az &> /dev/null; then
        errors+=("Azure CLI is not installed or not in PATH")
    fi

    # Check if infrastructure directory exists
    if [[ ! -d "$INFRASTRUCTURE_DIR" ]]; then
        errors+=("Infrastructure directory not found: $INFRASTRUCTURE_DIR")
    fi

    # Check if Terraform has been initialized
    if [[ ! -d "$INFRASTRUCTURE_DIR/.terraform" ]]; then
        errors+=("Terraform not initialized. Run 'terraform init' in infrastructure directory")
    fi

    # Check Azure CLI authentication
    if ! az account show &> /dev/null; then
        errors+=("Azure CLI not authenticated. Run 'az login' first")
    fi

    if [[ ${#errors[@]} -gt 0 ]]; then
        print_error "Prerequisites check failed:"
        for error in "${errors[@]}"; do
            print_error "  • $error"
        done
        return 1
    fi

    print_success "Prerequisites check passed"
    return 0
}

# Function to check Terraform workspace and state
check_terraform_state() {
    print_info "Checking Terraform state..."

    # Change to infrastructure directory
    cd "$INFRASTRUCTURE_DIR" || {
        print_error "Failed to change to infrastructure directory"
        return 1
    }

    # Check current workspace
    local current_workspace
    current_workspace=$(terraform workspace show 2>/dev/null || echo "default")
    
    if [[ "$current_workspace" != "$TERRAFORM_WORKSPACE" ]]; then
        print_warning "Current workspace ($current_workspace) differs from requested ($TERRAFORM_WORKSPACE)"
        print_info "Switching to workspace: $TERRAFORM_WORKSPACE"
        
        if ! terraform workspace select "$TERRAFORM_WORKSPACE" 2>/dev/null; then
            print_error "Failed to switch to workspace: $TERRAFORM_WORKSPACE"
            print_info "Available workspaces:"
            terraform workspace list
            return 1
        fi
    fi

    # Check if state exists and has resources
    local resource_count
    resource_count=$(terraform state list 2>/dev/null | wc -l || echo "0")
    
    if [[ "$resource_count" -eq 0 ]]; then
        print_error "No Terraform resources found in state"
        print_error "Please deploy infrastructure first using:"
        print_error "  ./scripts/deploy.sh"
        return 1
    fi

    print_success "Found $resource_count resources in Terraform state"
    
    if [[ "$VERBOSE" == true ]]; then
        print_info "Terraform state resources:"
        terraform state list | head -10
        if [[ "$resource_count" -gt 10 ]]; then
            print_info "... and $((resource_count - 10)) more resources"
        fi
    fi

    return 0
}

# Function to extract Terraform outputs
extract_terraform_outputs() {
    print_info "Extracting Terraform outputs..."

    # Get the environment variables output
    local outputs_json
    if ! outputs_json=$(terraform output -json environment_variables 2>/dev/null); then
        print_error "Failed to get environment_variables output from Terraform"
        print_error "This output should be defined in infrastructure/outputs.tf"
        return 1
    fi

    # Parse and validate the outputs
    if [[ -z "$outputs_json" || "$outputs_json" == "null" ]]; then
        print_error "Environment variables output is empty or null"
        return 1
    fi

    # Store outputs in global variable
    TERRAFORM_OUTPUTS="$outputs_json"

    if [[ "$VERBOSE" == true ]]; then
        print_info "Extracted Terraform outputs:"
        echo "$outputs_json" | jq '.' 2>/dev/null || echo "$outputs_json"
    fi

    print_success "Successfully extracted Terraform outputs"
    return 0
}

# Function to backup existing .env file
backup_env_file() {
    if [[ -f "$ENV_FILE" ]]; then
        if [[ "$BACKUP_EXISTING" == true ]]; then
            local backup_file="${ENV_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
            print_info "Backing up existing .env file to: $backup_file"
            
            if [[ "$DRY_RUN" == false ]]; then
                cp "$ENV_FILE" "$backup_file"
                print_success "Backup created: $backup_file"
            else
                print_info "[DRY RUN] Would create backup: $backup_file"
            fi
        fi
    fi
}

# Function to generate .env file content
generate_env_content() {
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    cat << EOF
# Azure OpenAI CLI Chatbot Configuration
# Generated automatically by $SCRIPT_NAME on $timestamp
# Terraform workspace: $TERRAFORM_WORKSPACE
#
# DO NOT EDIT MANUALLY - This file is auto-generated from Terraform outputs
# To regenerate, run: ./scripts/setup-env.sh

# =============================================================================
# AZURE OPENAI CONFIGURATION
# =============================================================================

# Azure OpenAI Service Endpoint
AZURE_OPENAI_ENDPOINT=$(echo "$TERRAFORM_OUTPUTS" | jq -r '.AZURE_OPENAI_ENDPOINT')

# Azure OpenAI Deployment Name (GPT-4 model deployment)
AZURE_OPENAI_DEPLOYMENT=$(echo "$TERRAFORM_OUTPUTS" | jq -r '.AZURE_OPENAI_DEPLOYMENT')

# Azure OpenAI API Version
AZURE_OPENAI_API_VERSION=$(echo "$TERRAFORM_OUTPUTS" | jq -r '.AZURE_OPENAI_API_VERSION')

# =============================================================================
# AZURE AUTHENTICATION CONFIGURATION
# =============================================================================

# Azure Managed Identity Client ID
AZURE_CLIENT_ID=$(echo "$TERRAFORM_OUTPUTS" | jq -r '.AZURE_CLIENT_ID')

# Azure Key Vault URL for secure credential storage
KEY_VAULT_URL=$(echo "$TERRAFORM_OUTPUTS" | jq -r '.KEY_VAULT_URL')

# =============================================================================
# APPLICATION INSIGHTS CONFIGURATION
# =============================================================================

# Application Insights connection string for telemetry
APPLICATIONINSIGHTS_CONNECTION_STRING=$(echo "$TERRAFORM_OUTPUTS" | jq -r '.APPLICATIONINSIGHTS_CONNECTION_STRING')

# =============================================================================
# APPLICATION CONFIGURATION
# =============================================================================

# Environment (dev, staging, prod)
ENVIRONMENT=$(echo "$TERRAFORM_OUTPUTS" | jq -r '.ENVIRONMENT')

# Application name
APP_NAME=$(echo "$TERRAFORM_OUTPUTS" | jq -r '.APP_NAME')

# Azure region
AZURE_LOCATION=$(echo "$TERRAFORM_OUTPUTS" | jq -r '.AZURE_LOCATION')

# Log level
LOG_LEVEL=$(echo "$TERRAFORM_OUTPUTS" | jq -r '.LOG_LEVEL')

# =============================================================================
# STORAGE CONFIGURATION
# =============================================================================

# Azure Storage Account for conversation history
AZURE_STORAGE_ACCOUNT_NAME=$(echo "$TERRAFORM_OUTPUTS" | jq -r '.AZURE_STORAGE_ACCOUNT_NAME')

# Storage container for conversations
CONVERSATIONS_CONTAINER=$(echo "$TERRAFORM_OUTPUTS" | jq -r '.CONVERSATIONS_CONTAINER')

# =============================================================================
# FEATURE FLAGS
# =============================================================================

# Enable conversation history storage
ENABLE_CONVERSATION_HISTORY=$(echo "$TERRAFORM_OUTPUTS" | jq -r '.ENABLE_CONVERSATION_HISTORY')

# Enable structured JSON logging
ENABLE_STRUCTURED_LOGGING=$(echo "$TERRAFORM_OUTPUTS" | jq -r '.ENABLE_STRUCTURED_LOGGING')

# Enable performance metrics collection
ENABLE_METRICS_COLLECTION=$(echo "$TERRAFORM_OUTPUTS" | jq -r '.ENABLE_METRICS_COLLECTION')

# =============================================================================
# OPENAI MODEL CONFIGURATION
# =============================================================================

# Maximum tokens per response
AZURE_OPENAI_MAX_TOKENS=$(echo "$TERRAFORM_OUTPUTS" | jq -r '.OPENAI_MAX_TOKENS')

# Model temperature (creativity level)
AZURE_OPENAI_TEMPERATURE=$(echo "$TERRAFORM_OUTPUTS" | jq -r '.OPENAI_TEMPERATURE')

# Maximum conversation history turns
MAX_CONVERSATION_TURNS=$(echo "$TERRAFORM_OUTPUTS" | jq -r '.CONVERSATION_MAX_HISTORY')

# =============================================================================
# ADDITIONAL CONFIGURATION
# =============================================================================

# Default conversation memory type
CONVERSATION_MEMORY_TYPE=buffer_window

# Request timeout in seconds
AZURE_OPENAI_REQUEST_TIMEOUT=30.0

# Log file path
LOG_FILE_PATH=logs/chatbot.log

# Log format (json, text)
LOG_FORMAT=json

# Enable conversation logging
ENABLE_CONVERSATION_LOGGING=true

# Enable performance metrics
ENABLE_PERFORMANCE_METRICS=true

# CLI configuration
CHATBOT_CONFIG_FILE=.env
CHATBOT_LOG_LEVEL=\${LOG_LEVEL}

# Development mode (set to False for production)
DEBUG=\$(if [[ "\${ENVIRONMENT}" == "dev" ]]; then echo "True"; else echo "False"; fi)

EOF
}

# Function to validate generated configuration
validate_env_content() {
    local content="$1"
    local errors=()

    print_info "Validating generated configuration..."

    # Check for null or empty values in critical settings
    local critical_vars=("AZURE_OPENAI_ENDPOINT" "AZURE_OPENAI_DEPLOYMENT" "KEY_VAULT_URL" "AZURE_CLIENT_ID")
    
    for var in "${critical_vars[@]}"; do
        local value
        value=$(echo "$content" | grep "^${var}=" | cut -d'=' -f2- | tr -d '"')
        
        if [[ -z "$value" || "$value" == "null" ]]; then
            errors+=("Critical variable $var is empty or null")
        fi
    done

    # Validate URL formats
    local endpoint
    endpoint=$(echo "$content" | grep "^AZURE_OPENAI_ENDPOINT=" | cut -d'=' -f2- | tr -d '"')
    if [[ -n "$endpoint" && ! "$endpoint" =~ ^https://.* ]]; then
        errors+=("AZURE_OPENAI_ENDPOINT should start with https://")
    fi

    local kv_url
    kv_url=$(echo "$content" | grep "^KEY_VAULT_URL=" | cut -d'=' -f2- | tr -d '"')
    if [[ -n "$kv_url" && ! "$kv_url" =~ ^https://.*\.vault\.azure\.net/?$ ]]; then
        errors+=("KEY_VAULT_URL should be a valid Azure Key Vault URL")
    fi

    if [[ ${#errors[@]} -gt 0 ]]; then
        print_error "Configuration validation failed:"
        for error in "${errors[@]}"; do
            print_error "  • $error"
        done
        return 1
    fi

    print_success "Configuration validation passed"
    return 0
}

# Function to write .env file
write_env_file() {
    print_info "Generating .env file..."

    # Generate the content
    local env_content
    env_content=$(generate_env_content)

    # Validate the content
    if ! validate_env_content "$env_content"; then
        return 1
    fi

    # Show preview in dry run mode
    if [[ "$DRY_RUN" == true ]]; then
        print_info "[DRY RUN] Would write .env file with the following content:"
        echo "----------------------------------------"
        echo "$env_content" | head -30
        echo "... (truncated for brevity)"
        echo "----------------------------------------"
        return 0
    fi

    # Check if file exists and handle accordingly
    if [[ -f "$ENV_FILE" ]] && [[ "$FORCE_OVERWRITE" == false ]]; then
        print_warning "Existing .env file found: $ENV_FILE"
        echo -n "Do you want to overwrite it? [y/N]: "
        read -r response
        
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            print_info "Operation cancelled by user"
            return 1
        fi
    fi

    # Backup existing file
    backup_env_file

    # Write the new file
    echo "$env_content" > "$ENV_FILE" || {
        print_error "Failed to write .env file"
        return 1
    }

    print_success "Successfully created .env file: $ENV_FILE"

    # Show summary
    local line_count
    line_count=$(wc -l < "$ENV_FILE")
    print_info "Configuration file contains $line_count lines"

    if [[ "$VERBOSE" == true ]]; then
        print_info "Key configuration values:"
        grep -E '^(AZURE_OPENAI_ENDPOINT|AZURE_OPENAI_DEPLOYMENT|KEY_VAULT_URL|ENVIRONMENT)=' "$ENV_FILE" || true
    fi

    return 0
}

# Function to test configuration
test_configuration() {
    if [[ "$DRY_RUN" == true ]]; then
        print_info "[DRY RUN] Would test configuration by running health check"
        return 0
    fi

    print_info "Testing application configuration..."

    # Change back to project root
    cd "$PROJECT_ROOT" || return 1

    # Check if virtual environment exists
    if [[ -d "venv" ]]; then
        print_info "Using virtual environment: venv"
        source venv/bin/activate || {
            print_warning "Failed to activate virtual environment"
        }
    else
        print_warning "Virtual environment not found. You may need to create it first."
    fi

    # Try to run the health check
    if python src/main.py health --output-format json &> /dev/null; then
        print_success "Application health check passed ✓"
        
        if [[ "$VERBOSE" == true ]]; then
            print_info "Running detailed health check:"
            python src/main.py health --output-format table
        fi
    else
        print_warning "Application health check failed"
        print_info "This may be normal if Azure resources are not fully ready"
        print_info "Try running: python src/main.py health"
    fi
}

# Function to show next steps
show_next_steps() {
    print_success "Environment setup completed successfully!"
    
    cat << EOF

🎉 Next Steps:

1. Review the generated configuration:
   cat .env

2. Test the application:
   python src/main.py health

3. Start chatting with the AI:
   python src/main.py chat

4. For more commands:
   python src/main.py --help

📁 Important Files:
   • .env                 - Application configuration (auto-generated)
   • .env.example         - Configuration template and documentation
   • src/main.py          - Main CLI application
   • infrastructure/      - Terraform infrastructure code

🔧 Configuration Management:
   • To update configuration: ./scripts/setup-env.sh
   • To redeploy infrastructure: ./scripts/deploy.sh
   • To destroy infrastructure: ./scripts/destroy.sh

📚 Documentation:
   • See README.md for detailed setup and usage instructions
   • Check logs/ directory for application logs
   • Use 'python src/main.py --help' for CLI help

EOF

    if [[ -f "${ENV_FILE}.backup.$(date +%Y%m%d)" ]]; then
        print_info "💾 Backup of previous .env file created"
    fi
}

# Function to handle cleanup on error
cleanup() {
    local exit_code=$?
    
    if [[ $exit_code -ne 0 ]]; then
        print_error "Script failed with exit code $exit_code"
        
        # Restore backup if something went wrong during file writing
        if [[ -f "${ENV_FILE}.backup.$(date +%Y%m%d_%H%M)" ]]; then
            print_info "Attempting to restore backup..."
            mv "${ENV_FILE}.backup.$(date +%Y%m%d_%H%M)" "$ENV_FILE" 2>/dev/null || true
        fi
    fi
    
    # Change back to original directory
    cd "$SCRIPT_DIR" 2>/dev/null || true
}

# Main function
main() {
    local start_time
    start_time=$(date +%s)
    
    # Set up error handling
    trap cleanup EXIT
    
    print_info "🚀 Azure OpenAI CLI Chatbot - Environment Setup"
    print_info "Extracting infrastructure configuration from Terraform..."
    echo

    # Parse command line arguments
    parse_args "$@"

    # Run prerequisite checks
    if ! check_prerequisites; then
        exit 1
    fi

    # Check Terraform state
    if ! check_terraform_state; then
        exit 1
    fi

    # Extract Terraform outputs
    if ! extract_terraform_outputs; then
        exit 1
    fi

    # Write .env file
    if ! write_env_file; then
        exit 1
    fi

    # Test configuration
    test_configuration

    # Show next steps
    show_next_steps

    local end_time duration
    end_time=$(date +%s)
    duration=$((end_time - start_time))
    
    echo
    print_success "✅ Environment setup completed in ${duration}s"
}

# Run main function if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi