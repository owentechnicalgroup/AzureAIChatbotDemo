# Azure OpenAI CLI Chatbot - PowerShell Environment Setup Script
# Extracts Terraform outputs to environment variables for application configuration

param(
    [switch]$Force,
    [switch]$NoBackup,
    [switch]$Verbose,
    [switch]$DryRun,
    [string]$Workspace = "default",
    [switch]$Help
)

# Script configuration
$script:ScriptName = "setup-env.ps1"
$script:ProjectRoot = Split-Path -Parent $PSScriptRoot
$script:InfrastructureDir = Join-Path $ProjectRoot "infrastructure"
$script:EnvFile = Join-Path $ProjectRoot ".env"
$script:EnvExampleFile = Join-Path $ProjectRoot ".env.example"

# Color output functions
function Write-ColorOutput {
    param([string]$Message, [string]$Color = "White")
    
    $colorMap = @{
        "Red" = "Red"
        "Green" = "Green"
        "Yellow" = "Yellow"
        "Blue" = "Cyan"
    }
    
    Write-Host $Message -ForegroundColor $colorMap[$Color]
}

function Write-Info { param([string]$Message) Write-ColorOutput "INFO: $Message" "Blue" }
function Write-Success { param([string]$Message) Write-ColorOutput "SUCCESS: $Message" "Green" }
function Write-Warning { param([string]$Message) Write-ColorOutput "WARNING: $Message" "Yellow" }
function Write-Error { param([string]$Message) Write-ColorOutput "ERROR: $Message" "Red" }

# Show usage
function Show-Usage {
    @"
Usage: .\scripts\setup-env.ps1 [Options]

Extract Terraform infrastructure outputs to application environment variables.

Options:
    -Force              Force overwrite existing .env file without backup
    -NoBackup          Don't create backup of existing .env file
    -Verbose           Enable verbose output
    -DryRun            Show what would be done without making changes
    -Workspace         Terraform workspace to use (default: default)
    -Help              Show this help message

Examples:
    .\scripts\setup-env.ps1                    # Extract outputs to .env file
    .\scripts\setup-env.ps1 -DryRun           # Preview what would be done
    .\scripts\setup-env.ps1 -Force            # Overwrite existing .env without backup
    .\scripts\setup-env.ps1 -Workspace production  # Use production workspace

Description:
    This script connects your deployed Azure infrastructure with the Python
    application by extracting key configuration values from Terraform outputs
    and populating them in a .env file for the application to use.

Prerequisites:
    • Terraform must be installed and configured
    • Azure CLI must be logged in with appropriate permissions
    • Infrastructure must be deployed using the included Terraform configuration

"@
}

# Check prerequisites
function Test-Prerequisites {
    Write-Info "Checking prerequisites..."
    $errors = @()

    # Check if we're in the right directory
    if (-not (Test-Path (Join-Path $script:ProjectRoot "src\main.py"))) {
        $errors += "Not in project root directory. Expected to find src\main.py"
    }

    # Check if Terraform is installed
    try {
        $null = Get-Command terraform -ErrorAction Stop
    }
    catch {
        $errors += "Terraform is not installed or not in PATH"
    }

    # Check if Azure CLI is installed
    try {
        $null = Get-Command az -ErrorAction Stop
    }
    catch {
        $errors += "Azure CLI is not installed or not in PATH"
    }

    # Check if infrastructure directory exists
    if (-not (Test-Path $script:InfrastructureDir)) {
        $errors += "Infrastructure directory not found: $script:InfrastructureDir"
    }

    # Check if Terraform has been initialized
    if (-not (Test-Path (Join-Path $script:InfrastructureDir ".terraform"))) {
        $errors += "Terraform not initialized. Run Terraform deployment first"
    }

    # Check Azure CLI authentication
    try {
        $null = az account show --output json 2>$null
    }
    catch {
        $errors += "Azure CLI not authenticated. Run 'az login' first"
    }

    if ($errors.Count -gt 0) {
        Write-Error "Prerequisites check failed:"
        foreach ($error in $errors) {
            Write-Error "  • $error"
        }
        return $false
    }

    Write-Success "Prerequisites check passed"
    return $true
}

