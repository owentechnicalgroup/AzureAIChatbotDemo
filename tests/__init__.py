"""
Dual Observability Test Suite

Comprehensive tests for the Azure OpenTelemetry logging modernization
with separated concerns between Application Logging and AI Chat Observability.

Test Structure:
- test_telemetry_service.py: Core telemetry routing and initialization
- test_application_logging.py: Application logging system tests
- test_chat_observability.py: Chat observability system tests
- test_dual_observability_integration.py: Integration tests
- test_backward_compatibility.py: Backward compatibility tests
- conftest.py: Test configuration and fixtures

Usage:
    # Run all tests
    python run_tests.py
    
    # Run specific test types
    python run_tests.py --type unit
    python run_tests.py --type integration
    python run_tests.py --type compatibility
    
    # Run with coverage
    python run_tests.py --coverage
    
    # Run specific test categories
    python run_tests.py --telemetry-only
    python run_tests.py --application-only
    python run_tests.py --chat-only
"""

__version__ = "1.0.0"
__author__ = "Azure OpenTelemetry Modernization Team"