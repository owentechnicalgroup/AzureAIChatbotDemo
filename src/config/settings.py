"""
Configuration settings with Azure Key Vault integration.
Task 11: Enhanced settings with multiple authentication methods and fallback patterns.
"""

import os
import logging
from typing import Optional, Dict, Any
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


class Settings(BaseSettings):
    """
    Application settings with Azure Key Vault integration.
    
    Supports multiple authentication methods:
    1. Managed Identity (production)
    2. Azure CLI (local development)
    3. Environment variables (fallback)
    4. Service Principal (CI/CD)
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
        1000,
        ge=1,
        le=4000,
        env='AZURE_OPENAI_MAX_TOKENS',
        description="Maximum tokens for response"
    )
    request_timeout: float = Field(
        30.0,
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
    
    def _load_from_keyvault(self) -> None:
        """
        Load configuration from Azure Key Vault using multiple authentication methods.
        
        Authentication chain:
        1. User-assigned managed identity (if azure_client_id provided)
        2. System-assigned managed identity
        3. Azure CLI credential (local development)
        4. Environment credential (service principal)
        5. DefaultAzureCredential (fallback)
        """
        logger.info("Loading configuration from Key Vault", key_vault_url=self.key_vault_url)
        
        try:
            # Create authentication credential chain
            credential_chain = []
            
            # 1. Try user-assigned managed identity if client_id provided
            if self.azure_client_id:
                logger.debug("Adding user-assigned managed identity to credential chain")
                credential_chain.append(
                    ManagedIdentityCredential(client_id=self.azure_client_id)
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
            client = SecretClient(vault_url=self.key_vault_url, credential=credential)
            
            # Test credential by attempting to get a token
            # This helps identify authentication issues early
            try:
                credential.get_token("https://vault.azure.net/.default")
                logger.debug("Successfully authenticated with Azure Key Vault")
            except Exception as auth_error:
                logger.warning(
                    "Authentication test failed, but proceeding with Key Vault access",
                    error=str(auth_error)
                )
            
            # Load secrets with fallback to current values
            secrets_loaded = 0
            
            # Azure OpenAI endpoint
            endpoint = self._get_secret_or_fallback(
                client, "openai-endpoint", self.azure_openai_endpoint
            )
            if endpoint != self.azure_openai_endpoint:
                self.azure_openai_endpoint = endpoint
                secrets_loaded += 1
            
            # Azure OpenAI API key
            api_key = self._get_secret_or_fallback(
                client, "openai-api-key", self.azure_openai_api_key
            )
            if api_key != self.azure_openai_api_key:
                self.azure_openai_api_key = api_key
                secrets_loaded += 1
            
            # Azure OpenAI deployment name
            deployment = self._get_secret_or_fallback(
                client, "gpt4-deployment-name", self.azure_openai_deployment
            )
            if deployment != self.azure_openai_deployment:
                self.azure_openai_deployment = deployment
                secrets_loaded += 1
            
            # Azure embedding deployment name
            embedding_deployment = self._get_secret_or_fallback(
                client, "embedding-deployment-name", self.azure_embedding_deployment
            )
            if embedding_deployment != self.azure_embedding_deployment:
                self.azure_embedding_deployment = embedding_deployment
                secrets_loaded += 1
            
            # Application Insights connection string
            app_insights = self._get_secret_or_fallback(
                client, "applicationinsights-connection-string", 
                self.applicationinsights_connection_string
            )
            if app_insights != self.applicationinsights_connection_string:
                self.applicationinsights_connection_string = app_insights
                secrets_loaded += 1
            
            # Chat Observability connection string
            chat_observability = self._get_secret_or_fallback(
                client, "chat-observability-connection-string",
                self.chat_observability_connection_string
            )
            if chat_observability != self.chat_observability_connection_string:
                self.chat_observability_connection_string = chat_observability
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