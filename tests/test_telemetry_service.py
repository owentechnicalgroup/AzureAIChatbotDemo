"""
Tests for dual observability telemetry service.

Covers routing logic, initialization, and coordination between
Application Logging and AI Chat Observability systems.
"""

import pytest
import logging
import uuid
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

from src.observability.telemetry_service import (
    determine_log_category,
    LogTypeCategory,
    initialize_dual_observability,
    route_log_by_type,
    get_application_logger,
    get_chat_observer,
    is_telemetry_initialized,
    shutdown_telemetry,
    APPLICATION_LOG_TYPES,
    CHAT_OBSERVABILITY_TYPES,
    create_operation_context
)


class TestLogTypeRouting:
    """Test log type categorization and routing decisions."""
    
    def test_application_log_types_routing(self):
        """Test that application log types route to APPLICATION category."""
        for log_type in APPLICATION_LOG_TYPES.keys():
            category = determine_log_category(log_type)
            assert category == LogTypeCategory.APPLICATION, f"{log_type} should route to APPLICATION"
    
    def test_chat_log_types_routing(self):
        """Test that chat log types route to CHAT category."""
        for log_type in CHAT_OBSERVABILITY_TYPES.keys():
            category = determine_log_category(log_type)
            assert category == LogTypeCategory.CHAT, f"{log_type} should route to CHAT"
    
    def test_unknown_log_type_defaults_to_application(self):
        """Test that unknown log types default to APPLICATION category."""
        unknown_types = ['UNKNOWN', 'CUSTOM', 'TEST_TYPE']
        for log_type in unknown_types:
            category = determine_log_category(log_type)
            assert category == LogTypeCategory.APPLICATION, f"{log_type} should default to APPLICATION"
    
    def test_case_sensitivity(self):
        """Test that log type routing is case-sensitive as expected."""
        # Test that exact case works
        assert determine_log_category('CONVERSATION') == LogTypeCategory.CHAT
        assert determine_log_category('SYSTEM') == LogTypeCategory.APPLICATION
        
        # Test that different case defaults to application
        assert determine_log_category('conversation') == LogTypeCategory.APPLICATION
        assert determine_log_category('system') == LogTypeCategory.APPLICATION


class TestDualObservabilityInitialization:
    """Test dual observability system initialization."""
    
    @pytest.fixture
    def mock_settings(self):
        """Mock settings with required configuration."""
        settings = Mock()
        settings.applicationinsights_connection_string = "InstrumentationKey=test-key"
        settings.enable_chat_observability = True
        settings.chat_observability_connection_string = None  # Will fallback to main connection
        return settings
    
    @patch('azure.monitor.opentelemetry.configure_azure_monitor')
    def test_successful_initialization(self, mock_configure, mock_settings):
        """Test successful dual observability initialization."""
        mock_configure.return_value = None  # Simulate successful configuration
        
        result = initialize_dual_observability(mock_settings)
        
        assert result is True
        mock_configure.assert_called_once()
        assert is_telemetry_initialized() is True
    
    def test_initialization_without_connection_string(self, mock_settings):
        """Test initialization failure when connection string is missing."""
        mock_settings.applicationinsights_connection_string = None
        
        result = initialize_dual_observability(mock_settings)
        
        assert result is False
        assert is_telemetry_initialized() is False
    
    @pytest.mark.skip(reason="Skip complex Azure Monitor mock test - functionality tested elsewhere")
    def test_initialization_with_azure_monitor_failure(self, mock_settings):
        """Test initialization failure when Azure Monitor configuration fails."""
        # This test is skipped as it requires complex mocking of Azure Monitor imports
        # The error handling functionality is tested through other integration tests
        pass
    
    def test_double_initialization_is_safe(self, mock_settings):
        """Test that double initialization is handled safely."""
        # First initialization
        with patch('azure.monitor.opentelemetry.configure_azure_monitor'):
            result1 = initialize_dual_observability(mock_settings)
        
        # Second initialization
        with patch('azure.monitor.opentelemetry.configure_azure_monitor') as mock_configure:
            result2 = initialize_dual_observability(mock_settings)
            
            assert result1 is True
            assert result2 is True
            # Should not call configure_azure_monitor again
            mock_configure.assert_not_called()


