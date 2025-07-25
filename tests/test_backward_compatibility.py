"""
Backward compatibility tests for dual observability system.

Ensures that existing logging patterns continue to work unchanged
when dual observability is enabled or disabled.
"""

import pytest
import logging
import uuid
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

from src.utils.logging_helpers import (
    StructuredLogger,
    log_startup_event,
    log_config_load,
    log_health_check,
    log_operation
)
from src.services.logging_service import (
    log_conversation_event,
    log_performance_metrics,
    log_security_event,
    ConversationLogger,
    get_logger,
    setup_logging
)


class TestStructuredLoggerBackwardCompatibility:
    """Test StructuredLogger backward compatibility."""
    
    @pytest.fixture
    def structured_logger(self):
        """Create StructuredLogger instance."""
        return StructuredLogger("test.module")
    
    def test_initialization_unchanged_interface(self, structured_logger):
        """Test that StructuredLogger initialization interface is unchanged."""
        # Should initialize with logger_name parameter
        assert structured_logger.logger is not None
        assert structured_logger.operation_id is not None
        
        # Should be able to create with any logger name
        logger2 = StructuredLogger("another.module")
        assert logger2.logger.name == "another.module"
    
    def test_log_conversation_event_signature_preserved(self, structured_logger):
        """Test that log_conversation_event method signature is preserved."""
        with patch.object(structured_logger, '_route_log') as mock_route:
            # Test all parameter combinations that existed before
            structured_logger.log_conversation_event(
                message="Test message",
                conversation_id="conv-123"
            )
            
            structured_logger.log_conversation_event(
                message="Test message",
                conversation_id="conv-123",
                user_id="user-456",
                session_id="session-789",
                turn_number=1,
                message_length=50,
                level="INFO"
            )
            
            # Should call routing twice
            assert mock_route.call_count == 2
            
            # Verify log_type is set correctly
            for call_args in mock_route.call_args_list:
                assert call_args[0][0] == 'CONVERSATION'
    
    def test_log_azure_operation_signature_preserved(self, structured_logger):
        """Test that log_azure_operation method signature is preserved."""
        with patch.object(structured_logger, '_route_log') as mock_route:
            # Test with minimal parameters
            structured_logger.log_azure_operation(
                message="Azure operation",
                resource_type="storage",
                resource_name="mystorageaccount",
                operation_type="upload"
            )
            
            # Test with all parameters
            structured_logger.log_azure_operation(
                message="Azure operation with all params",
                resource_type="openai",
                resource_name="gpt-4-deployment",
                operation_type="chat_completion",
                duration=1.5,
                success=True,
                error_type=None,
                error_code=None,
                level="INFO"
            )
            
            assert mock_route.call_count == 2
            
            # Verify correct log_type assignment
            call_args = mock_route.call_args_list
            # First call should be SYSTEM (storage)
            assert call_args[0][0][0] == 'SYSTEM'
            # Second call should be AZURE_OPENAI (openai)
            assert call_args[1][0][0] == 'AZURE_OPENAI'
    
    def test_log_performance_metrics_signature_preserved(self, structured_logger):
        """Test that log_performance_metrics method signature is preserved."""
        with patch.object(structured_logger, '_route_log') as mock_route:
            # Test with minimal parameters
            structured_logger.log_performance_metrics(
                message="Performance metric",
                response_time=1.5
            )
            
            # Test with all parameters
            structured_logger.log_performance_metrics(
                message="Full performance metric",
                response_time=2.5,
                tokens_prompt=100,
                tokens_completion=150,
                tokens_total=250,
                request_size=1024,
                response_size=2048,
                operation_name="api.chat_completion"
            )
            
            assert mock_route.call_count == 2
            
            # Verify log_type is PERFORMANCE
            for call_args in mock_route.call_args_list:
                assert call_args[0][0] == 'PERFORMANCE'
    
    def test_log_authentication_event_signature_preserved(self, structured_logger):
        """Test that log_authentication_event method signature is preserved."""
        with patch.object(structured_logger, '_route_log') as mock_route:
            # Test with minimal parameters
            structured_logger.log_authentication_event(
                message="Auth event",
                credential_type="azure_cli",
                success=True
            )
            
            # Test with all parameters
            structured_logger.log_authentication_event(
                message="Full auth event",
                credential_type="managed_identity",
                success=False,
                duration=0.5,
                error_type="AuthenticationError",
                resource_name="key-vault"
            )
            
            assert mock_route.call_count == 2
            
            # Verify log_type is SECURITY
            for call_args in mock_route.call_args_list:
                assert call_args[0][0] == 'SECURITY'
    
    def test_log_key_vault_operation_signature_preserved(self, structured_logger):
        """Test that log_key_vault_operation method signature is preserved."""
        with patch.object(structured_logger, '_route_log') as mock_route:
            # Test with minimal parameters
            structured_logger.log_key_vault_operation(
                message="Key vault op",
                secret_name="api-key",
                operation="get_secret",
                success=True
            )
            
            # Test with all parameters
            structured_logger.log_key_vault_operation(
                message="Full key vault op",
                secret_name="openai-key",
                operation="set_secret",
                success=False,
                duration=1.0,
                error_type="VaultError"
            )
            
            assert mock_route.call_count == 2
            
            # Verify log_type is SECURITY
            for call_args in mock_route.call_args_list:
                assert call_args[0][0] == 'SECURITY'