# Check Terraform workspace and state
function Test-TerraformState {
    Write-Info "Checking Terraform state..."

    Set-Location $script:InfrastructureDir

    try {
        # Check current workspace
        $currentWorkspace = terraform workspace show 2>$null
        if (-not $currentWorkspace) { $currentWorkspace = "default" }
        
        if ($currentWorkspace -ne $Workspace) {
            Write-Warning "Current workspace ($currentWorkspace) differs from requested ($Workspace)"
            Write-Info "Switching to workspace: $Workspace"
            
            $workspaces = terraform workspace list 2>$null
            if ($workspaces -notmatch $Workspace) {
                Write-Error "Workspace '$Workspace' does not exist"
                Write-Info "Available workspaces:"
                terraform workspace list
                return $false
            }
            
            terraform workspace select $Workspace 2>$null
            if ($LASTEXITCODE -ne 0) {
                Write-Error "Failed to switch to workspace: $Workspace"
                return $false
            }
        }

        # Check if state exists and has resources
        $stateList = terraform state list 2>$null
        $resourceCount = ($stateList | Measure-Object).Count
        
        if ($resourceCount -eq 0) {
            Write-Error "No Terraform resources found in state"
            Write-Error "Please deploy infrastructure first using: .\scripts\deploy.ps1"
            return $false
        }

        Write-Success "Found $resourceCount resources in Terraform state"
        
        if ($Verbose) {
            Write-Info "Terraform state resources:"
            $stateList | Select-Object -First 10 | ForEach-Object { Write-Info "  $_" }
            if ($resourceCount -gt 10) {
                Write-Info "  ... and $($resourceCount - 10) more resources"
            }
        }

        return $true
    }
    catch {
        Write-Error "Failed to check Terraform state: $_"
        return $false
    }
    finally {
        Set-Location $script:ProjectRoot
    }
}

# Extract Terraform outputs
function Get-TerraformOutputs {
    Write-Info "Extracting Terraform outputs..."

    Set-Location $script:InfrastructureDir

    try {
        # Get the environment variables output
        $outputsJson = terraform output -json environment_variables 2>$null
        
        if ($LASTEXITCODE -ne 0 -or -not $outputsJson) {
            Write-Error "Failed to get environment_variables output from Terraform"
            Write-Error "This output should be defined in infrastructure\outputs.tf"
            return $null
        }

        # Parse and validate the outputs
        $outputs = $outputsJson | ConvertFrom-Json
        if (-not $outputs) {
            Write-Error "Environment variables output is empty or null"
            return $null
        }

        if ($Verbose) {
            Write-Info "Extracted Terraform outputs:"
            $outputs | ConvertTo-Json -Depth 3
        }

        Write-Success "Successfully extracted Terraform outputs"
        return $outputs
    }
    catch {
        Write-Error "Failed to extract Terraform outputs: $_"
        return $null
    }
    finally {
        Set-Location $script:ProjectRoot
    }
}

# Backup existing .env file
function Backup-EnvFile {
    if (Test-Path $script:EnvFile) {
        if (-not $NoBackup) {
            $backupFile = "$($script:EnvFile).backup.$(Get-Date -Format 'yyyyMMdd_HHmmss')"
            Write-Info "Backing up existing .env file to: $backupFile"
            
            if (-not $DryRun) {
                Copy-Item $script:EnvFile $backupFile
                Write-Success "Backup created: $backupFile"
            }
            else {
                Write-Info "[DRY RUN] Would create backup: $backupFile"
            }
        }
    }
}

