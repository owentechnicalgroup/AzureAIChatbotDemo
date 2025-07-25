"""
Tests for AI Chat Observability system.

Covers CONVERSATION log type routing to specialized AI observability workspace
with conversation context tracking and user interaction analysis.
"""

import pytest
import uuid
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, Optional

from src.observability.chat_observability import (
    ChatObserver,
    ConversationLogger,
    log_conversation_event,
    log_user_interaction,
    log_ai_response
)


class TestChatObserver:
    """Test ChatObserver class functionality."""
    
    @pytest.fixture
    def chat_observer(self):
        """Create ChatObserver instance for testing."""
        return ChatObserver("src.chat")
    
    def test_initialization(self, chat_observer):
        """Test ChatObserver initialization."""
        assert chat_observer.logger is not None
        assert chat_observer.structlog_logger is not None
        assert chat_observer.operation_id is not None
    
    def test_route_conversation_log_valid(self, chat_observer):
        """Test routing valid CONVERSATION log data."""
        with patch.object(chat_observer, '_handle_conversation_log') as mock_handler:
            log_data = {
                'log_type': 'CONVERSATION',
                'message': 'Test conversation event',
                'conversation_id': 'test-conv-123'
            }
            
            chat_observer.route_conversation_log(log_data)
            
            mock_handler.assert_called_once_with(log_data)
    
    def test_route_conversation_log_invalid_type(self, chat_observer):
        """Test routing non-CONVERSATION log data shows warning."""
        with patch.object(chat_observer.logger, 'warning') as mock_warning:
            log_data = {
                'log_type': 'SYSTEM',
                'message': 'Wrong log type'
            }
            
            chat_observer.route_conversation_log(log_data)
            
            mock_warning.assert_called_once()
    
    def test_route_conversation_log_error_handling(self, chat_observer):
        """Test error handling in conversation log routing."""
        with patch.object(chat_observer, '_handle_conversation_log', side_effect=Exception("Handler error")):
            with patch.object(chat_observer.logger, 'error') as mock_error:
                log_data = {
                    'log_type': 'CONVERSATION',
                    'message': 'Test error handling'
                }
                
                chat_observer.route_conversation_log(log_data)
                
                mock_error.assert_called_once()


class TestConversationLogHandling:
    """Test conversation-specific log handling."""
    
    @pytest.fixture
    def chat_observer(self):
        return ChatObserver("src.chat")
    
    def test_handle_conversation_log_basic(self, chat_observer):
        """Test basic conversation log handling."""
        with patch.object(chat_observer.logger, 'info') as mock_log:
            log_data = {
                'message': 'User interaction',
                'conversation_id': 'test-conv-123',
                'user_id': 'user-456',
                'session_id': 'session-789',
                'level': 'INFO'
            }
            
            chat_observer._handle_conversation_log(log_data)
            
            mock_log.assert_called_once()
            call_args = mock_log.call_args
            assert call_args[0][0] == 'User interaction'
            
            extra = call_args[1]['extra']
            assert extra['log_type'] == 'CONVERSATION'
            assert extra['conversation_id'] == 'test-conv-123'
            assert extra['user_id'] == 'user-456'
            assert extra['session_id'] == 'session-789'
    
    def test_prepare_conversation_extra_full_context(self, chat_observer):
        """Test conversation extra preparation with full context."""
        log_data = {
            'conversation_id': 'conv-123',
            'user_id': 'user-456',
            'session_id': 'session-789',
            'turn_number': 5,
            'message_length': 150,
            'user_message_length': 80,
            'assistant_response_length': 200,
            'response_time': 2.5,
            'token_usage': {
                'prompt_tokens': 100,
                'completion_tokens': 150,
                'total_tokens': 250
            },
            'message_role': 'user',
            'conversation_stage': 'active',
            'user_satisfaction': 'positive'
        }
        
        extra = chat_observer._prepare_conversation_extra(log_data)
        
        # Basic conversation fields
        assert extra['log_type'] == 'CONVERSATION'
        assert extra['conversation_id'] == 'conv-123'
        assert extra['user_id'] == 'user-456'
        assert extra['session_id'] == 'session-789'
        
        # Conversation metrics
        assert extra['turn_number'] == 5
        assert extra['message_length'] == 150
        assert extra['user_message_length'] == 80
        assert extra['assistant_response_length'] == 200
        
        # AI performance metrics
        assert extra['response_time'] == 2.5
        assert extra['tokens_prompt'] == 100
        assert extra['tokens_completion'] == 150
        assert extra['tokens_total'] == 250
        
        # Conversation quality indicators
        assert extra['message_role'] == 'user'
        assert extra['conversation_stage'] == 'active'
        assert extra['user_satisfaction'] == 'positive'
    
    def test_prepare_conversation_extra_minimal(self, chat_observer):
        """Test conversation extra preparation with minimal data."""
        log_data = {
            'conversation_id': 'conv-123'
        }
        
        extra = chat_observer._prepare_conversation_extra(log_data)
        
        assert extra['log_type'] == 'CONVERSATION'
        assert extra['conversation_id'] == 'conv-123'
        assert extra['user_id'] == 'anonymous'  # Default value
        assert extra['operation_type'] == 'conversation'
        assert 'turn_number' not in extra  # Should not include None values
    
    def test_prepare_conversation_extra_with_error(self, chat_observer):
        """Test conversation extra preparation with error context."""
        log_data = {
            'conversation_id': 'conv-123',
            'error': Exception("Test error"),
            'error_type': 'ConversationError'
        }
        
        extra = chat_observer._prepare_conversation_extra(log_data)
        
        assert extra['error_type'] == 'ConversationError'
        assert extra['error_message'] == 'Test error'


