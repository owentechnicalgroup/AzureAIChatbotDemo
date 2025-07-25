"""
Integration tests for dual observability system.

Tests the full interaction between Application Logging and AI Chat Observability
systems working together, routing coordination, and end-to-end functionality.
"""

import pytest
import logging
import uuid
from unittest.mock import Mock, patch, MagicMock, call
from typing import Dict, Any

from src.observability.telemetry_service import (
    initialize_dual_observability,
    route_log_by_type,
    get_application_logger,
    get_chat_observer,
    shutdown_telemetry,
    is_telemetry_initialized
)
from src.utils.logging_helpers import StructuredLogger
from src.services.logging_service import (
    log_conversation_event,
    log_performance_metrics,
    log_security_event,
    ConversationLogger,
    setup_logging
)


class TestDualObservabilityIntegration:
    """Test integration between application and chat observability systems."""
    
    @pytest.fixture
    def mock_settings(self):
        """Mock settings for dual observability."""
        settings = Mock()
        settings.applicationinsights_connection_string = "InstrumentationKey=test-key"
        settings.enable_chat_observability = True
        settings.chat_observability_connection_string = None
        settings.enable_cross_correlation = True
        settings.log_level = "INFO"
        settings.enable_console_logging = True
        settings.enable_file_logging = False
        settings.enable_json_logging = True
        return settings
    
    def setUp(self):
        """Reset telemetry state before each test."""
        shutdown_telemetry()
    
    @patch('src.observability.telemetry_service.configure_azure_monitor')
    def test_end_to_end_dual_initialization(self, mock_configure, mock_settings):
        """Test complete dual observability initialization."""
        mock_configure.return_value = None
        
        # Initialize dual observability
        result = initialize_dual_observability(mock_settings)
        
        assert result is True
        assert is_telemetry_initialized() is True
        mock_configure.assert_called_once()
        
        # Verify both systems are accessible
        app_logger = get_application_logger()
        chat_observer = get_chat_observer()
        
        assert app_logger is not None
        assert chat_observer is not None
    
    @patch('src.observability.telemetry_service.configure_azure_monitor')
    def test_cross_system_log_routing(self, mock_configure, mock_settings):
        """Test that logs route to correct systems."""
        mock_configure.return_value = None
        initialize_dual_observability(mock_settings)
        
        with patch('src.observability.application_logging.ApplicationLogger.route_application_log') as mock_app_route:
            with patch('src.observability.chat_observability.ChatObserver.route_conversation_log') as mock_chat_route:
                
                # Test application log routing
                route_log_by_type('SYSTEM', {
                    'message': 'System startup',
                    'component': 'application'
                })
                
                route_log_by_type('SECURITY', {
                    'message': 'Authentication event',
                    'credential_type': 'azure_cli'
                })
                
                route_log_by_type('PERFORMANCE', {
                    'message': 'Performance metric',
                    'response_time': 1.5
                })
                
                route_log_by_type('AZURE_OPENAI', {
                    'message': 'API call',
                    'resource_type': 'openai'
                })
                
                # Test chat log routing
                route_log_by_type('CONVERSATION', {
                    'message': 'User interaction',
                    'conversation_id': 'conv-123'
                })
                
                # Verify application logs went to application system
                assert mock_app_route.call_count == 4
                app_calls = mock_app_route.call_args_list
                assert app_calls[0][0][0] == 'SYSTEM'
                assert app_calls[1][0][0] == 'SECURITY'
                assert app_calls[2][0][0] == 'PERFORMANCE'
                assert app_calls[3][0][0] == 'AZURE_OPENAI'
                
                # Verify chat logs went to chat system
                mock_chat_route.assert_called_once()
                chat_call = mock_chat_route.call_args[0][0]
                assert chat_call['message'] == 'User interaction'
    
    @patch('src.observability.telemetry_service.configure_azure_monitor')
    def test_operation_id_correlation(self, mock_configure, mock_settings):
        """Test that operation IDs enable cross-system correlation."""
        mock_configure.return_value = None
        initialize_dual_observability(mock_settings)
        
        test_operation_id = str(uuid.uuid4())
        
        with patch('src.observability.application_logging.ApplicationLogger.route_application_log') as mock_app_route:
            with patch('src.observability.chat_observability.ChatObserver.route_conversation_log') as mock_chat_route:
                
                # Send logs with same operation_id to both systems
                route_log_by_type('SYSTEM', {
                    'message': 'System event',
                    'operation_id': test_operation_id
                })
                
                route_log_by_type('CONVERSATION', {
                    'message': 'Related conversation',
                    'operation_id': test_operation_id,
                    'conversation_id': 'conv-123'
                })
                
                # Verify operation_id is preserved in both systems
                app_log_data = mock_app_route.call_args[0][1]
                chat_log_data = mock_chat_route.call_args[0][0]
                
                assert app_log_data['operation_id'] == test_operation_id
                assert chat_log_data['operation_id'] == test_operation_id


