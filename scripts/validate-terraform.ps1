# Terraform Configuration Validation Script (PowerShell)
# This script validates the Terraform configuration without requiring initialization

param([switch]$Help)

# Script configuration
$script:ScriptName = "validate-terraform.ps1"
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
Usage: .\scripts\validate-terraform.ps1 [Options]

Validates the Terraform configuration without requiring initialization.

Options:
    -Help              Show this help message

Description:
    This script performs comprehensive validation of the Terraform configuration
    including syntax checking, variable references, and placeholder detection.

"@
}

# Check Terraform syntax
function Test-TerraformSyntax {
    Write-Info "Checking Terraform syntax..."
    
    if (-not (Test-Path $script:InfrastructureDir)) {
        Write-Error "Infrastructure directory not found: $script:InfrastructureDir"
        return $false
    }
    
    Set-Location $script:InfrastructureDir
    
    try {
        # Check formatting
        terraform fmt -check -diff 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Terraform formatting is correct"
        }
        else {
            Write-Warning "Terraform files need formatting. Run 'terraform fmt' to fix."
        }
        
        return $true
    }
    catch {
        Write-Error "Error checking Terraform syntax: $_"
        return $false
    }
    finally {
        Set-Location $script:ProjectRoot
    }
}

# Check backend configuration
function Test-BackendConfig {
    Write-Info "Checking backend configuration..."
    
    $backendFile = Join-Path $script:InfrastructureDir "providers.tf"
    
    if (-not (Test-Path $backendFile)) {
        Write-Error "Backend configuration file not found: $backendFile"
        return $false
    }
    
    $content = Get-Content $backendFile -Raw
    if ($content -match "tfstateXXXXX") {
        Write-Error "Backend storage account name contains placeholder 'tfstateXXXXX'"
        Write-Error "Update the storage_account_name in providers.tf with a real globally unique name"
        
        # Generate suggestion
        $randomSuffix = -join ((1..8) | ForEach-Object { [char]((97..122) | Get-Random) })
        $timestamp = Get-Date -Format "yyyyMMdd"
        $suggestion = "tfstate$randomSuffix$timestamp"
        Write-Info "Example: $suggestion"
        
        return $false
    }
    else {
        Write-Success "Backend storage account name appears to be configured"
    }
    
    return $true
}

# Check variable references
function Test-VariableReferences {
    Write-Info "Checking variable references..."
    
    if (-not (Test-Path $script:InfrastructureDir)) {
        return $false
    }
    
    Set-Location $script:InfrastructureDir
    
    try {
        $undefinedVars = @()
        
        # Get all .tf files (excluding modules subdirectory)
        $tfFiles = Get-ChildItem -Path . -Filter "*.tf" | Where-Object { $_.Directory.Name -ne "modules" }
        
        # Read variables.tf to get defined variables
        $variablesFile = "variables.tf"
        $definedVars = @()
        
        if (Test-Path $variablesFile) {
            $variablesContent = Get-Content $variablesFile -Raw
            $variableMatches = [regex]::Matches($variablesContent, 'variable\s+"([^"]+)"')
            foreach ($match in $variableMatches) {
                $definedVars += $match.Groups[1].Value
            }
        }
        
        # Check each .tf file for variable references
        foreach ($file in $tfFiles) {
            $content = Get-Content $file.FullName -Raw
            $varMatches = [regex]::Matches($content, 'var\.([a-zA-Z_][a-zA-Z0-9_]*)')
            
            foreach ($match in $varMatches) {
                $varName = $match.Groups[1].Value
                if ($varName -notin $definedVars -and $varName -notin $undefinedVars) {
                    $undefinedVars += $varName
                }
            }
        }
        
        if ($undefinedVars.Count -gt 0) {
            Write-Error "Found references to undefined variables:"
            foreach ($var in ($undefinedVars | Sort-Object -Unique)) {
                Write-Error "  - var.$var"
            }
            return $false
        }
        else {
            Write-Success "All variable references appear to be defined"
        }
        
        return $true
    }
    catch {
        Write-Error "Error checking variable references: $_"
        return $false
    }
    finally {
        Set-Location $script:ProjectRoot
    }
}

