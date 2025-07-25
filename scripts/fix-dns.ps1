#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Fixes corporate DNS settings that may persist after disconnecting from corporate networks.

.DESCRIPTION
    This script detects corporate DNS servers on all network interfaces and replaces them
    with public DNS servers (Google DNS by default). It helps resolve SSL handshake failures
    during Python package installation when corporate DNS servers are unreachable.

.PARAMETER DnsServers
    Array of DNS servers to use. Defaults to Google DNS (8.8.8.8, 8.8.4.4).

.PARAMETER CorporatePatterns
    Array of IP patterns that identify corporate DNS servers. Defaults to common private IP ranges.

.PARAMETER Force
    Skip confirmation prompts and apply changes immediately.

.PARAMETER WhatIf
    Show what would be changed without actually making changes.

.EXAMPLE
    .\fix-dns.ps1
    # Interactive mode - shows detected issues and asks for confirmation

.EXAMPLE
    .\fix-dns.ps1 -Force
    # Automatically fixes all detected corporate DNS settings

.EXAMPLE
    .\fix-dns.ps1 -DnsServers @("1.1.1.1", "1.0.0.1") -Force
    # Uses Cloudflare DNS instead of Google DNS

.EXAMPLE
    .\fix-dns.ps1 -WhatIf
    # Shows what would be changed without making changes

.NOTES
    Author: GitHub Copilot
    Version: 1.0
    
    This script requires administrator privileges to modify DNS settings.
    Run from an elevated PowerShell session.
#>

[CmdletBinding(SupportsShouldProcess)]
param(
    [string[]]$DnsServers = @("8.8.8.8", "8.8.4.4"),
    [string[]]$CorporatePatterns = @(
        "172.16.*",      # RFC 1918 - Private networks
        "10.*",          # RFC 1918 - Private networks  
        "192.168.*",     # RFC 1918 - Private networks
        "169.254.*",     # RFC 3927 - Link-local
        "*.local"        # mDNS/Bonjour
    ),
    [switch]$Force
)

# Set error action preference
$ErrorActionPreference = "Stop"

