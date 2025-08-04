# Streamlit Configuration Files

This directory contains configuration files for the RAG-Enabled Chatbot Streamlit application.

## Files Overview

### `config.toml`
Main application configuration file that controls Streamlit's behavior and appearance.

**Key Settings:**
- **Server**: Port (8501), address (localhost), upload limits (10MB)
- **Theme**: Colors, fonts, styling
- **UI**: Toolbar, sidebar, footer settings
- **Performance**: Caching, rerun behavior, memory management

**Customization:**
```toml
[server]
port = 8501
maxUploadSize = 10

[theme]
primaryColor = "#FF6B6B"
backgroundColor = "#FFFFFF"
```

### `secrets.toml` (Template)
Template for sensitive configuration values. **DO NOT commit actual secrets!**

**Environment Variables Recommended:**
```bash
# Azure OpenAI
export AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com"
export AZURE_OPENAI_API_KEY="your-api-key"
export AZURE_OPENAI_DEPLOYMENT="gpt-4"

# Application Settings
export CHATBOT_LOG_LEVEL="INFO"
export CHROMADB_STORAGE_PATH="./data/chromadb"
```

**Alternative Secrets File Usage:**
```python
import streamlit as st
import os

# Priority: Environment > secrets.toml > default
api_key = os.getenv("AZURE_OPENAI_API_KEY") or st.secrets["azure_openai"]["api_key"]
```

### `credentials.toml` (Template)
Template for authentication credentials (future feature).

**For Production:**
- Use environment variables
- Use Azure Key Vault
- Never commit actual credentials

## Security Best Practices

### 1. Environment Variables (Recommended)
```bash
# Set in your shell or .env file (which is gitignored)
export AZURE_OPENAI_API_KEY="your-key-here"
export AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com"
```

### 2. Local Development Setup
1. Copy template files:
   ```bash
   cp .streamlit/secrets.toml .streamlit/secrets.toml.local
   cp .streamlit/credentials.toml .streamlit/credentials.toml.local
   ```

2. Edit `.local` files with actual values
3. `.local` files are gitignored automatically

### 3. Production Deployment
- Use Azure Key Vault integration
- Set environment variables in hosting platform
- Use managed identity for Azure resources
- Enable HTTPS and proper CORS settings

## Configuration Priority

Streamlit configuration follows this priority order:
1. Command-line arguments
2. Environment variables
3. `secrets.toml` / `credentials.toml`
4. `config.toml`
5. Default values

## Common Configuration Tasks

### Change Port
```bash
# Command line
streamlit run src/ui/streamlit_app.py --server.port 8502

# Or in config.toml
[server]
port = 8502
```

### Enable Production Mode
```toml
[global]
developmentMode = false

[server]
headless = true
enableCORS = true

[client]
showErrorDetails = false
```

### Custom Theme
```toml
[theme]
primaryColor = "#1f77b4"
backgroundColor = "#ffffff"
secondaryBackgroundColor = "#f0f0f0"
textColor = "#262730"
font = "monospace"
```

### Upload Limits
```toml
[server]
maxUploadSize = 50  # MB
```

## Troubleshooting

### Configuration Not Loading
1. Check file syntax with TOML validator
2. Verify file permissions (readable by app)
3. Check environment variable names (case-sensitive)
4. Clear Streamlit cache: `streamlit cache clear`

### Secrets Not Found
1. Verify `secrets.toml` exists and has correct structure
2. Check environment variables are set
3. Ensure no typos in section/key names
4. Use `st.secrets` debug mode

### Performance Issues
```toml
[runner]
fastReruns = true
postScriptGC = true

[server]
enableWebsocketCompression = true
```

## Development vs Production

### Development Settings
- `developmentMode = true`
- `showErrorDetails = true`
- `headless = false`
- File watching enabled

### Production Settings
- `developmentMode = false`
- `showErrorDetails = false`
- `headless = true`
- CORS and security enabled
- Environment-based secrets

## Related Documentation

- [Streamlit Configuration](https://docs.streamlit.io/library/advanced-features/configuration)
- [Secrets Management](https://docs.streamlit.io/streamlit-community-cloud/get-started/deploy-an-app/connect-to-data-sources/secrets-management)
- [Theming](https://docs.streamlit.io/library/advanced-features/theming)
- [Caching](https://docs.streamlit.io/library/advanced-features/caching)

## Security Checklist

- [ ] `secrets.toml` and `credentials.toml` in `.gitignore`
- [ ] Environment variables used in production
- [ ] No hardcoded API keys in code
- [ ] HTTPS enabled in production
- [ ] Proper CORS configuration
- [ ] File upload limits configured
- [ ] Error details hidden in production
- [ ] Regular credential rotation