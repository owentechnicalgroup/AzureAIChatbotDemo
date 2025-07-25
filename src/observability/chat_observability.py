"""
AI Chat observability system for conversation flow, user interactions, and AI agent behavior.

Handles log types: CONVERSATION (exclusively)
Routes to: Specialized AI observability workspace or separate log stream  
Purpose: User experience, conversation quality, AI agent performance analysis

Preserves conversation_id, user_id, session_id context and integrates with existing 
ConversationLogger and log_conversation_event patterns.
"""

import logging
import uuid
from typing import Optional, Dict, Any, Union
from datetime import datetime, timezone
from contextlib import contextmanager

import structlog
from structlog.typing import FilteringBoundLogger

from .telemetry_service import ChatObservabilityContext, create_operation_context

logger = structlog.get_logger(__name__).bind(log_type="CONVERSATION")


class ChatObserver:
    """
    AI Chat observability system with conversation context tracking.
    
    Handles CONVERSATION log type exclusively with rich conversation metadata.
    Routes to specialized AI observability workspace for conversation analysis.
    """
    
    def __init__(self, logger_name: str):
        """
        Initialize chat observer.
        
        Args:
            logger_name: Logger namespace for OpenTelemetry routing (e.g., 'src.chat')
        """
        self.logger = logging.getLogger(logger_name)
        self.structlog_logger = structlog.get_logger(logger_name)
        self.operation_id = str(uuid.uuid4())
    
    def route_conversation_log(self, log_data: Dict[str, Any]) -> None:
        """
        Route conversation log data to chat observability system.
        
        Args:
            log_data: Structured conversation log data with conversation context
        """
        try:
            # Ensure this is a conversation log
            if log_data.get('log_type') != 'CONVERSATION':
                logger.warning(
                    "Non-conversation log routed to chat observability",
                    log_type=log_data.get('log_type'),
                    redirecting_to_application_logging=True
                )
                # Could redirect to application logging here
                return
            
            self._handle_conversation_log(log_data)
            
        except Exception as e:
            # Ensure log routing failures don't break the application
            logger.error(
                "Failed to route conversation log",
                error=str(e),
                error_type=type(e).__name__,
                fallback_data=log_data
            )
    
    def _handle_conversation_log(self, log_data: Dict[str, Any]) -> None:
        """Handle CONVERSATION log type with rich conversation context."""
        extra = self._prepare_conversation_extra(log_data)
        
        level = log_data.get('level', 'INFO').lower()
        message = log_data.get('message', 'Conversation event')
        
        getattr(self.logger, level)(message, extra=extra)
    
    def _prepare_conversation_extra(self, log_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare conversation-specific extra fields for Azure Log Analytics.
        
        Args:
            log_data: Original conversation log data
            
        Returns:
            Dict with conversation fields optimized for AI observability analysis
        """
        extra = {
            'log_type': 'CONVERSATION',
            'conversation_id': log_data.get('conversation_id'),
            'user_id': log_data.get('user_id', 'anonymous'),
            'session_id': log_data.get('session_id'),
            'operation_id': log_data.get('operation_id', self.operation_id),
            'operation_type': 'conversation',
            'component': log_data.get('component', 'chatbot'),
            'event_type': log_data.get('event_type', 'user_interaction'),
            'event_category': 'conversation',
            'operation_name': log_data.get('operation_name', 'chatbot.conversation'),
        }
        
        # Add conversation-specific metrics
        if 'turn_number' in log_data:
            extra['turn_number'] = log_data['turn_number']
        if 'message_length' in log_data:
            extra['message_length'] = log_data['message_length']
        if 'user_message_length' in log_data:
            extra['user_message_length'] = log_data['user_message_length']
        if 'assistant_response_length' in log_data:
            extra['assistant_response_length'] = log_data['assistant_response_length']
        
        # Add AI performance metrics
        if 'response_time' in log_data:
            extra['response_time'] = float(log_data['response_time'])
        if 'token_usage' in log_data and isinstance(log_data['token_usage'], dict):
            token_usage = log_data['token_usage']
            if 'prompt_tokens' in token_usage:
                extra['tokens_prompt'] = int(token_usage['prompt_tokens'])
            if 'completion_tokens' in token_usage:
                extra['tokens_completion'] = int(token_usage['completion_tokens'])
            if 'total_tokens' in token_usage:
                extra['tokens_total'] = int(token_usage['total_tokens'])
        
        # Add conversation quality indicators
        if 'message_role' in log_data:
            extra['message_role'] = log_data['message_role']
        if 'conversation_stage' in log_data:
            extra['conversation_stage'] = log_data['conversation_stage']
        if 'user_satisfaction' in log_data:
            extra['user_satisfaction'] = log_data['user_satisfaction']
        
        # Add error context for conversation failures
        if 'error' in log_data:
            extra['error_type'] = log_data.get('error_type', 'conversation_error')
            extra['error_message'] = str(log_data['error'])
        
        return extra
    
    # Preserve existing log_conversation_event signature for backward compatibility
    
    def log_conversation_event(self, 
                             message: str,
                             conversation_id: str,
                             user_id: Optional[str] = None,
                             session_id: Optional[str] = None,
                             turn_number: Optional[int] = None,
                             message_length: Optional[int] = None,
                             level: str = 'INFO'):
        """Log conversation-related events with proper field mapping."""
        log_data = {
            'message': message,
            'conversation_id': conversation_id,
            'user_id': user_id,
            'session_id': session_id,
            'turn_number': turn_number,
            'message_length': message_length,
            'level': level,
            'log_type': 'CONVERSATION'
        }
        
        self.route_conversation_log(log_data)
    
    def log_user_interaction(self,
                           event: str,
                           conversation_id: str,
                           user_message: Optional[str] = None,
                           user_id: Optional[str] = None,
                           session_id: Optional[str] = None,
                           turn_number: Optional[int] = None,
                           **additional_context):
        """Log user interaction events with conversation context."""
        log_data = {
            'message': f"User interaction: {event}",
            'conversation_id': conversation_id,
            'user_id': user_id,
            'session_id': session_id,
            'turn_number': turn_number,
            'event_type': 'user_interaction',
            'interaction_event': event,
            'level': 'INFO',
            'log_type': 'CONVERSATION',
            **additional_context
        }
        
        if user_message:
            log_data['user_message_length'] = len(user_message)
            # Note: We don't log full message content for privacy
        
        self.route_conversation_log(log_data)
    
    def log_ai_response(self,
                       event: str,
                       conversation_id: str,
                       assistant_response: Optional[str] = None,
                       token_usage: Optional[Dict[str, int]] = None,
                       response_time: Optional[float] = None,
                       user_id: Optional[str] = None,
                       session_id: Optional[str] = None,
                       turn_number: Optional[int] = None,
                       **additional_context):
        """Log AI assistant response events with performance metrics."""
        log_data = {
            'message': f"AI response: {event}",
            'conversation_id': conversation_id,
            'user_id': user_id,
            'session_id': session_id,
            'turn_number': turn_number,
            'event_type': 'ai_response',
            'response_event': event,
            'token_usage': token_usage,
            'response_time': response_time,
            'level': 'INFO',
            'log_type': 'CONVERSATION',
            **additional_context
        }
        
        if assistant_response:
            log_data['assistant_response_length'] = len(assistant_response)
            # Note: We don't log full response content for privacy/cost reasons
        
        self.route_conversation_log(log_data)
    
    def log_conversation_error(self,
                              error: Exception,
                              conversation_id: str,
                              user_id: Optional[str] = None,
                              session_id: Optional[str] = None,
                              turn_number: Optional[int] = None,
                              context: Optional[Dict[str, Any]] = None):
        """Log conversation errors with context for debugging."""
        log_data = {
            'message': f"Conversation error: {str(error)}",
            'conversation_id': conversation_id,
            'user_id': user_id,
            'session_id': session_id,
            'turn_number': turn_number,
            'event_type': 'conversation_error',
            'error': error,
            'error_type': type(error).__name__,
            'level': 'ERROR',
            'log_type': 'CONVERSATION'
        }
        
        if context:
            log_data.update(context)
        
        self.route_conversation_log(log_data)


class ConversationLogger:
    """
    Context manager for conversation-specific logging.
    
    Provides backward compatibility with existing ConversationLogger usage
    while routing to the new chat observability system.
    """
    
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
        # Get the chat observer and bind conversation context
        from .telemetry_service import get_chat_observer
        chat_observer = get_chat_observer()
        
        # Create a bound structlog logger with conversation context
        self.logger = structlog.get_logger("src.chat").bind(
            log_type="CONVERSATION",
            conversation_id=self.conversation_id,
            user_id=self.user_id,
            session_id=self.session_id
        )
        return self.logger
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context."""
        if exc_type:
            # Log the error using chat observability
            from .telemetry_service import get_chat_observer
            chat_observer = get_chat_observer()
            
            chat_observer.log_conversation_error(
                error=exc_val,
                conversation_id=self.conversation_id,
                user_id=self.user_id,
                session_id=self.session_id,
                context={
                    'exception_type': exc_type.__name__ if exc_type else None,
                    'in_context_manager': True
                }
            )
    
    def log_message(
        self,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log a conversation message."""
        from .telemetry_service import get_chat_observer
        chat_observer = get_chat_observer()
        
        if role == "user":
            chat_observer.log_user_interaction(
                event="message",
                conversation_id=self.conversation_id,
                user_message=content,
                user_id=self.user_id,
                session_id=self.session_id,
                **(metadata or {})
            )
        elif role == "assistant":
            chat_observer.log_ai_response(
                event="response_generated",
                conversation_id=self.conversation_id,
                assistant_response=content,
                user_id=self.user_id,
                session_id=self.session_id,
                **(metadata or {})
            )


# Convenience functions for chat observability

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
    
    Provides backward compatibility with existing log_conversation_event function
    while routing to chat observability system.
    """
    from .telemetry_service import get_chat_observer
    chat_observer = get_chat_observer()
    
    log_data = {
        'message': f"Conversation event: {event}",
        'conversation_id': conversation_id,
        'event_type': 'conversation',
        'conversation_event': event,
        'level': 'ERROR' if error else 'INFO',
        'log_type': 'CONVERSATION',
        **additional_context
    }
    
    if user_message:
        log_data['user_message_length'] = len(user_message)
        
    if assistant_response:
        log_data['assistant_response_length'] = len(assistant_response)
        
    if token_usage:
        log_data['token_usage'] = token_usage
        
    if response_time:
        log_data['response_time'] = response_time
        
    if error:
        log_data['error'] = error
        log_data['error_type'] = 'conversation_error'
        
    chat_observer.route_conversation_log(log_data)


def log_user_interaction(event: str, conversation_id: str, **context):
    """Log user interaction events."""
    from .telemetry_service import get_chat_observer
    chat_observer = get_chat_observer()
    
    chat_observer.log_user_interaction(
        event=event,
        conversation_id=conversation_id,
        **context
    )


def log_ai_response(event: str, conversation_id: str, **context):
    """Log AI response events."""
    from .telemetry_service import get_chat_observer
    chat_observer = get_chat_observer()
    
    chat_observer.log_ai_response(
        event=event,
        conversation_id=conversation_id,
        **context
    )