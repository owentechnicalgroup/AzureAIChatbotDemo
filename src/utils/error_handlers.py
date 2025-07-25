"""
Custom exception classes and error handling utilities.
Task 12: Custom exception classes with error recovery suggestions and user-friendly formatting.
"""

from typing import Optional, Dict, Any, List
import structlog

logger = structlog.get_logger(__name__)


class ChatbotBaseError(Exception):
    """Base exception class for chatbot application."""
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        recovery_suggestions: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize base error.
        
        Args:
            message: Error message
            error_code: Unique error code for identification
            recovery_suggestions: List of recovery suggestions for the user
            context: Additional context information
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.recovery_suggestions = recovery_suggestions or []
        self.context = context or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary format."""
        return {
            'error_type': self.__class__.__name__,
            'message': self.message,
            'error_code': self.error_code,
            'recovery_suggestions': self.recovery_suggestions,
            'context': self.context
        }
    
    def get_user_friendly_message(self) -> str:
        """Get user-friendly error message."""
        return self.message


class ConfigurationError(ChatbotBaseError):
    """Raised when there are configuration-related errors."""
    
    def __init__(
        self,
        message: str,
        missing_config: Optional[str] = None,
        config_file: Optional[str] = None
    ):
        recovery_suggestions = [
            "Check your .env file for missing or incorrect configuration",
            "Verify that all required environment variables are set",
            "Run the setup script to configure the application"
        ]
        
        if missing_config:
            recovery_suggestions.insert(0, f"Set the {missing_config} configuration value")
        
        super().__init__(
            message=message,
            error_code="CONFIG_ERROR",
            recovery_suggestions=recovery_suggestions,
            context={
                'missing_config': missing_config,
                'config_file': config_file
            }
        )


class AzureOpenAIError(ChatbotBaseError):
    """Raised when there are Azure OpenAI service-related errors."""
    
    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        request_id: Optional[str] = None,
        endpoint: Optional[str] = None
    ):
        recovery_suggestions = []
        
        # Add specific recovery suggestions based on the error
        if status_code == 401:
            recovery_suggestions.extend([
                "Check your Azure OpenAI API key",
                "Verify that your API key has not expired",
                "Ensure you're using the correct endpoint"
            ])
        elif status_code == 403:
            recovery_suggestions.extend([
                "Check that your subscription has access to Azure OpenAI",
                "Verify that the deployment name is correct",
                "Contact your administrator for access permissions"
            ])
        elif status_code == 429:
            recovery_suggestions.extend([
                "Wait a few moments before retrying",
                "Check your rate limits and quota",
                "Consider upgrading your service tier"
            ])
        elif status_code == 500:
            recovery_suggestions.extend([
                "Azure OpenAI service may be temporarily unavailable",
                "Wait a few minutes and try again",
                "Check Azure service status page"
            ])
        else:
            recovery_suggestions.extend([
                "Check your internet connection",
                "Verify your Azure OpenAI configuration",
                "Try again in a few moments"
            ])
        
        super().__init__(
            message=message,
            error_code=f"AZURE_OPENAI_ERROR_{status_code}" if status_code else "AZURE_OPENAI_ERROR",
            recovery_suggestions=recovery_suggestions,
            context={
                'status_code': status_code,
                'request_id': request_id,
                'endpoint': endpoint
            }
        )


class ConversationError(ChatbotBaseError):
    """Raised when there are conversation management errors."""
    
    def __init__(
        self,
        message: str,
        conversation_id: Optional[str] = None,
        operation: Optional[str] = None
    ):
        recovery_suggestions = [
            "Try starting a new conversation",
            "Check if the conversation data is corrupted",
            "Clear the conversation history if needed"
        ]
        
        if operation == "load":
            recovery_suggestions.extend([
                "Check if the conversation file exists",
                "Verify the conversation file format",
                "Try loading a different conversation"
            ])
        elif operation == "save":
            recovery_suggestions.extend([
                "Check disk space availability",
                "Verify write permissions",
                "Try saving to a different location"
            ])
        
        super().__init__(
            message=message,
            error_code="CONVERSATION_ERROR",
            recovery_suggestions=recovery_suggestions,
            context={
                'conversation_id': conversation_id,
                'operation': operation
            }
        )


class KeyVaultError(ChatbotBaseError):
    """Raised when there are Azure Key Vault access errors."""
    
    def __init__(
        self,
        message: str,
        vault_url: Optional[str] = None,
        secret_name: Optional[str] = None
    ):
        recovery_suggestions = [
            "Check your Azure authentication (try 'az login')",
            "Verify Key Vault access permissions",
            "Ensure you have the required RBAC roles",
            "Check if Key Vault URL is correct"
        ]
        
        super().__init__(
            message=message,
            error_code="KEYVAULT_ERROR",
            recovery_suggestions=recovery_suggestions,
            context={
                'vault_url': vault_url,
                'secret_name': secret_name
            }
        )


class AuthenticationError(ChatbotBaseError):
    """Raised when there are authentication-related errors."""
    
    def __init__(
        self,
        message: str,
        auth_method: Optional[str] = None,
        service: Optional[str] = None
    ):
        recovery_suggestions = [
            "Check your authentication credentials",
            "Try logging in again (az login)",
            "Verify that your account has the required permissions"
        ]
        
        if service == "azure_openai":
            recovery_suggestions.extend([
                "Check your Azure OpenAI API key",
                "Verify that your key has not expired"
            ])
        elif service == "key_vault":
            recovery_suggestions.extend([
                "Check your Key Vault access permissions",
                "Verify RBAC role assignments"
            ])
        
        super().__init__(
            message=message,
            error_code="AUTH_ERROR",
            recovery_suggestions=recovery_suggestions,
            context={
                'auth_method': auth_method,
                'service': service
            }
        )


class ValidationError(ChatbotBaseError):
    """Raised when input validation fails."""
    
    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        expected_type: Optional[str] = None
    ):
        recovery_suggestions = [
            "Check your input format",
            "Refer to the documentation for valid values"
        ]
        
        if field:
            recovery_suggestions.insert(0, f"Check the '{field}' field")
        
        if expected_type:
            recovery_suggestions.append(f"Expected type: {expected_type}")
        
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            recovery_suggestions=recovery_suggestions,
            context={
                'field': field,
                'value': str(value) if value is not None else None,
                'expected_type': expected_type
            }
        )


class NetworkError(ChatbotBaseError):
    """Raised when there are network connectivity issues."""
    
    def __init__(
        self,
        message: str,
        endpoint: Optional[str] = None,
        timeout: Optional[float] = None
    ):
        recovery_suggestions = [
            "Check your internet connection",
            "Verify that the service endpoint is accessible",
            "Try again in a few moments",
            "Check firewall and proxy settings"
        ]
        
        if timeout:
            recovery_suggestions.append(f"Consider increasing the timeout (current: {timeout}s)")
        
        super().__init__(
            message=message,
            error_code="NETWORK_ERROR",
            recovery_suggestions=recovery_suggestions,
            context={
                'endpoint': endpoint,
                'timeout': timeout
            }
        )


class RateLimitError(ChatbotBaseError):
    """Raised when rate limits are exceeded."""
    
    def __init__(
        self,
        message: str,
        retry_after: Optional[int] = None,
        service: Optional[str] = None
    ):
        recovery_suggestions = [
            "Wait before making another request",
            "Consider upgrading your service tier for higher limits",
            "Implement request batching if possible"
        ]
        
        if retry_after:
            recovery_suggestions.insert(0, f"Wait {retry_after} seconds before retrying")
        
        super().__init__(
            message=message,
            error_code="RATE_LIMIT_ERROR",
            recovery_suggestions=recovery_suggestions,
            context={
                'retry_after': retry_after,
                'service': service
            }
        )


def handle_error(
    error: Exception,
    context: Optional[Dict[str, Any]] = None,
    log_error: bool = True
) -> ChatbotBaseError:
    """
    Handle and convert various exceptions to chatbot-specific errors.
    
    Args:
        error: The original exception
        context: Additional context information
        log_error: Whether to log the error
        
    Returns:
        ChatbotBaseError instance
    """
    if isinstance(error, ChatbotBaseError):
        # Already a chatbot error, just log and return
        if log_error:
            logger.error(
                "Chatbot error occurred",
                error_type=error.__class__.__name__,
                message=error.message,
                error_code=error.error_code,
                context=error.context
            )
        return error
    
    # Convert common exceptions to chatbot errors
    error_context = context or {}
    
    # Azure-specific errors
    if "azure" in str(type(error)).lower():
        if "authentication" in str(error).lower():
            converted_error = AuthenticationError(
                message=f"Azure authentication failed: {str(error)}",
                service="azure"
            )
        elif "keyvault" in str(error).lower() or "vault" in str(error).lower():
            converted_error = KeyVaultError(
                message=f"Key Vault error: {str(error)}"
            )
        else:
            converted_error = AzureOpenAIError(
                message=f"Azure service error: {str(error)}"
            )
    
    # OpenAI-specific errors
    elif "openai" in str(type(error)).lower():
        if "rate" in str(error).lower() or "429" in str(error):
            converted_error = RateLimitError(
                message=f"Rate limit exceeded: {str(error)}",
                service="openai"
            )
        elif "auth" in str(error).lower() or "401" in str(error):
            converted_error = AuthenticationError(
                message=f"OpenAI authentication failed: {str(error)}",
                service="azure_openai"
            )
        else:
            converted_error = AzureOpenAIError(
                message=f"Azure OpenAI error: {str(error)}"
            )
    
    # Network-related errors
    elif any(net_err in str(type(error)).lower() for net_err in ['connection', 'timeout', 'network']):
        converted_error = NetworkError(
            message=f"Network error: {str(error)}"
        )
    
    # Validation errors
    elif "validation" in str(type(error)).lower() or isinstance(error, ValueError):
        converted_error = ValidationError(
            message=f"Validation error: {str(error)}"
        )
    
    # Generic error
    else:
        converted_error = ChatbotBaseError(
            message=f"Unexpected error: {str(error)}",
            error_code="GENERIC_ERROR",
            recovery_suggestions=[
                "Try the operation again",
                "Check the application logs for more details",
                "Contact support if the problem persists"
            ]
        )
    
    # Add context if provided
    if error_context:
        converted_error.context.update(error_context)
    
    if log_error:
        logger.error(
            "Error handled and converted",
            original_error_type=type(error).__name__,
            original_error=str(error),
            converted_error_type=converted_error.__class__.__name__,
            error_code=converted_error.error_code,
            context=converted_error.context
        )
    
    return converted_error


def format_error_for_user(error: ChatbotBaseError) -> str:
    """
    Format error for user display.
    
    Args:
        error: ChatbotBaseError instance
        
    Returns:
        Formatted error message for user
    """
    lines = [
        f"❌ Error: {error.get_user_friendly_message()}"
    ]
    
    if error.recovery_suggestions:
        lines.append("\n💡 Suggestions:")
        for i, suggestion in enumerate(error.recovery_suggestions, 1):
            lines.append(f"  {i}. {suggestion}")
    
    if error.error_code:
        lines.append(f"\n🔍 Error Code: {error.error_code}")
    
    return "\n".join(lines)


def is_retryable_error(error: Exception) -> bool:
    """
    Check if an error is retryable.
    
    Args:
        error: Exception to check
        
    Returns:
        True if error is retryable, False otherwise
    """
    # Convert to chatbot error first
    chatbot_error = handle_error(error, log_error=False)
    
    # Check if it's a retryable error type
    retryable_types = [
        NetworkError,
        RateLimitError
    ]
    
    if isinstance(chatbot_error, tuple(retryable_types)):
        return True
    
    # Check for specific error codes
    if isinstance(chatbot_error, AzureOpenAIError):
        # HTTP status codes that are typically retryable
        status_code = chatbot_error.context.get('status_code')
        retryable_status_codes = [429, 500, 502, 503, 504]
        return status_code in retryable_status_codes
    
    return False


def get_retry_delay(error: Exception, attempt: int = 1) -> float:
    """
    Get suggested retry delay for an error.
    
    Args:
        error: Exception that occurred
        attempt: Current attempt number
        
    Returns:
        Suggested delay in seconds
    """
    chatbot_error = handle_error(error, log_error=False)
    
    # Check for explicit retry-after
    if isinstance(chatbot_error, RateLimitError):
        retry_after = chatbot_error.context.get('retry_after')
        if retry_after:
            return float(retry_after)
    
    # Exponential backoff: 2^attempt seconds, capped at 60
    base_delay = min(2 ** attempt, 60)
    
    # Add some jitter to avoid thundering herd
    import random
    jitter = random.uniform(0.1, 0.5)
    
    return base_delay + jitter