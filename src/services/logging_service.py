"""
Enhanced structured logging service with Azure Log Analytics integration.
Provides proper field mapping for Azure Application Insights and Log Analytics.
"""

import logging
import logging.handlers
import os
import sys
import json
import time
from typing import Any, Dict, Optional, Union
from pathlib import Path
from datetime import datetime, timezone
import structlog
from structlog.typing import FilteringBoundLogger
import uuid

from config.settings import Settings

try:
    from opencensus.ext.azure.log_exporter import AzureLogHandler
    from opencensus.trace import execution_context
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False


class ConversationContextFilter(logging.Filter):
    """Filter to add conversation context to log records."""
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Add conversation context if available."""
        # Add default context if not present
        if not hasattr(record, 'conversation_id'):
            record.conversation_id = None
        if not hasattr(record, 'user_id'):
            record.user_id = None
        if not hasattr(record, 'session_id'):
            record.session_id = None
        
        return True


class PerformanceMetricsProcessor:
    """Processor for performance metrics logging."""
    
    @staticmethod
    def add_performance_context(logger: FilteringBoundLogger, name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Add performance context to log events."""
        # Set log_type for performance metrics if not already set
        if 'log_type' not in event_dict and any(key in event_dict for key in ['response_time', 'duration', 'token_usage']):
            event_dict['log_type'] = 'PERFORMANCE'
        
        # Add standard fields for Azure Application Insights
        if 'conversation_id' in event_dict:
            event_dict['customDimensions'] = event_dict.get('customDimensions', {})
            event_dict['customDimensions']['conversation_id'] = event_dict['conversation_id']
        
        if 'response_time' in event_dict:
            event_dict['customMeasurements'] = event_dict.get('customMeasurements', {})
            event_dict['customMeasurements']['response_time'] = event_dict['response_time']
        
        if 'token_usage' in event_dict:
            event_dict['customMeasurements'] = event_dict.get('customMeasurements', {})
            if isinstance(event_dict['token_usage'], dict):
                for key, value in event_dict['token_usage'].items():
                    event_dict['customMeasurements'][f'tokens_{key}'] = value
        
        return event_dict


