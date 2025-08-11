"""
Simple utility to create AzureChatOpenAI client directly without wrapper.
This eliminates the complex azure_client.py wrapper and uses LangChain directly.
"""

from langchain_openai import AzureChatOpenAI
from src.config.settings import Settings
import structlog

logger = structlog.get_logger(__name__)


def create_azure_chat_openai(settings: Settings) -> AzureChatOpenAI:
    """
    Create AzureChatOpenAI client directly from settings.
    
    Args:
        settings: Application settings
        
    Returns:
        Configured AzureChatOpenAI client
        
    Raises:
        ValueError: If Azure OpenAI configuration is incomplete
    """
    # Validate configuration
    if not settings.has_azure_openai_config():
        raise ValueError("Azure OpenAI configuration is incomplete")
    
    try:
        client = AzureChatOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
            deployment_name=settings.azure_openai_deployment,
            temperature=settings.temperature,
            max_tokens=settings.max_tokens,
            timeout=settings.request_timeout,
            max_retries=3,
            # LangChain handles all the complexity for us
        )
        
        logger.info(
            "AzureChatOpenAI client created",
            deployment=settings.azure_openai_deployment,
            endpoint=settings.azure_openai_endpoint,
            api_version=settings.azure_openai_api_version
        )
        
        return client
        
    except Exception as e:
        logger.error(
            "Failed to create AzureChatOpenAI client",
            error=str(e),
            deployment=settings.azure_openai_deployment
        )
        raise ValueError(f"Failed to initialize Azure OpenAI client: {str(e)}")