class TestConversationEventLogging:
    """Test conversation event logging methods."""
    
    @pytest.fixture
    def chat_observer(self):
        return ChatObserver("src.chat")
    
    def test_log_conversation_event(self, chat_observer):
        """Test log_conversation_event method."""
        with patch.object(chat_observer, 'route_conversation_log') as mock_route:
            chat_observer.log_conversation_event(
                message="User sent message",
                conversation_id="conv-123",
                user_id="user-456",
                session_id="session-789",
                turn_number=1,
                message_length=50,
                level="INFO"
            )
            
            mock_route.assert_called_once()
            log_data = mock_route.call_args[0][0]
            
            assert log_data['message'] == "User sent message"
            assert log_data['conversation_id'] == "conv-123"
            assert log_data['user_id'] == "user-456"
            assert log_data['turn_number'] == 1
            assert log_data['log_type'] == 'CONVERSATION'
    
    def test_log_user_interaction(self, chat_observer):
        """Test log_user_interaction method."""
        with patch.object(chat_observer, 'route_conversation_log') as mock_route:
            chat_observer.log_user_interaction(
                event="message_sent",
                conversation_id="conv-123",
                user_message="Hello, how are you?",
                user_id="user-456",
                turn_number=1,
                additional_context="web_client"
            )
            
            mock_route.assert_called_once()
            log_data = mock_route.call_args[0][0]
            
            assert log_data['message'] == "User interaction: message_sent"
            assert log_data['event_type'] == 'user_interaction'
            assert log_data['interaction_event'] == 'message_sent'
            assert log_data['user_message_length'] == len("Hello, how are you?")
            assert log_data['additional_context'] == 'web_client'
    
    def test_log_ai_response(self, chat_observer):
        """Test log_ai_response method."""
        with patch.object(chat_observer, 'route_conversation_log') as mock_route:
            token_usage = {'prompt_tokens': 50, 'completion_tokens': 100, 'total_tokens': 150}
            
            chat_observer.log_ai_response(
                event="response_generated",
                conversation_id="conv-123",
                assistant_response="I'm doing well, thank you!",
                token_usage=token_usage,
                response_time=1.5,
                user_id="user-456",
                turn_number=1
            )
            
            mock_route.assert_called_once()
            log_data = mock_route.call_args[0][0]
            
            assert log_data['message'] == "AI response: response_generated"
            assert log_data['event_type'] == 'ai_response'
            assert log_data['response_event'] == 'response_generated'
            assert log_data['assistant_response_length'] == len("I'm doing well, thank you!")
            assert log_data['token_usage'] == token_usage
            assert log_data['response_time'] == 1.5
    
    def test_log_conversation_error(self, chat_observer):
        """Test log_conversation_error method."""
        with patch.object(chat_observer, 'route_conversation_log') as mock_route:
            error = ValueError("Test conversation error")
            
            chat_observer.log_conversation_error(
                error=error,
                conversation_id="conv-123",
                user_id="user-456",
                turn_number=1,
                context={'operation': 'message_processing'}
            )
            
            mock_route.assert_called_once()
            log_data = mock_route.call_args[0][0]
            
            assert log_data['message'] == "Conversation error: Test conversation error"
            assert log_data['event_type'] == 'conversation_error'
            assert log_data['error'] == error
            assert log_data['error_type'] == 'ValueError'
            assert log_data['level'] == 'ERROR'
            assert log_data['operation'] == 'message_processing'


