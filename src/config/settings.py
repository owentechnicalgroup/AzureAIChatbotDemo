"""
Configuration settings with Azure Key Vault integration.
Task 11: Enhanced settings with multiple authentication methods and fallback patterns.
"""

import os
import logging
import time
import threading
from typing import Optional, Dict, Any, Tuple
from pydantic import BaseModel, Field, field_validator, ConfigDict
from pydantic_settings import BaseSettings
from azure.identity import (
    DefaultAzureCredential,
    ChainedTokenCredential,
    AzureCliCredential,
    ManagedIdentityCredential,
    EnvironmentCredential
)
from azure.keyvault.secrets import SecretClient
from azure.core.exceptions import AzureError
import structlog

logger = structlog.get_logger(__name__).bind(log_type="SECURITY")


class _CredentialManager:
    """
    Singleton credential manager for caching Azure credentials and secrets.
    Separated from Pydantic model to avoid serialization issues.
    """
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._credential_cache = {}
                    cls._instance._secrets_cache = {}
                    cls._instance._cache_lock = threading.Lock()
                    cls._instance._cache_ttl_seconds = 3300  # 55 minutes
        return cls._instance
    
    def get_cached_credential_and_secrets(self, key_vault_url: str, azure_client_id: str) -> Tuple[Any, SecretClient, Dict[str, str]]:
        """Get cached credential, client, and secrets or create/fetch new ones."""
        cache_key = (key_vault_url or "", azure_client_id or "")
        current_time = time.time()
        
        with self._cache_lock:
            # Check if we have valid cached credential and secrets
            credential_valid = False
            secrets_valid = False
            
            # Check credential cache
            if cache_key in self._credential_cache:
                credential, client, cred_timestamp = self._credential_cache[cache_key]
                if current_time - cred_timestamp < self._cache_ttl_seconds:
                    credential_valid = True
                else:
                    logger.debug("Cached credential expired", 
                               cache_age_seconds=int(current_time - cred_timestamp))
                    del self._credential_cache[cache_key]
            
            # Check secrets cache
            cached_secrets = {}
            if cache_key in self._secrets_cache:
                cached_secrets, secrets_timestamp = self._secrets_cache[cache_key]
                if current_time - secrets_timestamp < self._cache_ttl_seconds:
                    secrets_valid = True
                else:
                    logger.debug("Cached secrets expired",
                               cache_age_seconds=int(current_time - secrets_timestamp))
                    del self._secrets_cache[cache_key]
            
            # If both credential and secrets are cached, return them
            if credential_valid and secrets_valid:
                logger.debug("Using cached Azure credential and secrets",
                           cache_age_seconds=int(current_time - min(cred_timestamp, secrets_timestamp)))
                return credential, client, cached_secrets
            
            # Create new credential if needed
            if not credential_valid:
                logger.debug("Creating new Azure credential chain")
                credential, client = self._create_credential_and_client(key_vault_url, azure_client_id)
                self._credential_cache[cache_key] = (credential, client, current_time)
                logger.debug("Cached new Azure credential")
            
            # Fetch secrets if not cached (even if credential was cached)
            if not secrets_valid:
                logger.debug("Fetching secrets from Key Vault")
                secrets = self._fetch_all_secrets(client)
                self._secrets_cache[cache_key] = (secrets, current_time)
                logger.debug("Cached secrets from Key Vault", secrets_count=len(secrets))
                return credential, client, secrets
            else:
                # Use cached secrets with new credential
                return credential, client, cached_secrets
    
    def _create_credential_and_client(self, key_vault_url: str, azure_client_id: str) -> Tuple[Any, SecretClient]:
        """Create new Azure credential and Key Vault client."""
        # Create authentication credential chain
        credential_chain = []
        
        # 1. Try user-assigned managed identity if client_id provided
        if azure_client_id:
            logger.debug("Adding user-assigned managed identity to credential chain")
            credential_chain.append(
                ManagedIdentityCredential(client_id=azure_client_id)
            )
        
        # 2. Try system-assigned managed identity
        logger.debug("Adding system-assigned managed identity to credential chain")
        credential_chain.append(ManagedIdentityCredential())
        
        # 3. Try Azure CLI (local development)
        logger.debug("Adding Azure CLI credential to credential chain")
        credential_chain.append(AzureCliCredential())
        
        # 4. Try environment credential (service principal)
        logger.debug("Adding environment credential to credential chain")
        credential_chain.append(EnvironmentCredential())
        
        # Create chained credential
        if len(credential_chain) > 1:
            credential = ChainedTokenCredential(*credential_chain)
        else:
            credential = DefaultAzureCredential()
        
        # Create Key Vault client
        client = SecretClient(vault_url=key_vault_url, credential=credential)
        
        # Test credential by attempting to get a token
        try:
            credential.get_token("https://vault.azure.net/.default")
            logger.debug("Successfully authenticated with Azure Key Vault")
        except Exception as auth_error:
            logger.warning(
                "Authentication test failed, but proceeding with Key Vault access",
                error=str(auth_error)
            )
        
        return credential, client
    
    def _fetch_all_secrets(self, client: SecretClient) -> Dict[str, str]:
        """Fetch all required secrets from Key Vault in one batch."""
        secrets = {}
        secret_names = [
            ("openai-endpoint", "azure_openai_endpoint"),
            ("openai-api-key", "azure_openai_api_key"), 
            ("gpt4-deployment-name", "azure_openai_deployment"),
            ("embedding-deployment-name", "azure_embedding_deployment"),
            ("applicationinsights-connection-string", "applicationinsights_connection_string"),
            ("chat-observability-connection-string", "chat_observability_connection_string"),
            ("ffiec-cdr-api-key", "ffiec_cdr_api_key"),
            ("ffiec-cdr-username", "ffiec_cdr_username"),
        ]
        
        for vault_name, settings_key in secret_names:
            try:
                logger.debug("Retrieving secret from Key Vault", secret_name=vault_name)
                secret = client.get_secret(vault_name)
                secrets[settings_key] = secret.value
                logger.debug("Successfully retrieved secret", secret_name=vault_name)
            except Exception as e:
                logger.warning(
                    "Failed to retrieve secret from Key Vault",
                    secret_name=vault_name,
                    error=str(e)
                )
                secrets[settings_key] = None
        
        return secrets
    
    def clear_cache(self) -> None:
        """Clear both credential and secrets cache."""
        with self._cache_lock:
            self._credential_cache.clear()
            self._secrets_cache.clear()
            logger.debug("Cleared Azure credential and secrets cache")


