# DNS Fix Script

## Overview

The `fix-dns.ps1` script automatically detects and fixes corporate DNS settings that persist after disconnecting from corporate networks. This is particularly useful when experiencing SSL handshake failures during Python package installation.

## The Problem

When connected to corporate networks, Windows often configures network interfaces to use corporate DNS servers (like `172.16.2.173`). These settings can persist even after disconnecting from the corporate network, causing:

- SSL handshake failures during `pip install`
- DNS resolution timeouts
- Package installation errors
- Network connectivity issues

## The Solution

This script:

1. **Detects** corporate DNS servers on all network interfaces
2. **Identifies** problematic corporate IP patterns
3. **Replaces** corporate DNS with public DNS servers (Google DNS by default)
4. **Flushes** the DNS cache to clear old entries
5. **Tests** DNS resolution to verify the fix

## Quick Usage

### Option 1: Double-click the batch file (Recommended)

```cmd
# Simply double-click fix-dns.cmd
# It will automatically request administrator privileges
```

### Option 2: Run PowerShell directly

```powershell
# Run as administrator
.\scripts\fix-dns.ps1
```

### Option 3: Force mode (no prompts)

```powershell
# Automatically fix all detected issues
.\scripts\fix-dns.ps1 -Force
```

## Command Line Options

### Basic Usage

```powershell
# Interactive mode - shows detected issues and asks for confirmation
.\fix-dns.ps1

# Automatically fix all issues without prompts
.\fix-dns.ps1 -Force

# Show what would be changed without making changes
.\fix-dns.ps1 -WhatIf
```

### Custom DNS Servers

```powershell
# Use Cloudflare DNS instead of Google DNS
.\fix-dns.ps1 -DnsServers @("1.1.1.1", "1.0.0.1") -Force

# Use OpenDNS
.\fix-dns.ps1 -DnsServers @("208.67.222.222", "208.67.220.220") -Force

# Use Quad9 DNS
.\fix-dns.ps1 -DnsServers @("9.9.9.9", "149.112.112.112") -Force
```

### Custom Corporate Patterns

```powershell
# Add custom corporate IP patterns to detect
.\fix-dns.ps1 -CorporatePatterns @("172.16.*", "10.*", "192.168.*", "203.0.113.*") -Force
```

## What the Script Detects

The script identifies corporate DNS servers by looking for these IP patterns:

- `172.16.*` - RFC 1918 Private networks (Class B)
- `10.*` - RFC 1918 Private networks (Class A)
- `192.168.*` - RFC 1918 Private networks (Class C)
- `169.254.*` - RFC 3927 Link-local addresses
- `*.local` - mDNS/Bonjour addresses

## Example Output

```
🔍 Corporate DNS Fixer v1.0
================================
✅ Running with administrator privileges

🔍 Scanning network interfaces...

📋 Current DNS Configuration:
================================================================================
Interface: Ethernet (FHLBI-BYOD)
  Status: 🔴 CORPORATE
  DNS Servers: 172.16.2.173, 172.16.2.174, 172.16.0.23

Interface: Wi-Fi (AndroidAP_4912 2)
  Status: ✅ OK
  DNS Servers: 8.8.8.8, 8.8.4.4

🛠️  Detected Issues:
================================================================================
❌ Ethernet: Corporate DNS detected
   Current: 172.16.2.173, 172.16.2.174, 172.16.0.23
   Corporate IPs: 172.16.2.173, 172.16.2.174, 172.16.0.23
   Will change to: 8.8.8.8, 8.8.4.4

❓ Do you want to fix these DNS settings? (y/N) y

🔧 Applying DNS fixes...
🔄 Fixing Ethernet...
   ✅ Successfully updated Ethernet

🧹 Flushing DNS cache...
✅ DNS cache flushed successfully

🧪 Testing DNS resolution...
✅ DNS resolution test passed (pypi.org → 151.101.64.223)

📊 Summary:
================================================================================
✅ Successfully fixed: 1 interface(s)

🎉 DNS configuration has been updated!
You can now try installing Python packages:
   pip install -r requirements.txt
```

## When to Use This Script

Use this script when you experience:

- **SSL handshake failures** during pip install
- **DNS resolution timeouts** to public websites
- **Corporate network remnants** after disconnecting
- **Python package installation errors** related to network connectivity

## Common Error Messages This Fixes

```
WARNING: Retrying (Retry(total=0, connect=None, read=None, redirect=None, status=None))
after connection broken by 'SSLError(SSLEOFError(8, 'EOF occurred in violation of protocol (_ssl.c:997)'))': /simple/requests/

Could not fetch URL https://pypi.org/simple/requests/: There was a problem confirming
the ssl certificate: HTTPSConnectionPool(host='pypi.org', port=443): Max retries exceeded

SSL: TLSV1_ALERT_PROTOCOL_VERSION
```

## Requirements

- **Windows PowerShell 5.1+** or **PowerShell Core**
- **Administrator privileges** (script will request elevation)
- **Network connectivity** to test DNS resolution

## Files

- `fix-dns.ps1` - Main PowerShell script
- `fix-dns.cmd` - Batch wrapper that ensures admin privileges
- `fix-dns-README.md` - This documentation

## Troubleshooting

### Script won't run

- Ensure you're running as administrator
- Check PowerShell execution policy: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`

### Still having DNS issues after running

- Try restarting your computer to fully clear network caches
- Check if VPN software is interfering
- Verify your antivirus isn't blocking DNS changes

### Corporate policies preventing changes

- Contact your IT department if you're on a managed device
- Try using a different DNS server (Cloudflare, OpenDNS, etc.)
- Consider using a VPN as a workaround

## Popular Public DNS Servers

| Provider   | Primary        | Secondary       | Features                   |
| ---------- | -------------- | --------------- | -------------------------- |
| Google     | 8.8.8.8        | 8.8.4.4         | Fast, reliable             |
| Cloudflare | 1.1.1.1        | 1.0.0.1         | Privacy-focused, very fast |
| OpenDNS    | 208.67.222.222 | 208.67.220.220  | Filtering options          |
| Quad9      | 9.9.9.9        | 149.112.112.112 | Security filtering         |

## License

This script is provided as-is for educational and troubleshooting purposes. Use at your own discretion.
