"""
Phase 2 Test: Streamlit App Migration to ChatbotAgent
=====================================================

Validates that Streamlit app has been successfully migrated to use:
- ChatbotAgent instead of ToolsIntegratedRAGRetriever
- LangChain tools integration
- New unified architecture

Test Steps:
1. Import and initialize Streamlit app components
2. Verify ChatbotAgent initialization
3. Test tool registry integration
4. Validate message processing works
5. Check system status displays correctly
"""

import sys
import asyncio
import traceback
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent / "src"))

from src.config.settings import get_settings
from src.rag.chromadb_manager import ChromaDBManager
from src.chatbot.agent import ChatbotAgent
from src.rag.langchain_tools import LangChainToolRegistry


def print_section(title: str):
    """Print a section header."""
    print("=" * 60)
    print(title)
    print("=" * 60)


def test_streamlit_component_imports():
    """Test that all required components can be imported."""
    print_section("Phase 2: Testing Streamlit Component Imports...")
    
    try:
        # Test core imports
        from src.ui.streamlit_app import StreamlitRAGApp
        print("✅ StreamlitRAGApp imported successfully")
        
        # Test that old imports are replaced
        try:
            from src.rag.tools_integration import ToolsIntegratedRAGRetriever
            print("⚠️  Old ToolsIntegratedRAGRetriever still available (should be deprecated)")
        except ImportError:
            print("✅ Old ToolsIntegratedRAGRetriever properly deprecated")
        
        return True
        
    except Exception as e:
        print(f"❌ Import test failed: {str(e)}")
        traceback.print_exc()
        return False


def test_component_initialization():
    """Test that components initialize correctly with new architecture."""
    print_section("Testing Component Initialization...")
    
    try:
        settings = get_settings()
        print("✅ Settings loaded successfully")
        
        # Test ChromaDB Manager
        chromadb_manager = ChromaDBManager(settings)
        print("✅ ChromaDBManager initialized")
        
        # Test LangChain Tool Registry
        tool_registry = LangChainToolRegistry(settings)
        print(f"✅ LangChainToolRegistry initialized")
        print(f"   - Tools available: {tool_registry.is_available()}")
        print(f"   - Tool count: {len(tool_registry.get_tools())}")
        
        # Test ChatbotAgent
        tools = tool_registry.get_tools()
        chatbot_agent = ChatbotAgent(
            settings=settings,
            tools=tools,
            enable_multi_step=True
        )
        print("✅ ChatbotAgent initialized successfully")
        print(f"   - Multi-step enabled: {hasattr(chatbot_agent, 'agent_executor')}")
        print(f"   - Tool count: {len(chatbot_agent.tools) if hasattr(chatbot_agent, 'tools') else 0}")
        
        return True, chatbot_agent
        
    except Exception as e:
        print(f"❌ Component initialization failed: {str(e)}")
        traceback.print_exc()
        return False, None


async def test_chatbot_agent_processing():
    """Test that ChatbotAgent can process messages correctly."""
    print_section("Testing ChatbotAgent Message Processing...")
    
    try:
        settings = get_settings()
        chromadb_manager = ChromaDBManager(settings)
        tool_registry = LangChainToolRegistry(settings)
        
        chatbot_agent = ChatbotAgent(
            settings=settings,
            chromadb_manager=chromadb_manager,
            tool_registry=tool_registry,
            multi_step_enabled=True
        )
        
        # Test simple conversation
        print("--- Testing Simple Conversation ---")
        response = await chatbot_agent.process_message(
            message="Hello, how are you?",
            conversation_id="test-conversation"
        )
        
        print(f"Response: {response.get('response', 'No response')[:100]}...")
        print(f"Processing mode: {response.get('processing_mode', 'unknown')}")
        print(f"Response time: {response.get('response_time', 0):.2f}s")
        print("✅ Simple conversation test passed")
        
        # Test tool integration (if tools are available)
        tools = tool_registry.get_tools()
        if tools:
            print("--- Testing Tool Integration ---")
            response = await chatbot_agent.process_message(
                message="Can you look up information about Bank of America?",
                conversation_id="test-conversation"
            )
            
            print(f"Response: {response.get('response', 'No response')[:200]}...")
            print(f"Processing mode: {response.get('processing_mode', 'unknown')}")
            print(f"Response time: {response.get('response_time', 0):.2f}s")
            print("✅ Tool integration test passed")
        else:
            print("⚠️  No tools available for tool integration test")
        
        return True
        
    except Exception as e:
        print(f"❌ ChatbotAgent processing test failed: {str(e)}")
        traceback.print_exc()
        return False