class TestBackwardCompatibilityIntegration:
    """Test backward compatibility with existing logging patterns."""
    
    @pytest.fixture
    def mock_settings(self):
        settings = Mock()
        settings.applicationinsights_connection_string = "InstrumentationKey=test-key"
        settings.enable_chat_observability = True
        settings.chat_observability_connection_string = None
        return settings
    
    def setUp(self):
        """Reset telemetry state before each test."""
        shutdown_telemetry()
    
    @patch('src.observability.telemetry_service.configure_azure_monitor')
    @patch('src.observability.telemetry_service.is_telemetry_initialized')
    def test_structured_logger_routing_integration(self, mock_is_initialized, mock_configure, mock_settings):
        """Test StructuredLogger integration with dual observability."""
        mock_configure.return_value = None
        mock_is_initialized.return_value = True
        initialize_dual_observability(mock_settings)
        
        logger = StructuredLogger("test_module")
        
        with patch('src.utils.logging_helpers.route_log_by_type') as mock_route:
            # Test conversation event routing
            logger.log_conversation_event(
                message="User interaction",
                conversation_id="conv-123",
                user_id="user-456"
            )
            
            mock_route.assert_called_once()
            call_args = mock_route.call_args
            assert call_args[0][0] == 'CONVERSATION'
            
            log_data = call_args[0][1]
            assert log_data['message'] == "User interaction"
            assert log_data['conversation_id'] == "conv-123"
    
    @patch('src.observability.telemetry_service.configure_azure_monitor')
    @patch('src.observability.telemetry_service.is_telemetry_initialized')
    def test_logging_service_functions_integration(self, mock_is_initialized, mock_configure, mock_settings):
        """Test logging service functions with dual observability."""
        mock_configure.return_value = None
        mock_is_initialized.return_value = True
        initialize_dual_observability(mock_settings)
        
        with patch('src.observability.chat_observability.log_conversation_event') as mock_chat_log:
            with patch('src.observability.application_logging.log_performance_event') as mock_perf_log:
                with patch('src.observability.application_logging.log_security_event') as mock_sec_log:
                    
                    # Test conversation event
                    log_conversation_event(
                        event="user_message",
                        conversation_id="conv-123",
                        user_message="Hello"
                    )
                    mock_chat_log.assert_called_once()
                    
                    # Test performance event
                    log_performance_metrics(
                        operation="api_call",
                        duration=1.5,
                        success=True
                    )
                    mock_perf_log.assert_called_once()
                    
                    # Test security event
                    log_security_event(
                        event_type="authentication",
                        details={'method': 'azure_cli'},
                        severity="info"
                    )
                    mock_sec_log.assert_called_once()
    
    @patch('src.observability.telemetry_service.configure_azure_monitor')
    @patch('src.observability.telemetry_service.is_telemetry_initialized')
    def test_conversation_logger_integration(self, mock_is_initialized, mock_configure, mock_settings):
        """Test ConversationLogger integration with dual observability."""
        mock_configure.return_value = None
        mock_is_initialized.return_value = True
        initialize_dual_observability(mock_settings)
        
        with patch('src.observability.chat_observability.ConversationLogger') as mock_new_logger_class:
            mock_new_logger = Mock()
            mock_new_logger_class.return_value = mock_new_logger
            
            # Use the logging service ConversationLogger
            from src.services.logging_service import ConversationLogger
            
            with ConversationLogger(conversation_id="conv-123") as logger:
                # Should use the new chat observability ConversationLogger
                mock_new_logger_class.assert_called_once_with(
                    conversation_id="conv-123",
                    user_id=None,
                    session_id=mock_new_logger_class.call_args[1]['session_id']
                )
                mock_new_logger.__enter__.assert_called_once()


