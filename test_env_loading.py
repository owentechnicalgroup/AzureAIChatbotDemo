#!/usr/bin/env python3
"""
Test environment variable loading from .env file
"""

import os
import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

def test_direct_dotenv():
    """Test direct python-dotenv loading"""
    print("Testing direct python-dotenv loading...")
    
    try:
        from dotenv import load_dotenv
        
        # Load .env file explicitly
        env_path = Path(__file__).parent / ".env"
        if env_path.exists():
            print(f"Found .env file at: {env_path}")
            result = load_dotenv(env_path)
            print(f"load_dotenv result: {result}")
            
            # Test specific variables
            test_vars = [
                'APPLICATIONINSIGHTS_CONNECTION_STRING',
                'AZURE_OPENAI_ENDPOINT',
                'AZURE_OPENAI_DEPLOYMENT',
                'ENABLE_CHAT_OBSERVABILITY'
            ]
            
            for var in test_vars:
                value = os.getenv(var)
                print(f"   {var}: {'[OK]' if value else '[MISSING]'}")
                if value and len(value) > 50:
                    print(f"      Preview: {value[:50]}...")
                elif value:
                    print(f"      Value: {value}")
            
        else:
            print("No .env file found")
            
    except ImportError:
        print("python-dotenv not installed")
        print("Install with: pip install python-dotenv")
        return False
    
    return True

def test_pydantic_settings():
    """Test pydantic settings loading"""
    print("\nTesting pydantic settings loading...")
    
    try:
        from config.settings import get_settings
        
        settings = get_settings()
        print("Settings loaded successfully")
        
        print(f"   azure_openai_endpoint: {'[OK]' if settings.azure_openai_endpoint else '[MISSING]'}")
        print(f"   applicationinsights_connection_string: {'[OK]' if settings.applicationinsights_connection_string else '[MISSING]'}")
        print(f"   azure_openai_deployment: {'[OK]' if settings.azure_openai_deployment else '[MISSING]'}")
        
        # Test validation
        validation = settings.validate_configuration()
        print(f"   Configuration complete: {'[OK]' if validation['configuration_complete'] else '[FAILED]'}")
        
        return True
        
    except Exception as e:
        print(f"Error loading settings: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("Environment Variable Loading Test")
    print("=" * 50)
    
    # First test direct loading
    success1 = test_direct_dotenv()
    
    # Then test pydantic settings
    success2 = test_pydantic_settings()
    
    if success1 and success2:
        print("\n[SUCCESS] Environment loading working correctly")
        return 0
    else:
        print("\n[FAILED] Environment loading has issues")
        return 1

if __name__ == "__main__":
    sys.exit(main())