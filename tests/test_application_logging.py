"""
Tests for Application Logging system.

Covers SYSTEM, SECURITY, PERFORMANCE, and AZURE_OPENAI log types
routing to standard Azure Application Insights workspace.
"""

import pytest
import logging
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

from src.observability.application_logging import (
    ApplicationLogger,
    log_system_event,
    log_security_event,
    log_performance_event,
    log_azure_openai_event,
    log_operation
)


class TestApplicationLogger:
    """Test ApplicationLogger class functionality."""
    
    @pytest.fixture
    def app_logger(self):
        """Create ApplicationLogger instance for testing."""
        return ApplicationLogger("test.application")
    
    def test_initialization(self, app_logger):
        """Test ApplicationLogger initialization."""
        assert app_logger.logger is not None
        assert app_logger.structlog_logger is not None
        assert app_logger.operation_id is not None
    
    def test_route_application_log_system(self, app_logger):
        """Test routing SYSTEM log type."""
        with patch.object(app_logger, '_handle_system_log') as mock_handler:
            log_data = {'message': 'Test system log', 'component': 'test'}
            
            app_logger.route_application_log('SYSTEM', log_data)
            
            mock_handler.assert_called_once_with(log_data)
    
    def test_route_application_log_security(self, app_logger):
        """Test routing SECURITY log type."""
        with patch.object(app_logger, '_handle_security_log') as mock_handler:
            log_data = {'message': 'Test security log', 'credential_type': 'api_key'}
            
            app_logger.route_application_log('SECURITY', log_data)
            
            mock_handler.assert_called_once_with(log_data)
    
    def test_route_application_log_performance(self, app_logger):
        """Test routing PERFORMANCE log type."""
        with patch.object(app_logger, '_handle_performance_log') as mock_handler:
            log_data = {'message': 'Test performance log', 'response_time': 1.5}
            
            app_logger.route_application_log('PERFORMANCE', log_data)
            
            mock_handler.assert_called_once_with(log_data)
    
    def test_route_application_log_azure_openai(self, app_logger):
        """Test routing AZURE_OPENAI log type."""
        with patch.object(app_logger, '_handle_azure_openai_log') as mock_handler:
            log_data = {'message': 'Test Azure OpenAI log', 'resource_type': 'openai'}
            
            app_logger.route_application_log('AZURE_OPENAI', log_data)
            
            mock_handler.assert_called_once_with(log_data)
    
    def test_route_application_log_unknown_defaults_to_system(self, app_logger):
        """Test that unknown log types default to SYSTEM handling."""
        with patch.object(app_logger, '_handle_system_log') as mock_handler:
            log_data = {'message': 'Test unknown log type'}
            
            app_logger.route_application_log('UNKNOWN_TYPE', log_data)
            
            mock_handler.assert_called_once_with(log_data)
    
    def test_route_application_log_error_handling(self, app_logger):
        """Test error handling in log routing."""
        with patch.object(app_logger, '_handle_system_log', side_effect=Exception("Handler error")):
            log_data = {'message': 'Test error handling'}
            
            # Should not raise exception
            app_logger.route_application_log('SYSTEM', log_data)


class TestSystemLogHandling:
    """Test SYSTEM log type handling."""
    
    @pytest.fixture
    def app_logger(self):
        return ApplicationLogger("test.application")
    
    def test_handle_system_log_basic(self, app_logger):
        """Test basic system log handling."""
        with patch.object(app_logger.logger, 'info') as mock_log:
            log_data = {
                'message': 'Application started',
                'level': 'INFO',
                'component': 'startup'
            }
            
            app_logger._handle_system_log(log_data)
            
            mock_log.assert_called_once()
            call_args = mock_log.call_args
            assert call_args[0][0] == 'Application started'
            
            extra = call_args[1]['extra']
            assert extra['log_type'] == 'SYSTEM'
            assert extra['component'] == 'startup'
            assert extra['event_category'] == 'system'
    
    def test_handle_system_log_with_defaults(self, app_logger):
        """Test system log handling with default values."""
        with patch.object(app_logger.logger, 'info') as mock_log:
            log_data = {'message': 'Test message'}
            
            app_logger._handle_system_log(log_data)
            
            call_args = mock_log.call_args
            extra = call_args[1]['extra']
            
            assert extra['operation_type'] == 'system'
            assert extra['component'] == 'application'
            assert extra['event_type'] == 'system_event'
            assert extra['operation_name'] == 'system.operation'
    
    def test_handle_system_log_different_levels(self, app_logger):
        """Test system log handling with different log levels."""
        levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR']
        
        for level in levels:
            with patch.object(app_logger.logger, level.lower()) as mock_log:
                log_data = {'message': f'Test {level} message', 'level': level}
                
                app_logger._handle_system_log(log_data)
                
                mock_log.assert_called_once()