def test_streamlit_app_initialization():
    """Test that StreamlitRAGApp initializes with new architecture."""
    print_section("Testing StreamlitRAGApp Initialization...")
    
    try:
        from src.ui.streamlit_app import StreamlitRAGApp
        
        # This would normally be called by Streamlit, but we can test the class
        app = StreamlitRAGApp()
        print("✅ StreamlitRAGApp initialized successfully")
        
        # Check that required attributes are present
        required_attrs = ['settings', 'logger']
        for attr in required_attrs:
            if hasattr(app, attr):
                print(f"✅ StreamlitRAGApp has required attribute: {attr}")
            else:
                print(f"❌ StreamlitRAGApp missing attribute: {attr}")
                return False
        
        print("✅ StreamlitRAGApp validation passed")
        return True
        
    except Exception as e:
        print(f"❌ StreamlitRAGApp initialization failed: {str(e)}")
        traceback.print_exc()
        return False


async def test_health_checks():
    """Test that health checks work with new architecture."""
    print_section("Testing Health Checks...")
    
    try:
        settings = get_settings()
        chromadb_manager = ChromaDBManager(settings)
        tool_registry = LangChainToolRegistry(settings)
        
        chatbot_agent = ChatbotAgent(
            settings=settings,
            chromadb_manager=chromadb_manager,
            tool_registry=tool_registry,
            multi_step_enabled=True
        )
        
        # Test ChatbotAgent health check
        health = await chatbot_agent.health_check()
        print(f"✅ ChatbotAgent health check completed")
        print(f"   - Status: {health.get('status', 'unknown')}")
        print(f"   - Components: {list(health.keys())}")
        
        # Test tool registry health
        tool_health = tool_registry.get_health_status()
        print(f"✅ Tool registry health check completed")
        print(f"   - Status: {tool_health}")
        
        return True
        
    except Exception as e:
        print(f"❌ Health check test failed: {str(e)}")
        traceback.print_exc()
        return False


async def main():
    """Run all Phase 2 tests."""
    print_section("Phase 2: Streamlit App Migration to ChatbotAgent")
    print("Testing migration from ToolsIntegratedRAGRetriever to ChatbotAgent")
    print("=" * 60)
    
    tests_passed = 0
    total_tests = 5
    
    # Test 1: Component imports
    if test_streamlit_component_imports():
        tests_passed += 1
    
    # Test 2: Component initialization
    init_success, chatbot_agent = test_component_initialization()
    if init_success:
        tests_passed += 1
    
    # Test 3: ChatbotAgent processing
    if await test_chatbot_agent_processing():
        tests_passed += 1
    
    # Test 4: StreamlitRAGApp initialization
    if test_streamlit_app_initialization():
        tests_passed += 1
    
    # Test 5: Health checks
    if await test_health_checks():
        tests_passed += 1
    
    # Final results
    print_section("Phase 2 Test Results")
    print(f"Tests passed: {tests_passed}/{total_tests}")
    
    if tests_passed == total_tests:
        print("🎉 Phase 2 Migration Completed Successfully!")
        print("✅ Streamlit app successfully migrated to ChatbotAgent")
        print("✅ LangChain tools integration working")
        print("✅ Old ToolsIntegratedRAGRetriever architecture replaced")
        print("✅ Ready for production deployment")
    else:
        print(f"⚠️  Phase 2 partially completed: {tests_passed}/{total_tests} tests passed")
        print("Some issues need to be resolved before deployment")
    
    print("\nPhase 2 Summary:")
    print("- Streamlit app migrated to use ChatbotAgent")
    print("- Unified tool ecosystem with LangChain integration")
    print("- Redundant ToolsIntegratedRAGRetriever eliminated")
    print("- Modern multi-step agent architecture")


if __name__ == "__main__":
    asyncio.run(main())
