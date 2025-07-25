@echo off
:: Corporate DNS Fixer - Batch Wrapper
:: This script ensures the PowerShell script runs with administrator privileges

echo Corporate DNS Fixer
echo ==================

:: Check if running as administrator
net session >nul 2>&1
if %errorLevel% == 0 (
    echo Running with administrator privileges...
    goto :run_script
) else (
    echo This script requires administrator privileges.
    echo Requesting elevation...
    
    :: Request elevation and run the PowerShell script
    powershell -Command "Start-Process cmd -ArgumentList '/c cd /d \"%~dp0\" && powershell -ExecutionPolicy Bypass -File fix-dns.ps1 %*' -Verb RunAs"
    goto :end
)

:run_script
:: Run the PowerShell script directly
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File fix-dns.ps1 %*

:end
pause
