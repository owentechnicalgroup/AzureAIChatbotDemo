# Bootstrap script to set up Terraform backend storage
# This should be run once before the main deployment

param(
    [string]$Environment = "dev",
    [string]$Location = "East US"
)

$ErrorActionPreference = "Stop"

# Paths
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$BootstrapDir = Join-Path $ProjectRoot "infrastructure\bootstrap"
$MainInfraDir = Join-Path $ProjectRoot "infrastructure"

Write-Host "🚀 Setting up Terraform backend storage..." -ForegroundColor Cyan

# Check prerequisites
Write-Host "Checking prerequisites..." -ForegroundColor Blue
if (-not (Get-Command terraform -ErrorAction SilentlyContinue)) {
    throw "Terraform not found. Please install Terraform."
}

if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
    throw "Azure CLI not found. Please install Azure CLI."
}

# Check Azure authentication
$accountInfo = az account show --output json 2>$null | ConvertFrom-Json
if (-not $accountInfo) {
    throw "Not authenticated to Azure. Please run 'az login'."
}

Write-Host "✅ Authenticated as: $($accountInfo.user.name)" -ForegroundColor Green

# Change to bootstrap directory
Set-Location $BootstrapDir

try {
    Write-Host "Initializing bootstrap Terraform..." -ForegroundColor Blue
    terraform init
    
    if ($LASTEXITCODE -ne 0) {
        throw "Bootstrap terraform init failed"
    }
    
    Write-Host "Planning bootstrap infrastructure..." -ForegroundColor Blue
    terraform plan -var="environment=$Environment" -var="location=$Location" -out="bootstrap.tfplan"
    
    if ($LASTEXITCODE -ne 0) {
        throw "Bootstrap terraform plan failed"
    }
    
    Write-Host "Applying bootstrap infrastructure..." -ForegroundColor Blue
    terraform apply "bootstrap.tfplan"
    
    if ($LASTEXITCODE -ne 0) {
        throw "Bootstrap terraform apply failed"
    }
    
    # Get outputs
    Write-Host "Getting backend configuration..." -ForegroundColor Blue
    $backendConfig = terraform output -json backend_config | ConvertFrom-Json
    
    Write-Host "✅ Backend storage created successfully!" -ForegroundColor Green
    Write-Host "  Resource Group: $($backendConfig.resource_group_name)" -ForegroundColor White
    Write-Host "  Storage Account: $($backendConfig.storage_account_name)" -ForegroundColor White
    Write-Host "  Container: $($backendConfig.container_name)" -ForegroundColor White
    
    # Update main providers.tf
    Write-Host "Updating main infrastructure backend configuration..." -ForegroundColor Blue
    $providersFile = Join-Path $MainInfraDir "providers.tf"
    $content = Get-Content $providersFile -Raw
    
    $updatedContent = $content -replace 'resource_group_name\s*=\s*"[^"]*"', "resource_group_name  = `"$($backendConfig.resource_group_name)`""
    $updatedContent = $updatedContent -replace 'storage_account_name\s*=\s*"[^"]*"', "storage_account_name = `"$($backendConfig.storage_account_name)`""
    $updatedContent = $updatedContent -replace 'container_name\s*=\s*"[^"]*"', "container_name       = `"$($backendConfig.container_name)`""
    
    Set-Content -Path $providersFile -Value $updatedContent
    Write-Host "✅ Updated main providers.tf with backend configuration" -ForegroundColor Green
    
    Write-Host ""
    Write-Host "🎉 Bootstrap completed successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Yellow
    Write-Host "1. Run: .\scripts\deploy.ps1 -ForceReinit" -ForegroundColor White
    Write-Host "2. This will initialize the main infrastructure with remote state" -ForegroundColor White
    
} finally {
    Set-Location $ProjectRoot
}
