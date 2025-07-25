# Azure OpenAI CLI Chatbot - PowerShell Destroy Script
# Safely destroys the deployed infrastructure with confirmations

param(
    [string]$Environment = "dev",
    [string]$Location = "East US",
    [switch]$Force,
    [switch]$PlanOnly,
    [switch]$Help
)

# Script configuration
$script:ScriptName = "destroy.ps1"
$script:ProjectRoot = Split-Path -Parent $PSScriptRoot
$script:InfrastructureDir = Join-Path $ProjectRoot "infrastructure"

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

function Write-Info { param([string]$Message) Write-ColorOutput "ℹ️  $Message" "Blue" }
function Write-Success { param([string]$Message) Write-ColorOutput "✅ $Message" "Green" }
function Write-Warning { param([string]$Message) Write-ColorOutput "⚠️  $Message" "Yellow" }
function Write-Error { param([string]$Message) Write-ColorOutput "❌ $Message" "Red" }

# Show usage
function Show-Usage {
    @"
Usage: .\scripts\destroy.ps1 [Environment] [Location] [Options]

Safely destroys the deployed Azure OpenAI infrastructure.

Arguments:
    Environment    Deployment environment (dev/staging/prod) [default: dev]
    Location       Azure region [default: "East US"]

Options:
    -Force         Skip confirmation prompts (DANGEROUS)
    -PlanOnly      Only show destroy plan, don't execute
    -Help          Show this help message

Examples:
    .\scripts\destroy.ps1 dev "East US"
    .\scripts\destroy.ps1 prod -PlanOnly
    .\scripts\destroy.ps1 staging -Force

⚠️  WARNING: This will permanently delete all Azure resources!
    - Azure OpenAI service and models
    - Key Vault and all secrets
    - Storage account and conversation data
    - Log Analytics and Application Insights
    - All associated data will be lost!

"@
}

# Safety confirmation
function Confirm-Destruction {
    param([string]$Environment)
    
    if ($Force) {
        Write-Warning "⚠️  Force mode enabled - skipping confirmations!"
        return $true
    }
    
    Write-Warning "🚨 DESTRUCTIVE OPERATION WARNING 🚨"
    Write-Warning ""
    Write-Warning "This will permanently destroy the following Azure resources:"
    Write-Warning "  • Azure OpenAI service (including GPT-4 deployments)"
    Write-Warning "  • Azure Key Vault (including all secrets)"
    Write-Warning "  • Storage Account (including conversation history)"
    Write-Warning "  • Log Analytics Workspace"
    Write-Warning "  • Application Insights"
    Write-Warning "  • All monitoring and diagnostic data"
    Write-Warning ""
    Write-Warning "Environment: $Environment"
    Write-Warning "Location: $Location"
    Write-Warning ""
    Write-Error "⚠️  ALL DATA WILL BE PERMANENTLY LOST! ⚠️"
    Write-Warning ""
    
    $response1 = Read-Host "Type 'DESTROY' to confirm you want to delete all resources"
    if ($response1 -ne "DESTROY") {
        Write-Info "Operation cancelled - confirmation not received"
        return $false
    }
    
    $response2 = Read-Host "Type the environment name '$Environment' to double-confirm"
    if ($response2 -ne $Environment) {
        Write-Info "Operation cancelled - environment confirmation failed"
        return $false
    }
    
    Write-Warning "Final confirmation: Are you absolutely sure? [yes/NO]"
    $response3 = Read-Host
    if ($response3 -notmatch "^yes$") {
        Write-Info "Operation cancelled by user"
        return $false
    }
    
    Write-Warning "Proceeding with destruction in 10 seconds... Press Ctrl+C to abort!"
    Start-Sleep -Seconds 10
    
    return $true
}