# Generate .env file content
function New-EnvContent {
    param($TerraformOutputs)
    
    $timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    
    $content = @"
# Azure OpenAI CLI Chatbot Configuration
# Generated automatically by $script:ScriptName on $timestamp
# Terraform workspace: $Workspace
#
# DO NOT EDIT MANUALLY - This file is auto-generated from Terraform outputs
# To regenerate, run: .\scripts\setup-env.ps1

# =============================================================================
# AZURE OPENAI CONFIGURATION
# =============================================================================

# Azure OpenAI Service Endpoint
AZURE_OPENAI_ENDPOINT=$($TerraformOutputs.AZURE_OPENAI_ENDPOINT)

# Azure OpenAI Deployment Name (GPT-4 model deployment)
AZURE_OPENAI_DEPLOYMENT=$($TerraformOutputs.AZURE_OPENAI_DEPLOYMENT)

# Azure OpenAI API Version
AZURE_OPENAI_API_VERSION=$($TerraformOutputs.AZURE_OPENAI_API_VERSION)

# =============================================================================
# AZURE AUTHENTICATION CONFIGURATION
# =============================================================================

# Azure Managed Identity Client ID
AZURE_CLIENT_ID=$($TerraformOutputs.AZURE_CLIENT_ID)

# Azure Key Vault URL for secure credential storage
KEY_VAULT_URL=$($TerraformOutputs.KEY_VAULT_URL)

# =============================================================================
# APPLICATION INSIGHTS CONFIGURATION
# =============================================================================

# Application Insights connection string for application/infrastructure telemetry
APPLICATIONINSIGHTS_CONNECTION_STRING=$($TerraformOutputs.APPLICATIONINSIGHTS_CONNECTION_STRING)

# Chat Observability connection string for conversation/user experience telemetry
# Note: If not set, will fallback to APPLICATIONINSIGHTS_CONNECTION_STRING
CHAT_OBSERVABILITY_CONNECTION_STRING=$($TerraformOutputs.CHAT_OBSERVABILITY_CONNECTION_STRING)

# Enable dual observability (separate workspaces for app vs chat logs)
ENABLE_CHAT_OBSERVABILITY=$($TerraformOutputs.ENABLE_CHAT_OBSERVABILITY)

# Enable cross-correlation between application and chat observability systems
ENABLE_CROSS_CORRELATION=$($TerraformOutputs.ENABLE_CROSS_CORRELATION)

# =============================================================================
# APPLICATION CONFIGURATION
# =============================================================================

# Environment (dev, staging, prod)
ENVIRONMENT=$($TerraformOutputs.ENVIRONMENT)

# Application name
APP_NAME=$($TerraformOutputs.APP_NAME)

# Azure region
AZURE_LOCATION=$($TerraformOutputs.AZURE_LOCATION)

# Log level
LOG_LEVEL=$($TerraformOutputs.LOG_LEVEL)

# =============================================================================
# STORAGE CONFIGURATION
# =============================================================================

# Azure Storage Account for conversation history
AZURE_STORAGE_ACCOUNT_NAME=$($TerraformOutputs.AZURE_STORAGE_ACCOUNT_NAME)

# Storage container for conversations
CONVERSATIONS_CONTAINER=$($TerraformOutputs.CONVERSATIONS_CONTAINER)

# =============================================================================
# FEATURE FLAGS
# =============================================================================

# Enable conversation history storage
ENABLE_CONVERSATION_HISTORY=$($TerraformOutputs.ENABLE_CONVERSATION_HISTORY)

# Enable structured JSON logging
ENABLE_STRUCTURED_LOGGING=$($TerraformOutputs.ENABLE_STRUCTURED_LOGGING)

# Enable performance metrics collection
ENABLE_METRICS_COLLECTION=$($TerraformOutputs.ENABLE_METRICS_COLLECTION)

# =============================================================================
# OPENAI MODEL CONFIGURATION
# =============================================================================

# Maximum tokens per response
AZURE_OPENAI_MAX_TOKENS=$($TerraformOutputs.OPENAI_MAX_TOKENS)

# Model temperature (creativity level)
AZURE_OPENAI_TEMPERATURE=$($TerraformOutputs.OPENAI_TEMPERATURE)

# Maximum conversation history turns
MAX_CONVERSATION_TURNS=$($TerraformOutputs.CONVERSATION_MAX_HISTORY)

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
CHATBOT_LOG_LEVEL=$($TerraformOutputs.LOG_LEVEL)

# Development mode (set to False for production)
DEBUG=$(if ($TerraformOutputs.ENVIRONMENT -eq "dev") { "True" } else { "False" })

"@

    return $content
}