class TestSecurityLogHandling:
    """Test SECURITY log type handling."""
    
    @pytest.fixture
    def app_logger(self):
        return ApplicationLogger("test.application")
    
    def test_handle_security_log_authentication(self, app_logger):
        """Test security log handling for authentication events."""
        with patch.object(app_logger.logger, 'info') as mock_log:
            log_data = {
                'message': 'Authentication successful',
                'level': 'INFO',
                'credential_type': 'azure_cli',
                'operation_type': 'authentication',
                'success': True
            }
            
            app_logger._handle_security_log(log_data)
            
            call_args = mock_log.call_args
            extra = call_args[1]['extra']
            
            assert extra['log_type'] == 'SECURITY'
            assert extra['credential_type'] == 'azure_cli'
            assert extra['event_category'] == 'security'
            assert extra['resource_type'] == 'credential'
    
    def test_handle_security_log_key_vault(self, app_logger):
        """Test security log handling for Key Vault operations."""
        with patch.object(app_logger.logger, 'error') as mock_log:
            log_data = {
                'message': 'Key Vault operation failed',
                'level': 'ERROR',
                'secret_name': 'openai-api-key',
                'resource_type': 'key_vault',
                'operation_type': 'get_secret',
                'success': False
            }
            
            app_logger._handle_security_log(log_data)
            
            call_args = mock_log.call_args
            extra = call_args[1]['extra']
            
            assert extra['log_type'] == 'SECURITY'
            assert extra['secret_name'] == 'openai-api-key'
            assert extra['resource_type'] == 'key_vault'


class TestPerformanceLogHandling:
    """Test PERFORMANCE log type handling."""
    
    @pytest.fixture
    def app_logger(self):
        return ApplicationLogger("test.application")
    
    def test_handle_performance_log_with_metrics(self, app_logger):
        """Test performance log handling with various metrics."""
        with patch.object(app_logger.logger, 'info') as mock_log:
            log_data = {
                'message': 'API request completed',
                'level': 'INFO',
                'response_time': 2.5,
                'duration': 2.3,
                'tokens_prompt': 150,
                'tokens_completion': 200,
                'tokens_total': 350,
                'request_size': 1024,
                'response_size': 2048
            }
            
            app_logger._handle_performance_log(log_data)
            
            call_args = mock_log.call_args
            extra = call_args[1]['extra']
            
            assert extra['log_type'] == 'PERFORMANCE'
            assert extra['response_time'] == 2.5
            assert extra['duration'] == 2.3
            assert extra['tokens_prompt'] == 150
            assert extra['tokens_completion'] == 200
            assert extra['tokens_total'] == 350
            assert extra['request_size'] == 1024
            assert extra['response_size'] == 2048
            assert extra['event_category'] == 'performance'
    
    def test_handle_performance_log_minimal(self, app_logger):
        """Test performance log handling with minimal data."""
        with patch.object(app_logger.logger, 'info') as mock_log:
            log_data = {
                'message': 'Performance metric',
                'response_time': 1.0
            }
            
            app_logger._handle_performance_log(log_data)
            
            call_args = mock_log.call_args
            extra = call_args[1]['extra']
            
            assert extra['log_type'] == 'PERFORMANCE'
            assert extra['response_time'] == 1.0
            assert 'tokens_prompt' not in extra  # Should not include None values


