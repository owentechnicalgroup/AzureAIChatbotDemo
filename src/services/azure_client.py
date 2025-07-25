"""
Azure OpenAI client wrapper using LangChain integration with enhanced logging.
Provides structured logging for Azure Log Analytics integration.
"""

import asyncio
import logging
import time
from typing import List, Dict, Any, Optional, AsyncGenerator
from dataclasses import dataclass
import structlog
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)
from langchain_openai import AzureChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.outputs import ChatResult, LLMResult
from azure.core.exceptions import AzureError
import openai

from config.settings import Settings
from utils.error_handlers import AzureOpenAIError
from utils.logging_helpers import StructuredLogger

# Create module-level logger for retry decorators - Azure best practice
module_logger = logging.getLogger(__name__)

@dataclass
class TokenUsage:
    """Token usage information from Azure OpenAI."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    
    def to_dict(self) -> Dict[str, int]:
        return {
            'prompt_tokens': self.prompt_tokens,
            'completion_tokens': self.completion_tokens,
            'total_tokens': self.total_tokens
        }

@dataclass
class ResponseMetadata:
    """Response metadata from Azure OpenAI."""
    model: str
    finish_reason: Optional[str] = None
    token_usage: Optional[TokenUsage] = None
    response_time: float = 0.0
    request_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'model': self.model,
            'finish_reason': self.finish_reason,
            'token_usage': self.token_usage.to_dict() if self.token_usage else {},
            'response_time': self.response_time,
            'request_id': self.request_id
        }

class AzureOpenAIClient:
    """
    Azure OpenAI client wrapper with LangChain integration.
    
    Features:
    - Connection pooling and retry logic with exponential backoff
    - Rate limiting awareness and user feedback
    - Token usage tracking and logging
    - Comprehensive error handling
    - Performance metrics collection
    - Async support for better concurrency
    """
    
    def __init__(self, settings: Settings):
        """
        Initialize Azure OpenAI client.
        
        Args:
            settings: Application settings instance
        """
        self.settings = settings
        
        # Initialize structured logger with Azure patterns - moved before other initialization
        self.logger = StructuredLogger(__name__)
        
        # Validate configuration
        if not settings.has_azure_openai_config():
            raise AzureOpenAIError("Azure OpenAI configuration is incomplete")
        
        # Initialize LangChain Azure OpenAI client
        self._client = self._create_langchain_client()
        
        # Store deployment name for easy access
        self.deployment_name = settings.azure_openai_deployment
        
        # Performance tracking
        self._request_count = 0
        self._total_tokens_used = 0
        self._total_response_time = 0.0
        
        # Log successful initialization
        self.logger.log_azure_operation(
            message="Application settings initialized successfully",
            resource_type="azure_openai",
            resource_name=self.deployment_name,
            operation_type="startup",
            success=True
        )
    
    def _create_langchain_client(self) -> AzureChatOpenAI:
        """Create LangChain Azure OpenAI client with proper configuration."""
        try:
            client = AzureChatOpenAI(
                azure_endpoint=self.settings.azure_openai_endpoint,
                api_key=self.settings.azure_openai_api_key,
                api_version=self.settings.azure_openai_api_version,
                deployment_name=self.settings.azure_openai_deployment,
                temperature=self.settings.temperature,
                max_tokens=self.settings.max_tokens,
                timeout=self.settings.request_timeout,
                max_retries=3,  # Built-in retry mechanism
                # Streaming support
                streaming=False,  # Can be enabled per request
                # Additional Azure-specific settings
                validate_base_url=True,
            )
            
            self.logger.debug("LangChain Azure OpenAI client created successfully")
            return client
            
        except Exception as e:
            self.logger.log_azure_operation(
                message=f"Failed to create LangChain client: {str(e)}",
                resource_type="azure_openai",
                resource_name=self.settings.azure_openai_deployment,
                operation_type="initialization",
                success=False,
                error_type=type(e).__name__,
                level='ERROR'
            )
            raise AzureOpenAIError(f"Failed to initialize Azure OpenAI client: {str(e)}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((openai.RateLimitError, openai.APITimeoutError, AzureError)),
        before_sleep=before_sleep_log(module_logger, logging.INFO, exc_info=True),  # Fixed: use module_logger
        reraise=True
    )
    async def generate_response_async(
        self,
        messages: List[Dict[str, str]],
        conversation_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate response asynchronously with retry logic and error handling.
        
        Args:
            messages: List of messages in conversation format
            conversation_id: Optional conversation ID for tracking
            **kwargs: Additional parameters for generation
            
        Returns:
            Dictionary containing response and metadata
        """
        start_time = time.time()
        
        try:
            # Log operation start
            self.logger.log_azure_operation(
                message="Starting asynchronous response generation",
                resource_type="azure_openai",
                resource_name=self.deployment_name,
                operation_type="generate_response_async",
                success=True
            )
            
            # Convert messages to LangChain format
            langchain_messages = self._convert_messages_to_langchain(messages)
            
            # Generate response using LangChain
            response = await self._client.agenerate([langchain_messages])
            
            # Extract response information
            generation = response.generations[0][0]
            response_content = generation.text
            
            # Calculate response time
            response_time = time.time() - start_time
            
            # Extract token usage and metadata
            llm_output = response.llm_output or {}
            token_usage_data = llm_output.get('token_usage', {})
            
            token_usage = TokenUsage(
                prompt_tokens=token_usage_data.get('prompt_tokens', 0),
                completion_tokens=token_usage_data.get('completion_tokens', 0),
                total_tokens=token_usage_data.get('total_tokens', 0)
            )
            
            metadata = ResponseMetadata(
                model=llm_output.get('model_name', self.settings.azure_openai_deployment),
                finish_reason=generation.generation_info.get('finish_reason') if generation.generation_info else None,
                token_usage=token_usage,
                response_time=response_time,
                request_id=llm_output.get('request_id')
            )
            
            # Update performance metrics
            self._update_metrics(token_usage, response_time)
            
            # Log performance metrics
            self.logger.log_performance_metrics(
                operation="azure_openai_async_generation",
                duration=response_time,
                success=True,
                tokens_used=token_usage.total_tokens,
                tokens_prompt=token_usage.prompt_tokens,
                tokens_completion=token_usage.completion_tokens,
                operation_name='azure_openai.generate_response_async',
                component='azure_client',
                resource_type='azure_openai',
                resource_name=self.deployment_name
            )
            
            return {
                'content': response_content,
                'metadata': metadata.to_dict(),
                'conversation_id': conversation_id,
                'timestamp': time.time()
            }
            
        except Exception as e:
            response_time = time.time() - start_time
            
            # Log performance metrics for failed operation
            self.logger.log_performance_metrics(
                operation="azure_openai_async_generation",
                duration=response_time,
                success=False,
                error_message=str(e),
                tokens_used=0,
                operation_name='azure_openai.generate_response_async',
                component='azure_client',
                resource_type='azure_openai',
                resource_name=self.deployment_name
            )
            
            # Log failed operation
            self.logger.log_azure_operation(
                message=f"Error in asynchronous response generation: {str(e)}",
                resource_type="azure_openai",
                resource_name=self.deployment_name,
                operation_type="generate_response_async",
                duration=response_time,
                success=False,
                error_type=type(e).__name__,
                level='ERROR'
            )
            
            # Handle specific Azure OpenAI errors
            if isinstance(e, openai.RateLimitError):
                raise AzureOpenAIError(
                    "Rate limit exceeded. Please try again in a few moments."
                ) from e
            elif isinstance(e, openai.APITimeoutError):
                raise AzureOpenAIError(
                    f"Request timed out after {self.settings.request_timeout}s."
                ) from e
            elif isinstance(e, openai.AuthenticationError):
                raise AzureOpenAIError(
                    "Authentication failed. Please check your API key configuration."
                ) from e
            else:
                raise AzureOpenAIError(f"Service temporarily unavailable: {str(e)}") from e
    
    def generate_response_sync(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Generate response synchronously with proper Azure logging."""
        start_time = time.time()
        
        try:
            # Log operation start
            self.logger.log_azure_operation(
                message="Starting synchronous response generation",
                resource_type="azure_openai",
                resource_name=self.deployment_name,
                operation_type="generate_response_sync",
                success=True
            )
            
            # Convert messages to LangChain format and generate response
            langchain_messages = self._convert_messages_to_langchain(messages)
            response = self._client.invoke(langchain_messages)
            
            response_time = time.time() - start_time
            response_content = response.content if hasattr(response, 'content') else str(response)
            
            # For LangChain, token usage might not be directly available
            # We'll estimate or set to 0 for now - Azure best practice for missing data
            tokens_prompt = 0
            tokens_completion = 0
            tokens_total = 0
            
            # Calculate sizes safely
            request_content = str(messages)
            request_size = len(request_content.encode('utf-8')) if request_content else 0
            response_size = len(response_content.encode('utf-8')) if response_content else 0
            
            # Log performance metrics with required arguments - Azure pattern
            self.logger.log_performance_metrics(
                operation="azure_openai_sync_generation",  # Required: operation name
                duration=response_time,  # Required: operation duration
                success=True,
                tokens_used=tokens_total,
                tokens_prompt=tokens_prompt,
                tokens_completion=tokens_completion,
                request_size=request_size,
                response_size=response_size,
                operation_name='azure_openai.generate_response_sync',
                component='azure_client',
                resource_type='azure_openai',
                resource_name=self.deployment_name
            )
            
            # Log successful Azure operation
            self.logger.log_azure_operation(
                message="Successfully generated response synchronously",
                resource_type="azure_openai",
                resource_name=self.deployment_name,
                operation_type="generate_response_sync",
                duration=response_time,
                success=True
            )
            
            return response_content
            
        except Exception as e:
            response_time = time.time() - start_time
            
            # Log performance metrics for failed operation - Azure pattern
            self.logger.log_performance_metrics(
                operation="azure_openai_sync_generation",  # Required: operation name
                duration=response_time,  # Required: operation duration
                success=False,
                error_message=str(e),
                tokens_used=0,
                operation_name='azure_openai.generate_response_sync',
                component='azure_client',
                resource_type='azure_openai',
                resource_name=self.deployment_name
            )
            
            # Log failed Azure operation
            self.logger.log_azure_operation(
                message=f"Error in synchronous response generation: {str(e)}",
                resource_type="azure_openai",
                resource_name=self.deployment_name,
                operation_type="generate_response_sync",
                duration=response_time,
                success=False,
                error_type=type(e).__name__,
                level='ERROR'
            )
            
            raise AzureOpenAIError(f"Failed to generate response: {str(e)}") from e
    
    def generate_response(
        self,
        messages: List[Dict[str, str]],
        conversation_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate response synchronously (wrapper around async method).
        
        Args:
            messages: List of messages in conversation format
            conversation_id: Optional conversation ID for tracking
            **kwargs: Additional parameters for generation
            
        Returns:
            Dictionary containing response and metadata
        """
        try:
            # Run async method with proper event loop handling
            try:
                # Check if we're already in a running event loop
                loop = asyncio.get_running_loop()
                # If we're already in an event loop, create a new task in a thread
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        self.generate_response_async(messages, conversation_id, **kwargs)
                    )
                    result = future.result()
            except RuntimeError:
                # No event loop running, safe to create new one
                result = asyncio.run(
                    self.generate_response_async(messages, conversation_id, **kwargs)
                )
            
            return result
            
        except Exception as e:
            self.logger.log_azure_operation(
                message=f"Error in response generation wrapper: {str(e)}",
                resource_type="azure_openai",
                resource_name=self.deployment_name,
                operation_type="generate_response",
                success=False,
                error_type=type(e).__name__,
                level='ERROR'
            )
            raise
    
    def _convert_messages_to_langchain(
        self, 
        messages: List[Dict[str, str]]
    ) -> List[BaseMessage]:
        """
        Convert message format to LangChain messages.
        
        Args:
            messages: List of messages in dictionary format
            
        Returns:
            List of LangChain BaseMessage objects
        """
        langchain_messages = []
        
        for message in messages:
            role = message.get('role', '').lower()
            content = message.get('content', '')
            
            if role == 'system':
                langchain_messages.append(SystemMessage(content=content))
            elif role == 'user':
                langchain_messages.append(HumanMessage(content=content))
            elif role == 'assistant':
                langchain_messages.append(AIMessage(content=content))
            else:
                # Default to human message for unknown roles
                langchain_messages.append(HumanMessage(content=content))
        
        return langchain_messages
    
    def _update_metrics(self, token_usage: TokenUsage, response_time: float) -> None:
        """Update performance metrics."""
        self._request_count += 1
        self._total_tokens_used += token_usage.total_tokens
        self._total_response_time += response_time
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on the Azure OpenAI service.
        
        Returns:
            Dictionary containing health check results
        """
        try:
            # Simple test message
            test_messages = [
                {'role': 'user', 'content': 'Hello, are you working?'}
            ]
            
            start_time = time.time()
            response = self.generate_response_sync(test_messages)
            response_time = time.time() - start_time
            
            health_result = {
                'status': 'healthy',
                'response_time': response_time,
                'endpoint': self.settings.azure_openai_endpoint,
                'deployment': self.settings.azure_openai_deployment,
                'timestamp': time.time()
            }
            
            # Log successful health check
            self.logger.log_azure_operation(
                message="Health check completed successfully",
                resource_type="azure_openai",
                resource_name=self.deployment_name,
                operation_type="health_check",
                duration=response_time,
                success=True
            )
            
            return health_result
            
        except Exception as e:
            health_result = {
                'status': 'unhealthy',
                'error': str(e),
                'endpoint': self.settings.azure_openai_endpoint,
                'deployment': self.settings.azure_openai_deployment,
                'timestamp': time.time()
            }
            
            # Log failed health check
            self.logger.log_azure_operation(
                message=f"Health check failed: {str(e)}",
                resource_type="azure_openai",
                resource_name=self.deployment_name,
                operation_type="health_check",
                success=False,
                error_type=type(e).__name__,
                level='ERROR'
            )
            
            return health_result
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get performance metrics.
        
        Returns:
            Dictionary containing performance metrics
        """
        avg_response_time = (
            self._total_response_time / self._request_count 
            if self._request_count > 0 else 0.0
        )
        
        return {
            'request_count': self._request_count,
            'total_tokens_used': self._total_tokens_used,
            'average_response_time': avg_response_time,
            'total_response_time': self._total_response_time,
            'average_tokens_per_request': (
                self._total_tokens_used / self._request_count
                if self._request_count > 0 else 0
            )
        }
    
    def reset_metrics(self) -> None:
        """Reset performance metrics."""
        self._request_count = 0
        self._total_tokens_used = 0
        self._total_response_time = 0.0
        
        self.logger.log_azure_operation(
            message="Performance metrics reset",
            resource_type="azure_openai",
            resource_name=self.deployment_name,
            operation_type="metrics_reset",
            success=True
        )
    
    def __repr__(self) -> str:
        """String representation of the client."""
        return (
            f"AzureOpenAIClient("
            f"deployment={self.settings.azure_openai_deployment}, "
            f"requests={self._request_count}, "
            f"tokens={self._total_tokens_used}"
            f")"
        )