class TestLoggingHelpersBackwardCompatibility:
    """Test logging helpers backward compatibility."""
    
    def test_log_startup_event_signature_preserved(self):
        """Test that log_startup_event function signature is preserved."""
        with patch('src.utils.logging_helpers.StructuredLogger') as mock_logger_class:
            mock_logger = Mock()
            mock_logger_class.return_value = mock_logger
            
            # Test with minimal parameters
            log_startup_event("App started", "application")
            
            # Test with all parameters
            log_startup_event(
                message="App started with error",
                component="database",
                success=False,
                error_type="ConnectionError"
            )
            
            # Should create StructuredLogger and call log_azure_operation
            assert mock_logger_class.call_count == 2
            assert mock_logger.log_azure_operation.call_count == 2
    
    def test_log_config_load_signature_preserved(self):
        """Test that log_config_load function signature is preserved."""
        with patch('src.utils.logging_helpers.StructuredLogger') as mock_logger_class:
            mock_logger = Mock()
            mock_logger_class.return_value = mock_logger
            
            # Test with minimal parameters
            log_config_load("Config loaded", ".env")
            
            # Test with all parameters
            log_config_load(
                message="Config load failed",
                config_source="key_vault",
                success=False,
                error_type="ConfigError"
            )
            
            assert mock_logger_class.call_count == 2
            assert mock_logger.log_azure_operation.call_count == 2
    
    def test_log_health_check_signature_preserved(self):
        """Test that log_health_check function signature is preserved."""
        with patch('src.utils.logging_helpers.StructuredLogger') as mock_logger_class:
            mock_logger = Mock()
            mock_logger_class.return_value = mock_logger
            
            # Test with minimal parameters
            log_health_check("Health check", "database")
            
            # Test with all parameters
            log_health_check(
                message="Health check failed",
                component="redis",
                success=False,
                duration=5.0,
                error_type="TimeoutError"
            )
            
            assert mock_logger_class.call_count == 2
            assert mock_logger.log_azure_operation.call_count == 2
    
    def test_log_operation_decorator_signature_preserved(self):
        """Test that log_operation decorator signature is preserved."""
        with patch('src.utils.logging_helpers.StructuredLogger') as mock_logger_class:
            mock_logger = Mock()
            mock_logger_class.return_value = mock_logger
            
            # Test with minimal parameters
            @log_operation("test_operation")
            def test_func1():
                return "result1"
            
            # Test with all parameters
            @log_operation("test_operation_2", component="test_component", resource_type="test_resource")
            def test_func2():
                return "result2"
            
            result1 = test_func1()
            result2 = test_func2()
            
            assert result1 == "result1"
            assert result2 == "result2"
            assert mock_logger_class.call_count == 2
            assert mock_logger.log_azure_operation.call_count == 2