class TestAzureOpenAILogHandling:
    """Test AZURE_OPENAI log type handling."""
    
    @pytest.fixture
    def app_logger(self):
        return ApplicationLogger("test.application")
    
    def test_handle_azure_openai_log_api_call(self, app_logger):
        """Test Azure OpenAI log handling for API calls."""
        with patch.object(app_logger.logger, 'info') as mock_log:
            log_data = {
                'message': 'Azure OpenAI API call successful',
                'level': 'INFO',
                'resource_type': 'openai',
                'resource_name': 'gpt-4-deployment',
                'operation_type': 'chat_completion'
            }
            
            app_logger._handle_azure_openai_log(log_data)
            
            call_args = mock_log.call_args
            extra = call_args[1]['extra']
            
            assert extra['log_type'] == 'AZURE_OPENAI'
            assert extra['resource_type'] == 'openai'
            assert extra['resource_name'] == 'gpt-4-deployment'
            assert extra['event_category'] == 'azure_service'
    
    def test_handle_azure_openai_log_with_defaults(self, app_logger):
        """Test Azure OpenAI log handling with default values."""
        with patch.object(app_logger.logger, 'info') as mock_log:
            log_data = {'message': 'Azure OpenAI event'}
            
            app_logger._handle_azure_openai_log(log_data)
            
            call_args = mock_log.call_args
            extra = call_args[1]['extra']
            
            assert extra['operation_type'] == 'azure_openai'
            assert extra['component'] == 'azure_client'
            assert extra['operation_name'] == 'azure.openai.operation'


class TestBackwardCompatibilityMethods:
    """Test backward compatibility methods in ApplicationLogger."""
    
    @pytest.fixture
    def app_logger(self):
        return ApplicationLogger("test.application")
    
    def test_log_azure_operation_openai_routing(self, app_logger):
        """Test that OpenAI operations route to AZURE_OPENAI log type."""
        with patch.object(app_logger, 'route_application_log') as mock_route:
            app_logger.log_azure_operation(
                message="OpenAI API call",
                resource_type="openai",
                resource_name="gpt-4",
                operation_type="chat_completion",
                success=True
            )
            
            mock_route.assert_called_once()
            assert mock_route.call_args[0][0] == 'AZURE_OPENAI'
    
    def test_log_azure_operation_key_vault_routing(self, app_logger):
        """Test that Key Vault operations route to SECURITY log type."""
        with patch.object(app_logger, 'route_application_log') as mock_route:
            app_logger.log_azure_operation(
                message="Key Vault operation",
                resource_type="key_vault",
                resource_name="my-keyvault",
                operation_type="get_secret",
                success=True
            )
            
            mock_route.assert_called_once()
            assert mock_route.call_args[0][0] == 'SECURITY'
    
    def test_log_azure_operation_other_resources_routing(self, app_logger):
        """Test that other resources route to SYSTEM log type."""
        with patch.object(app_logger, 'route_application_log') as mock_route:
            app_logger.log_azure_operation(
                message="Storage operation",
                resource_type="storage",
                resource_name="mystorageaccount",
                operation_type="upload",
                success=True
            )
            
            mock_route.assert_called_once()
            assert mock_route.call_args[0][0] == 'SYSTEM'
    
    def test_log_performance_metrics(self, app_logger):
        """Test performance metrics logging method."""
        with patch.object(app_logger, 'route_application_log') as mock_route:
            app_logger.log_performance_metrics(
                message="Performance metric",
                response_time=1.5,
                tokens_prompt=100,
                tokens_completion=150
            )
            
            mock_route.assert_called_once()
            assert mock_route.call_args[0][0] == 'PERFORMANCE'
            
            log_data = mock_route.call_args[0][1]
            assert log_data['response_time'] == 1.5
            assert log_data['tokens_prompt'] == 100
    
    def test_log_authentication_event(self, app_logger):
        """Test authentication event logging method."""
        with patch.object(app_logger, 'route_application_log') as mock_route:
            app_logger.log_authentication_event(
                message="Authentication successful",
                credential_type="azure_cli",
                success=True,
                duration=0.5
            )
            
            mock_route.assert_called_once()
            assert mock_route.call_args[0][0] == 'SECURITY'
            
            log_data = mock_route.call_args[0][1]
            assert log_data['credential_type'] == 'azure_cli'
            assert log_data['success'] is True
    
    def test_log_key_vault_operation(self, app_logger):
        """Test Key Vault operation logging method."""
        with patch.object(app_logger, 'route_application_log') as mock_route:
            app_logger.log_key_vault_operation(
                message="Secret retrieved",
                secret_name="openai-key",
                operation="get_secret",
                success=True
            )
            
            mock_route.assert_called_once()
            assert mock_route.call_args[0][0] == 'SECURITY'
            
            log_data = mock_route.call_args[0][1]
            assert log_data['secret_name'] == 'openai-key'
            assert log_data['operation_type'] == 'get_secret'