class EnhancedApplicationInsightsFormatter(logging.Formatter):
    """Enhanced formatter that properly maps data to Azure Log Analytics fields."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with proper Azure Log Analytics field mapping."""
        # Extract custom data from the log record
        custom_dimensions = self._extract_custom_dimensions(record)
        custom_measurements = self._extract_custom_measurements(record)
        
        # Get operation context for correlation
        operation_id = self._get_operation_id(record)
        operation_name = self._get_operation_name(record)
        
        # Determine log_type based on record attributes
        log_type = self._determine_log_type(record)
        
        # Create the structured log entry
        log_entry = {
            'message': self._get_clean_message(record),
            'log_type': log_type,
            'customDimensions': custom_dimensions,
            'customMeasurements': custom_measurements,
            'severityLevel': self._map_severity_level(record.levelname),
            'timestamp': datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
        }
        
        # Add operation correlation if available
        if operation_id:
            log_entry['operation_Id'] = operation_id
        if operation_name:
            log_entry['operation_Name'] = operation_name
            
        return json.dumps(log_entry, default=str, ensure_ascii=False)
    
    def _extract_custom_dimensions(self, record: logging.LogRecord) -> Dict[str, str]:
        """Extract searchable metadata for customDimensions (excluding standard Properties fields)."""
        dimensions = {}
        
        # Add conversation context if available
        if hasattr(record, 'conversation_id') and record.conversation_id:
            dimensions['conversation_id'] = str(record.conversation_id)
        if hasattr(record, 'user_id') and record.user_id:
            dimensions['user_id'] = str(record.user_id)
        if hasattr(record, 'session_id') and record.session_id:
            dimensions['session_id'] = str(record.session_id)
            
        # Add operation context
        if hasattr(record, 'operation_type') and record.operation_type:
            dimensions['operation_type'] = str(record.operation_type)
        if hasattr(record, 'component') and record.component:
            dimensions['component'] = str(record.component)
        if hasattr(record, 'event_type') and record.event_type:
            dimensions['event_type'] = str(record.event_type)
        if hasattr(record, 'event_category') and record.event_category:
            dimensions['event_category'] = str(record.event_category)
        if hasattr(record, 'operation') and record.operation:
            dimensions['operation'] = str(record.operation)
        if hasattr(record, 'custom_field') and record.custom_field:
            dimensions['custom_field'] = str(record.custom_field)
            
        # Add authentication context
        if hasattr(record, 'credential_type') and record.credential_type:
            dimensions['credential_type'] = str(record.credential_type)
            
        # Add success/failure status
        if hasattr(record, 'success') and record.success is not None:
            dimensions['success'] = str(record.success).lower()
            
        # Add error context
        if hasattr(record, 'error_type') and record.error_type:
            dimensions['error_type'] = str(record.error_type)
        if hasattr(record, 'error_code') and record.error_code:
            dimensions['error_code'] = str(record.error_code)
            
        # Add Azure resource context
        if hasattr(record, 'resource_type') and record.resource_type:
            dimensions['resource_type'] = str(record.resource_type)
        if hasattr(record, 'resource_name') and record.resource_name:
            dimensions['resource_name'] = str(record.resource_name)
        if hasattr(record, 'secret_name') and record.secret_name:
            dimensions['secret_name'] = str(record.secret_name)
            
        # Add numeric fields that should be searchable as strings
        if hasattr(record, 'turn_number') and record.turn_number is not None:
            dimensions['turn_number'] = str(record.turn_number)
        if hasattr(record, 'message_length') and record.message_length is not None:
            dimensions['message_length'] = str(record.message_length)
            
        return dimensions
    
    def _extract_custom_measurements(self, record: logging.LogRecord) -> Dict[str, float]:
        """Extract numeric metrics for customMeasurements."""
        measurements = {}
        
        # Performance metrics
        if hasattr(record, 'response_time') and record.response_time is not None:
            measurements['response_time'] = float(record.response_time)
        if hasattr(record, 'duration') and record.duration is not None:
            measurements['duration'] = float(record.duration)
            
        # Token usage metrics
        if hasattr(record, 'tokens_prompt') and record.tokens_prompt is not None:
            measurements['tokens_prompt'] = float(record.tokens_prompt)
        if hasattr(record, 'tokens_completion') and record.tokens_completion is not None:
            measurements['tokens_completion'] = float(record.tokens_completion)
        if hasattr(record, 'tokens_total') and record.tokens_total is not None:
            measurements['tokens_total'] = float(record.tokens_total)
            
        # Request metrics
        if hasattr(record, 'request_size') and record.request_size is not None:
            measurements['request_size'] = float(record.request_size)
        if hasattr(record, 'response_size') and record.response_size is not None:
            measurements['response_size'] = float(record.response_size)
            
        # Conversation metrics
        if hasattr(record, 'turn_number') and record.turn_number is not None:
            measurements['turn_number'] = float(record.turn_number)
        if hasattr(record, 'message_length') and record.message_length is not None:
            measurements['message_length'] = float(record.message_length)
            
        return measurements
    
    def _get_clean_message(self, record: logging.LogRecord) -> str:
        """Get a clean, human-readable message without structured data."""
        if hasattr(record, 'clean_message') and record.clean_message:
            return str(record.clean_message)
        
        # If structlog provided an event field, use that as the clean message
        if hasattr(record, 'event') and record.event:
            return str(record.event)
        
        # Get the original message
        message = record.getMessage()
        
        # If the message contains key-value pairs (from structlog KeyValueRenderer),
        # try to extract just the event part
        if "event=" in message:
            try:
                # Look for event='...' pattern and extract the value
                import re
                event_match = re.search(r"event='([^']*)'", message)
                if event_match:
                    return event_match.group(1)
            except Exception:
                pass
        
        # Return the original message as fallback
        return message
    
    def _get_operation_id(self, record: logging.LogRecord) -> Optional[str]:
        """Get operation ID for request correlation."""
        if hasattr(record, 'operation_id') and record.operation_id:
            return str(record.operation_id)
        
        # Try to get from execution context
        if AZURE_AVAILABLE:
            try:
                tracer = execution_context.get_opencensus_tracer()
                if tracer and tracer.span_context:
                    return tracer.span_context.trace_id
            except Exception:
                pass
                
        return None
    
    def _get_operation_name(self, record: logging.LogRecord) -> Optional[str]:
        """Get operation name for request classification."""
        if hasattr(record, 'operation_name') and record.operation_name:
            return str(record.operation_name)
        
        # Generate from logger name and function
        if record.funcName and record.funcName != '<module>':
            return f"{record.name}.{record.funcName}"
        
        return record.name
    
    def _map_severity_level(self, level_name: str) -> int:
        """Map Python log levels to Application Insights severity levels."""
        mapping = {
            'CRITICAL': 4,
            'ERROR': 3,
            'WARNING': 2,
            'INFO': 1,
            'DEBUG': 0
        }
        return mapping.get(level_name.upper(), 1)
    
    def _determine_log_type(self, record: logging.LogRecord) -> str:
        """Determine the appropriate log_type based on record attributes."""
        # Check if log_type is explicitly set
        if hasattr(record, 'log_type') and record.log_type:
            return str(record.log_type)
        
        # Check for conversation-related logs
        if (hasattr(record, 'conversation_id') and record.conversation_id) or \
           (hasattr(record, 'event_type') and record.event_type == 'conversation'):
            return 'CONVERSATION'
        
        # Check for Azure OpenAI related logs
        if (hasattr(record, 'component') and 'azure' in str(record.component).lower()) or \
           (hasattr(record, 'operation_type') and 'azure_openai' in str(record.operation_type).lower()) or \
           (hasattr(record, 'resource_type') and 'openai' in str(record.resource_type).lower()):
            return 'AZURE_OPENAI'
        
        # Check for performance metrics
        if (hasattr(record, 'response_time') and record.response_time is not None) or \
           (hasattr(record, 'duration') and record.duration is not None) or \
           (hasattr(record, 'event_type') and record.event_type == 'performance'):
            return 'PERFORMANCE'
        
        # Check for security/authentication related logs
        if (hasattr(record, 'credential_type') and record.credential_type) or \
           (hasattr(record, 'secret_name') and record.secret_name) or \
           (hasattr(record, 'event_type') and record.event_type == 'security'):
            return 'SECURITY'
        
        # Default to SYSTEM for application lifecycle, errors, and general system events
        return 'SYSTEM'


