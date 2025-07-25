# PowerShell Scripts Guide

## 🎯 **Overview**

The Azure OpenAI CLI Chatbot includes both **Bash** and **PowerShell** versions of all deployment scripts for maximum compatibility:

- **PowerShell scripts** (`.ps1`) - Optimized for Windows, VS Code, and PowerShell environments  
- **Bash scripts** (`.sh`) - For Linux, macOS, and Git Bash environments

## 📁 **Available Scripts**

| Script | PowerShell | Bash | Purpose |
|--------|------------|------|---------|
| **Deploy** | `deploy.ps1` | `deploy.sh` | Deploy Azure infrastructure |
| **Setup Environment** | `setup-env.ps1` | `setup-env.sh` | Configure application environment |
| **Validate** | `validate-terraform.ps1` | `validate-terraform.sh` | Validate Terraform configuration |
| **Destroy** | `destroy.ps1` | `destroy.sh` | Safely destroy infrastructure |

## 🚀 **PowerShell Scripts Usage**

### **1. Deploy Infrastructure**

```powershell
# Test deployment first (recommended)
.\scripts\deploy.ps1 dev "East US" -PlanOnly

# Deploy to development environment
.\scripts\deploy.ps1 dev "East US"

# Deploy to production with force reinit
.\scripts\deploy.ps1 prod "West Europe" -ForceReinit

# Setup backend storage only
.\scripts\deploy.ps1 dev "East US" -SetupBackendOnly

# Get help
.\scripts\deploy.ps1 -Help
```

**Key Features:**
- ✅ Automatic backend storage account creation with unique names
- ✅ Comprehensive prerequisite checking (Azure CLI, Terraform)
- ✅ Color-coded output with progress tracking
- ✅ Plan-only mode for safe testing
- ✅ Force reinitialization option
- ✅ Detailed logging to `logs/deployment-*.log`

### **2. Setup Application Environment**

```powershell  
# Extract Terraform outputs to .env file
.\scripts\setup-env.ps1

# Preview changes without making them
.\scripts\setup-env.ps1 -DryRun

# Force overwrite existing .env file
.\scripts\setup-env.ps1 -Force

# Skip backup of existing .env
.\scripts\setup-env.ps1 -NoBackup

# Use different Terraform workspace
.\scripts\setup-env.ps1 -Workspace production

# Verbose output
.\scripts\setup-env.ps1 -Verbose
```

**Key Features:**
- ✅ Extracts all Terraform outputs to environment variables
- ✅ Automatic backup of existing `.env` files
- ✅ Comprehensive validation of extracted values
- ✅ Dry-run mode to preview changes
- ✅ Multiple workspace support
- ✅ Application health check testing

### **3. Validate Configuration**

```powershell
# Run full validation
.\scripts\validate-terraform.ps1

# Get help
.\scripts\validate-terraform.ps1 -Help
```

**Validation Checks:**
- ✅ Required files existence
- ✅ Terraform syntax and formatting
- ✅ Backend configuration
- ✅ Variable references validation  
- ✅ Placeholder value detection
- ✅ Deployment readiness assessment

### **4. Destroy Infrastructure**

```powershell
# Show destroy plan (safe)
.\scripts\destroy.ps1 dev -PlanOnly

# Destroy with safety confirmations
.\scripts\destroy.ps1 dev "East US"

# Force destroy without confirmations (DANGEROUS)
.\scripts\destroy.ps1 dev "East US" -Force
```

**Safety Features:**
- ⚠️ Multiple confirmation prompts
- ⚠️ Environment name double-confirmation  
- ⚠️ 10-second countdown before execution
- ⚠️ Plan-only mode for safe preview
- ⚠️ Automatic cleanup of local configuration files

## 🎨 **VS Code Integration**

### **Setup in VS Code:**
1. **Open VS Code** in your project directory
2. **Open Terminal**: `Ctrl + ` ` (backtick)
3. **PowerShell is default** - ready to go!
4. **Run scripts directly**:
   ```powershell
   .\scripts\deploy.ps1 -Help
   ```

### **Recommended VS Code Extensions:**
- **PowerShell** - Enhanced PowerShell support
- **Azure Tools** - Azure integration
- **Terraform** - Terraform syntax highlighting

## 🔧 **Script Features**

### **Common Features (All Scripts):**
- ✅ **Color-coded output** - Info (blue), Success (green), Warning (yellow), Error (red)
- ✅ **Comprehensive help** - Use `-Help` parameter
- ✅ **Error handling** - Graceful failures with detailed messages
- ✅ **Prerequisite checking** - Validates requirements before execution
- ✅ **Progress tracking** - Clear status indicators
- ✅ **Logging** - Detailed logs for troubleshooting

### **Windows-Specific Improvements:**
- ✅ **Native PowerShell parameters** - Better than argument parsing
- ✅ **Windows path handling** - Proper backslash usage
- ✅ **PowerShell error handling** - Native try/catch blocks
- ✅ **Windows terminal colors** - Optimized color scheme

## 📋 **Complete Deployment Workflow**

### **Step 1: Validate Configuration**
```powershell
.\scripts\validate-terraform.ps1
```

### **Step 2: Test Deployment**
```powershell  
.\scripts\deploy.ps1 dev "East US" -PlanOnly
```

### **Step 3: Deploy Infrastructure** 
```powershell
.\scripts\deploy.ps1 dev "East US"
```

### **Step 4: Configure Application**
```powershell
.\scripts\setup-env.ps1
```

### **Step 5: Install Dependencies**
```powershell
. venv_linux\Scripts\activate
pip install -r requirements.txt
```

### **Step 6: Test Application**
```powershell
python src\main.py health
python src\main.py config
python src\main.py chat
```

### **Step 7: Clean Up (When Done)**
```powershell
.\scripts\destroy.ps1 dev "East US" -PlanOnly  # Preview
.\scripts\destroy.ps1 dev "East US"            # Execute
```

## ⚡ **Quick Start**

```powershell
# Clone and navigate to project
cd "C:\Users\owenm\OneDrive - Mo Knows Tech\context-engineering-intro"

# Validate everything is ready
.\scripts\validate-terraform.ps1

# Deploy in one command
.\scripts\deploy.ps1 dev "East US"

# Configure environment  
.\scripts\setup-env.ps1

# Test the application
python src\main.py health
```

## 🆚 **PowerShell vs Bash Comparison**

| Feature | PowerShell | Bash | Notes |
|---------|------------|------|-------|
| **VS Code Integration** | ✅ Native | ⚠️ Requires Git Bash | PowerShell is default terminal |
| **Windows Compatibility** | ✅ Perfect | ⚠️ Requires Git Bash/WSL | PowerShell built into Windows |
| **Parameter Handling** | ✅ Native `-Parameter` | ⚠️ Manual parsing | PowerShell parameters are cleaner |
| **Error Handling** | ✅ Try/Catch blocks | ⚠️ Exit codes | PowerShell exceptions are cleaner |
| **Path Handling** | ✅ Windows paths | ⚠️ Unix-style paths | PowerShell handles Windows paths natively |
| **Color Output** | ✅ Native colors | ⚠️ ANSI codes | PowerShell colors work in all terminals |

## 🔍 **Troubleshooting**

### **Common Issues:**

**1. Execution Policy Error:**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**2. Azure CLI Not Found:**
```powershell
# Install Azure CLI
winget install Microsoft.AzureCLI
```

**3. Terraform Not Found:**
```powershell  
# Install Terraform
winget install Hashicorp.Terraform
```

**4. PowerShell Version:**
```powershell
# Check version (requires PowerShell 5.1+ or PowerShell Core 6+)
$PSVersionTable.PSVersion
```

## 📚 **Additional Resources**

- **Azure CLI Documentation**: https://docs.microsoft.com/en-us/cli/azure/
- **Terraform Documentation**: https://www.terraform.io/docs/
- **PowerShell Documentation**: https://docs.microsoft.com/en-us/powershell/
- **VS Code PowerShell Extension**: https://marketplace.visualstudio.com/items?itemName=ms-vscode.PowerShell

---

**Both script versions provide identical functionality - choose the one that works best for your environment!** 🎯