# Validate generated configuration
function Test-EnvContent {
    param([string]$Content)
    
    Write-Info "Validating generated configuration..."
    $errors = @()

    # Check for null or empty values in critical settings
    $criticalVars = @("AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_DEPLOYMENT", "KEY_VAULT_URL", "AZURE_CLIENT_ID")
    
    foreach ($var in $criticalVars) {
        $pattern = "^${var}=(.+)$"
        $match = [regex]::Match($Content, $pattern, [System.Text.RegularExpressions.RegexOptions]::Multiline)
        
        if (-not $match.Success -or -not $match.Groups[1].Value -or $match.Groups[1].Value -eq "null") {
            $errors += "Critical variable $var is empty or null"
        }
    }

    # Validate URL formats
    $endpointMatch = [regex]::Match($Content, "^AZURE_OPENAI_ENDPOINT=(.+)$", [System.Text.RegularExpressions.RegexOptions]::Multiline)
    if ($endpointMatch.Success -and $endpointMatch.Groups[1].Value) {
        $endpoint = $endpointMatch.Groups[1].Value.Trim()
        if (-not $endpoint.StartsWith("https://")) {
            $errors += "AZURE_OPENAI_ENDPOINT should start with https://"
        }
    }

    $kvMatch = [regex]::Match($Content, "^KEY_VAULT_URL=(.+)$", [System.Text.RegularExpressions.RegexOptions]::Multiline)
    if ($kvMatch.Success -and $kvMatch.Groups[1].Value) {
        $kvUrl = $kvMatch.Groups[1].Value.Trim()
        if ($kvUrl -notmatch "^https://.*\.vault\.azure\.net/?$") {
            $errors += "KEY_VAULT_URL should be a valid Azure Key Vault URL"
        }
    }

    if ($errors.Count -gt 0) {
        Write-Error "Configuration validation failed:"
        foreach ($errorMsg in $errors) {
            Write-Error "  • $errorMsg"
        }
        return $false
    }

    Write-Success "Configuration validation passed"
    return $true
}

# Write .env file
function Set-EnvFile {
    param($TerraformOutputs)
    
    Write-Info "Generating .env file..."

    # Generate the content
    $envContent = New-EnvContent -TerraformOutputs $TerraformOutputs

    # Validate the content
    if (-not (Test-EnvContent -Content $envContent)) {
        return $false
    }

    # Show preview in dry run mode
    if ($DryRun) {
        Write-Info "[DRY RUN] Would write .env file with the following content:"
        Write-Host "----------------------------------------"
        ($envContent -split "`n")[0..29] | ForEach-Object { Write-Host $_ }
        Write-Host "... (truncated for brevity)"
        Write-Host "----------------------------------------"
        return $true
    }

    # Check if file exists and handle accordingly
    if ((Test-Path $script:EnvFile) -and -not $Force) {
        Write-Warning "Existing .env file found: $script:EnvFile"
        $response = Read-Host "Do you want to overwrite it? [y/N]"
        
        if ($response -notmatch "^[Yy]$") {
            Write-Info "Operation cancelled by user"
            return $false
        }
    }

    # Backup existing file
    Backup-EnvFile

    # Write the new file
    try {
        $envContent | Out-File -FilePath $script:EnvFile -Encoding UTF8
        Write-Success "Successfully created .env file: $script:EnvFile"

        # Show summary
        $lineCount = ($envContent -split "`n").Count
        Write-Info "Configuration file contains $lineCount lines"

        if ($Verbose) {
            Write-Info "Key configuration values:"
            Select-String -Path $script:EnvFile -Pattern "^(AZURE_OPENAI_ENDPOINT|AZURE_OPENAI_DEPLOYMENT|KEY_VAULT_URL|ENVIRONMENT)=" | ForEach-Object { Write-Info "  $($_.Line)" }
        }

        return $true
    }
    catch {
        Write-Error "Failed to write .env file: $_"
        return $false
    }
}