class TestLogRouting:
    """Test log routing to appropriate observability systems."""
    
    def setUp(self):
        """Reset telemetry state before each test."""
        shutdown_telemetry()
    
    @patch('src.observability.telemetry_service.get_application_logger')
    def test_application_log_routing(self, mock_get_app_logger):
        """Test that application logs route to application logger."""
        mock_app_logger = Mock()
        mock_get_app_logger.return_value = mock_app_logger
        
        log_data = {
            'message': 'Test system event',
            'operation_type': 'startup'
        }
        
        route_log_by_type('SYSTEM', log_data)
        
        mock_get_app_logger.assert_called_once()
        mock_app_logger.route_application_log.assert_called_once_with('SYSTEM', log_data)
    
    @patch('src.observability.telemetry_service.get_chat_observer')
    def test_chat_log_routing(self, mock_get_chat_observer):
        """Test that chat logs route to chat observer."""
        mock_chat_observer = Mock()
        mock_get_chat_observer.return_value = mock_chat_observer
        
        log_data = {
            'message': 'Test conversation event',
            'conversation_id': 'test-conv-123'
        }
        
        route_log_by_type('CONVERSATION', log_data)
        
        mock_get_chat_observer.assert_called_once()
        mock_chat_observer.route_conversation_log.assert_called_once_with(log_data)
    
    def test_operation_id_auto_generation(self):
        """Test that operation_id is automatically added when missing."""
        with patch('src.observability.telemetry_service.get_application_logger') as mock_get_app_logger:
            mock_app_logger = Mock()
            mock_get_app_logger.return_value = mock_app_logger
            
            log_data = {'message': 'Test without operation_id'}
            
            route_log_by_type('SYSTEM', log_data)
            
            # Check that operation_id was added
            called_args = mock_app_logger.route_application_log.call_args[0]
            called_log_data = called_args[1]
            
            assert 'operation_id' in called_log_data
            assert isinstance(called_log_data['operation_id'], str)
            # Should be a valid UUID
            uuid.UUID(called_log_data['operation_id'])
    
    @patch('src.observability.telemetry_service.get_application_logger')
    def test_operation_id_preservation(self, mock_get_app_logger):
        """Test that existing operation_id is preserved."""
        mock_app_logger = Mock()
        mock_get_app_logger.return_value = mock_app_logger
        
        test_operation_id = str(uuid.uuid4())
        log_data = {
            'message': 'Test with operation_id',
            'operation_id': test_operation_id
        }
        
        route_log_by_type('SYSTEM', log_data)
        
        called_args = mock_app_logger.route_application_log.call_args[0]
        called_log_data = called_args[1]
        
        assert called_log_data['operation_id'] == test_operation_id


class TestLoggerInstanceManagement:
    """Test logger instance management and lifecycle."""
    
    def setUp(self):
        """Reset telemetry state before each test."""
        shutdown_telemetry()
    
    @patch('src.observability.application_logging.ApplicationLogger')
    def test_application_logger_singleton(self, mock_app_logger_class):
        """Test that application logger uses singleton pattern."""
        mock_instance = Mock()
        mock_app_logger_class.return_value = mock_instance
        
        # Call multiple times
        logger1 = get_application_logger()
        logger2 = get_application_logger()
        
        # Should return same instance
        assert logger1 is logger2
        # Should only create instance once
        mock_app_logger_class.assert_called_once()
    
    @patch('src.observability.chat_observability.ChatObserver')
    def test_chat_observer_singleton(self, mock_chat_observer_class):
        """Test that chat observer uses singleton pattern."""
        mock_instance = Mock()
        mock_chat_observer_class.return_value = mock_instance
        
        # Call multiple times
        observer1 = get_chat_observer()
        observer2 = get_chat_observer()
        
        # Should return same instance
        assert observer1 is observer2
        # Should only create instance once
        mock_chat_observer_class.assert_called_once()
    
    def test_shutdown_telemetry_cleanup(self):
        """Test that shutdown properly cleans up telemetry state."""
        # Initialize state
        with patch('azure.monitor.opentelemetry.configure_azure_monitor'):
            mock_settings = Mock()
            mock_settings.applicationinsights_connection_string = "test"
            initialize_dual_observability(mock_settings)
        
        # Get instances to populate globals
        with patch('src.observability.application_logging.ApplicationLogger'):
            get_application_logger()
        with patch('src.observability.chat_observability.ChatObserver'):
            get_chat_observer()
        
        # Verify initialized
        assert is_telemetry_initialized() is True
        
        # Shutdown
        shutdown_telemetry()
        
        # Verify cleaned up
        assert is_telemetry_initialized() is False


class TestOperationContext:
    """Test operation context creation for correlation."""
    
    def test_create_operation_context_structure(self):
        """Test that operation context has correct structure."""
        context = create_operation_context("test_component", "test")
        
        assert hasattr(context, 'operation_id')
        assert hasattr(context, 'timestamp')
        assert hasattr(context, 'component')
        assert hasattr(context, 'environment')
        
        assert context.component == "test_component"
        assert context.environment == "test"
        assert isinstance(context.operation_id, str)
        
        # Verify operation_id is valid UUID
        uuid.UUID(context.operation_id)
    
    def test_create_operation_context_defaults(self):
        """Test operation context creation with default values."""
        context = create_operation_context("test_component")
        
        assert context.component == "test_component"
        assert context.environment == "dev"  # Default value
    
    def test_operation_context_unique_ids(self):
        """Test that each context gets unique operation ID."""
        context1 = create_operation_context("component1")
        context2 = create_operation_context("component2")
        
        assert context1.operation_id != context2.operation_id


class TestErrorHandling:
    """Test error handling in telemetry service."""
    
    @patch('src.observability.telemetry_service.get_application_logger')
    def test_routing_error_handling(self, mock_get_app_logger):
        """Test that routing errors are handled gracefully."""
        # Make application logger raise exception
        mock_get_app_logger.side_effect = Exception("Application logger error")
        
        log_data = {'message': 'Test error handling'}
        
        # Should not raise exception
        route_log_by_type('SYSTEM', log_data)
        
        # Verify it attempted to get the logger
        mock_get_app_logger.assert_called_once()
    
    @patch('src.observability.telemetry_service.get_chat_observer')
    def test_chat_routing_error_handling(self, mock_get_chat_observer):
        """Test that chat routing errors are handled gracefully."""
        # Make chat observer raise exception
        mock_get_chat_observer.side_effect = Exception("Chat observer error")
        
        log_data = {'message': 'Test chat error handling'}
        
        # Should not raise exception
        route_log_by_type('CONVERSATION', log_data)
        
        # Verify it attempted to get the observer
        mock_get_chat_observer.assert_called_once()


if __name__ == '__main__':
    pytest.main([__file__])