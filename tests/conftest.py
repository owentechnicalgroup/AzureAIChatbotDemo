"""
Pytest configuration for dual observability tests.

Provides common fixtures and test configuration for all test modules.
"""

import pytest
import logging
import os
import sys
from unittest.mock import Mock, patch
from pathlib import Path

# Add src directory to Python path for imports
test_dir = Path(__file__).parent
src_dir = test_dir.parent / "src"
sys.path.insert(0, str(src_dir))


@pytest.fixture(autouse=True)
def reset_logging_state():
    """Reset logging state before each test."""
    # Clear any existing handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Reset to default level
    root_logger.setLevel(logging.WARNING)
    
    yield
    
    # Cleanup after test
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)


@pytest.fixture(autouse=True)
def reset_telemetry_state():
    """Reset telemetry state before each test."""
    try:
        from src.observability.telemetry_service import shutdown_telemetry
        shutdown_telemetry()
    except ImportError:
        # If telemetry service not available, that's okay
        pass
    
    yield
    
    # Cleanup after test
    try:
        from src.observability.telemetry_service import shutdown_telemetry
        shutdown_telemetry()
    except ImportError:
        pass


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    settings = Mock()
    settings.applicationinsights_connection_string = "InstrumentationKey=test-key"
    settings.enable_chat_observability = True
    settings.chat_observability_connection_string = None
    settings.enable_cross_correlation = True
    settings.log_level = "INFO"
    settings.log_format = "json"
    settings.log_file_path = "logs/test.log"
    settings.enable_console_logging = True
    settings.enable_file_logging = False
    settings.enable_json_logging = True
    settings.environment = "test"
    settings.temperature = 0.7
    settings.max_tokens = 1000
    settings.max_conversation_turns = 20
    settings.conversation_memory_type = "buffer_window"
    settings.azure_openai_endpoint = "https://test.openai.azure.com/"
    settings.azure_openai_api_version = "2024-05-01-preview"
    settings.key_vault_url = None
    return settings


@pytest.fixture
def mock_azure_monitor():
    """Mock Azure Monitor configuration."""
    with patch('src.observability.telemetry_service.configure_azure_monitor') as mock_configure:
        mock_configure.return_value = None
        yield mock_configure


@pytest.fixture
def sample_log_data():
    """Sample log data for testing."""
    return {
        'message': 'Test log message',
        'operation_id': 'test-op-123',
        'timestamp': '2024-01-01T00:00:00Z',
        'component': 'test_component',
        'success': True
    }


@pytest.fixture
def sample_conversation_log():
    """Sample conversation log data for testing."""
    return {
        'message': 'User interaction',
        'log_type': 'CONVERSATION',
        'conversation_id': 'conv-123',
        'user_id': 'user-456',
        'session_id': 'session-789',
        'turn_number': 1,
        'message_length': 20,
        'level': 'INFO'
    }


@pytest.fixture
def sample_application_log():
    """Sample application log data for testing."""
    return {
        'message': 'System operation',
        'log_type': 'SYSTEM',
        'operation_type': 'startup',
        'component': 'application',
        'success': True,
        'level': 'INFO'
    }


@pytest.fixture
def sample_performance_log():
    """Sample performance log data for testing."""
    return {
        'message': 'Performance metric',
        'log_type': 'PERFORMANCE',
        'response_time': 1.5,
        'tokens_prompt': 100,
        'tokens_completion': 150,
        'tokens_total': 250,
        'operation_name': 'api.chat_completion',
        'level': 'INFO'
    }


@pytest.fixture
def sample_security_log():
    """Sample security log data for testing."""
    return {
        'message': 'Authentication event',
        'log_type': 'SECURITY',
        'credential_type': 'azure_cli',
        'operation_type': 'authentication',
        'success': True,
        'duration': 0.5,
        'level': 'INFO'
    }


@pytest.fixture
def sample_azure_openai_log():
    """Sample Azure OpenAI log data for testing."""
    return {
        'message': 'Azure OpenAI API call',
        'log_type': 'AZURE_OPENAI',
        'resource_type': 'openai',
        'resource_name': 'gpt-4-deployment',
        'operation_type': 'chat_completion',
        'success': True,
        'duration': 2.0,
        'level': 'INFO'
    }


