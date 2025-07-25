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
from utils.logging_helpers import StructuredLogger, log_operation

logger = structlog.get_logger(__name__)
structured_logger = StructuredLogger(__name__)


@dataclass
class TokenUsage:
    """Token usage information for a request."""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    
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
    finish_reason: Optional[str]
    token_usage: TokenUsage
    response_time: float
    request_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'model': self.model,
            'finish_reason': self.finish_reason,
            'token_usage': self.token_usage.to_dict(),
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
        self.logger = logger.bind(
            log_type="AZURE_OPENAI",
            component="azure_openai_client",
            deployment=settings.azure_openai_deployment
        )
        
        # Validate configuration
        if not settings.has_azure_openai_config():
            raise AzureOpenAIError("Azure OpenAI configuration is incomplete")
        
        # Initialize LangChain Azure OpenAI client
        self._client = self._create_langchain_client()
        
        # Performance tracking
        self._request_count = 0
        self._total_tokens_used = 0
        self._total_response_time = 0.0
        
        self.logger.info(
            "Azure OpenAI client initialized",
            endpoint=settings.azure_openai_endpoint,
            deployment=settings.azure_openai_deployment,
            api_version=settings.azure_openai_api_version
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
            self.logger.error(
                "Failed to create LangChain client",
                error=str(e),
                error_type=type(e).__name__
            )
            raise AzureOpenAIError(f"Failed to initialize Azure OpenAI client: {str(e)}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((openai.RateLimitError, openai.APITimeoutError, AzureError)),
        before_sleep=before_sleep_log(logger, logging.INFO, exc_info=True),
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
        request_logger = self.logger.bind(conversation_id=conversation_id)
        
        try:
            # Convert messages to LangChain format
            langchain_messages = self._convert_messages_to_langchain(messages)
            
            request_logger.info(
                "Generating response",
                message_count=len(messages),
                model=self.settings.azure_openai_deployment,
                temperature=self.settings.temperature,
                max_tokens=self.settings.max_tokens
            )
            
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
                finish_reason=generation.generation_info.get('finish_reason'),
                token_usage=token_usage,
                response_time=response_time,
                request_id=llm_output.get('request_id')
            )
            
            # Update performance metrics
            self._update_metrics(token_usage, response_time)
            
            # Log successful response
            request_logger.info(
                "Response generated successfully",
                response_time=response_time,
                token_usage=token_usage.to_dict(),
                finish_reason=metadata.finish_reason,
                content_length=len(response_content)
            )
            
            return {
                'content': response_content,
                'metadata': metadata.to_dict(),
                'conversation_id': conversation_id,
                'timestamp': time.time()
            }
            
        except openai.RateLimitError as e:
            # Handle rate limiting with specific guidance
            request_logger.warning(
                "Rate limit exceeded",
                error=str(e),
                retry_after=getattr(e, 'retry_after', None)
            )
            
            # Re-raise to trigger retry mechanism
            raise AzureOpenAIError(
                "Rate limit exceeded. The service is temporarily unavailable. "
                "Please try again in a few moments."
            ) from e
            
        except openai.APITimeoutError as e:
            request_logger.warning(
                "Request timeout",
                error=str(e),
                timeout=self.settings.request_timeout
            )
            raise AzureOpenAIError(
                f"Request timed out after {self.settings.request_timeout}s. "
                "Please try again or consider reducing the complexity of your request."
            ) from e
            
        except openai.AuthenticationError as e:
            request_logger.error(
                "Authentication failed",
                error=str(e)
            )
            raise AzureOpenAIError(
                "Authentication failed. Please check your API key configuration."
            ) from e
            
        except openai.BadRequestError as e:
            request_logger.error(
                "Bad request",
                error=str(e)
            )
            raise AzureOpenAIError(
                f"Invalid request: {str(e)}"
            ) from e
            
        except Exception as e:
            request_logger.error(
                "Unexpected error during response generation",
                error=str(e),
                error_type=type(e).__name__,
                response_time=time.time() - start_time
            )
            raise AzureOpenAIError(
                f"Service temporarily unavailable: {str(e)}"
            ) from e
    
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
        start_time = time.time()
        
        try:
            # Log the request start
            structured_logger.log_azure_operation(
                message="Starting synchronous response generation",
                resource_type="azure_openai",
                resource_name=self.settings.azure_openai_deployment or "unknown",
                operation_type="generate_response_sync",
                success=True
            )
            
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
            
            # Log successful completion with performance metrics
            duration = time.time() - start_time
            token_usage = result.get('token_usage', {})
            
            structured_logger.log_performance_metrics(
                message="Successfully generated response synchronously",
                response_time=duration,
                tokens_prompt=token_usage.get('prompt_tokens'),
                tokens_completion=token_usage.get('completion_tokens'),
                tokens_total=token_usage.get('total_tokens'),
                operation_name="azure_openai.generate_response_sync"
            )
            
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            
            # Log the error with structured logging
            structured_logger.log_azure_operation(
                message=f"Error in synchronous response generation: {str(e)}",
                resource_type="azure_openai",
                resource_name=self.settings.azure_openai_deployment or "unknown",
                operation_type="generate_response_sync",
                duration=duration,
                success=False,
                error_type=type(e).__name__,
                level='ERROR'
            )
            
            self.logger.error(
                "Error in synchronous response generation",
                error=str(e),
                conversation_id=conversation_id
            )
            raise
    
    async def generate_stream_async(
        self,
        messages: List[Dict[str, str]],
        conversation_id: Optional[str] = None,
        **kwargs
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Generate streaming response asynchronously.
        
        Args:
            messages: List of messages in conversation format
            conversation_id: Optional conversation ID for tracking
            **kwargs: Additional parameters for generation
            
        Yields:
            Dictionary containing response chunks and metadata
        """
        request_logger = self.logger.bind(conversation_id=conversation_id)
        start_time = time.time()
        
        try:
            # Create streaming client
            streaming_client = AzureChatOpenAI(
                azure_endpoint=self.settings.azure_openai_endpoint,
                api_key=self.settings.azure_openai_api_key,
                api_version=self.settings.azure_openai_api_version,
                deployment_name=self.settings.azure_openai_deployment,
                temperature=self.settings.temperature,
                max_tokens=self.settings.max_tokens,
                timeout=self.settings.request_timeout,
                streaming=True
            )
            
            # Convert messages to LangChain format
            langchain_messages = self._convert_messages_to_langchain(messages)
            
            request_logger.info("Starting streaming response generation")
            
            # Stream response
            async for chunk in streaming_client.astream(langchain_messages):
                chunk_data = {
                    'content': chunk.content,
                    'conversation_id': conversation_id,
                    'timestamp': time.time(),
                    'is_final': False
                }
                yield chunk_data
            
            # Final chunk with metadata
            response_time = time.time() - start_time
            final_chunk = {
                'content': '',
                'conversation_id': conversation_id,
                'timestamp': time.time(),
                'is_final': True,
                'metadata': {
                    'response_time': response_time,
                    'model': self.settings.azure_openai_deployment
                }
            }
            
            request_logger.info(
                "Streaming response completed",
                response_time=response_time
            )
            
            yield final_chunk
            
        except Exception as e:
            request_logger.error(
                "Error in streaming response generation",
                error=str(e),
                error_type=type(e).__name__
            )
            
            # Yield error chunk
            yield {
                'content': '',
                'error': str(e),
                'conversation_id': conversation_id,
                'timestamp': time.time(),
                'is_final': True
            }
    
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
                self.logger.warning(f"Unknown message role: {role}")
                # Default to human message
                langchain_messages.append(HumanMessage(content=content))
        
        return langchain_messages
    
    def _update_metrics(self, token_usage: TokenUsage, response_time: float) -> None:
        """Update performance metrics."""
        self._request_count += 1
        self._total_tokens_used += token_usage.total_tokens
        self._total_response_time += response_time
    
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
            response = self.generate_response(test_messages, conversation_id="health_check")
            response_time = time.time() - start_time
            
            return {
                'status': 'healthy',
                'response_time': response_time,
                'endpoint': self.settings.azure_openai_endpoint,
                'deployment': self.settings.azure_openai_deployment,
                'timestamp': time.time()
            }
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'endpoint': self.settings.azure_openai_endpoint,
                'deployment': self.settings.azure_openai_deployment,
                'timestamp': time.time()
            }
    
    def reset_metrics(self) -> None:
        """Reset performance metrics."""
        self._request_count = 0
        self._total_tokens_used = 0
        self._total_response_time = 0.0
        
        self.logger.info("Performance metrics reset")
    
    def __repr__(self) -> str:
        """String representation of the client."""
        return (
            f"AzureOpenAIClient("
            f"deployment={self.settings.azure_openai_deployment}, "
            f"requests={self._request_count}, "
            f"tokens={self._total_tokens_used}"
            f")"
        )