class TestConvenienceFunctions:
    """Test convenience functions for application logging."""
    
    @patch('src.observability.application_logging.get_application_logger')
    def test_log_system_event(self, mock_get_logger):
        """Test log_system_event convenience function."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        log_system_event(
            message="System event occurred",
            component="test_component",
            success=True
        )
        
        mock_get_logger.assert_called_once()
        mock_logger.route_application_log.assert_called_once()
        
        call_args = mock_logger.route_application_log.call_args
        assert call_args[0][0] == 'SYSTEM'
        
        log_data = call_args[0][1]
        assert log_data['message'] == 'System event occurred'
        assert log_data['component'] == 'test_component'
        assert log_data['success'] is True
    
    @patch('src.observability.application_logging.get_application_logger')
    def test_log_security_event(self, mock_get_logger):
        """Test log_security_event convenience function."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        log_security_event(
            message="Security event occurred",
            credential_type="api_key",
            success=False,
            error_type="AuthenticationError"
        )
        
        mock_logger.route_application_log.assert_called_once()
        
        call_args = mock_logger.route_application_log.call_args
        assert call_args[0][0] == 'SECURITY'
        
        log_data = call_args[0][1]
        assert log_data['credential_type'] == 'api_key'
        assert log_data['success'] is False
    
    @patch('src.observability.application_logging.get_application_logger')
    def test_log_performance_event(self, mock_get_logger):
        """Test log_performance_event convenience function."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        log_performance_event(
            message="Performance event",
            response_time=2.5,
            tokens_used=300
        )
        
        mock_logger.route_application_log.assert_called_once()
        
        call_args = mock_logger.route_application_log.call_args
        assert call_args[0][0] == 'PERFORMANCE'
        
        log_data = call_args[0][1]
        assert log_data['response_time'] == 2.5
        assert log_data['tokens_used'] == 300
    
    @patch('src.observability.application_logging.get_application_logger')
    def test_log_azure_openai_event(self, mock_get_logger):
        """Test log_azure_openai_event convenience function."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        log_azure_openai_event(
            message="Azure OpenAI event",
            resource_name="gpt-4-deployment",
            operation_type="chat_completion",
            success=True,
            tokens=250
        )
        
        mock_logger.route_application_log.assert_called_once()
        
        call_args = mock_logger.route_application_log.call_args
        assert call_args[0][0] == 'AZURE_OPENAI'
        
        log_data = call_args[0][1]
        assert log_data['resource_name'] == 'gpt-4-deployment'
        assert log_data['tokens'] == 250


class TestLogOperationDecorator:
    """Test log_operation decorator functionality."""
    
    @patch('src.observability.application_logging.get_application_logger')
    def test_log_operation_success(self, mock_get_logger):
        """Test log_operation decorator for successful operations."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        @log_operation("test_operation", component="test_component")
        def test_function():
            return "success"
        
        result = test_function()
        
        assert result == "success"
        mock_logger.log_azure_operation.assert_called_once()
        
        call_args = mock_logger.log_azure_operation.call_args[1]
        assert call_args['operation_type'] == 'test_operation'
        assert call_args['success'] is True
        assert 'duration' in call_args
    
    @patch('src.observability.application_logging.get_application_logger')
    def test_log_operation_failure(self, mock_get_logger):
        """Test log_operation decorator for failed operations."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        @log_operation("test_operation", component="test_component")
        def test_function():
            raise ValueError("Test error")
        
        with pytest.raises(ValueError):
            test_function()
        
        mock_logger.log_azure_operation.assert_called_once()
        
        call_args = mock_logger.log_azure_operation.call_args[1]
        assert call_args['success'] is False
        assert call_args['error_type'] == 'ValueError'
        assert call_args['level'] == 'ERROR'


if __name__ == '__main__':
    pytest.main([__file__])