class TestFallbackAndErrorHandling:
    """Test fallback behavior and error handling in dual observability."""
    
    def setUp(self):
        """Reset telemetry state before each test."""
        shutdown_telemetry()
    
    def test_fallback_when_dual_observability_unavailable(self):
        """Test fallback to legacy logging when dual observability unavailable."""
        # Simulate dual observability not available
        with patch('src.services.logging_service.DUAL_OBSERVABILITY_AVAILABLE', False):
            with patch('src.services.logging_service.get_logger') as mock_get_logger:
                mock_logger = Mock()
                mock_get_logger.return_value = mock_logger
                
                # Should fall back to legacy logging
                log_conversation_event(
                    event="user_message",
                    conversation_id="conv-123",
                    user_message="Hello"
                )
                
                # Verify legacy logger was used
                mock_get_logger.assert_called_once()
                mock_logger.bind.assert_called_once()
    
    @patch('src.observability.telemetry_service.configure_azure_monitor')
    def test_fallback_when_initialization_fails(self, mock_configure):
        """Test fallback when dual observability initialization fails."""
        mock_configure.side_effect = Exception("Initialization failed")
        
        settings = Mock()
        settings.applicationinsights_connection_string = "test"
        
        # Should not raise exception
        result = initialize_dual_observability(settings)
        
        assert result is False
        assert is_telemetry_initialized() is False
    
    @patch('src.observability.telemetry_service.configure_azure_monitor')
    @patch('src.observability.telemetry_service.is_telemetry_initialized')
    def test_fallback_when_new_system_fails(self, mock_is_initialized, mock_configure):
        """Test fallback when new system components fail."""
        mock_configure.return_value = None
        mock_is_initialized.return_value = True
        
        settings = Mock()
        settings.applicationinsights_connection_string = "test"
        initialize_dual_observability(settings)
        
        # Make new chat observability fail
        with patch('src.observability.chat_observability.log_conversation_event', side_effect=Exception("Chat system failed")):
            with patch('src.services.logging_service.get_logger') as mock_get_logger:
                mock_logger = Mock()
                mock_get_logger.return_value = mock_logger
                
                # Should fall back to legacy logging
                log_conversation_event(
                    event="user_message",
                    conversation_id="conv-123"
                )
                
                # Verify fallback was used
                mock_get_logger.assert_called_once()


class TestSetupLoggingIntegration:
    """Test setup_logging integration with dual observability."""
    
    @pytest.fixture
    def mock_settings(self):
        settings = Mock()
        settings.applicationinsights_connection_string = "InstrumentationKey=test-key"
        settings.enable_chat_observability = True
        settings.chat_observability_connection_string = None
        settings.log_level = "INFO"
        settings.enable_console_logging = True
        settings.enable_file_logging = False
        settings.enable_json_logging = True
        return settings
    
    @patch('src.services.logging_service.setup_dual_observability_logging')
    @patch('src.services.logging_service.setup_file_logging')
    @patch('src.services.logging_service.setup_console_logging')
    @patch('src.services.logging_service.configure_structlog')
    def test_setup_logging_with_dual_observability(
        self, 
        mock_configure_structlog,
        mock_setup_console,
        mock_setup_file,
        mock_setup_dual,
        mock_settings
    ):
        """Test that setup_logging properly initializes dual observability."""
        mock_setup_dual.return_value = True
        mock_setup_console.return_value = Mock()
        mock_setup_file.return_value = None
        
        setup_logging(mock_settings)
        
        # Verify dual observability was initialized
        mock_setup_dual.assert_called_once_with(mock_settings)
        
        # Verify structlog was configured
        mock_configure_structlog.assert_called_once_with(mock_settings)
        
        # Verify logging setup completed
        mock_setup_console.assert_called_once_with(mock_settings)
    
    @patch('src.services.logging_service.setup_dual_observability_logging')
    def test_setup_logging_dual_observability_failure_handling(self, mock_setup_dual, mock_settings):
        """Test setup_logging handles dual observability failures gracefully."""
        mock_setup_dual.side_effect = Exception("Dual observability setup failed")
        
        # Should not raise exception
        with patch('src.services.logging_service.configure_structlog'):
            with patch('src.services.logging_service.setup_console_logging', return_value=Mock()):
                with patch('src.services.logging_service.setup_file_logging', return_value=None):
                    setup_logging(mock_settings)
                    
                    # Verify it attempted dual observability setup
                    mock_setup_dual.assert_called_once()


