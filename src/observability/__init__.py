"""
Observability package for Azure OpenAI chatbot.

Provides separated concerns for:
- Application Logging: Infrastructure, performance, security, and system events
- AI Chat Observability: Conversation flow, user interactions, and AI agent behavior

Uses Azure Monitor OpenTelemetry with dual exporters for specialized analysis.
"""

from .telemetry_service import (
    initialize_dual_observability,
    get_application_logger,
    get_chat_observer
)
from .application_logging import (
    ApplicationLogger,
    log_system_event,
    log_security_event, 
    log_performance_event,
    log_azure_openai_event
)
from .chat_observability import (
    ChatObserver,
    log_conversation_event,
    log_user_interaction,
    log_ai_response
)

__all__ = [
    'initialize_dual_observability',
    'get_application_logger',
    'get_chat_observer',
    'ApplicationLogger',
    'log_system_event',
    'log_security_event',
    'log_performance_event', 
    'log_azure_openai_event',
    'ChatObserver',
    'log_conversation_event',
    'log_user_interaction',
    'log_ai_response'
]