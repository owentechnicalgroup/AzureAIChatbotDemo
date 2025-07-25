# Azure OpenAI CLI Chatbot - PowerShell Deployment Script
# Converted from bash version for Windows PowerShell/VS Code compatibility

param(
    [string]$Environment = "dev",
    [string]$Location = "East US",
    [switch]$ForceReinit,
    [switch]$PlanOnly,
    [switch]$SetupBackendOnly,
    [switch]$Help
)

# Script configuration
$script:ScriptName = "deploy.ps1"
$script:ProjectRoot = Split-Path -Parent $PSScriptRoot
$script:InfrastructureDir = Join-Path $ProjectRoot "infrastructure"
$script:LogFile = Join-Path $ProjectRoot "logs\deployment-$(Get-Date -Format 'yyyyMMdd-HHmmss').log"

# Create logs directory if it doesn't exist
$LogsDir = Join-Path $ProjectRoot "logs"
if (-not (Test-Path $LogsDir)) {
    New-Item -ItemType Directory -Path $LogsDir -Force | Out-Null
}

# Color functions
function Write-ColorOutput {
    param([string]$Message, [string]$Color = "White")
    
    $colorMap = @{
        "Red" = "Red"
        "Green" = "Green" 
        "Yellow" = "Yellow"
        "Blue" = "Cyan"
        "White" = "White"
    }
    
    Write-Host $Message -ForegroundColor $colorMap[$Color]
    Add-Content -Path $script:LogFile -Value "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $Message"
}

function Write-Info { param([string]$Message) Write-ColorOutput "ℹ️  $Message" "Blue" }
function Write-Success { param([string]$Message) Write-ColorOutput "✅ $Message" "Green" }
function Write-Warning { param([string]$Message) Write-ColorOutput "⚠️  $Message" "Yellow" }
function Write-Error { param([string]$Message) Write-ColorOutput "❌ $Message" "Red" }

# Show usage information
function Show-Usage {
    @"
Usage: .\scripts\deploy.ps1 [Environment] [Location] [Options]

Arguments:
    Environment    Deployment environment (dev/staging/prod) [default: dev]
    Location       Azure region [default: "East US"]

Options:
    -ForceReinit         Force Terraform reinitialization
    -PlanOnly           Only run terraform plan, don't apply
    -SetupBackendOnly   Only validate backend storage configuration
    -Help              Show this help message

Examples:
    .\scripts\deploy.ps1 dev "East US"
    .\scripts\deploy.ps1 prod "West Europe" -ForceReinit
    .\scripts\deploy.ps1 staging -PlanOnly

Environment Variables:
    `$env:AZURE_SUBSCRIPTION_ID    Override Azure subscription
    `$env:AZURE_TENANT_ID         Override Azure tenant
    
Prerequisites:
    - Azure CLI installed and logged in (az login)
    - Terraform installed (>= 1.0)
    - Backend storage initialized (run .\scripts\bootstrap.ps1 first)
    - Appropriate Azure permissions for resource creation

IMPORTANT: If this is your first deployment, run the bootstrap script first:
    .\scripts\bootstrap.ps1 -Environment dev -Location "East US"
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
        Write-Success "Terraform is available"
    }
    catch {
        $errors += "Terraform is not installed or not in PATH"
    }

    # Check if Azure CLI is installed
    try {
        $null = Get-Command az -ErrorAction Stop
        Write-Success "Azure CLI is available"
    }
    catch {
        $errors += "Azure CLI is not installed or not in PATH"
    }

    # Check if infrastructure directory exists
    if (-not (Test-Path $script:InfrastructureDir)) {
        $errors += "Infrastructure directory not found: $script:InfrastructureDir"
    }

    # Check Azure CLI authentication
    try {
        $accountInfo = az account show --output json 2>$null | ConvertFrom-Json
        if ($accountInfo) {
            Write-Success "Azure CLI is authenticated as: $($accountInfo.user.name)"
            Write-Info "Using subscription: $($accountInfo.name) ($($accountInfo.id))"
        }
        else {
            $errors += "Azure CLI not authenticated. Run 'az login' first"
        }
    }
    catch {
        $errors += "Azure CLI not authenticated. Run 'az login' first"
    }

    if ($errors.Count -gt 0) {
        Write-Error "Prerequisites check failed:"
        foreach ($err in $errors) {
            Write-Error "  • $err"
        }
        return $false
    }

    Write-Success "Prerequisites check passed"
    return $true
}

