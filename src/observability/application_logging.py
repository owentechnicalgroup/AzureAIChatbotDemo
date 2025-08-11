"""
Application logging system for infrastructure, performance, security, and system events.

Handles log types: SYSTEM, SECURITY, PERFORMANCE, AZURE_OPENAI
Routes to: Standard Azure Application Insights workspace
Purpose: Performance monitoring, error tracking, security auditing

Preserves existing StructuredLogger methods for backward compatibility.
"""

import logging
import uuid
import time
from typing import Optional, Dict, Any, Union, Literal
from functools import wraps
from datetime import datetime

import structlog
from structlog.typing import FilteringBoundLogger

from .telemetry_service import ApplicationLogContext, create_operation_context

logger = structlog.get_logger(__name__).bind(log_type="SYSTEM")


class ApplicationLogger:
    """
    Application infrastructure logging with proper Azure Log Analytics field mapping.
    
    Handles SYSTEM, SECURITY, PERFORMANCE, and AZURE_OPENAI log types.
    Routes to standard Azure Application Insights workspace.
    """
    
    def __init__(self, logger_name: str):
        """
        Initialize application logger.
        
        Args:
            logger_name: Logger namespace for OpenTelemetry routing
        """
        self.logger = logging.getLogger(logger_name)
        self.structlog_logger = structlog.get_logger(logger_name)
        self.operation_id = str(uuid.uuid4())
    
    def route_application_log(self, log_type: str, log_data: Dict[str, Any]) -> None:
        """
        Route application log to appropriate handler based on log_type.
        
        Args:
            log_type: One of SYSTEM, SECURITY, PERFORMANCE, AZURE_OPENAI
            log_data: Structured log data with context
        """
        try:
            if log_type == 'SYSTEM':
                self._handle_system_log(log_data)
            elif log_type == 'SECURITY':
                self._handle_security_log(log_data)
            elif log_type == 'PERFORMANCE':
                self._handle_performance_log(log_data)
            elif log_type == 'AZURE_OPENAI':
                self._handle_azure_openai_log(log_data)
            else:
                # Fallback for unknown application log types
                self._handle_system_log(log_data)
                
        except Exception as e:
            # Ensure log routing failures don't break the application
            logger.error(
                "Failed to route application log",
                log_type=log_type,
                error=str(e),
                error_type=type(e).__name__,
                fallback_data=log_data
            )
    
    def _handle_system_log(self, log_data: Dict[str, Any]) -> None:
        """Handle SYSTEM log type - Application lifecycle, configuration, health checks, errors."""
        extra = self._prepare_base_extra('SYSTEM', log_data)
        
        # Add system-specific fields
        extra.update({
            'operation_type': log_data.get('operation_type', 'system'),
            'component': log_data.get('component', 'application'),
            'event_type': log_data.get('event_type', 'system_event'),
            'event_category': 'system',
            'operation_name': log_data.get('operation_name', 'system.operation'),
        })
        
        level = log_data.get('level', 'INFO').lower()
        message = log_data.get('message', 'System event')
        
        getattr(self.logger, level)(message, extra=extra)
    
    def _handle_security_log(self, log_data: Dict[str, Any]) -> None:
        """Handle SECURITY log type - Authentication, Key Vault operations, credential management."""
        extra = self._prepare_base_extra('SECURITY', log_data)
        
        # Add security-specific fields
        extra.update({
            'operation_type': log_data.get('operation_type', 'security'),
            'component': log_data.get('component', 'auth'),
            'event_type': log_data.get('event_type', 'security_event'),
            'event_category': 'security',
            'operation_name': log_data.get('operation_name', 'security.operation'),
            'credential_type': log_data.get('credential_type'),
            'resource_type': log_data.get('resource_type', 'credential'),
            'resource_name': log_data.get('resource_name'),
            'secret_name': log_data.get('secret_name'),
        })
        
        level = log_data.get('level', 'INFO').lower()
        message = log_data.get('message', 'Security event')
        
        getattr(self.logger, level)(message, extra=extra)
    
    def _handle_performance_log(self, log_data: Dict[str, Any]) -> None:
        """Handle PERFORMANCE log type - Response times, throughput metrics, resource usage."""
        extra = self._prepare_base_extra('PERFORMANCE', log_data)
        
        # Add performance-specific fields
        extra.update({
            'operation_type': log_data.get('operation_type', 'performance'),
            'component': log_data.get('component', 'metrics'),
            'event_type': log_data.get('event_type', 'performance_measurement'),
            'event_category': 'performance',
            'operation_name': log_data.get('operation_name', 'metrics.performance'),
        })
        
        # Add performance metrics
        if 'response_time' in log_data:
            extra['response_time'] = float(log_data['response_time'])
        if 'duration' in log_data:
            extra['duration'] = float(log_data['duration'])
        if 'tokens_prompt' in log_data:
            extra['tokens_prompt'] = int(log_data['tokens_prompt'])
        if 'tokens_completion' in log_data:
            extra['tokens_completion'] = int(log_data['tokens_completion'])
        if 'tokens_total' in log_data:
            extra['tokens_total'] = int(log_data['tokens_total'])
        if 'request_size' in log_data:
            extra['request_size'] = int(log_data['request_size'])
        if 'response_size' in log_data:
            extra['response_size'] = int(log_data['response_size'])
        
        level = log_data.get('level', 'INFO').lower()
        message = log_data.get('message', 'Performance metric')
        
        getattr(self.logger, level)(message, extra=extra)
    
    def _handle_azure_openai_log(self, log_data: Dict[str, Any]) -> None:
        """Handle AZURE_OPENAI log type - Azure OpenAI API calls, responses, token usage (API-level only)."""
        extra = self._prepare_base_extra('AZURE_OPENAI', log_data)
        
        # Add Azure OpenAI-specific fields
        extra.update({
            'operation_type': log_data.get('operation_type', 'azure_openai'),
            'component': log_data.get('component', 'azure_client'),
            'event_type': log_data.get('event_type', 'azure_operation'),
            'event_category': 'azure_service',
            'operation_name': log_data.get('operation_name', 'azure.openai.operation'),
            'resource_type': log_data.get('resource_type', 'openai'),
            'resource_name': log_data.get('resource_name'),
        })
        
        level = log_data.get('level', 'INFO').lower()
        message = log_data.get('message', 'Azure OpenAI operation')
        
        getattr(self.logger, level)(message, extra=extra)
    
    def _prepare_base_extra(self, log_type: str, log_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare base extra fields for all application logs.
        
        Args:
            log_type: The log type (SYSTEM, SECURITY, PERFORMANCE, AZURE_OPENAI)
            log_data: Original log data
            
        Returns:
            Dict with base fields for Azure Log Analytics
        """
        extra = {
            'log_type': log_type,
            'operation_id': log_data.get('operation_id', self.operation_id),
        }
        
        # Only include fields with valid values (OpenTelemetry doesn't accept None)
        if log_data.get('success') is not None:
            extra['success'] = log_data.get('success')
        if log_data.get('error_type') is not None:
            extra['error_type'] = log_data.get('error_type')
        if log_data.get('error_code') is not None:
            extra['error_code'] = log_data.get('error_code')
            
        return extra
    
    # Preserve existing StructuredLogger method signatures for backward compatibility
    
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
            
        log_data = {
            'message': message,
            'resource_type': resource_type,
            'resource_name': resource_name,
            'operation_type': operation_type,
            'duration': duration,
            'success': success,
            'error_type': error_type,
            'error_code': error_code,
            'level': level
        }
        
        self.route_application_log(log_type, log_data)
    
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
        log_data = {
            'message': message,
            'response_time': response_time,
            'tokens_prompt': tokens_prompt,
            'tokens_completion': tokens_completion,
            'tokens_total': tokens_total,
            'request_size': request_size,
            'response_size': response_size,
            'operation_name': operation_name or 'metrics.performance',
            'level': 'INFO'
        }
        
        self.route_application_log('PERFORMANCE', log_data)
    
    def log_authentication_event(self,
                                message: str,
                                credential_type: str,
                                success: bool,
                                duration: Optional[float] = None,
                                error_type: Optional[str] = None,
                                resource_name: Optional[str] = None):
        """Log authentication events with proper field mapping."""
        log_data = {
            'message': message,
            'credential_type': credential_type,
            'success': success,
            'duration': duration,
            'error_type': error_type,
            'resource_name': resource_name or credential_type,
            'level': 'INFO' if success else 'ERROR'
        }
        
        self.route_application_log('SECURITY', log_data)
    
    def log_key_vault_operation(self,
                               message: str,
                               secret_name: str,
                               operation: str,
                               success: bool,
                               duration: Optional[float] = None,
                               error_type: Optional[str] = None):
        """Log Key Vault operations with proper field mapping."""
        log_data = {
            'message': message,
            'secret_name': secret_name,
            'resource_type': 'key_vault',
            'resource_name': secret_name,
            'operation_type': operation,
            'success': success,
            'duration': duration,
            'error_type': error_type,
            'level': 'INFO' if success else 'ERROR'
        }
        
        self.route_application_log('SECURITY', log_data)


# Convenience functions for application logging

def log_system_event(message: str, component: str, success: bool = True, error_type: str = None):
    """Log application system events."""
    from .telemetry_service import get_application_logger
    logger = get_application_logger()
    
    log_data = {
        'message': message,
        'component': component,
        'operation_type': 'system',
        'success': success,
        'error_type': error_type,
        'level': 'INFO' if success else 'ERROR'
    }
    
    logger.route_application_log('SYSTEM', log_data)


def log_security_event(message: str, credential_type: str, success: bool = True, error_type: str = None):
    """Log security events."""
    from .telemetry_service import get_application_logger
    logger = get_application_logger()
    
    log_data = {
        'message': message,
        'credential_type': credential_type,
        'operation_type': 'security',
        'success': success,
        'error_type': error_type,
        'level': 'INFO' if success else 'ERROR'
    }
    
    logger.route_application_log('SECURITY', log_data)


def log_performance_event(message: str, response_time: float, **metrics):
    """Log performance events."""
    from .telemetry_service import get_application_logger
    logger = get_application_logger()
    
    log_data = {
        'message': message,
        'response_time': response_time,
        'operation_type': 'performance',
        'level': 'INFO',
        **metrics
    }
    
    logger.route_application_log('PERFORMANCE', log_data)


def log_azure_openai_event(message: str, resource_name: str, operation_type: str, success: bool = True, **context):
    """Log Azure OpenAI API events."""
    from .telemetry_service import get_application_logger
    logger = get_application_logger()
    
    log_data = {
        'message': message,
        'resource_name': resource_name,
        'operation_type': operation_type,
        'resource_type': 'openai',
        'success': success,
        'level': 'INFO' if success else 'ERROR',
        **context
    }
    
    logger.route_application_log('AZURE_OPENAI', log_data)


def log_operation(operation_name: str, component: str = None, resource_type: str = None):
    """Decorator to automatically log function operations with proper field mapping."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            from .telemetry_service import get_application_logger
            logger = get_application_logger()
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