# Global credential manager instance
_credential_manager = _CredentialManager()


class Settings(BaseSettings):
    """
    Application settings with Azure Key Vault integration.
    
    Supports multiple authentication methods:
    1. Managed Identity (production)
    2. Azure CLI (local development)
    3. Environment variables (fallback)
    4. Service Principal (CI/CD)
    
    Features credential caching for improved performance.
    """
    
    # Key Vault Configuration
    key_vault_url: Optional[str] = Field(
        None,
        env='KEY_VAULT_URL',
        description="Azure Key Vault URL (e.g., https://mykv.vault.azure.net/)"
    )
    azure_client_id: Optional[str] = Field(
        None,
        env='AZURE_CLIENT_ID',
        description="Client ID for user-assigned managed identity"
    )
    
    # Azure OpenAI Configuration (can be overridden by Key Vault)
    azure_openai_endpoint: Optional[str] = Field(
        None,
        env='AZURE_OPENAI_ENDPOINT',
        description="Azure OpenAI endpoint URL"
    )
    azure_openai_api_key: Optional[str] = Field(
        None,
        env='AZURE_OPENAI_API_KEY',
        description="Azure OpenAI API key"
    )
    azure_openai_deployment: Optional[str] = Field(
        None,
        env='AZURE_OPENAI_DEPLOYMENT',
        description="Azure OpenAI deployment name"
    )
    azure_embedding_deployment: Optional[str] = Field(
        None,
        env='AZURE_EMBEDDING_DEPLOYMENT',
        description="Azure OpenAI embedding deployment name"
    )
    azure_openai_api_version: str = Field(
        "2024-08-01-preview",
        env='AZURE_OPENAI_API_VERSION',
        description="Azure OpenAI API version"
    )
    
    # Model Configuration
    temperature: float = Field(
        0.7,
        ge=0.0,
        le=2.0,
        env='AZURE_OPENAI_TEMPERATURE',
        description="Sampling temperature (0.0 to 2.0)"
    )
    max_tokens: int = Field(
        4000,
        ge=1,
        le=8000,
        env='AZURE_OPENAI_MAX_TOKENS',
        description="Maximum tokens for response"
    )
    request_timeout: float = Field(
        120.0,
        ge=1.0,
        le=300.0,
        env='AZURE_OPENAI_REQUEST_TIMEOUT',
        description="Request timeout in seconds"
    )
    
    # System Message Configuration
    system_message: str = Field(
        "You are a helpful AI assistant that provides accurate and concise responses.",
        env='AZURE_OPENAI_SYSTEM_MESSAGE',
        description="System message for the AI assistant"
    )
    
    # Conversation Configuration
    max_conversation_turns: int = Field(
        20,
        ge=1,
        le=100,
        env='MAX_CONVERSATION_TURNS',
        description="Maximum conversation turns to keep in memory"
    )
    conversation_memory_type: str = Field(
        "buffer_window",
        env='CONVERSATION_MEMORY_TYPE',
        description="Type of conversation memory (buffer, buffer_window, summary)"
    )
    
    # Logging Configuration
    log_level: str = Field(
        "INFO",
        env='LOG_LEVEL',
        description="Logging level"
    )
    log_format: str = Field(
        "json",
        env='LOG_FORMAT',
        description="Log format (json, text)"
    )
    log_file_path: str = Field(
        "logs/chatbot.log",
        env='LOG_FILE_PATH',
        description="Log file path"
    )
    enable_console_logging: bool = Field(
        True,
        env='ENABLE_CONSOLE_LOGGING',
        description="Enable console logging output"
    )
    enable_file_logging: bool = Field(
        False,
        env='ENABLE_FILE_LOGGING',
        description="Enable file logging"
    )
    enable_json_logging: bool = Field(
        True,
        env='ENABLE_JSON_LOGGING',
        description="Use structured JSON logging"
    )
    
    # Application Insights Configuration
    applicationinsights_connection_string: Optional[str] = Field(
        None,
        env='APPLICATIONINSIGHTS_CONNECTION_STRING',
        description="Application Insights connection string for application logging"
    )
    application_insights_enabled: bool = Field(
        True,
        env='APPLICATION_INSIGHTS_ENABLED',
        description="Enable Application Insights logging"
    )
    
    # AI Chat Observability Configuration
    chat_observability_connection_string: Optional[str] = Field(
        None,
        env='CHAT_OBSERVABILITY_CONNECTION_STRING',
        description="Dedicated connection string for AI chat observability workspace"
    )
    enable_chat_observability: bool = Field(
        True,
        env='ENABLE_CHAT_OBSERVABILITY',
        description="Enable specialized AI chat observability system"
    )
    enable_cross_correlation: bool = Field(
        True,
        env='ENABLE_CROSS_CORRELATION',
        description="Enable correlation between application and chat observability systems"
    )
    
    # Environment Configuration
    environment: str = Field(
        "dev",
        env='ENVIRONMENT',
        description="Deployment environment (dev, staging, prod)"
    )
    
    # RAG Configuration
    chromadb_storage_path: str = Field(
        "./data/chromadb",
        env='CHROMADB_STORAGE_PATH',
        description="Local ChromaDB storage directory path"
    )
    enable_rag: bool = Field(
        True,
        env='ENABLE_RAG',
        description="Enable RAG (Retrieval-Augmented Generation) functionality"
    )
    
    # Document Processing Configuration
    chunk_size: int = Field(
        1000,
        ge=100,
        le=2000,
        env='DOCUMENT_CHUNK_SIZE',
        description="Text chunk size for document processing"
    )
    chunk_overlap: int = Field(
        200,
        ge=0,
        le=500,
        env='DOCUMENT_CHUNK_OVERLAP',
        description="Text chunk overlap for document processing"
    )
    max_file_size_mb: int = Field(
        100,
        ge=1,
        le=500,
        env='MAX_FILE_SIZE_MB',
        description="Maximum file size for document uploads (MB)"
    )
    
    # Streamlit Configuration
    streamlit_port: int = Field(
        8501,
        ge=1024,
        le=65535,
        env='STREAMLIT_PORT',
        description="Streamlit application port"
    )
    streamlit_host: str = Field(
        "localhost",
        env='STREAMLIT_HOST',
        description="Streamlit application host"
    )
    
    # Tools Configuration
    enable_tools: bool = Field(
        True,
        env='ENABLE_TOOLS',
        description="Enable external tools and function calling"
    )
    tools_timeout_seconds: int = Field(
        30,
        ge=5,
        le=300,
        env='TOOLS_TIMEOUT_SECONDS',
        description="Default timeout for tool execution (seconds)"
    )
    tools_cache_ttl_minutes: int = Field(
        15,
        ge=0,
        le=1440,
        env='TOOLS_CACHE_TTL_MINUTES',
        description="Tool response cache TTL in minutes (0 to disable)"
    )
    
    # Call Report Tools Configuration
    call_report_enabled: bool = Field(
        True,
        env='ENABLE_CALL_REPORT_TOOLS',
        description="Enable Call Report data tools for financial analysis"
    )
    call_report_timeout_seconds: int = Field(
        30,
        ge=5,
        le=300,
        env='CALL_REPORT_TIMEOUT_SECONDS',
        description="Timeout for Call Report API operations (seconds)"
    )
    
    # API Keys for External Tools
    yelp_api_key: Optional[str] = Field(
        None,
        env='YELP_API_KEY',
        description="Yelp API key for restaurant ratings"
    )
    google_places_api_key: Optional[str] = Field(
        None,
        env='GOOGLE_PLACES_API_KEY',
        description="Google Places API key for business info"
    )
    openweather_api_key: Optional[str] = Field(
        None,
        env='OPENWEATHER_API_KEY',
        description="OpenWeatherMap API key for weather data"
    )
    tmdb_api_key: Optional[str] = Field(
        None,
        env='TMDB_API_KEY',
        description="The Movie Database API key for movie ratings"
    )
    fdic_api_key: Optional[str] = Field(
        None,
        env='FDIC_API_KEY',
        description="FDIC BankFind Suite API key for bank institution and financial data"
    )
    
    # FDIC Financial API Configuration
    fdic_financial_api_timeout: float = Field(
        30.0,
        ge=5.0,
        le=300.0,
        env='FDIC_FINANCIAL_API_TIMEOUT',
        description="FDIC Financial API request timeout in seconds"
    )
    fdic_financial_cache_ttl: int = Field(
        1800,
        ge=300,
        le=7200,
        env='FDIC_FINANCIAL_CACHE_TTL',
        description="FDIC Financial API cache TTL in seconds (5 min to 2 hours)"
    )
    
    # FFIEC CDR API Configuration
    ffiec_cdr_enabled: bool = Field(
        True,
        env='FFIEC_CDR_ENABLED',
        description="Enable FFIEC CDR Public Data Distribution API for call report data"
    )
    ffiec_cdr_api_key: Optional[str] = Field(
        None,
        env='FFIEC_CDR_API_KEY',
        description="FFIEC CDR API key (PIN) for call report data access"
    )
    ffiec_cdr_username: Optional[str] = Field(
        None,
        env='FFIEC_CDR_USERNAME',
        description="FFIEC CDR username for authentication"
    )
    ffiec_cdr_timeout_seconds: int = Field(
        30,
        ge=5,
        le=300,
        env='FFIEC_CDR_TIMEOUT_SECONDS',
        description="FFIEC CDR API request timeout in seconds"
    )
    ffiec_cdr_cache_ttl: int = Field(
        3600,
        ge=300,
        le=7200,
        env='FFIEC_CDR_CACHE_TTL',
        description="FFIEC CDR call report data cache TTL in seconds (5 min to 2 hours)"
    )
    
    # Feature Flags
    enable_conversation_logging: bool = Field(
        True,
        env='ENABLE_CONVERSATION_LOGGING',
        description="Enable conversation logging"
    )
    enable_performance_metrics: bool = Field(
        True,
        env='ENABLE_PERFORMANCE_METRICS',
        description="Enable performance metrics collection"
    )
    
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8", 
        case_sensitive=False,
        validate_assignment=True,
        extra="ignore"  # Allow extra fields in .env file
    )
        
    def __init__(self, **kwargs):
        """Initialize settings and load from Key Vault if configured."""
        super().__init__(**kwargs)
        
        # Load from Key Vault after initial configuration
        if self.key_vault_url:
            try:
                self._load_from_keyvault()
                # Log successful Key Vault loading with structured logging
                from src.utils.logging_helpers import log_config_load
                log_config_load(
                    message="Successfully loaded configuration from Key Vault",
                    config_source=self.key_vault_url,
                    success=True
                )
            except Exception as e:
                # Log Key Vault loading failure with structured logging
                from src.utils.logging_helpers import log_config_load
                log_config_load(
                    message=f"Failed to load from Key Vault: {str(e)}",
                    config_source=self.key_vault_url,
                    success=False,
                    error_type=type(e).__name__
                )
                logger.warning(
                    "Failed to load from Key Vault, using environment variables",
                    error=str(e),
                    key_vault_url=self.key_vault_url
                )
    
    @classmethod
    def clear_credential_cache(cls) -> None:
        """
        Clear the credential cache. Useful for testing or forcing re-authentication.
        """
        _credential_manager.clear_cache()
    
    def _load_from_keyvault(self) -> None:
        """
        Load configuration from Azure Key Vault using cached credentials for performance.
        
        Authentication chain:
        1. User-assigned managed identity (if azure_client_id provided)
        2. System-assigned managed identity
        3. Azure CLI credential (local development)
        4. Environment credential (service principal)
        5. DefaultAzureCredential (fallback)
        """
        logger.info("Loading configuration from Key Vault", key_vault_url=self.key_vault_url)
        
        try:
            # Get cached credential, client, and secrets
            credential, client, cached_secrets = _credential_manager.get_cached_credential_and_secrets(
                self.key_vault_url, self.azure_client_id
            )
            
            # Apply cached secrets to settings with fallback to current values
            secrets_loaded = 0
            
            # Azure OpenAI endpoint
            if cached_secrets.get("azure_openai_endpoint") and cached_secrets["azure_openai_endpoint"] != self.azure_openai_endpoint:
                self.azure_openai_endpoint = cached_secrets["azure_openai_endpoint"]
                secrets_loaded += 1
            
            # Azure OpenAI API key  
            if cached_secrets.get("azure_openai_api_key") and cached_secrets["azure_openai_api_key"] != self.azure_openai_api_key:
                self.azure_openai_api_key = cached_secrets["azure_openai_api_key"]
                secrets_loaded += 1
            
            # Azure OpenAI deployment name
            if cached_secrets.get("azure_openai_deployment") and cached_secrets["azure_openai_deployment"] != self.azure_openai_deployment:
                self.azure_openai_deployment = cached_secrets["azure_openai_deployment"]
                secrets_loaded += 1
            
            # Azure embedding deployment name
            if cached_secrets.get("azure_embedding_deployment") and cached_secrets["azure_embedding_deployment"] != self.azure_embedding_deployment:
                self.azure_embedding_deployment = cached_secrets["azure_embedding_deployment"]
                secrets_loaded += 1
            
            # Application Insights connection string
            if cached_secrets.get("applicationinsights_connection_string") and cached_secrets["applicationinsights_connection_string"] != self.applicationinsights_connection_string:
                self.applicationinsights_connection_string = cached_secrets["applicationinsights_connection_string"]
                secrets_loaded += 1
            
            # Chat Observability connection string
            if cached_secrets.get("chat_observability_connection_string") and cached_secrets["chat_observability_connection_string"] != self.chat_observability_connection_string:
                self.chat_observability_connection_string = cached_secrets["chat_observability_connection_string"]
                secrets_loaded += 1
            
            # FFIEC CDR API key
            if cached_secrets.get("ffiec_cdr_api_key") and cached_secrets["ffiec_cdr_api_key"] != self.ffiec_cdr_api_key:
                self.ffiec_cdr_api_key = cached_secrets["ffiec_cdr_api_key"]
                secrets_loaded += 1
            
            # FFIEC CDR username
            if cached_secrets.get("ffiec_cdr_username") and cached_secrets["ffiec_cdr_username"] != self.ffiec_cdr_username:
                self.ffiec_cdr_username = cached_secrets["ffiec_cdr_username"]
                secrets_loaded += 1
            
            logger.info(
                "Successfully loaded configuration from Key Vault",
                secrets_loaded=secrets_loaded,
                key_vault_url=self.key_vault_url
            )
            
        except AzureError as e:
            logger.error(
                "Azure Key Vault error",
                error=str(e),
                error_type=type(e).__name__,
                key_vault_url=self.key_vault_url
            )
            raise
        except Exception as e:
            logger.error(
                "Unexpected error loading from Key Vault",
                error=str(e),
                error_type=type(e).__name__,
                key_vault_url=self.key_vault_url
            )
            raise
    
    def _get_secret_or_fallback(
        self, 
        client: SecretClient, 
        secret_name: str, 
        fallback_value: Optional[str]
    ) -> Optional[str]:
        """
        Get secret from Key Vault with fallback to current value.
        
        Args:
            client: Key Vault client
            secret_name: Name of the secret to retrieve
            fallback_value: Current value to use if secret retrieval fails
            
        Returns:
            Secret value from Key Vault or fallback value
        """
        try:
            logger.debug("Retrieving secret from Key Vault", secret_name=secret_name)
            secret = client.get_secret(secret_name)
            
            if secret and secret.value:
                logger.debug("Successfully retrieved secret", secret_name=secret_name)
                return secret.value
            else:
                logger.debug("Secret value is empty", secret_name=secret_name)
                return fallback_value
                
        except Exception as e:
            logger.debug(
                "Could not retrieve secret, using fallback", 
                secret_name=secret_name,
                error=str(e)
            )
            return fallback_value
    
    @field_validator('azure_openai_endpoint')
    @classmethod
    def validate_endpoint(cls, v):
        """Validate Azure OpenAI endpoint format."""
        if v and not v.startswith('https://'):
            raise ValueError('Azure OpenAI endpoint must start with https://')
        return v
    
    @field_validator('log_level')
    @classmethod
    def validate_log_level(cls, v):
        """Validate log level."""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f'Log level must be one of: {valid_levels}')
        return v.upper()
    
    @field_validator('environment')
    @classmethod
    def validate_environment(cls, v):
        """Validate environment."""
        valid_envs = ['dev', 'staging', 'prod']
        if v not in valid_envs:
            raise ValueError(f'Environment must be one of: {valid_envs}')
        return v
    
    @field_validator('conversation_memory_type')
    @classmethod
    def validate_memory_type(cls, v):
        """Validate conversation memory type."""
        valid_types = ['buffer', 'buffer_window', 'summary']
        if v not in valid_types:
            raise ValueError(f'Memory type must be one of: {valid_types}')
        return v
    
    def get_azure_openai_config(self) -> Dict[str, Any]:
        """
        Get Azure OpenAI configuration dictionary.
        
        Returns:
            Dictionary containing Azure OpenAI configuration
        """
        return {
            'azure_endpoint': self.azure_openai_endpoint,
            'api_key': self.azure_openai_api_key,
            'api_version': self.azure_openai_api_version,
            'deployment_name': self.azure_openai_deployment,
            'temperature': self.temperature,
            'max_tokens': self.max_tokens,
            'request_timeout': self.request_timeout,
        }
    
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == 'prod'
    
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == 'dev'
    
    def has_key_vault_config(self) -> bool:
        """Check if Key Vault configuration is available."""
        return bool(self.key_vault_url)
    
    def has_azure_openai_config(self) -> bool:
        """Check if Azure OpenAI configuration is complete."""
        return bool(
            self.azure_openai_endpoint and 
            self.azure_openai_api_key and 
            self.azure_openai_deployment
        )
    
    def has_dual_observability_config(self) -> bool:
        """Check if dual observability configuration is complete."""
        return bool(
            self.applicationinsights_connection_string and
            (not self.enable_chat_observability or 
             self.chat_observability_connection_string or 
             self.applicationinsights_connection_string)  # Can fallback to same connection string
        )
    
    def validate_configuration(self) -> Dict[str, bool]:
        """
        Validate the current configuration.
        
        Returns:
            Dictionary with validation results
        """
        results = {
            'key_vault_configured': self.has_key_vault_config(),
            'azure_openai_configured': self.has_azure_openai_config(),
            'logging_configured': bool(self.log_file_path),
            'application_insights_configured': bool(self.applicationinsights_connection_string),
            'dual_observability_configured': self.has_dual_observability_config(),
            'chat_observability_enabled': self.enable_chat_observability,
        }
        
        results['configuration_complete'] = all([
            results['azure_openai_configured'],
            results['logging_configured'],
            results['dual_observability_configured']
        ])
        
        return results
    
    def get_log_config(self) -> Dict[str, Any]:
        """
        Get logging configuration.
        
        Returns:
            Dictionary containing logging configuration
        """
        return {
            'level': self.log_level,
            'format': self.log_format,
            'file_path': self.log_file_path,
            'enable_conversation_logging': self.enable_conversation_logging,
            'application_insights_connection_string': self.applicationinsights_connection_string,
            'chat_observability_connection_string': self.chat_observability_connection_string,
            'enable_chat_observability': self.enable_chat_observability,
            'enable_cross_correlation': self.enable_cross_correlation,
        }
    
    def __repr__(self) -> str:
        """Secure string representation that doesn't expose secrets."""
        return (
            f"Settings("
            f"environment={self.environment}, "
            f"key_vault_configured={self.has_key_vault_config()}, "
            f"azure_openai_configured={self.has_azure_openai_config()}, "
            f"log_level={self.log_level}"
            f")"
        )


# Global settings instance
_settings: Optional[Settings] = None


def clear_settings_cache():
    """Clear the global settings cache to force reload."""
    global _settings
    _settings = None


def get_settings(reload: bool = False) -> Settings:
    """
    Get application settings instance (singleton pattern).
    
    Args:
        reload: Whether to reload settings from environment/Key Vault
        
    Returns:
        Settings instance
    """
    global _settings
    
    if _settings is None or reload:
        _settings = Settings()
        logger.info(
            "Settings loaded",
            environment=_settings.environment,
            key_vault_configured=_settings.has_key_vault_config(),
            azure_openai_configured=_settings.has_azure_openai_config()
        )
    
    return _settings


def reload_settings() -> Settings:
    """
    Reload settings from environment and Key Vault.
    
    Returns:
        Reloaded settings instance
    """
    return get_settings(reload=True)