#!/usr/bin/env python3
"""
Simple integration test to demonstrate dual observability system functionality.

This is a practical test to verify the system works end-to-end without complex mocking.
"""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from unittest.mock import Mock
from src.observability.telemetry_service import (
    initialize_dual_observability,
    route_log_by_type,
    get_application_logger,
    get_chat_observer,
    shutdown_telemetry,
    is_telemetry_initialized,
    determine_log_category,
    LogTypeCategory,
    APPLICATION_LOG_TYPES,
    CHAT_OBSERVABILITY_TYPES
)


def test_log_type_routing():
    """Test that log types are correctly categorized."""
    print("Testing log type routing...")
    
    # Test application log types
    for log_type in APPLICATION_LOG_TYPES.keys():
        category = determine_log_category(log_type)
        assert category == LogTypeCategory.APPLICATION, f"{log_type} should route to APPLICATION"
        print(f"[OK] {log_type} -> APPLICATION")
    
    # Test chat log types  
    for log_type in CHAT_OBSERVABILITY_TYPES.keys():
        category = determine_log_category(log_type)
        assert category == LogTypeCategory.CHAT, f"{log_type} should route to CHAT"
        print(f"[OK] {log_type} -> CHAT")
    
    # Test unknown log types default to application
    unknown_types = ['UNKNOWN', 'CUSTOM', 'TEST_TYPE']
    for log_type in unknown_types:
        category = determine_log_category(log_type)
        assert category == LogTypeCategory.APPLICATION, f"{log_type} should default to APPLICATION"
        print(f"[OK] {log_type} -> APPLICATION (default)")
    
    print("Log type routing test: PASSED\n")


def test_system_components():
    """Test that system components can be created and accessed."""
    print("Testing system components...")
    
    # Test that we can get logger instances
    app_logger = get_application_logger()
    assert app_logger is not None
    print("[OK] Application logger created")
    
    chat_observer = get_chat_observer()
    assert chat_observer is not None
    print("[OK] Chat observer created")
    
    # Test singleton behavior
    app_logger2 = get_application_logger()
    assert app_logger is app_logger2, "Application logger should be singleton"
    print("[OK] Application logger singleton behavior")
    
    chat_observer2 = get_chat_observer()
    assert chat_observer is chat_observer2, "Chat observer should be singleton"
    print("[OK] Chat observer singleton behavior")
    
    print("System components test: PASSED\n")


def test_initialization_without_azure_monitor():
    """Test initialization behavior without actual Azure Monitor."""
    print("Testing initialization...")
    
    # Create mock settings
    mock_settings = Mock()
    mock_settings.applicationinsights_connection_string = None
    
    # Test initialization failure with missing connection string
    result = initialize_dual_observability(mock_settings)
    assert result is False, "Should fail without connection string"
    assert is_telemetry_initialized() is False, "Should not be initialized"
    print("[OK] Initialization correctly fails without connection string")
    
    # Test with connection string (will fail Azure Monitor setup but that's expected)
    mock_settings.applicationinsights_connection_string = "InstrumentationKey=test-key"
    result = initialize_dual_observability(mock_settings)
    # This will be True because the Azure Monitor package is installed, even if connection string is fake
    print(f"[OK] Initialization with connection string: {result}")
    
    print("Initialization test: PASSED\n")


def test_log_routing_functionality():
    """Test log routing without actual Azure Monitor."""
    print("Testing log routing functionality...")
    
    # Initialize system first
    mock_settings = Mock()
    mock_settings.applicationinsights_connection_string = "InstrumentationKey=test-key"
    initialize_dual_observability(mock_settings)
    
    # Test that routing doesn't crash
    test_logs = [
        ('SYSTEM', {'message': 'System startup', 'operation_id': 'test-op-1'}),
        ('SECURITY', {'message': 'Authentication event', 'credential_type': 'azure_cli'}),
        ('PERFORMANCE', {'message': 'Performance metric', 'response_time': 1.5}),
        ('AZURE_OPENAI', {'message': 'API call', 'resource_type': 'openai'}),
        ('CONVERSATION', {'message': 'User interaction', 'conversation_id': 'conv-123'}),
    ]
    
    for log_type, log_data in test_logs:
        try:
            route_log_by_type(log_type, log_data)
            print(f"[OK] Successfully routed {log_type} log")
        except Exception as e:
            print(f"[FAIL] Failed to route {log_type} log: {e}")
            raise
    
    print("Log routing functionality test: PASSED\n")


def test_operation_id_auto_generation():
    """Test that operation IDs are automatically generated."""
    print("Testing operation ID auto-generation...")
    
    # Test log without operation_id
    import uuid
    from unittest.mock import patch
    
    original_route_calls = []
    
    def mock_app_route(log_type, log_data):
        original_route_calls.append(('app', log_type, log_data))
    
    def mock_chat_route(log_data):
        original_route_calls.append(('chat', 'CONVERSATION', log_data))
    
    with patch.object(get_application_logger(), 'route_application_log', side_effect=mock_app_route):
        with patch.object(get_chat_observer(), 'route_conversation_log', side_effect=mock_chat_route):
            
            # Test application log without operation_id
            route_log_by_type('SYSTEM', {'message': 'Test without operation_id'})
            
            # Test chat log without operation_id  
            route_log_by_type('CONVERSATION', {'message': 'Test chat', 'conversation_id': 'conv-123'})
    
    # Verify operation_ids were added
    assert len(original_route_calls) == 2
    
    app_log_data = original_route_calls[0][2]
    assert 'operation_id' in app_log_data
    assert isinstance(app_log_data['operation_id'], str)
    # Verify it's a valid UUID
    uuid.UUID(app_log_data['operation_id'])
    print("[OK] Application log auto-generated operation_id")
    
    chat_log_data = original_route_calls[1][2]
    assert 'operation_id' in chat_log_data
    assert isinstance(chat_log_data['operation_id'], str)
    # Verify it's a valid UUID
    uuid.UUID(chat_log_data['operation_id'])
    print("[OK] Chat log auto-generated operation_id")
    
    print("Operation ID auto-generation test: PASSED\n")


def test_cleanup():
    """Test system cleanup."""
    print("Testing cleanup...")
    
    # Ensure system is initialized (it may fail due to fake connection string, but shutdown should work)
    mock_settings = Mock()
    mock_settings.applicationinsights_connection_string = "InstrumentationKey=test-key"
    result = initialize_dual_observability(mock_settings)
    
    # Test shutdown regardless of initialization result (cleanup should always work)
    shutdown_telemetry()
    assert is_telemetry_initialized() is False
    print("[OK] System shutdown correctly")
    
    print("Cleanup test: PASSED\n")


def main():
    """Run all integration tests."""
    print("Running Dual Observability Integration Tests")
    print("=" * 60)
    
    try:
        test_log_type_routing()
        test_system_components()
        test_initialization_without_azure_monitor()
        test_log_routing_functionality()
        test_operation_id_auto_generation()
        test_cleanup()
        
        print("=" * 60)
        print("ALL INTEGRATION TESTS PASSED!")
        print("\nDual Observability System is working correctly!")
        return 0
        
    except Exception as e:
        print("=" * 60)
        print(f"INTEGRATION TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)