class TestConversationLoggerContextManager:
    """Test ConversationLogger context manager."""
    
    def test_conversation_logger_initialization(self):
        """Test ConversationLogger initialization."""
        logger = ConversationLogger(
            conversation_id="conv-123",
            user_id="user-456",
            session_id="session-789"
        )
        
        assert logger.conversation_id == "conv-123"
        assert logger.user_id == "user-456"
        assert logger.session_id == "session-789"
    
    def test_conversation_logger_auto_generation(self):
        """Test ConversationLogger with auto-generated IDs."""
        logger = ConversationLogger()
        
        # Should generate valid UUIDs
        uuid.UUID(logger.conversation_id)
        uuid.UUID(logger.session_id)
        assert logger.user_id is None
    
    @patch('src.observability.chat_observability.get_chat_observer')
    def test_conversation_logger_context_entry(self, mock_get_observer):
        """Test ConversationLogger context entry."""
        mock_observer = Mock()
        mock_get_observer.return_value = mock_observer
        
        with patch('structlog.get_logger') as mock_get_structlog:
            mock_bound_logger = Mock()
            mock_structlog_logger = Mock()
            mock_structlog_logger.bind.return_value = mock_bound_logger
            mock_get_structlog.return_value = mock_structlog_logger
            
            logger = ConversationLogger(conversation_id="conv-123")
            
            with logger as bound_logger:
                assert bound_logger == mock_bound_logger
                mock_structlog_logger.bind.assert_called_once_with(
                    log_type="CONVERSATION",
                    conversation_id="conv-123",
                    user_id=None,
                    session_id=logger.session_id
                )
    
    @patch('src.observability.chat_observability.get_chat_observer')
    def test_conversation_logger_exception_handling(self, mock_get_observer):
        """Test ConversationLogger exception handling."""
        mock_observer = Mock()
        mock_get_observer.return_value = mock_observer
        
        logger = ConversationLogger(conversation_id="conv-123")
        
        try:
            with logger:
                raise ValueError("Test exception")
        except ValueError:
            pass
        
        # Should call log_conversation_error
        mock_observer.log_conversation_error.assert_called_once()
        error_call = mock_observer.log_conversation_error.call_args[1]
        assert error_call['conversation_id'] == "conv-123"
        assert error_call['context']['in_context_manager'] is True
    
    @patch('src.observability.chat_observability.get_chat_observer')
    def test_conversation_logger_log_message_user(self, mock_get_observer):
        """Test ConversationLogger log_message for user messages."""
        mock_observer = Mock()
        mock_get_observer.return_value = mock_observer
        
        logger = ConversationLogger(conversation_id="conv-123")
        
        logger.log_message(
            role="user",
            content="Hello, world!",
            metadata={'client': 'web'}
        )
        
        mock_observer.log_user_interaction.assert_called_once()
        call_args = mock_observer.log_user_interaction.call_args[1]
        assert call_args['event'] == 'message'
        assert call_args['conversation_id'] == 'conv-123'
        assert call_args['user_message'] == 'Hello, world!'
        assert call_args['client'] == 'web'
    
    @patch('src.observability.chat_observability.get_chat_observer')
    def test_conversation_logger_log_message_assistant(self, mock_get_observer):
        """Test ConversationLogger log_message for assistant messages."""
        mock_observer = Mock()
        mock_get_observer.return_value = mock_observer
        
        logger = ConversationLogger(conversation_id="conv-123")
        
        logger.log_message(
            role="assistant",
            content="Hello! How can I help you?",
            metadata={'model': 'gpt-4'}
        )
        
        mock_observer.log_ai_response.assert_called_once()
        call_args = mock_observer.log_ai_response.call_args[1]
        assert call_args['event'] == 'response_generated'
        assert call_args['conversation_id'] == 'conv-123'
        assert call_args['assistant_response'] == 'Hello! How can I help you?'
        assert call_args['model'] == 'gpt-4'


