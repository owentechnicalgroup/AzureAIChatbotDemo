"""
Structured logging helpers with dual observability routing.

Provides convenience classes and functions for consistent, structured logging
with automatic routing between Application Logging and AI Chat Observability systems.

Routes based on log_type:
- Application Logging: SYSTEM, SECURITY, PERFORMANCE, AZURE_OPENAI
- AI Chat Observability: CONVERSATION
"""

import logging
import uuid
import time
from typing import Optional, Dict, Any, Union
from functools import wraps

# Import dual observability routing system
from src.observability.telemetry_service import route_log_by_type, get_application_logger, get_chat_observer


class StructuredLogger:
    """Helper class for structured logging with dual observability routing.
    
    Routes logs based on log_type:
    - Application Logging: SYSTEM, SECURITY, PERFORMANCE, AZURE_OPENAI
    - AI Chat Observability: CONVERSATION
    
    Preserves all existing method signatures for backward compatibility.
    """
    
    def __init__(self, logger_name: str):
        self.logger = logging.getLogger(logger_name)
        self.operation_id = str(uuid.uuid4())
        
        # Initialize access to dual observability systems
        self._app_logger = None
        self._chat_observer = None
    
    def _get_application_logger(self):
        """Lazy initialization of application logger."""
        if self._app_logger is None:
            self._app_logger = get_application_logger()
        return self._app_logger
    
    def _get_chat_observer(self):
        """Lazy initialization of chat observer."""
        if self._chat_observer is None:
            self._chat_observer = get_chat_observer()
        return self._chat_observer
    
    def _route_log(self, log_type: str, log_data: Dict[str, Any]) -> None:
        """Route log to appropriate observability system based on log_type."""
        # Ensure operation_id is included for correlation
        if 'operation_id' not in log_data:
            log_data['operation_id'] = self.operation_id
            
        # Route using the central routing function
        route_log_by_type(log_type, log_data)
    
    def log_conversation_event(self, 
                             message: str,
                             conversation_id: str,
                             user_id: Optional[str] = None,
                             session_id: Optional[str] = None,
                             turn_number: Optional[int] = None,
                             message_length: Optional[int] = None,
                             level: str = 'INFO'):
        """Log conversation-related events with proper field mapping.
        
        Routes to AI Chat Observability system for conversation analysis.
        """
        log_data = {
            'message': message,
            'log_type': 'CONVERSATION',
            'conversation_id': conversation_id,
            'user_id': user_id or 'anonymous',
            'session_id': session_id,
            'turn_number': turn_number,
            'message_length': message_length,
            'level': level,
            'operation_type': 'conversation',
            'component': 'chatbot',
            'event_type': 'user_interaction',
            'event_category': 'conversation',
            'operation_name': 'chatbot.conversation',
        }
        
        # Route to chat observability system
        self._route_log('CONVERSATION', log_data)
    
    def log_azure_operation(self,
                           message: str,
                           resource_type: str,
                           resource_name: str,
                           operation_type: str,
                           duration: Optional[float] = None,
                           success: bool = True,
                           error_type: Optional[str] = None,
                           error_code: Optional[str] = None,
                           level: str = 'INFO'):
        """Log Azure service operations with proper field mapping.
        
        Routes to Application Logging system based on resource type.
        """
        # Determine log_type based on resource_type
        if 'openai' in resource_type.lower() or 'cognitive' in resource_type.lower():
            log_type = 'AZURE_OPENAI'
        elif 'key_vault' in resource_type.lower() or 'credential' in resource_type.lower():
            log_type = 'SECURITY'
        else:
            log_type = 'SYSTEM'
            
        log_data = {
            'message': message,
            'log_type': log_type,
            'resource_type': resource_type,
            'resource_name': resource_name,
            'operation_type': operation_type,
            'duration': duration,
            'success': success,
            'error_type': error_type,
            'error_code': error_code,
            'level': level,
            'component': 'azure_client',
            'event_type': 'azure_operation' if success else 'azure_error',
            'event_category': 'azure_service',
            'operation_name': f"azure.{resource_type}.{operation_type}",
        }
        
        # Route to application logging system
        self._route_log(log_type, log_data)
    
    def log_performance_metrics(
        self,
        operation: str,
        duration: float,
        success: bool = True,
        tokens_used: Optional[int] = None,
        error_message: Optional[str] = None,
        **additional_context
    ) -> None:
        """Log performance metrics with safe numeric values."""
        
        # Ensure we have valid numeric values
        safe_duration = float(duration) if duration is not None else 0.0
        safe_tokens = int(tokens_used) if tokens_used is not None else 0
        
        # Extract additional performance metrics from context
        tokens_prompt = additional_context.get('tokens_prompt', 0)
        tokens_completion = additional_context.get('tokens_completion', 0)
        request_size = additional_context.get('request_size', 0)
        response_size = additional_context.get('response_size', 0)
        
        # Ensure all metrics are valid numbers
        safe_tokens_prompt = int(tokens_prompt) if tokens_prompt is not None else 0
        safe_tokens_completion = int(tokens_completion) if tokens_completion is not None else 0
        safe_request_size = int(request_size) if request_size is not None else 0
        safe_response_size = int(response_size) if response_size is not None else 0
        
        log_data = {
            'message': f"Performance metrics for {operation}",
            'log_type': 'PERFORMANCE',
            'event_type': 'performance',
            'event_category': 'performance',
            'operation_type': operation,
            'component': additional_context.get('component', 'metrics'),
            'duration': safe_duration,
            'response_time': safe_duration,  # Alias for duration
            'success': bool(success),
            'tokens_total': safe_tokens,
            'tokens_prompt': safe_tokens_prompt,
            'tokens_completion': safe_tokens_completion,
            'request_size': safe_request_size,
            'response_size': safe_response_size,
            'level': 'INFO' if success else 'ERROR',
            'operation_name': additional_context.get('operation_name', f'performance.{operation}'),
            'resource_type': additional_context.get('resource_type', 'application'),
            'resource_name': additional_context.get('resource_name', operation)
        }
        
        # Add error context if present
        if not success and error_message:
            log_data['error_message'] = error_message
            log_data['error_type'] = additional_context.get('error_type', 'Unknown')
        
        # Remove any remaining None values to prevent conversion errors
        log_data = {k: v for k, v in log_data.items() if v is not None}
        
        # Route to performance logging system
        self._route_log('PERFORMANCE', log_data)
    
    def log_authentication_event(self,
                                message: str,
                                credential_type: str,
                                success: bool,
                                duration: Optional[float] = None,
                                error_type: Optional[str] = None,
                                resource_name: Optional[str] = None):
        """Log authentication events with proper field mapping.
        
        Routes to Application Logging system for security auditing.
        """
        log_data = {
            'message': message,
            'log_type': 'SECURITY',
            'credential_type': credential_type,
            'success': success,
            'duration': duration,
            'error_type': error_type,
            'resource_name': resource_name or credential_type,
            'level': 'INFO' if success else 'ERROR',
            'operation_type': 'authentication',
            'component': 'auth',
            'event_type': 'auth_success' if success else 'auth_failure',
            'event_category': 'security',
            'operation_name': f"auth.{credential_type}",
            'resource_type': 'credential'
        }
        
        # Route to application logging system
        self._route_log('SECURITY', log_data)
    
    def log_key_vault_operation(self,
                               message: str,
                               secret_name: str,
                               operation: str,
                               success: bool,
                               duration: Optional[float] = None,
                               error_type: Optional[str] = None):
        """Log Key Vault operations with proper field mapping.
        
        Routes to Application Logging system for security auditing.
        """
        log_data = {
            'message': message,
            'log_type': 'SECURITY',
            'secret_name': secret_name,
            'resource_type': 'key_vault',
            'resource_name': secret_name,
            'operation_type': operation,
            'success': success,
            'duration': duration,
            'error_type': error_type,
            'level': 'INFO' if success else 'ERROR',
            'component': 'key_vault_client',
            'event_type': 'key_vault_success' if success else 'key_vault_error',
            'event_category': 'security',
            'operation_name': f"key_vault.{operation}"
        }
        
        # Route to application logging system
        self._route_log('SECURITY', log_data)
    
    # Standard logging methods for backward compatibility
    def debug(self, message: str, **kwargs):
        """Log debug message - routes to application logging as SYSTEM."""
        log_data = {
            'message': message,
            'level': 'DEBUG',
            'operation_type': 'debug',
            'component': 'application',
            'event_type': 'debug_log',
            'event_category': 'system',
            **kwargs
        }
        self._route_log('SYSTEM', log_data)
    
    def info(self, message: str, **kwargs):
        """Log info message - routes to application logging as SYSTEM."""
        log_data = {
            'message': message,
            'level': 'INFO',
            'operation_type': 'info',
            'component': 'application',
            'event_type': 'info_log',
            'event_category': 'system',
            **kwargs
        }
        self._route_log('SYSTEM', log_data)
    
    def warning(self, message: str, **kwargs):
        """Log warning message - routes to application logging as SYSTEM."""
        log_data = {
            'message': message,
            'level': 'WARNING',
            'operation_type': 'warning',
            'component': 'application',
            'event_type': 'warning_log',
            'event_category': 'system',
            **kwargs
        }
        self._route_log('SYSTEM', log_data)
    
    def error(self, message: str, **kwargs):
        """Log error message - routes to application logging as SYSTEM."""
        log_data = {
            'message': message,
            'level': 'ERROR',
            'operation_type': 'error',
            'component': 'application',
            'event_type': 'error_log',
            'event_category': 'system',
            **kwargs
        }
        self._route_log('SYSTEM', log_data)

