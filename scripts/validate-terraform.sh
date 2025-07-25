#!/bin/bash

# Terraform Configuration Validation Script
# This script validates the Terraform configuration without requiring initialization

set -euo pipefail

readonly SCRIPT_NAME="$(basename "$0")"
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
readonly INFRASTRUCTURE_DIR="$PROJECT_ROOT/infrastructure"

# Color output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

print_color() {
    local color=$1
    shift
    echo -e "${color}$*${NC}"
}

print_info() { print_color "$BLUE" "ℹ️  $*"; }
print_success() { print_color "$GREEN" "✅ $*"; }
print_warning() { print_color "$YELLOW" "⚠️  $*"; }
print_error() { print_color "$RED" "❌ $*"; }

check_terraform_syntax() {
    print_info "Checking Terraform syntax..."
    
    cd "$INFRASTRUCTURE_DIR" || {
        print_error "Failed to change to infrastructure directory"
        return 1
    }
    
    # Check formatting
    if terraform fmt -check -diff; then
        print_success "Terraform formatting is correct"
    else
        print_warning "Terraform files need formatting. Run 'terraform fmt' to fix."
    fi
    
    return 0
}

check_backend_config() {
    print_info "Checking backend configuration..."
    
    local backend_file="$INFRASTRUCTURE_DIR/providers.tf"
    
    if grep -q "tfstateXXXXX" "$backend_file"; then
        print_error "Backend storage account name contains placeholder 'tfstateXXXXX'"
        print_error "Update the storage_account_name in providers.tf with a real globally unique name"
        print_info "Example: tfstate$(openssl rand -hex 4)$(date +%Y%m%d)"
        return 1
    else
        print_success "Backend storage account name appears to be configured"
    fi
    
    return 0
}

check_variable_references() {
    print_info "Checking variable references..."
    
    cd "$INFRASTRUCTURE_DIR" || return 1
    
    # Check for undefined variables
    local undefined_vars=()
    
    # This is a basic check - in production you'd want more sophisticated parsing
    while IFS= read -r line; do
        if [[ "$line" =~ var\.[a-zA-Z_][a-zA-Z0-9_]* ]]; then
            local var_name
            var_name=$(echo "$line" | grep -o 'var\.[a-zA-Z_][a-zA-Z0-9_]*' | sed 's/var\.//')
            
            if ! grep -q "variable \"$var_name\"" variables.tf; then
                undefined_vars+=("$var_name")
            fi
        fi
    done < <(find . -name "*.tf" -not -path "./modules/*" -exec cat {} \;)
    
    if [[ ${#undefined_vars[@]} -gt 0 ]]; then
        print_error "Found references to undefined variables:"
        printf '%s\n' "${undefined_vars[@]}" | sort -u | while read -r var; do
            print_error "  - var.$var"
        done
        return 1
    else
        print_success "All variable references appear to be defined"
    fi
    
    return 0
}

check_required_files() {
    print_info "Checking required files..."
    
    local required_files=(
        "$INFRASTRUCTURE_DIR/main.tf"
        "$INFRASTRUCTURE_DIR/variables.tf"
        "$INFRASTRUCTURE_DIR/outputs.tf"
        "$INFRASTRUCTURE_DIR/providers.tf"
        "$INFRASTRUCTURE_DIR/modules/azure-openai/main.tf"
        "$INFRASTRUCTURE_DIR/modules/azure-openai/variables.tf"
        "$INFRASTRUCTURE_DIR/modules/azure-openai/outputs.tf"
        "$INFRASTRUCTURE_DIR/modules/azure-openai/rbac.tf"
    )
    
    local missing_files=()
    
    for file in "${required_files[@]}"; do
        if [[ ! -f "$file" ]]; then
            missing_files+=("$file")
        fi
    done
    
    if [[ ${#missing_files[@]} -gt 0 ]]; then
        print_error "Missing required files:"
        for file in "${missing_files[@]}"; do
            print_error "  - $file"
        done
        return 1
    else
        print_success "All required files are present"
    fi
    
    return 0
}

check_placeholder_values() {
    print_info "Checking for placeholder values..."
    
    cd "$INFRASTRUCTURE_DIR" || return 1
    
    local placeholder_patterns=(
        "XXXXX"
        "TODO"
        "CHANGEME"
        "admin@example.com"
        "your-"
    )
    
    local found_placeholders=()
    
    for pattern in "${placeholder_patterns[@]}"; do
        if grep -r "$pattern" --include="*.tf" .; then
            found_placeholders+=("$pattern")
        fi
    done > /dev/null 2>&1
    
    if [[ ${#found_placeholders[@]} -gt 0 ]]; then
        print_warning "Found potential placeholder values that may need updating:"
        for pattern in "${found_placeholders[@]}"; do
            print_warning "  - Pattern: $pattern"
            grep -rn "$pattern" --include="*.tf" . | head -3
        done
        print_info "Review these values and update them if needed for your deployment"
    else
        print_success "No obvious placeholder values found"
    fi
    
    return 0
}

show_deployment_readiness() {
    print_info "Deployment readiness summary:"
    
    cat << EOF

To deploy this infrastructure:

1. Ensure you have Azure CLI installed and logged in:
   az login

2. Create the backend storage account (if not exists):
   ./scripts/deploy.sh --setup-backend-only

3. Initialize and deploy Terraform:
   ./scripts/deploy.sh

4. Set up the application environment:
   ./scripts/setup-env.sh

5. Test the application:
   python src/main.py health

EOF
}

main() {
    print_info "🔍 Terraform Configuration Validation"
    echo
    
    local errors=0
    
    check_required_files || ((errors++))
    check_terraform_syntax || ((errors++))
    check_backend_config || ((errors++))
    check_variable_references || ((errors++))
    check_placeholder_values # This is just a warning, don't count as error
    
    echo
    
    if [[ $errors -eq 0 ]]; then
        print_success "✅ All validation checks passed!"
        show_deployment_readiness
    else
        print_error "❌ Found $errors validation error(s)"
        print_error "Please fix the errors above before proceeding with deployment"
        exit 1
    fi
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi