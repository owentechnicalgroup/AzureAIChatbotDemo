# Azure OpenAI CLI Chatbot

A production-ready CLI chatbot powered by Azure OpenAI and LangChain, featuring secure credential management, comprehensive logging, and enterprise-grade architecture.

## 🎯 **Overview**

This project implements a comprehensive Azure OpenAI chatbot with:
- **Azure OpenAI GPT-4 integration** via LangChain
- **Complete Terraform infrastructure** with remote state management
- **Azure Key Vault** for secure credential storage
- **Managed Identity authentication** for enhanced security
- **Rich CLI interface** with Click and Rich console integration
- **Structured JSON logging** with Application Insights compatibility
- **Conversation memory management** with persistence
- **Comprehensive error handling** with graceful degradation

## 🏗️ **Architecture**

```
Azure Resource Group
├── Azure OpenAI Service
│   └── GPT-4 Deployment
├── Azure Key Vault (Secrets Management)
├── User Assigned Managed Identity
├── Log Analytics Workspace
├── Application Insights (Monitoring)
├── Storage Account (Conversation History)
└── Optional: Linux App Service
```

## 📋 **Prerequisites**

- **Azure CLI** (2.0+ with active subscription)
- **Terraform** (1.0+)
- **Python** (3.8+)
- **PowerShell** (Windows) or **Bash** (Linux/macOS)
- **Git** (for version control)

## 🚀 **Quick Start**

### **Option 1: PowerShell (Windows/VS Code) - Recommended**

```powershell
# 1. Clone and navigate
git clone <repository-url>
cd context-engineering-intro

# 2. Login to Azure
az login

# 3. Validate configuration
.\scripts\validate-terraform.ps1

# 4. Deploy infrastructure (test first)
.\scripts\deploy.ps1 dev "East US" -PlanOnly
.\scripts\deploy.ps1 dev "East US"

# 5. Configure application
.\scripts\setup-env.ps1

# 6. Install dependencies
. venv_linux\Scripts\activate
pip install -r requirements.txt

# 7. Test and use
python src\main.py health
python src\main.py chat
```

### **Option 2: Bash (Linux/macOS/Git Bash)**

```bash
# 1. Clone and navigate  
git clone <repository-url>
cd context-engineering-intro

# 2. Login to Azure
az login

# 3. Validate configuration
./scripts/validate-terraform.sh

# 4. Deploy infrastructure
./scripts/deploy.sh dev "East US"

# 5. Configure application
./scripts/setup-env.sh

# 6. Install dependencies
source venv_linux/bin/activate
pip install -r requirements.txt

# 7. Test and use
python src/main.py health
python src/main.py chat
```

## 📁 **Project Structure**

```
├── src/                           # Python application source
│   ├── config/                    # Configuration management
│   ├── services/                  # Azure services integration
│   ├── chatbot/                   # Core chatbot functionality
│   ├── utils/                     # Utility functions
│   └── main.py                    # CLI entry point
├── infrastructure/                # Terraform IaC
│   ├── modules/azure-openai/      # Azure OpenAI module
│   ├── main.tf                    # Main configuration
│   ├── variables.tf               # Input variables
│   └── outputs.tf                 # Infrastructure outputs
├── scripts/                       # Deployment automation
│   ├── deploy.ps1/.sh            # Infrastructure deployment
│   ├── setup-env.ps1/.sh         # Environment configuration
│   ├── validate-terraform.ps1/.sh # Configuration validation
│   └── destroy.ps1/.sh           # Resource cleanup
├── .env.example                   # Environment template
├── requirements.txt               # Python dependencies
└── venv_linux/                   # Virtual environment
```

## 🔧 **Configuration**

### **Environment Variables**

After deployment, the application uses these key variables (auto-configured):

```bash
# Azure OpenAI Configuration
AZURE_OPENAI_ENDPOINT=https://your-openai.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4-deployment
AZURE_CLIENT_ID=your-managed-identity-client-id

# Security
KEY_VAULT_URL=https://your-keyvault.vault.azure.net/

# Monitoring
APPLICATIONINSIGHTS_CONNECTION_STRING=InstrumentationKey=...

# Application Settings
ENVIRONMENT=dev
LOG_LEVEL=INFO
MAX_CONVERSATION_TURNS=20
```

### **Terraform Variables**

Key infrastructure configuration options:

```hcl
# Core Configuration
environment = "dev"                    # dev, staging, prod
location = "East US"                  # Azure region
app_name = "aoai-chatbot"            # Application name prefix

# Azure OpenAI Settings
gpt4_model_name = "gpt-4"            # Model to deploy
gpt4_capacity = 10                   # TPM capacity
openai_sku = "S0"                    # Service tier

# Monitoring
alert_email = "admin@yourcompany.com" # Alert notifications
log_retention_days = 30              # Log retention period
```

## 🛠️ **Available Scripts**

| Command | PowerShell | Bash | Purpose |
|---------|------------|------|---------|
| **Validate** | `.\scripts\validate-terraform.ps1` | `./scripts/validate-terraform.sh` | Validate Terraform configuration |
| **Deploy** | `.\scripts\deploy.ps1 [env] [region]` | `./scripts/deploy.sh [env] [region]` | Deploy Azure infrastructure |
| **Configure** | `.\scripts\setup-env.ps1` | `./scripts/setup-env.sh` | Extract config from Terraform |
| **Destroy** | `.\scripts\destroy.ps1 [env]` | `./scripts/destroy.sh [env]` | Safely destroy resources |

### **Script Options**

```powershell
# Deployment options
.\scripts\deploy.ps1 -PlanOnly          # Test deployment
.\scripts\deploy.ps1 -ForceReinit       # Force Terraform reinit
.\scripts\deploy.ps1 -SetupBackendOnly  # Only setup state backend

# Environment setup options  
.\scripts\setup-env.ps1 -DryRun         # Preview changes
.\scripts\setup-env.ps1 -Force          # Overwrite existing .env
.\scripts\setup-env.ps1 -Verbose        # Detailed output

# Destroy options
.\scripts\destroy.ps1 -PlanOnly         # Preview destruction
.\scripts\destroy.ps1 -Force            # Skip confirmations (DANGEROUS)
```

## 💬 **CLI Usage**

### **Interactive Chat**
```bash
python src/main.py chat
python src/main.py chat --prompt-type technical --max-turns 50
```

### **Single Questions**
```bash
python src/main.py ask "Explain quantum computing"
python src/main.py ask "Write Python code for API client" --output-format json
```

### **System Management**
```bash
python src/main.py health              # Check system health
python src/main.py config              # Show configuration  
python src/main.py prompts             # List prompt types
python src/main.py reload --reload     # Reload configuration
```

### **Conversation Management**
```bash
python src/main.py show-conversation conversation.json
python src/main.py chat --save-conversation output.json
```

## 🔐 **Security Features**

### **Authentication & Authorization**
- **Azure Managed Identity** for credential-free authentication
- **Azure Key Vault** for secure secret storage
- **RBAC permissions** with least privilege access
- **Azure AD integration** for identity management

### **Security Best Practices**
- ✅ No hardcoded credentials in code
- ✅ TLS 1.2+ for all communications
- ✅ Encrypted storage for conversation history
- ✅ Comprehensive audit logging
- ✅ Network security groups for App Service (optional)
- ✅ Key rotation support

## 📊 **Monitoring & Logging**

### **Application Insights Integration**
- Performance metrics collection
- Error tracking and alerting
- User interaction analytics
- Resource utilization monitoring

### **Structured Logging**
- JSON-formatted logs for easy parsing
- Correlation IDs for request tracking
- Multiple log levels (DEBUG, INFO, WARNING, ERROR)
- Conversation event logging

### **Alerts & Notifications**
- High token usage alerts
- Error rate monitoring
- Performance degradation detection
- Email notifications for critical issues

## 🧪 **Testing**

### **Health Checks**
```bash
# Basic health check
python src/main.py health

# Detailed health information
python src/main.py health --output-format table

# JSON output for automation
python src/main.py health --output-format json
```

### **Configuration Validation**
```bash
# Validate current configuration
python src/main.py config

# Test Key Vault access
python src/main.py ask "Test message" --verbose
```

## 🚨 **Troubleshooting**

### **Common Issues**

**1. Authentication Errors**
```bash
# Check Azure login
az account show

# Verify Key Vault permissions
az keyvault secret list --vault-name your-keyvault
```

**2. Configuration Issues**
```bash
# Regenerate environment configuration
.\scripts\setup-env.ps1 -Force

# Check Terraform outputs
cd infrastructure && terraform output
```

**3. Package Installation Problems**
```bash
# Upgrade pip
pip install --upgrade pip

# Install with trusted hosts
pip install --trusted-host pypi.org -r requirements.txt
```

**4. Terraform Issues**
```bash
# Validate configuration
.\scripts\validate-terraform.ps1

# Force reinitialization
.\scripts\deploy.ps1 -ForceReinit
```

### **Debug Mode**
```bash
python src/main.py --debug chat
python src/main.py --log-level DEBUG health
```

## 🔄 **Development Workflow**

### **Making Changes**
1. **Update code** in `src/` directory
2. **Test locally** with `python src/main.py health`
3. **Update infrastructure** by modifying Terraform files
4. **Validate changes** with `.\scripts\validate-terraform.ps1`
5. **Deploy updates** with `.\scripts\deploy.ps1`
6. **Update environment** with `.\scripts\setup-env.ps1`

### **Environment Management**
- **Development**: `dev` environment for testing
- **Staging**: `staging` environment for pre-production validation  
- **Production**: `prod` environment for live deployment

```powershell
# Deploy to different environments
.\scripts\deploy.ps1 dev "East US"
.\scripts\deploy.ps1 staging "West Europe"  
.\scripts\deploy.ps1 prod "East US 2"
```

## 📚 **Advanced Usage**

### **Custom System Prompts**
```bash
python src/main.py chat --prompt-type technical
python src/main.py chat --system-prompt "You are an expert DevOps consultant"
```

### **Conversation Memory Types**
- `buffer` - Keep all conversation history
- `buffer_window` - Keep last N turns (default)
- `summary` - Summarize older conversations

### **Multiple Model Support**
Configure different GPT-4 models by updating Terraform variables:
```hcl
gpt4_model_name = "gpt-4"        # or "gpt-4-32k"
gpt4_model_version = "0613"      # Model version
```

## 🤝 **Contributing**

1. **Fork the repository**
2. **Create feature branch**: `git checkout -b feature/amazing-feature`
3. **Make changes** following the coding standards in `CLAUDE.md`
4. **Test thoroughly** with both unit tests and integration tests
5. **Update documentation** as needed
6. **Submit pull request**

## 📄 **Documentation Files**

- **`TERRAFORM_STATUS.md`** - Infrastructure validation and status
- **`DEPLOYMENT_TEST.md`** - Comprehensive deployment test results
- **`POWERSHELL_SCRIPTS_GUIDE.md`** - Detailed PowerShell script usage
- **`CLAUDE.md`** - Project-specific development guidelines
- **`.env.example`** - Environment configuration template

## 📞 **Support**

### **Getting Help**
1. **Check documentation** in project files
2. **Review logs** in `logs/` directory
3. **Run health checks** to identify issues
4. **Validate configuration** with validation scripts

### **Common Resources**
- **Azure OpenAI Documentation**: https://docs.microsoft.com/azure/cognitive-services/openai/
- **Terraform Azure Provider**: https://registry.terraform.io/providers/hashicorp/azurerm/
- **LangChain Documentation**: https://python.langchain.com/
- **Azure CLI Reference**: https://docs.microsoft.com/cli/azure/

---

## 🎉 **Success Criteria**

Your deployment is successful when:
- ✅ `python src/main.py health` shows "healthy" status
- ✅ `python src/main.py ask "Hello"` returns a response
- ✅ All Azure resources are visible in the Azure portal
- ✅ Conversation history persists between sessions
- ✅ Monitoring data appears in Application Insights

**Happy chatting with your Azure OpenAI assistant!** 🤖✨