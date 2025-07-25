"""
Structured logging helpers for Azure Log Analytics integration.
Provides convenience classes and functions for consistent, structured logging.
"""

import logging
import uuid
import time
from typing import Optional, Dict, Any, Union
from functools import wraps


class StructuredLogger:
    """Helper class for structured logging with proper Azure Log Analytics field mapping."""
    
    def __init__(self, logger_name: str):
        self.logger = logging.getLogger(logger_name)
        self.operation_id = str(uuid.uuid4())
    
    def log_conversation_event(self, 
                             message: str,
                             conversation_id: str,
                             user_id: Optional[str] = None,
                             session_id: Optional[str] = None,
                             turn_number: Optional[int] = None,
                             message_length: Optional[int] = None,
                             level: str = 'INFO'):
        """Log conversation-related events with proper field mapping."""
        extra = {
            'log_type': 'CONVERSATION',
            'conversation_id': conversation_id,
            'user_id': user_id or 'anonymous',
            'session_id': session_id,
            'operation_type': 'conversation',
            'component': 'chatbot',
            'event_type': 'user_interaction',
            'event_category': 'conversation',
            'operation_id': self.operation_id,
            'operation_name': 'chatbot.conversation',
        }
        
        if turn_number is not None:
            extra['turn_number'] = turn_number
        if message_length is not None:
            extra['message_length'] = message_length
            
        getattr(self.logger, level.lower())(message, extra=extra)
    
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
        """Log Azure service operations with proper field mapping."""
        # Determine log_type based on resource_type
        if 'openai' in resource_type.lower() or 'cognitive' in resource_type.lower():
            log_type = 'AZURE_OPENAI'
        elif 'key_vault' in resource_type.lower() or 'credential' in resource_type.lower():
            log_type = 'SECURITY'
        else:
            log_type = 'SYSTEM'
            
        extra = {
            'log_type': log_type,
            'resource_type': resource_type,
            'resource_name': resource_name,
            'operation_type': operation_type,
            'component': 'azure_client',
            'event_type': 'azure_operation' if success else 'azure_error',
            'event_category': 'azure_service',
            'success': success,
            'operation_id': self.operation_id,
            'operation_name': f"azure.{resource_type}.{operation_type}",
        }
        
        if duration is not None:
            extra['duration'] = duration
        if not success:
            if error_type:
                extra['error_type'] = error_type
            if error_code:
                extra['error_code'] = error_code
            
        getattr(self.logger, level.lower())(message, extra=extra)
    
    def log_performance_metrics(self,
                               message: str,
                               response_time: float,
                               tokens_prompt: Optional[int] = None,
                               tokens_completion: Optional[int] = None,
                               tokens_total: Optional[int] = None,
                               request_size: Optional[int] = None,
                               response_size: Optional[int] = None,
                               operation_name: Optional[str] = None):
        """Log performance metrics with proper field mapping."""
        extra = {
            'log_type': 'PERFORMANCE',
            'response_time': response_time,
            'operation_type': 'performance',
            'component': 'metrics',
            'event_type': 'performance_measurement',
            'event_category': 'performance',
            'operation_id': self.operation_id,
            'operation_name': operation_name or 'metrics.performance',
        }
        
        if tokens_prompt is not None:
            extra['tokens_prompt'] = tokens_prompt
        if tokens_completion is not None:
            extra['tokens_completion'] = tokens_completion
        if tokens_total is not None:
            extra['tokens_total'] = tokens_total
        if request_size is not None:
            extra['request_size'] = request_size
        if response_size is not None:
            extra['response_size'] = response_size
            
        self.logger.info(message, extra=extra)
    
    def log_authentication_event(self,
                                message: str,
                                credential_type: str,
                                success: bool,
                                duration: Optional[float] = None,
                                error_type: Optional[str] = None,
                                resource_name: Optional[str] = None):
        """Log authentication events with proper field mapping."""
        extra = {
            'log_type': 'SECURITY',
            'credential_type': credential_type,
            'operation_type': 'authentication',
            'component': 'auth',
            'event_type': 'auth_success' if success else 'auth_failure',
            'event_category': 'security',
            'success': success,
            'operation_id': self.operation_id,
            'operation_name': f"auth.{credential_type}",
            'resource_type': 'credential',
            'resource_name': resource_name or credential_type,
        }
        
        if duration is not None:
            extra['duration'] = duration
        if not success and error_type:
            extra['error_type'] = error_type
            
        level = 'info' if success else 'error'
        getattr(self.logger, level)(message, extra=extra)
    
    def log_key_vault_operation(self,
                               message: str,
                               secret_name: str,
                               operation: str,
                               success: bool,
                               duration: Optional[float] = None,
                               error_type: Optional[str] = None):
        """Log Key Vault operations with proper field mapping."""
        extra = {
            'log_type': 'SECURITY',
            'secret_name': secret_name,
            'resource_type': 'key_vault',
            'resource_name': secret_name,
            'operation_type': operation,
            'component': 'key_vault_client',
            'event_type': 'key_vault_success' if success else 'key_vault_error',
            'event_category': 'security',
            'success': success,
            'operation_id': self.operation_id,
            'operation_name': f"key_vault.{operation}",
        }
        
        if duration is not None:
            extra['duration'] = duration
        if not success and error_type:
            extra['error_type'] = error_type
            
        level = 'info' if success else 'error'
        getattr(self.logger, level)(message, extra=extra)

def log_operation(operation_name: str, component: str = None, resource_type: str = None):
    """Decorator to automatically log function operations with proper field mapping."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = StructuredLogger(func.__module__)
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
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
    """Log application startup events."""
    logger = StructuredLogger('startup')
    # This will use log_type 'SYSTEM' due to the resource_type logic in log_azure_operation
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
    """Log configuration loading events."""
    logger = StructuredLogger('config')
    # This will use log_type 'SYSTEM' due to the resource_type logic in log_azure_operation
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
    """Log health check events."""
    logger = StructuredLogger('health')
    # This will use log_type 'SYSTEM' due to the resource_type logic in log_azure_operation
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