# Run Terraform destroy
function Invoke-TerraformDestroy {
    param([string]$Environment, [string]$Location, [bool]$PlanOnly)
    
    if ($PlanOnly) {
        Write-Info "Running Terraform destroy plan..."
    }
    else {
        Write-Info "Executing Terraform destroy..."
    }
    
    Set-Location $script:InfrastructureDir
    
    try {
        if ($PlanOnly) {
            terraform plan -destroy `
                -var="environment=$Environment" `
                -var="location=$Location"
        }
        else {
            terraform destroy `
                -var="environment=$Environment" `
                -var="location=$Location" `
                -auto-approve
        }
        
        if ($LASTEXITCODE -ne 0) {
            throw "Terraform destroy failed with exit code: $LASTEXITCODE"
        }
        
        if ($PlanOnly) {
            Write-Success "Destroy plan completed"
        }
        else {
            Write-Success "Infrastructure destroyed successfully"
        }
    }
    catch {
        Write-Error "Terraform destroy failed: $_"
        throw
    }
    finally {
        Set-Location $script:ProjectRoot
    }
}

# Clean up local files
function Remove-LocalFiles {
    Write-Info "Cleaning up local configuration files..."
    
    $filesToRemove = @(
        (Join-Path $script:ProjectRoot ".env"),
        (Join-Path $script:ProjectRoot ".env.backup.*")
    )
    
    foreach ($pattern in $filesToRemove) {
        $files = Get-ChildItem -Path (Split-Path $pattern) -Filter (Split-Path $pattern -Leaf) -ErrorAction SilentlyContinue
        foreach ($file in $files) {
            try {
                Remove-Item $file.FullName -Force
                Write-Success "Removed: $($file.Name)"
            }
            catch {
                Write-Warning "Could not remove: $($file.Name) - $_"
            }
        }
    }
    
    # Clean Terraform state files (if any local state exists)
    $terraformDir = Join-Path $script:InfrastructureDir ".terraform"
    if (Test-Path $terraformDir) {
        Write-Warning "Terraform state directory exists locally"
        Write-Info "Note: Remote state should be preserved unless manually deleted"
    }
}

# Main destroy function
function Start-Destruction {
    param([string]$Environment, [string]$Location, [bool]$PlanOnly, [bool]$Force)
    
    $startTime = Get-Date
    
    Write-Info "🔥 Azure OpenAI CLI Chatbot - Infrastructure Destruction"
    Write-Info "Target environment: $Environment"
    Write-Info "Target location: $Location"
    Write-Host
    
    try {
        # Safety confirmations (unless plan-only)
        if (-not $PlanOnly) {
            if (-not (Confirm-Destruction -Environment $Environment)) {
                Write-Info "Destruction cancelled"
                return
            }
        }
        
        # Check prerequisites
        if (-not (Test-Path $script:InfrastructureDir)) {
            throw "Infrastructure directory not found: $script:InfrastructureDir"
        }
        
        # Check if Terraform is available
        try {
            $null = Get-Command terraform -ErrorAction Stop
        }
        catch {
            throw "Terraform is not installed or not in PATH"
        }
        
        # Run Terraform destroy
        Invoke-TerraformDestroy -Environment $Environment -Location $Location -PlanOnly $PlanOnly
        
        # Clean up local files (only if actually destroying)
        if (-not $PlanOnly) {
            Remove-LocalFiles
            
            Write-Host
            Write-Success "🎯 Destruction completed successfully!"
            Write-Host
            Write-Info "Infrastructure has been destroyed:"
            Write-Info "  ✓ All Azure resources deleted"
            Write-Info "  ✓ Local configuration files cleaned up"
            Write-Host
            Write-Warning "📝 Manual cleanup may be required for:"
            Write-Warning "  • Backend storage account (if you want to remove Terraform state)"
            Write-Warning "  • Any custom DNS records or external integrations"
            Write-Warning "  • Log data in external systems"
            Write-Host
            Write-Info "To redeploy, run: .\scripts\deploy.ps1 $Environment '$Location'"
        }
        else {
            Write-Host
            Write-Info "📋 Destroy plan completed. Review the plan above."
            Write-Info "To execute destruction, run: .\scripts\destroy.ps1 $Environment '$Location'"
        }
        
        $duration = (Get-Date) - $startTime
        Write-Success "Operation completed in $($duration.ToString('hh\:mm\:ss'))"
        
    }
    catch {
        Write-Error "❌ Destruction failed: $_"
        Write-Error "Some resources may still exist. Check the Azure portal and clean up manually if needed."
        
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

# Start destruction
Start-Destruction -Environment $Environment -Location $Location -PlanOnly $PlanOnly -Force $Force