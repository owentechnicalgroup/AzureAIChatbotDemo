#!/usr/bin/env python3
"""
Simple test script to check if all required packages are installed and working.
"""

def test_imports():
    """Test all required imports."""
    print("Testing package imports...")
    
    try:
        import pydantic
        from pydantic_settings import BaseSettings
        print("✅ Pydantic: OK")
    except ImportError as e:
        print(f"❌ Pydantic: {e}")
        return False
    
    try:
        import azure.identity
        import azure.keyvault.secrets
        import azure.core.exceptions
        print("✅ Azure SDK: OK")
    except ImportError as e:
        print(f"❌ Azure SDK: {e}")
        return False
    
    try:
        import langchain
        import langchain_openai
        import langchain_core
        print("✅ LangChain: OK")
    except ImportError as e:
        print(f"❌ LangChain: {e}")
        return False
    
    try:
        import openai
        print("✅ OpenAI: OK")
    except ImportError as e:
        print(f"❌ OpenAI: {e}")
        return False
    
    try:
        import structlog
        print("✅ StructLog: OK")
    except ImportError as e:
        print(f"❌ StructLog: {e}")
        return False
    
    try:
        import tenacity
        print("✅ Tenacity: OK")
    except ImportError as e:
        print(f"❌ Tenacity: {e}")
        return False
    
    try:
        import click
        import rich
        import typer
        print("✅ CLI Tools: OK")
    except ImportError as e:
        print(f"❌ CLI Tools: {e}")
        return False
    
    print("\n🎉 All packages imported successfully!")
    return True

def test_env_file():
    """Test if .env file exists and contains required variables."""
    import os
    
    env_file = ".env"
    if not os.path.exists(env_file):
        print(f"❌ Environment file '{env_file}' not found")
        return False
    
    print(f"✅ Environment file '{env_file}' found")
    
    # Check for required environment variables
    required_vars = [
        "AZURE_OPENAI_ENDPOINT",
        "KEY_VAULT_URL",
        "AZURE_CLIENT_ID"
    ]
    
    from dotenv import load_dotenv
    load_dotenv()
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        return False
    
    print("✅ All required environment variables found")
    return True

if __name__ == "__main__":
    print("🚀 Azure OpenAI Chatbot - Dependency Test")
    print("=" * 50)
    
    imports_ok = test_imports()
    env_ok = test_env_file()
    
    if imports_ok and env_ok:
        print("\n✅ All tests passed! The chatbot should work.")
    else:
        print("\n❌ Some tests failed. Please check the errors above.")