@pytest.fixture
def mock_structlog_logger():
    """Mock structlog logger for testing."""
    logger = Mock()
    
    # Mock common logging methods
    logger.info = Mock()
    logger.error = Mock()
    logger.warning = Mock()
    logger.debug = Mock()
    logger.critical = Mock()
    
    # Mock bind method to return self for chaining
    logger.bind = Mock(return_value=logger)
    
    return logger


@pytest.fixture
def mock_python_logger():
    """Mock Python standard logger for testing."""
    logger = Mock()
    
    # Mock logging methods
    logger.info = Mock()
    logger.error = Mock()
    logger.warning = Mock()
    logger.debug = Mock()
    logger.critical = Mock()
    
    # Mock logger properties
    logger.name = "test.logger"
    logger.level = logging.INFO
    
    return logger


class TestDataGenerator:
    """Helper class to generate test data."""
    
    @staticmethod
    def conversation_context(
        conversation_id: str = "test-conv-123",
        user_id: str = "test-user-456", 
        session_id: str = "test-session-789"
    ):
        """Generate conversation context data."""
        return {
            'conversation_id': conversation_id,
            'user_id': user_id,
            'session_id': session_id
        }
    
    @staticmethod
    def token_usage(
        prompt_tokens: int = 100,
        completion_tokens: int = 150,
        total_tokens: int = 250
    ):
        """Generate token usage data."""
        return {
            'prompt_tokens': prompt_tokens,
            'completion_tokens': completion_tokens,
            'total_tokens': total_tokens
        }
    
    @staticmethod
    def performance_metrics(
        response_time: float = 1.5,
        tokens_used: int = 250,
        request_size: int = 1024,
        response_size: int = 2048
    ):
        """Generate performance metrics data."""
        return {
            'response_time': response_time,
            'tokens_used': tokens_used,
            'request_size': request_size,
            'response_size': response_size
        }


@pytest.fixture
def test_data_generator():
    """Test data generator fixture."""
    return TestDataGenerator()


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "unit: mark test as unit test"
    )
    config.addinivalue_line(
        "markers", "compatibility: mark test as backward compatibility test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )


def pytest_collection_modifyitems(config, items):
    """Add markers to tests based on their location."""
    for item in items:
        # Add markers based on test file names
        if "integration" in item.fspath.basename:
            item.add_marker(pytest.mark.integration)
        elif "compatibility" in item.fspath.basename:
            item.add_marker(pytest.mark.compatibility)
        else:
            item.add_marker(pytest.mark.unit)
        
        # Add slow marker for integration tests
        if "integration" in item.fspath.basename:
            item.add_marker(pytest.mark.slow)


# Custom assertions for dual observability tests
class DualObservabilityAssertions:
    """Custom assertions for dual observability testing."""
    
    @staticmethod
    def assert_log_routed_to_application(mock_app_logger, log_type: str, expected_calls: int = 1):
        """Assert that logs were routed to application logging system."""
        assert mock_app_logger.route_application_log.call_count == expected_calls
        
        if expected_calls > 0:
            call_args = mock_app_logger.route_application_log.call_args
            assert call_args[0][0] == log_type
    
    @staticmethod
    def assert_log_routed_to_chat(mock_chat_observer, expected_calls: int = 1):
        """Assert that logs were routed to chat observability system."""
        assert mock_chat_observer.route_conversation_log.call_count == expected_calls
        
        if expected_calls > 0:
            call_args = mock_chat_observer.route_conversation_log.call_args
            log_data = call_args[0][0]
            assert log_data.get('log_type') == 'CONVERSATION'
    
    @staticmethod
    def assert_operation_id_present(log_data: dict):
        """Assert that operation_id is present and valid UUID."""
        assert 'operation_id' in log_data
        assert isinstance(log_data['operation_id'], str)
        
        # Should be valid UUID format
        import uuid
        uuid.UUID(log_data['operation_id'])
    
    @staticmethod
    def assert_log_type_present(log_data: dict, expected_log_type: str):
        """Assert that log_type is present and correct."""
        assert 'log_type' in log_data
        assert log_data['log_type'] == expected_log_type


@pytest.fixture
def dual_obs_assertions():
    """Dual observability assertions fixture."""
    return DualObservabilityAssertions()