class ConversationContextFilter(logging.Filter):
    """Filter to add conversation context to log records."""
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Add conversation context if available."""
        # Add default context if not present
        if not hasattr(record, 'conversation_id'):
            record.conversation_id = None
        if not hasattr(record, 'user_id'):
            record.user_id = None
        if not hasattr(record, 'session_id'):
            record.session_id = None
        
        return True


def setup_file_logging(settings: Settings) -> Optional[logging.Handler]:
    """Set up file logging with rotation."""
    # Return None if file logging is disabled
    if not settings.enable_file_logging:
        return None
    
    # Ensure logs directory exists
    log_path = Path(settings.log_file_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Create rotating file handler
    file_handler = logging.handlers.RotatingFileHandler(
        log_path,
        maxBytes=50 * 1024 * 1024,  # 50MB
        backupCount=10,
        encoding='utf-8'
    )
    
    # Set formatter based on log format preference
    if settings.enable_json_logging:
        file_handler.setFormatter(EnhancedApplicationInsightsFormatter())
    else:
        file_handler.setFormatter(
            logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        )
    
    # Add conversation context filter
    file_handler.addFilter(ConversationContextFilter())
    
    return file_handler


def setup_console_logging(settings: Settings) -> Optional[logging.Handler]:
    """Set up console logging with color support."""
    # Return None if console logging is disabled
    if not settings.enable_console_logging:
        return None
    
    console_handler = logging.StreamHandler(sys.stdout)
    
    if settings.enable_json_logging:
        console_handler.setFormatter(EnhancedApplicationInsightsFormatter())
    else:
        # Use simple format for console readability
        console_handler.setFormatter(
            logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s',
                datefmt='%H:%M:%S'
            )
        )
    
    console_handler.addFilter(ConversationContextFilter())
    
    return console_handler


def setup_application_insights_logging(settings: Settings) -> Optional[logging.Handler]:
    """Set up Azure Application Insights logging if configured."""
    if not settings.applicationinsights_connection_string:
        return None
    
    try:
        # Try to import and set up Application Insights
        from opencensus.ext.azure.log_exporter import AzureLogHandler
        
        ai_handler = AzureLogHandler(
            connection_string=settings.applicationinsights_connection_string
        )
        
        # Set the cloud role name for Application Insights
        # This maps to AppRoleName in Azure Log Analytics
        def add_role_name(envelope):
            envelope.tags['ai.cloud.role'] = 'aoai-chatbot'
            envelope.tags['ai.cloud.roleInstance'] = f'aoai-chatbot-{os.getenv("HOSTNAME", "local")}'
            return True
        
        ai_handler.add_telemetry_processor(add_role_name)
        
        # Use enhanced formatter that's compatible with Application Insights
        ai_handler.setFormatter(EnhancedApplicationInsightsFormatter())
        ai_handler.addFilter(ConversationContextFilter())
        
        return ai_handler
        
    except ImportError:
        logging.getLogger(__name__).warning(
            "opencensus-ext-azure not installed. Application Insights logging disabled."
        )
        return None
    except Exception as e:
        logging.getLogger(__name__).error(
            f"Failed to setup Application Insights logging: {e}"
        )
        return None


def configure_structlog(settings: Settings) -> None:
    """Configure structlog for structured logging."""
    processors = [
        # Add performance context
        PerformanceMetricsProcessor.add_performance_context,
        # Add log level
        structlog.stdlib.add_log_level,
        # Add logger name
        structlog.stdlib.add_logger_name,
        # Add timestamp
        structlog.processors.TimeStamper(fmt="ISO"),
        # Add stack info for exceptions
        structlog.processors.StackInfoRenderer(),
        # Format exceptions
        structlog.processors.format_exc_info,
    ]
    
    # Use KeyValueRenderer for console/file output to avoid JSON duplication
    # The EnhancedApplicationInsightsFormatter will handle JSON formatting for Azure
    processors.append(structlog.processors.KeyValueRenderer(key_order=['timestamp', 'level', 'event']))
    
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        context_class=structlog.threadlocal.wrap_dict(dict),
        cache_logger_on_first_use=True,
    )


def setup_logging(settings: Optional[Settings] = None) -> None:
    """
    Set up comprehensive logging configuration.
    
    Args:
        settings: Application settings instance
    """
    if settings is None:
        from config.settings import get_settings
        settings = get_settings()
    
    # Configure structlog first
    configure_structlog(settings)
    
    # Clear any existing handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Set root log level
    log_level = getattr(logging, settings.log_level.upper())
    root_logger.setLevel(log_level)
    
    # Set up handlers
    handlers = []
    
    # File logging
    try:
        file_handler = setup_file_logging(settings)
        handlers.append(file_handler)
    except Exception as e:
        logging.error(f"Failed to setup file logging: {e}")
    
    # Console logging
    try:
        console_handler = setup_console_logging(settings)
        handlers.append(console_handler)
    except Exception as e:
        logging.error(f"Failed to setup console logging: {e}")
    
    # Application Insights logging
    try:
        ai_handler = setup_application_insights_logging(settings)
        if ai_handler:
            # Ensure the handler has a proper lock
            if not hasattr(ai_handler, 'lock') or ai_handler.lock is None:
                import threading
                ai_handler.lock = threading.RLock()
            handlers.append(ai_handler)
    except Exception as e:
        logging.error(f"Failed to setup Application Insights logging: {e}")
    
    # Add all handlers to root logger
    for handler in handlers:
        if handler is not None:  # Filter out None handlers
            handler.setLevel(log_level)
            root_logger.addHandler(handler)
    
    # Configure third-party loggers to reduce noise
    logging.getLogger('azure').setLevel(logging.WARNING)
    logging.getLogger('openai').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    
    # Log successful setup
    logger = structlog.get_logger(__name__)
    logger.info(
        "Logging configured",
        level=settings.log_level,
        format=settings.log_format,
        file_path=settings.log_file_path,
        handlers=len(handlers),
        application_insights_enabled=bool(settings.applicationinsights_connection_string)
    )


def get_logger(name: str, **context) -> FilteringBoundLogger:
    """
    Get a configured logger with optional context binding.
    
    Args:
        name: Logger name (usually __name__)
        **context: Additional context to bind to logger
        
    Returns:
        Bound logger with context
    """
    logger = structlog.get_logger(name)
    
    if context:
        logger = logger.bind(**context)
    
    return logger


def log_conversation_event(
    event: str,
    conversation_id: str,
    user_message: Optional[str] = None,
    assistant_response: Optional[str] = None,
    token_usage: Optional[Dict[str, int]] = None,
    response_time: Optional[float] = None,
    error: Optional[str] = None,
    **additional_context
) -> None:
    """
    Log a conversation event with structured data.
    
    Args:
        event: Event type (e.g., 'message_received', 'response_generated')
        conversation_id: Unique conversation identifier
        user_message: User's message content (optional)
        assistant_response: Assistant's response content (optional)
        token_usage: Token usage statistics (optional)
        response_time: Response time in seconds (optional)
        error: Error message if applicable (optional)
        **additional_context: Additional context to include
    """
    logger = get_logger(__name__).bind(
        conversation_id=conversation_id,
        event_type="conversation",
        log_type="CONVERSATION"
    )
    
    log_data = {
        'event': event,
        **additional_context
    }
    
    if user_message:
        log_data['user_message_length'] = len(user_message)
        # Don't log full message content for privacy, just metadata
        
    if assistant_response:
        log_data['assistant_response_length'] = len(assistant_response)
        
    if token_usage:
        log_data['token_usage'] = token_usage
        
    if response_time:
        log_data['response_time'] = response_time
        
    if error:
        # Remove 'event' from log_data to avoid argument conflict with structlog
        error_log_data = {k: v for k, v in log_data.items() if k != 'event'}
        logger.error(log_data.get('event', 'Conversation error'), error=error, **error_log_data)
    else:
        # Remove 'event' from log_data to avoid argument conflict with structlog
        info_log_data = {k: v for k, v in log_data.items() if k != 'event'}
        logger.info(log_data.get('event', 'Conversation event'), **info_log_data)


def log_performance_metrics(
    operation: str,
    duration: float,
    success: bool = True,
    **metrics
) -> None:
    """
    Log performance metrics.
    
    Args:
        operation: Operation name
        duration: Operation duration in seconds
        success: Whether operation was successful
        **metrics: Additional metrics to log
    """
    logger = get_logger(__name__).bind(
        event_type="performance",
        log_type="PERFORMANCE"
    )
    
    logger.info(
        "Performance metric",
        operation=operation,
        duration=duration,
        success=success,
        **metrics
    )


def log_security_event(
    event_type: str,
    details: Dict[str, Any],
    severity: str = "info",
    user_id: Optional[str] = None
) -> None:
    """
    Log security-related events.
    
    Args:
        event_type: Type of security event
        details: Event details
        severity: Severity level
        user_id: User ID if applicable
    """
    logger = get_logger(__name__).bind(
        event_type="security",
        security_event=event_type,
        log_type="SECURITY"
    )
    
    if user_id:
        logger = logger.bind(user_id=user_id)
    
    log_method = getattr(logger, severity.lower(), logger.info)
    log_method("Security event", **details)


class ConversationLogger:
    """Context manager for conversation-specific logging."""
    
    def __init__(
        self,
        conversation_id: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ):
        """
        Initialize conversation logger.
        
        Args:
            conversation_id: Conversation ID (generated if not provided)
            user_id: User ID (optional)
            session_id: Session ID (optional)
        """
        self.conversation_id = conversation_id or str(uuid.uuid4())
        self.user_id = user_id
        self.session_id = session_id or str(uuid.uuid4())
        self.logger = None
    
    def __enter__(self) -> FilteringBoundLogger:
        """Enter context and return bound logger."""
        self.logger = get_logger(__name__).bind(
            conversation_id=self.conversation_id,
            user_id=self.user_id,
            session_id=self.session_id
        )
        return self.logger
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context."""
        if exc_type:
            self.logger.error(
                "Conversation context error",
                exception=str(exc_val),
                exception_type=exc_type.__name__ if exc_type else None
            )
    
    def log_message(
        self,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log a conversation message."""
        log_conversation_event(
            event="message",
            conversation_id=self.conversation_id,
            user_message=content if role == "user" else None,
            assistant_response=content if role == "assistant" else None,
            message_role=role,
            **(metadata or {})
        )