# Check if running as administrator
function Test-Administrator {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

# Check if an IP matches corporate patterns
function Test-CorporateIP {
    param([string]$IP)
    
    foreach ($pattern in $CorporatePatterns) {
        if ($IP -like $pattern) {
            return $true
        }
    }
    return $false
}

# Get network interfaces with DNS settings
function Get-NetworkInterfacesWithDNS {
    $interfaces = @()
    
    Get-NetConnectionProfile | ForEach-Object {
        $netProfile = $_
        $dnsServers = Get-DnsClientServerAddress -InterfaceIndex $netProfile.InterfaceIndex | 
            Where-Object { $_.AddressFamily -eq 2 -and $_.ServerAddresses.Count -gt 0 } |
            Select-Object -ExpandProperty ServerAddresses
        
        if ($dnsServers) {
            $interfaces += [PSCustomObject]@{
                ProfileName = $netProfile.Name
                InterfaceAlias = $netProfile.InterfaceAlias
                InterfaceIndex = $netProfile.InterfaceIndex
                NetworkCategory = $netProfile.NetworkCategory
                DnsServers = $dnsServers
                HasCorporateDNS = ($dnsServers | Where-Object { Test-CorporateIP $_ }).Count -gt 0
            }
        }
    }
    
    return $interfaces
}

# Main execution
try {
    Write-Host "🔍 Corporate DNS Fixer v1.0" -ForegroundColor Cyan
    Write-Host "================================" -ForegroundColor Cyan
    
    # Check administrator privileges
    if (-not (Test-Administrator)) {
        Write-Warning "⚠️  This script requires administrator privileges to modify DNS settings."
        Write-Warning "Please run from an elevated PowerShell session."
        exit 1
    }
    
    Write-Host "✅ Running with administrator privileges" -ForegroundColor Green
    
    # Get network interfaces
    Write-Host "`n🔍 Scanning network interfaces..." -ForegroundColor Yellow
    $interfaces = Get-NetworkInterfacesWithDNS
    
    if ($interfaces.Count -eq 0) {
        Write-Host "ℹ️  No network interfaces with DNS settings found." -ForegroundColor Blue
        exit 0
    }
    
    # Display current DNS settings
    Write-Host "`n📋 Current DNS Configuration:" -ForegroundColor Yellow
    Write-Host ("=" * 80) -ForegroundColor Gray
    
    $corporateInterfaces = @()
    foreach ($interface in $interfaces) {
        $status = if ($interface.HasCorporateDNS) { "🔴 CORPORATE" } else { "✅ OK" }
        Write-Host "Interface: $($interface.InterfaceAlias) ($($interface.ProfileName))" -ForegroundColor White
        Write-Host "  Status: $status" -ForegroundColor $(if ($interface.HasCorporateDNS) { "Red" } else { "Green" })
        Write-Host "  DNS Servers: $($interface.DnsServers -join ', ')" -ForegroundColor Gray
        Write-Host ""
        
        if ($interface.HasCorporateDNS) {
            $corporateInterfaces += $interface
        }
    }
    
    # Check if any corporate DNS found
    if ($corporateInterfaces.Count -eq 0) {
        Write-Host "✅ No corporate DNS servers detected. All interfaces look good!" -ForegroundColor Green
        exit 0
    }
    
    # Show what will be changed
    Write-Host "🛠️  Detected Issues:" -ForegroundColor Red
    Write-Host ("=" * 80) -ForegroundColor Gray
    
    foreach ($interface in $corporateInterfaces) {
        $corporateDns = $interface.DnsServers | Where-Object { Test-CorporateIP $_ }
        Write-Host "❌ $($interface.InterfaceAlias): Corporate DNS detected" -ForegroundColor Red
        Write-Host "   Current: $($interface.DnsServers -join ', ')" -ForegroundColor Gray
        Write-Host "   Corporate IPs: $($corporateDns -join ', ')" -ForegroundColor Red
        Write-Host "   Will change to: $($DnsServers -join ', ')" -ForegroundColor Green
        Write-Host ""
    }
    
    # Confirm changes (unless -Force or -WhatIf)
    if ($WhatIfPreference) {
        Write-Host "🔍 WhatIf: Would fix $($corporateInterfaces.Count) interface(s) with corporate DNS" -ForegroundColor Blue
        exit 0
    }
    
    if (-not $Force) {
        $response = Read-Host "`n❓ Do you want to fix these DNS settings? (y/N)"
        if ($response -notmatch "^[Yy]") {
            Write-Host "❌ Operation cancelled by user." -ForegroundColor Yellow
            exit 0
        }
    }
    
    # Apply DNS changes
    Write-Host "`n🔧 Applying DNS fixes..." -ForegroundColor Yellow
    
    $successCount = 0
    $errorCount = 0
    
    foreach ($interface in $corporateInterfaces) {
        try {
            Write-Host "🔄 Fixing $($interface.InterfaceAlias)..." -ForegroundColor Yellow
            
            if ($PSCmdlet.ShouldProcess($interface.InterfaceAlias, "Set DNS servers to $($DnsServers -join ', ')")) {
                Set-DnsClientServerAddress -InterfaceAlias $interface.InterfaceAlias -ServerAddresses $DnsServers -ErrorAction Stop
                Write-Host "   ✅ Successfully updated $($interface.InterfaceAlias)" -ForegroundColor Green
                $successCount++
            }
        }
        catch {
            Write-Error "   ❌ Failed to update $($interface.InterfaceAlias): $($_.Exception.Message)"
            $errorCount++
        }
    }
    
    # Flush DNS cache
    if ($successCount -gt 0) {
        Write-Host "`n🧹 Flushing DNS cache..." -ForegroundColor Yellow
        try {
            $result = ipconfig /flushdns 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Host "✅ DNS cache flushed successfully" -ForegroundColor Green
            } else {
                Write-Warning "⚠️  Failed to flush DNS cache: $result"
            }
        }
        catch {
            Write-Warning "⚠️  Failed to flush DNS cache: $($_.Exception.Message)"
        }
    }
    
    # Test DNS resolution
    Write-Host "`n🧪 Testing DNS resolution..." -ForegroundColor Yellow
    try {
        $result = Resolve-DnsName "pypi.org" -Type A -ErrorAction Stop | Select-Object -First 1
        Write-Host "✅ DNS resolution test passed (pypi.org → $($result.IPAddress))" -ForegroundColor Green
    }
    catch {
        Write-Warning "⚠️  DNS resolution test failed: $($_.Exception.Message)"
    }
    
    # Summary
    Write-Host "`n📊 Summary:" -ForegroundColor Cyan
    Write-Host ("=" * 80) -ForegroundColor Gray
    Write-Host "✅ Successfully fixed: $successCount interface(s)" -ForegroundColor Green
    if ($errorCount -gt 0) {
        Write-Host "❌ Failed to fix: $errorCount interface(s)" -ForegroundColor Red
    }
    
    if ($successCount -gt 0) {
        Write-Host "`n🎉 DNS configuration has been updated!" -ForegroundColor Green
        Write-Host "You can now try installing Python packages:" -ForegroundColor White
        Write-Host "   pip install -r requirements.txt" -ForegroundColor Gray
    }
    
    exit $(if ($errorCount -gt 0) { 1 } else { 0 })
}
catch {
    Write-Error "💥 Unexpected error: $($_.Exception.Message)"
    Write-Host "Stack trace:" -ForegroundColor Red
    Write-Host $_.ScriptStackTrace -ForegroundColor Red
    exit 1
}