# Check required files
function Test-RequiredFiles {
    Write-Info "Checking required files..."
    
    $requiredFiles = @(
        (Join-Path $script:InfrastructureDir "main.tf"),
        (Join-Path $script:InfrastructureDir "variables.tf"),
        (Join-Path $script:InfrastructureDir "outputs.tf"),
        (Join-Path $script:InfrastructureDir "providers.tf"),
        (Join-Path $script:InfrastructureDir "modules\azure-openai\main.tf"),
        (Join-Path $script:InfrastructureDir "modules\azure-openai\variables.tf"),
        (Join-Path $script:InfrastructureDir "modules\azure-openai\outputs.tf"),
        (Join-Path $script:InfrastructureDir "modules\azure-openai\rbac.tf")
    )
    
    $missingFiles = @()
    
    foreach ($file in $requiredFiles) {
        if (-not (Test-Path $file)) {
            $missingFiles += $file
        }
    }
    
    if ($missingFiles.Count -gt 0) {
        Write-Error "Missing required files:"
        foreach ($file in $missingFiles) {
            Write-Error "  - $file"
        }
        return $false
    }
    else {
        Write-Success "All required files are present"
    }
    
    return $true
}

# Check for placeholder values
function Test-PlaceholderValues {
    Write-Info "Checking for placeholder values..."
    
    if (-not (Test-Path $script:InfrastructureDir)) {
        return
    }
    
    Set-Location $script:InfrastructureDir
    
    try {
        $placeholderPatterns = @("XXXXX", "TODO", "CHANGEME", "admin@example.com", "your-")
        $foundPlaceholders = @()
        
        $tfFiles = Get-ChildItem -Path . -Filter "*.tf" -Recurse
        
        foreach ($pattern in $placeholderPatterns) {
            foreach ($file in $tfFiles) {
                $matches = Select-String -Path $file.FullName -Pattern $pattern -SimpleMatch
                if ($matches) {
                    $foundPlaceholders += @{
                        Pattern = $pattern
                        File = $file.FullName
                        Matches = $matches
                    }
                }
            }
        }
        
        if ($foundPlaceholders.Count -gt 0) {
            Write-Warning "Found potential placeholder values that may need updating:"
            foreach ($item in $foundPlaceholders) {
                Write-Warning "  - Pattern: $($item.Pattern)"
                $item.Matches | Select-Object -First 3 | ForEach-Object {
                    Write-Host "    $($_.Filename):$($_.LineNumber): $($_.Line.Trim())" -ForegroundColor Yellow
                }
            }
            Write-Info "Review these values and update them if needed for your deployment"
        }
        else {
            Write-Success "No obvious placeholder values found"
        }
    }
    catch {
        Write-Warning "Error checking placeholders: $_"
    }
    finally {
        Set-Location $script:ProjectRoot
    }
}

# Show deployment readiness
function Show-DeploymentReadiness {
    Write-Info "Deployment readiness summary:"
    
    @"

To deploy this infrastructure:

1. Ensure you have Azure CLI installed and logged in:
   az login

2. Deploy the infrastructure:
   .\scripts\deploy.ps1

3. Set up the application environment:
   .\scripts\setup-env.ps1

4. Test the application:
   python src\main.py health

"@
}

# Main validation function
function Start-Validation {
    Write-Info "🔍 Terraform Configuration Validation"
    Write-Host
    
    $errors = 0
    
    if (-not (Test-RequiredFiles)) { $errors++ }
    if (-not (Test-TerraformSyntax)) { $errors++ }
    if (-not (Test-BackendConfig)) { $errors++ }
    if (-not (Test-VariableReferences)) { $errors++ }
    Test-PlaceholderValues # This is just a warning, don't count as error
    
    Write-Host
    
    if ($errors -eq 0) {
        Write-Success "✅ All validation checks passed!"
        Show-DeploymentReadiness
    }
    else {
        Write-Error "❌ Found $errors validation error(s)"
        Write-Error "Please fix the errors above before proceeding with deployment"
        exit 1
    }
}

# Main script execution
if ($Help) {
    Show-Usage
    exit 0
}

Start-Validation