def log_operation(operation_name: str, component: str = None, resource_type: str = None):
    """Decorator to automatically log function operations with dual observability routing.
    
    Routes to appropriate observability system based on resource_type:
    - OpenAI/Cognitive resources → AZURE_OPENAI → Application Logging
    - Key Vault/Credential resources → SECURITY → Application Logging
    - Other resources → SYSTEM → Application Logging
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = StructuredLogger(func.__module__)
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                # Log success via dual routing system
                logger.log_azure_operation(
                    message=f"Successfully completed {operation_name}",
                    resource_type=resource_type or component or func.__module__.split('.')[-1],
                    resource_name=func.__name__,
                    operation_type=operation_name,
                    duration=duration,
                    success=True
                )
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                
                # Log failure via dual routing system
                logger.log_azure_operation(
                    message=f"Failed to complete {operation_name}: {str(e)}",
                    resource_type=resource_type or component or func.__module__.split('.')[-1],
                    resource_name=func.__name__,
                    operation_type=operation_name,
                    duration=duration,
                    success=False,
                    error_type=type(e).__name__,
                    level='ERROR'
                )
                
                raise
                
        return wrapper
    return decorator

# Convenience functions for common logging patterns
def log_startup_event(message: str, component: str, success: bool = True, error_type: str = None):
    """Log application startup events.
    
    Routes to Application Logging system as SYSTEM log type.
    """
    logger = StructuredLogger('startup')
    # This will route to Application Logging as SYSTEM log type
    logger.log_azure_operation(
        message=message,
        resource_type='application',
        resource_name=component,
        operation_type='startup',
        success=success,
        error_type=error_type,
        level='INFO' if success else 'ERROR'
    )


def log_config_load(message: str, config_source: str, success: bool = True, error_type: str = None):
    """Log configuration loading events.
    
    Routes to Application Logging system as SYSTEM log type.
    """
    logger = StructuredLogger('config')
    # This will route to Application Logging as SYSTEM log type
    logger.log_azure_operation(
        message=message,
        resource_type='configuration',
        resource_name=config_source,
        operation_type='load_config',
        success=success,
        error_type=error_type,
        level='INFO' if success else 'ERROR'
    )


def log_health_check(message: str, component: str, success: bool = True, duration: float = None, error_type: str = None):
    """Log health check events.
    
    Routes to Application Logging system as SYSTEM log type.
    """
    logger = StructuredLogger('health')
    # This will route to Application Logging as SYSTEM log type
    logger.log_azure_operation(
        message=message,
        resource_type='health_check',
        resource_name=component,
        operation_type='health_check',
        duration=duration,
        success=success,
        error_type=error_type,
        level='INFO' if success else 'ERROR'
    )

def get_logger(name: str, **context) -> StructuredLogger:
    """
    Get a configured structured logger with optional context binding.
    
    Args:
        name: Logger name (usually __name__)
        **context: Additional context to bind to logger
        
    Returns:
        StructuredLogger instance with dual observability routing
    """
    logger = StructuredLogger(name)
    
    # Bind any provided context
    if context:
        for key, value in context.items():
            setattr(logger, key, value)
    
    return logger


# Update existing convenience functions to use the fixed performance logging
def log_performance_metrics(
    operation: str,
    duration: float,
    success: bool = True,
    tokens_used: Optional[int] = None,
    error_message: Optional[str] = None,
    **additional_context
) -> None:
    """Log performance metrics with safe numeric values - standalone function."""
    logger = StructuredLogger('performance')
    logger.log_performance_metrics(
        operation=operation,
        duration=duration,
        success=success,
        tokens_used=tokens_used,
        error_message=error_message,
        **additional_context
    )