class TestLoggingServiceBackwardCompatibility:
    """Test logging service backward compatibility."""
    
    def test_log_conversation_event_signature_preserved(self):
        """Test that log_conversation_event function signature is preserved."""
        with patch('src.services.logging_service.DUAL_OBSERVABILITY_AVAILABLE', False):
            with patch('src.services.logging_service.get_logger') as mock_get_logger:
                mock_logger = Mock()
                mock_bound_logger = Mock()
                mock_logger.bind.return_value = mock_bound_logger
                mock_get_logger.return_value = mock_logger
                
                # Test with minimal parameters
                log_conversation_event(
                    event="user_message",
                    conversation_id="conv-123"
                )
                
                # Test with all parameters
                log_conversation_event(
                    event="assistant_response",
                    conversation_id="conv-456",
                    user_message="Hello",
                    assistant_response="Hi there!",
                    token_usage={'total_tokens': 50},
                    response_time=1.5,
                    error=None,
                    additional_context="web_client"
                )
                
                # Should call get_logger and bind
                assert mock_get_logger.call_count == 2
                assert mock_logger.bind.call_count == 2
    
    def test_log_performance_metrics_signature_preserved(self):
        """Test that log_performance_metrics function signature is preserved."""
        with patch('src.services.logging_service.DUAL_OBSERVABILITY_AVAILABLE', False):
            with patch('src.services.logging_service.get_logger') as mock_get_logger:
                mock_logger = Mock()
                mock_bound_logger = Mock()
                mock_logger.bind.return_value = mock_bound_logger
                mock_get_logger.return_value = mock_logger
                
                # Test with minimal parameters
                log_performance_metrics(
                    operation="api_call",
                    duration=1.5
                )
                
                # Test with all parameters
                log_performance_metrics(
                    operation="complex_operation",
                    duration=2.5,
                    success=True,
                    tokens=150,
                    request_size=1024
                )
                
                assert mock_get_logger.call_count == 2
                assert mock_logger.bind.call_count == 2
    
    def test_log_security_event_signature_preserved(self):
        """Test that log_security_event function signature is preserved."""
        with patch('src.services.logging_service.DUAL_OBSERVABILITY_AVAILABLE', False):
            with patch('src.services.logging_service.get_logger') as mock_get_logger:
                mock_logger = Mock()
                mock_bound_logger = Mock()
                mock_logger.bind.return_value = mock_bound_logger
                mock_get_logger.return_value = mock_logger
                
                # Test with minimal parameters
                log_security_event(
                    event_type="authentication",
                    details={'method': 'azure_cli'}
                )
                
                # Test with all parameters
                log_security_event(
                    event_type="authorization",
                    details={'resource': 'key_vault', 'action': 'read'},
                    severity="warning",
                    user_id="user-123"
                )
                
                assert mock_get_logger.call_count == 2
                assert mock_logger.bind.call_count == 2
    
    def test_conversation_logger_signature_preserved(self):
        """Test that ConversationLogger class signature is preserved."""
        with patch('src.services.logging_service.DUAL_OBSERVABILITY_AVAILABLE', False):
            # Test with minimal parameters
            logger1 = ConversationLogger()
            assert logger1.conversation_id is not None
            assert logger1.session_id is not None
            assert logger1.user_id is None
            
            # Test with all parameters
            logger2 = ConversationLogger(
                conversation_id="conv-123",
                user_id="user-456",
                session_id="session-789"
            )
            assert logger2.conversation_id == "conv-123"
            assert logger2.user_id == "user-456"
            assert logger2.session_id == "session-789"
    
    def test_conversation_logger_context_manager_behavior(self):
        """Test that ConversationLogger context manager behavior is preserved."""
        with patch('src.services.logging_service.DUAL_OBSERVABILITY_AVAILABLE', False):
            with patch('src.services.logging_service.get_logger') as mock_get_logger:
                mock_logger = Mock()
                mock_bound_logger = Mock()
                mock_logger.bind.return_value = mock_bound_logger
                mock_get_logger.return_value = mock_logger
                
                logger = ConversationLogger(conversation_id="conv-123")
                
                # Test context manager entry
                with logger as bound_logger:
                    assert bound_logger == mock_bound_logger
                    
                    # Test log_message method
                    logger.log_message("user", "Hello", {"client": "web"})
                
                # Verify logger was bound with correct context
                mock_logger.bind.assert_called_once()
                bind_args = mock_logger.bind.call_args[1]
                assert bind_args['conversation_id'] == "conv-123"
    
    def test_get_logger_signature_preserved(self):
        """Test that get_logger function signature is preserved."""
        with patch('structlog.get_logger') as mock_structlog_get:
            mock_logger = Mock()
            mock_bound_logger = Mock()
            mock_logger.bind.return_value = mock_bound_logger
            mock_structlog_get.return_value = mock_logger
            
            # Test with minimal parameters
            logger1 = get_logger("test.module")
            assert logger1 == mock_logger
            
            # Test with context binding
            logger2 = get_logger("test.module", context_key="context_value")
            assert logger2 == mock_bound_logger
            
            mock_structlog_get.assert_called_with("test.module")
            mock_logger.bind.assert_called_once_with(context_key="context_value")


