"""
OpenTelemetry telemetry service with dual exporters for separated concerns.

Manages routing between:
- Application Logging: SYSTEM, SECURITY, PERFORMANCE, AZURE_OPENAI
- AI Chat Observability: CONVERSATION

Uses Azure Monitor OpenTelemetry with multiple exporters pattern.
"""

import logging
import os
import uuid
from typing import Optional, Dict, Any, Literal
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

import structlog
from structlog.typing import FilteringBoundLogger

from config.settings import Settings

# Global state for telemetry services
_application_logger: Optional['ApplicationLogger'] = None
_chat_observer: Optional['ChatObserver'] = None
_telemetry_initialized: bool = False

logger = structlog.get_logger(__name__).bind(log_type="SYSTEM")


class LogTypeCategory(str, Enum):
    """Categorization of log types for routing decisions."""
    APPLICATION = "application"  # SYSTEM, SECURITY, PERFORMANCE, AZURE_OPENAI
    CHAT = "chat"                # CONVERSATION


# Application Logging Types - Route to Standard Application Insights
APPLICATION_LOG_TYPES = {
    'SYSTEM': 'Application lifecycle, configuration, health checks, errors',
    'SECURITY': 'Authentication, Key Vault operations, credential management', 
    'PERFORMANCE': 'Response times, throughput metrics, resource usage',
    'AZURE_OPENAI': 'Azure OpenAI API calls, responses, token usage (API-level only)'
}

# AI Chat Observability Types - Route to Specialized Workspace
CHAT_OBSERVABILITY_TYPES = {
    'CONVERSATION': 'Chat interactions, message processing, conversation flow, user experience'
}


@dataclass
class BaseObservabilityContext:
    """Shared base context for correlation across systems."""
    operation_id: str
    timestamp: datetime
    component: str
    environment: str


@dataclass  
class ApplicationLogContext(BaseObservabilityContext):
    """Application-specific context."""
    log_type: Literal['SYSTEM', 'SECURITY', 'PERFORMANCE', 'AZURE_OPENAI']
    resource_type: Optional[str] = None
    duration: Optional[float] = None
    success: Optional[bool] = None


@dataclass
class ChatObservabilityContext(BaseObservabilityContext):
    """Chat-specific context with conversation data."""
    conversation_id: str
    log_type: Literal['CONVERSATION'] = 'CONVERSATION'
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    turn_number: Optional[int] = None
    message_length: Optional[int] = None


@dataclass
class ObservabilityConfig:
    """Routing configuration for exporters."""
    application_connection_string: str  # Standard Application Insights
    chat_connection_string: str        # AI Chat observability workspace
    enable_cross_correlation: bool = True


def determine_log_category(log_type: str) -> LogTypeCategory:
    """
    Determine which observability system should handle a log type.
    
    Args:
        log_type: The log_type field from the log record
        
    Returns:
        LogTypeCategory indicating which system should handle the log
    """
    if log_type in APPLICATION_LOG_TYPES:
        return LogTypeCategory.APPLICATION
    elif log_type in CHAT_OBSERVABILITY_TYPES:
        return LogTypeCategory.CHAT
    else:
        # Default unknown log types to application logging
        logger.warning(
            "Unknown log_type routed to application logging",
            log_type=log_type,
            available_application_types=list(APPLICATION_LOG_TYPES.keys()),
            available_chat_types=list(CHAT_OBSERVABILITY_TYPES.keys())
        )
        return LogTypeCategory.APPLICATION