# Set up backend storage account
function Set-BackendStorage {
    param([string]$Environment, [string]$Location)
    
    Write-Info "Validating Terraform backend configuration..."
    
    # Check if providers.tf has proper backend configuration
    $providersFile = Join-Path $script:InfrastructureDir "providers.tf"
    $content = Get-Content $providersFile -Raw
    
    # Extract storage account name from providers.tf
    if ($content -match 'storage_account_name\s*=\s*"([^"]*)"') {
        $storageAccountName = $matches[1]
        
        if ($storageAccountName -eq "tfstateXXXXX" -or $storageAccountName -eq "") {
            Write-Warning "Backend storage not configured properly."
            Write-Warning "Please run the bootstrap script first:"
            Write-Warning "  .\scripts\bootstrap.ps1 -Environment $Environment -Location '$Location'"
            throw "Backend storage not initialized"
        }
        
        Write-Success "Backend storage account: $storageAccountName"
        
        # Try to validate the storage account exists and is accessible
        Write-Info "Validating storage account accessibility..."
        $resourceGroupName = "tfstate-rg-$Environment"
        
        # Test access by trying to list containers
        az storage container list --account-name $storageAccountName --auth-mode login --output table 2>$null | Out-Null
        
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Storage account is accessible"
        } else {
            Write-Warning "Storage account exists but may not be accessible."
            Write-Info "The bootstrap script should have granted permissions."
            Write-Info "If this persists, check your Azure permissions."
        }
        
        return @{
            ResourceGroupName = $resourceGroupName
            StorageAccountName = $storageAccountName
            ContainerName = "tfstate"
        }
    } else {
        throw "Could not find storage account configuration in providers.tf"
    }
}

# Initialize Terraform
function Initialize-Terraform {
    param([bool]$ForceReinit = $false)
    
    Write-Info "Initializing Terraform..."
    
    Set-Location $script:InfrastructureDir
    
    try {
        if ($ForceReinit -and (Test-Path ".terraform")) {
            Write-Warning "Removing existing .terraform directory for reinit"
            Remove-Item ".terraform" -Recurse -Force
        }
        
        Write-Info "Running terraform init..."
        terraform init -upgrade
        
        if ($LASTEXITCODE -ne 0) {
            throw "Terraform init failed"
        }
        
        Write-Success "Terraform initialization completed"
    }
    catch {
        Write-Error "Terraform initialization failed: $_"
        throw
    }
    finally {
        Set-Location $script:ProjectRoot
    }
}

# Run Terraform plan
function Invoke-TerraformPlan {
    param([string]$Environment, [string]$Location, [hashtable]$BackendConfig)
    
    Write-Info "Running Terraform plan..."
    
    Set-Location $script:InfrastructureDir
    
    try {
        $planFile = "tfplan-$Environment-$(Get-Date -Format 'yyyyMMddHHmmss')"
        
        terraform plan `
            -var="environment=$Environment" `
            -var="location=$Location" `
            -out=$planFile `
            -detailed-exitcode
            
        $planExitCode = $LASTEXITCODE
        
        if ($planExitCode -eq 0) {
            Write-Success "No changes needed"
            return $false
        }
        elseif ($planExitCode -eq 2) {
            Write-Success "Plan completed successfully - changes detected"
            Write-Info "Plan saved to: $planFile"
            return $true
        }
        else {
            throw "Terraform plan failed with exit code: $planExitCode"
        }
    }
    catch {
        Write-Error "Terraform plan failed: $_"
        throw
    }
    finally {
        Set-Location $script:ProjectRoot
    }
}