class TestSetupLoggingBackwardCompatibility:
    """Test setup_logging backward compatibility."""
    
    @pytest.fixture
    def mock_settings(self):
        """Mock settings for testing."""
        settings = Mock()
        settings.log_level = "INFO"
        settings.log_format = "json"
        settings.log_file_path = "logs/test.log"
        settings.enable_console_logging = True
        settings.enable_file_logging = False
        settings.enable_json_logging = True
        settings.applicationinsights_connection_string = None
        settings.enable_chat_observability = False
        return settings
    
    @patch('src.services.logging_service.configure_structlog')
    @patch('src.services.logging_service.setup_file_logging')
    @patch('src.services.logging_service.setup_console_logging')
    @patch('src.services.logging_service.setup_dual_observability_logging')
    def test_setup_logging_signature_preserved(
        self,
        mock_setup_dual,
        mock_setup_console,
        mock_setup_file,
        mock_configure_structlog,
        mock_settings
    ):
        """Test that setup_logging function signature is preserved."""
        mock_setup_dual.return_value = False
        mock_setup_console.return_value = Mock()
        mock_setup_file.return_value = None
        
        # Test with no parameters (should get default settings)
        with patch('src.services.logging_service.get_settings') as mock_get_settings:
            mock_get_settings.return_value = mock_settings
            setup_logging()
            mock_get_settings.assert_called_once()
        
        # Test with settings parameter
        setup_logging(mock_settings)
        
        # Verify all expected setup functions were called
        assert mock_configure_structlog.call_count == 2
        assert mock_setup_console.call_count == 2
        assert mock_setup_file.call_count == 2
        assert mock_setup_dual.call_count == 2
    
    @patch('src.services.logging_service.setup_dual_observability_logging')
    def test_setup_logging_legacy_behavior_when_dual_fails(self, mock_setup_dual, mock_settings):
        """Test that setup_logging falls back to legacy behavior when dual observability fails."""
        mock_setup_dual.return_value = False
        
        with patch('src.services.logging_service.configure_structlog'):
            with patch('src.services.logging_service.setup_console_logging', return_value=Mock()):
                with patch('src.services.logging_service.setup_file_logging', return_value=None):
                    with patch('logging.getLogger') as mock_get_root_logger:
                        mock_root_logger = Mock()
                        mock_root_logger.handlers = []
                        mock_get_root_logger.return_value = mock_root_logger
                        
                        # Should not raise exception
                        setup_logging(mock_settings)
                        
                        # Should still set up basic logging
                        mock_root_logger.setLevel.assert_called_once()