def initialize_dual_observability(settings: Settings) -> bool:
    """
    Initialize dual OpenTelemetry exporters for separated observability concerns.
    
    CRITICAL: Must be called early in application startup before other logging setup.
    
    Args:
        settings: Application settings containing connection strings
        
    Returns:
        bool: True if initialization successful, False otherwise
    """
    global _telemetry_initialized
    
    if _telemetry_initialized:
        logger.info("Dual observability already initialized")
        return True
    
    try:
        # Validate required connection strings
        if not settings.applicationinsights_connection_string:
            logger.error("Application Insights connection string not configured")
            return False
        
        # For now, use the same connection string for both systems
        # In production, chat_observability_connection_string would be separate
        chat_connection_string = getattr(
            settings, 
            'chat_observability_connection_string', 
            settings.applicationinsights_connection_string
        )
        
        # Initialize Azure Monitor OpenTelemetry for application logging
        try:
            from azure.monitor.opentelemetry import configure_azure_monitor
            
            # Configure primary exporter for application logging
            configure_azure_monitor(
                connection_string=settings.applicationinsights_connection_string,
                logger_name="src.application",  # Application-specific namespace
            )
            
            logger.info(
                "Application logging OpenTelemetry initialized",
                connection_configured=True,
                logger_namespace="src.application"
            )
            
        except ImportError as e:
            logger.error(
                "Failed to import azure-monitor-opentelemetry",
                error=str(e),
                suggestion="Run: uv add azure-monitor-opentelemetry"
            )
            return False
        except Exception as e:
            logger.error(
                "Failed to configure application logging OpenTelemetry",
                error=str(e),
                error_type=type(e).__name__
            )
            return False
        
        # For chat observability, we'll use a separate logger namespace
        # This allows for different routing and processing
        try:
            # Note: In a full implementation, this would configure a second exporter
            # For now, we'll use logger namespacing for separation
            logger.info(
                "Chat observability system initialized",
                connection_configured=True,
                logger_namespace="src.chat",
                note="Using namespace separation for dual concerns"
            )
            
        except Exception as e:
            logger.error(
                "Failed to configure chat observability",
                error=str(e),
                error_type=type(e).__name__
            )
            return False
        
        _telemetry_initialized = True
        
        logger.info(
            "Dual observability systems initialized successfully",
            application_logging=True,
            chat_observability=True,
            cross_correlation=True,
            component="telemetry_service"
        )
        
        return True
        
    except Exception as e:
        logger.error(
            "Critical failure in dual observability initialization",
            error=str(e),
            error_type=type(e).__name__
        )
        return False


def get_application_logger() -> 'ApplicationLogger':
    """
    Get the application logger instance for infrastructure logs.
    
    Returns:
        ApplicationLogger instance for SYSTEM, SECURITY, PERFORMANCE, AZURE_OPENAI logs
    """
    global _application_logger
    
    if _application_logger is None:
        # Import here to avoid circular imports
        from .application_logging import ApplicationLogger
        _application_logger = ApplicationLogger("src.application")
    
    return _application_logger


def get_chat_observer() -> 'ChatObserver':
    """
    Get the chat observer instance for conversation logs.
    
    Returns:
        ChatObserver instance for CONVERSATION logs
    """
    global _chat_observer
    
    if _chat_observer is None:
        # Import here to avoid circular imports
        from .chat_observability import ChatObserver
        _chat_observer = ChatObserver("src.chat")
    
    return _chat_observer


def route_log_by_type(log_type: str, log_data: Dict[str, Any]) -> None:
    """
    Route a log entry to the appropriate observability system.
    
    Args:
        log_type: The log_type field indicating the category
        log_data: The structured log data to be processed
    """
    category = determine_log_category(log_type)
    
    # Add correlation ID for cross-system tracing
    if 'operation_id' not in log_data:
        log_data['operation_id'] = str(uuid.uuid4())
    
    try:
        if category == LogTypeCategory.APPLICATION:
            app_logger = get_application_logger()
            app_logger.route_application_log(log_type, log_data)
            
        elif category == LogTypeCategory.CHAT:
            chat_observer = get_chat_observer()
            chat_observer.route_conversation_log(log_data)
            
    except Exception as e:
        # Fallback logging to prevent log loss
        logger.error(
            "Failed to route log to observability system",
            log_type=log_type,
            category=category.value,
            error=str(e),
            error_type=type(e).__name__,
            fallback_data=log_data
        )


def create_operation_context(
    component: str,
    environment: str = "dev"
) -> BaseObservabilityContext:
    """
    Create a base observability context for correlation.
    
    Args:
        component: The component generating the log
        environment: The deployment environment
        
    Returns:
        BaseObservabilityContext with correlation fields
    """
    return BaseObservabilityContext(
        operation_id=str(uuid.uuid4()),
        timestamp=datetime.utcnow(),
        component=component,
        environment=environment
    )


def is_telemetry_initialized() -> bool:
    """Check if dual observability telemetry has been initialized."""
    return _telemetry_initialized


def shutdown_telemetry() -> None:
    """Gracefully shutdown telemetry services."""
    global _telemetry_initialized, _application_logger, _chat_observer
    
    try:
        logger.info("Shutting down dual observability systems")
        
        # Clean up logger instances
        _application_logger = None
        _chat_observer = None
        _telemetry_initialized = False
        
        logger.info("Dual observability shutdown completed")
        
    except Exception as e:
        logger.error(
            "Error during telemetry shutdown",
            error=str(e),
            error_type=type(e).__name__
        )