class TestConvenienceFunctions:
    """Test convenience functions for chat observability."""
    
    @patch('src.observability.chat_observability.get_chat_observer')
    def test_log_conversation_event_function(self, mock_get_observer):
        """Test log_conversation_event convenience function."""
        mock_observer = Mock()
        mock_get_observer.return_value = mock_observer
        
        log_conversation_event(
            event="user_message",
            conversation_id="conv-123",
            user_message="Hello",
            assistant_response="Hi there!",
            token_usage={'total_tokens': 50},
            response_time=1.2,
            additional_context="web_client"
        )
        
        mock_observer.route_conversation_log.assert_called_once()
        log_data = mock_observer.route_conversation_log.call_args[0][0]
        
        assert log_data['message'] == "Conversation event: user_message"
        assert log_data['conversation_id'] == "conv-123"
        assert log_data['user_message_length'] == 5
        assert log_data['assistant_response_length'] == 9
        assert log_data['token_usage'] == {'total_tokens': 50}
        assert log_data['response_time'] == 1.2
        assert log_data['additional_context'] == "web_client"
    
    @patch('src.observability.chat_observability.get_chat_observer')
    def test_log_conversation_event_with_error(self, mock_get_observer):
        """Test log_conversation_event with error."""
        mock_observer = Mock()
        mock_get_observer.return_value = mock_observer
        
        log_conversation_event(
            event="processing_error",
            conversation_id="conv-123",
            error="Failed to process message"
        )
        
        mock_observer.route_conversation_log.assert_called_once()
        log_data = mock_observer.route_conversation_log.call_args[0][0]
        
        assert log_data['level'] == 'ERROR'
        assert log_data['error'] == "Failed to process message"
        assert log_data['error_type'] == 'conversation_error'
    
    @patch('src.observability.chat_observability.get_chat_observer')
    def test_log_user_interaction_function(self, mock_get_observer):
        """Test log_user_interaction convenience function."""
        mock_observer = Mock()
        mock_get_observer.return_value = mock_observer
        
        log_user_interaction(
            event="button_click",
            conversation_id="conv-123",
            user_id="user-456",
            action="send_message"
        )
        
        mock_observer.log_user_interaction.assert_called_once()
        call_args = mock_observer.log_user_interaction.call_args[1]
        assert call_args['event'] == 'button_click'
        assert call_args['conversation_id'] == 'conv-123'
        assert call_args['user_id'] == 'user-456'
        assert call_args['action'] == 'send_message'
    
    @patch('src.observability.chat_observability.get_chat_observer')
    def test_log_ai_response_function(self, mock_get_observer):
        """Test log_ai_response convenience function."""
        mock_observer = Mock()
        mock_get_observer.return_value = mock_observer
        
        log_ai_response(
            event="streaming_complete",
            conversation_id="conv-123",
            response_time=2.3,
            tokens_used=150
        )
        
        mock_observer.log_ai_response.assert_called_once()
        call_args = mock_observer.log_ai_response.call_args[1]
        assert call_args['event'] == 'streaming_complete'
        assert call_args['conversation_id'] == 'conv-123'
        assert call_args['response_time'] == 2.3
        assert call_args['tokens_used'] == 150


class TestPrivacyAndSecurity:
    """Test privacy and security considerations in chat observability."""
    
    @pytest.fixture 
    def chat_observer(self):
        return ChatObserver("src.chat")
    
    def test_message_content_not_logged_by_default(self, chat_observer):
        """Test that full message content is not logged for privacy."""
        with patch.object(chat_observer, 'route_conversation_log') as mock_route:
            chat_observer.log_user_interaction(
                event="message_sent",
                conversation_id="conv-123",
                user_message="This is sensitive user data"
            )
            
            log_data = mock_route.call_args[0][0]
            
            # Should log message length but not content
            assert log_data['user_message_length'] == len("This is sensitive user data")
            assert 'user_message' not in log_data
    
    def test_response_content_not_logged_by_default(self, chat_observer):
        """Test that full response content is not logged for privacy/cost."""
        with patch.object(chat_observer, 'route_conversation_log') as mock_route:
            chat_observer.log_ai_response(
                event="response_generated",
                conversation_id="conv-123",
                assistant_response="This is the AI response content"
            )
            
            log_data = mock_route.call_args[0][0]
            
            # Should log response length but not content
            assert log_data['assistant_response_length'] == len("This is the AI response content")
            assert 'assistant_response' not in log_data
    
    def test_user_id_anonymization(self, chat_observer):
        """Test that user_id defaults to anonymous when not provided."""
        log_data = {'conversation_id': 'conv-123'}
        
        extra = chat_observer._prepare_conversation_extra(log_data)
        
        assert extra['user_id'] == 'anonymous'


if __name__ == '__main__':
    pytest.main([__file__])