class TestDataStructureCompatibility:
    """Test that data structures and return values remain compatible."""
    
    def test_structured_logger_operation_id_type(self):
        """Test that operation_id remains a string type."""
        logger = StructuredLogger("test.module")
        assert isinstance(logger.operation_id, str)
        
        # Should be a valid UUID string
        uuid.UUID(logger.operation_id)
    
    def test_log_data_structure_compatibility(self):
        """Test that log data structures maintain expected fields."""
        logger = StructuredLogger("test.module")
        
        with patch.object(logger, '_route_log') as mock_route:
            logger.log_conversation_event(
                message="Test",
                conversation_id="conv-123",
                user_id="user-456",
                turn_number=1
            )
            
            # Verify log data structure
            call_args = mock_route.call_args
            log_type = call_args[0][0]
            log_data = call_args[0][1]
            
            assert log_type == 'CONVERSATION'
            assert isinstance(log_data, dict)
            
            # Check expected fields exist
            expected_fields = [
                'message', 'log_type', 'conversation_id', 
                'user_id', 'turn_number', 'level', 'operation_type',
                'component', 'event_type', 'event_category', 'operation_name'
            ]
            
            for field in expected_fields:
                assert field in log_data
    
    def test_conversation_logger_context_manager_return_type(self):
        """Test that ConversationLogger context manager returns expected type."""
        with patch('src.services.logging_service.DUAL_OBSERVABILITY_AVAILABLE', False):
            with patch('src.services.logging_service.get_logger') as mock_get_logger:
                mock_logger = Mock()
                mock_bound_logger = Mock()
                mock_logger.bind.return_value = mock_bound_logger
                mock_get_logger.return_value = mock_logger
                
                logger = ConversationLogger()
                
                with logger as bound_logger:
                    # Should return the bound logger
                    assert bound_logger == mock_bound_logger
                    
                    # Should have expected methods
                    assert hasattr(bound_logger, 'info')
                    assert hasattr(bound_logger, 'error')
                    assert hasattr(bound_logger, 'warning')


class TestErrorBackwardCompatibility:
    """Test that error handling remains compatible."""
    
    def test_initialization_errors_preserved(self):
        """Test that initialization errors are handled as before."""
        # Should not raise exception for invalid logger names
        logger = StructuredLogger("")
        assert logger is not None
        
        logger = StructuredLogger("test.module.with.dots")
        assert logger is not None
    
    def test_logging_method_errors_preserved(self):
        """Test that logging method errors are handled as before."""
        logger = StructuredLogger("test.module")
        
        with patch.object(logger, '_route_log', side_effect=Exception("Route error")):
            # Should not raise exception
            logger.log_conversation_event(
                message="Test",
                conversation_id="conv-123"
            )
    
    def test_setup_logging_error_handling_preserved(self):
        """Test that setup_logging error handling remains the same."""
        settings = Mock()
        settings.log_level = "INVALID_LEVEL"  # This should cause an error
        settings.enable_console_logging = True
        settings.enable_file_logging = False
        settings.applicationinsights_connection_string = None
        
        # Should handle invalid log level gracefully
        with patch('src.services.logging_service.configure_structlog'):
            with patch('src.services.logging_service.setup_dual_observability_logging', return_value=False):
                with patch('logging.getLogger') as mock_get_root_logger:
                    mock_root_logger = Mock()
                    mock_root_logger.handlers = []
                    mock_get_root_logger.return_value = mock_root_logger
                    
                    # Should not raise exception
                    setup_logging(settings)


if __name__ == '__main__':
    pytest.main([__file__])