# Run Terraform apply
function Invoke-TerraformApply {
    param([string]$PlanFile)
    
    Write-Info "Applying Terraform configuration..."
    
    Set-Location $script:InfrastructureDir
    
    try {
        if ($PlanFile) {
            terraform apply $PlanFile
        }
        else {
            terraform apply -auto-approve
        }
        
        if ($LASTEXITCODE -ne 0) {
            throw "Terraform apply failed"
        }
        
        Write-Success "Terraform apply completed successfully"
    }
    catch {
        Write-Error "Terraform apply failed: $_"
        throw
    }
    finally {
        Set-Location $script:ProjectRoot
    }
}

# Show deployment summary
function Show-DeploymentSummary {
    param([string]$Environment, [string]$Location)
    
    Write-Success "🎉 Deployment completed successfully!"
    
    @"

📊 Deployment Summary:
   • Environment: $Environment
   • Location: $Location
   • Terraform Workspace: $(terraform workspace show 2>$null)
   • Deployment Time: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')

🔗 Next Steps:

1. Set up application environment:
   .\scripts\setup-env.ps1

2. Install Python dependencies:
   . venv\Scripts\activate
   pip install -r requirements.txt

3. Test the application:
   python src\main.py health

4. Start chatting:
   python src\main.py chat

📁 Important Files:
   • Deployment log: $script:LogFile
   • Infrastructure code: infrastructure\
   • Bootstrap code: infrastructure\bootstrap\
   • Application code: src\

🔧 Management Commands:
   • View outputs: terraform output (from infrastructure\ directory)
   • Update environment: .\scripts\setup-env.ps1
   • Destroy resources: .\scripts\destroy.ps1
   • Destroy backend: cd infrastructure\bootstrap && terraform destroy

"@
}

# Main deployment function
function Start-Deployment {
    param([string]$Environment, [string]$Location, [bool]$PlanOnly, [bool]$SetupBackendOnly, [bool]$ForceReinit)
    
    $startTime = Get-Date
    
    Write-Info "🚀 Azure OpenAI CLI Chatbot - PowerShell Deployment"
    Write-Info "Starting deployment for environment: $Environment"
    Write-Info "Target location: $Location"
    
    try {
        # Check prerequisites
        if (-not (Test-Prerequisites)) {
            throw "Prerequisites check failed"
        }
        
        # Set up backend storage
        $backendConfig = Set-BackendStorage -Environment $Environment -Location $Location
        
        if ($SetupBackendOnly) {
            Write-Success "Backend setup completed. Use -PlanOnly to test deployment next."
            return
        }
        
        # Initialize Terraform
        Initialize-Terraform -ForceReinit $ForceReinit
        
        # Run Terraform plan
        $hasChanges = Invoke-TerraformPlan -Environment $Environment -Location $Location -BackendConfig $backendConfig
        
        if ($PlanOnly) {
            Write-Success "Plan-only mode completed. Review the plan above."
            return
        }
        
        if ($hasChanges) {
            # Apply changes
            Invoke-TerraformApply
            
            # Show summary
            Show-DeploymentSummary -Environment $Environment -Location $Location
        }
        else {
            Write-Info "No changes to apply."
        }
        
        $duration = (Get-Date) - $startTime
        Write-Success "✅ Deployment completed in $($duration.ToString('hh\:mm\:ss'))"
        
    }
    catch {
        Write-Error "❌ Deployment failed: $_"
        Write-Error "Check the log file for details: $script:LogFile"
        
        $duration = (Get-Date) - $startTime
        Write-Error "Failed after $($duration.ToString('hh\:mm\:ss'))"
        
        exit 1
    }
}

# Main script execution
if ($Help) {
    Show-Usage
    exit 0
}

# Validate parameters
$validEnvironments = @("dev", "staging", "prod")
if ($Environment -notin $validEnvironments) {
    Write-Error "Invalid environment: $Environment. Must be one of: $($validEnvironments -join ', ')"
    Show-Usage
    exit 1
}

# Start deployment
Start-Deployment -Environment $Environment -Location $Location -PlanOnly $PlanOnly -SetupBackendOnly $SetupBackendOnly -ForceReinit $ForceReinit