class TestConcurrentLogging:
    """Test concurrent logging scenarios in dual observability."""
    
    @pytest.fixture
    def mock_settings(self):
        settings = Mock()
        settings.applicationinsights_connection_string = "InstrumentationKey=test-key"
        settings.enable_chat_observability = True
        return settings
    
    def setUp(self):
        """Reset telemetry state before each test."""
        shutdown_telemetry()
    
    @patch('src.observability.telemetry_service.configure_azure_monitor')
    def test_concurrent_log_routing(self, mock_configure, mock_settings):
        """Test concurrent logs are routed correctly."""
        mock_configure.return_value = None
        initialize_dual_observability(mock_settings)
        
        with patch('src.observability.application_logging.ApplicationLogger.route_application_log') as mock_app_route:
            with patch('src.observability.chat_observability.ChatObserver.route_conversation_log') as mock_chat_route:
                
                # Simulate concurrent logging
                logs = [
                    ('SYSTEM', {'message': 'System log 1'}),
                    ('CONVERSATION', {'message': 'Chat log 1', 'conversation_id': 'conv-1'}),
                    ('PERFORMANCE', {'message': 'Performance log 1', 'response_time': 1.0}),
                    ('CONVERSATION', {'message': 'Chat log 2', 'conversation_id': 'conv-2'}),
                    ('SECURITY', {'message': 'Security log 1', 'credential_type': 'key'}),
                ]
                
                for log_type, log_data in logs:
                    route_log_by_type(log_type, log_data)
                
                # Verify correct routing counts
                assert mock_app_route.call_count == 3  # SYSTEM, PERFORMANCE, SECURITY
                assert mock_chat_route.call_count == 2  # CONVERSATION logs
                
                # Verify log types
                app_log_types = [call[0][0] for call in mock_app_route.call_args_list]
                assert 'SYSTEM' in app_log_types
                assert 'PERFORMANCE' in app_log_types
                assert 'SECURITY' in app_log_types
                
                # Verify conversation logs
                chat_calls = [call[0][0] for call in mock_chat_route.call_args_list]
                assert len(chat_calls) == 2
                assert all('conversation_id' in call for call in chat_calls)


class TestCleanupAndShutdown:
    """Test cleanup and shutdown of dual observability system."""
    
    @pytest.fixture
    def mock_settings(self):
        settings = Mock()
        settings.applicationinsights_connection_string = "InstrumentationKey=test-key"
        return settings
    
    @patch('src.observability.telemetry_service.configure_azure_monitor')
    def test_shutdown_telemetry_cleanup(self, mock_configure, mock_settings):
        """Test that shutdown properly cleans up both systems."""
        mock_configure.return_value = None
        
        # Initialize
        initialize_dual_observability(mock_settings)
        assert is_telemetry_initialized() is True
        
        # Get logger instances to populate globals
        app_logger = get_application_logger()
        chat_observer = get_chat_observer()
        assert app_logger is not None
        assert chat_observer is not None
        
        # Shutdown
        shutdown_telemetry()
        
        # Verify cleanup
        assert is_telemetry_initialized() is False
        
        # Verify new instances are created after shutdown
        new_app_logger = get_application_logger()
        new_chat_observer = get_chat_observer()
        
        # Should be new instances (due to reset globals)
        assert new_app_logger is not app_logger
        assert new_chat_observer is not chat_observer


if __name__ == '__main__':
    pytest.main([__file__])