# Test configuration
function Test-Configuration {
    if ($DryRun) {
        Write-Info "[DRY RUN] Would test configuration by running health check"
        return
    }

    Write-Info "Testing application configuration..."

    # Check if virtual environment exists
    $venvPath = Join-Path $script:ProjectRoot "venv"
    if (Test-Path $venvPath) {
        Write-Info "Virtual environment found: venv"
    }
    else {
        Write-Warning "Virtual environment not found. You may need to create it first."
    }

    # Try to run the health check (basic test)
    try {
        $pythonCmd = if (Test-Path $venvPath) { Join-Path $venvPath "Scripts\python.exe" } else { "python" }
        $healthCheck = & $pythonCmd (Join-Path $script:ProjectRoot "src\main.py") health --output-format json 2>$null
        
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Application health check passed"
            
            if ($Verbose) {
                Write-Info "Running detailed health check:"
                & $pythonCmd (Join-Path $script:ProjectRoot "src\main.py") health --output-format table
            }
        }
        else {
            Write-Warning "Application health check failed"
            Write-Info "This may be normal if Azure resources are not fully ready or dependencies aren't installed"
            Write-Info "Try running: python src\main.py health"
        }
    }
    catch {
        Write-Warning "Could not test application (likely missing dependencies)"
        Write-Info "Install dependencies with: pip install -r requirements.txt"
    }
}

# Show next steps
function Show-NextSteps {
    Write-Success "Environment setup completed successfully!"
    
    @"

NEXT STEPS:

1. Review the generated configuration:
   Get-Content .env

2. Install Python dependencies:
   . venv\Scripts\activate
   pip install -r requirements.txt

3. Test the application:
   python src\main.py health

4. Start chatting with the AI:
   python src\main.py chat

5. For more commands:
   python src\main.py --help

IMPORTANT FILES:
   • .env                 - Application configuration (auto-generated)
   • .env.example         - Configuration template and documentation
   • src\main.py          - Main CLI application
   • infrastructure\      - Terraform infrastructure code

CONFIGURATION MANAGEMENT:
   • To update configuration: .\scripts\setup-env.ps1
   • To redeploy infrastructure: .\scripts\deploy.ps1
   • To destroy infrastructure: .\scripts\destroy.ps1

DOCUMENTATION:
   • See README.md for detailed setup and usage instructions
   • Check logs\ directory for application logs
   • Use 'python src\main.py --help' for CLI help

"@

    $todaysBackup = Get-ChildItem -Path "$($script:EnvFile).backup.$(Get-Date -Format 'yyyyMMdd')*" -ErrorAction SilentlyContinue
    if ($todaysBackup) {
        Write-Info "💾 Backup of previous .env file created"
    }
}

# Main function
function Start-EnvironmentSetup {
    $startTime = Get-Date
    
    Write-Info "🚀 Azure OpenAI CLI Chatbot - Environment Setup"
    Write-Info "Extracting infrastructure configuration from Terraform..."
    Write-Host

    try {
        # Check prerequisites
        if (-not (Test-Prerequisites)) {
            throw "Prerequisites check failed"
        }

        # Check Terraform state
        if (-not (Test-TerraformState)) {
            throw "Terraform state check failed"
        }

        # Extract Terraform outputs
        $terraformOutputs = Get-TerraformOutputs
        if (-not $terraformOutputs) {
            throw "Failed to extract Terraform outputs"
        }

        # Write .env file
        if (-not (Set-EnvFile -TerraformOutputs $terraformOutputs)) {
            throw "Failed to create .env file"
        }

        # Test configuration
        Test-Configuration

        # Show next steps
        Show-NextSteps

        $duration = (Get-Date) - $startTime
        Write-Host
        Write-Success "✅ Environment setup completed in $($duration.ToString('hh\:mm\:ss'))"
    }
    catch {
        Write-Error "Environment setup failed: $_"
        exit 1
    }
}

# Main script execution
if ($Help) {
    Show-Usage
    exit 0
}

Start-EnvironmentSetup