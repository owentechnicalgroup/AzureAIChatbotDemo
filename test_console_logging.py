#!/usr/bin/env python3
"""
Test script for console logging configuration.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from config.settings import get_settings
from services.logging_service import setup_logging
from utils.console import create_console
import structlog

def test_console_logging():
    """Test console logging configuration."""
    
    print("Testing console logging configuration...")
    print("=" * 50)
    
    # Test 1: Console logging enabled (default)
    print("\n1. Testing with console logging ENABLED:")
    settings = get_settings()
    settings.enable_console_logging = True
    settings.enable_file_logging = False
    settings.enable_json_logging = False
    
    setup_logging(settings)
    console = create_console(settings=settings)
    
    logger = structlog.get_logger(__name__)
    logger.info("Console logging is enabled")
    console.print_status("Console output is enabled", status="info")
    
    # Test 2: Console logging disabled
    print("\n2. Testing with console logging DISABLED:")
    settings.enable_console_logging = False
    
    setup_logging(settings)
    console = create_console(settings=settings)
    
    logger.info("This log message should appear (structured logging)")
    console.print_status("This console message should NOT appear", status="info")
    
    # Test 3: File logging enabled
    print("\n3. Testing with file logging ENABLED:")
    settings.enable_console_logging = True
    settings.enable_file_logging = True
    settings.log_file_path = "test_logs/test.log"
    
    setup_logging(settings)
    console = create_console(settings=settings)
    
    logger.info("This message should appear in both console and file")
    console.print_status("Console and file logging enabled", status="success")
    
    print("\nTest completed!")
    print("Check 'test_logs/test.log' for file logging output")

if __name__ == "__main__":
    test_console_logging()
