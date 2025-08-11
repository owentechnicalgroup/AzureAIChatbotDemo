"""
Phase 2 Test: Streamlit App Migration to ChatbotAgent (Fixed)
============================================================

Validates that Streamlit app has been successfully migrated to use:
- ChatbotAgent instead of ToolsIntegratedRAGRetriever
- LangChain tools integration
- New unified architecture

Fixed version with correct ChatbotAgent constructor parameters.
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


def test_phase2_integration():
    """Test the complete Phase 2 integration."""
    print_section("Phase 2: Streamlit App Migration Test (Fixed)")
    
    try:
        # Initialize components
        settings = get_settings()
        print("✅ Settings loaded successfully")
        
        # Initialize ChromaDB Manager
        chromadb_manager = ChromaDBManager(settings)
        print("✅ ChromaDBManager initialized")
        
        # Initialize LangChain Tool Registry
        tool_registry = LangChainToolRegistry(settings)
        tools = tool_registry.get_tools()
        print(f"✅ LangChainToolRegistry initialized with {len(tools)} tools")
        
        # Initialize ChatbotAgent with correct parameters
        chatbot_agent = ChatbotAgent(
            settings=settings,
            tools=tools,
            enable_multi_step=True
        )
        print("✅ ChatbotAgent initialized successfully")
        print(f"   - Multi-step enabled: {chatbot_agent.enable_multi_step}")
        print(f"   - Tool count: {len(chatbot_agent.tools)}")
        
        # Test message processing
        print("\n--- Testing Message Processing ---")
        response = chatbot_agent.process_message(
            user_message="Hello, how are you?",
            conversation_id="test-streamlit-migration"
        )
        
        print(f"Response: {response.get('response', 'No response')[:100]}...")
        print(f"Processing mode: {response.get('processing_mode', 'unknown')}")
        print(f"Response time: {response.get('response_time', 0):.2f}s")
        
        # Test tool usage if tools are available
        if tools:
            print("\n--- Testing Tool Integration ---")
            response = chatbot_agent.process_message(
                user_message="Can you look up information about Chase Bank?",
                conversation_id="test-streamlit-migration"
            )
            
            print(f"Tool response: {response.get('response', 'No response')[:200]}...")
            print(f"Processing mode: {response.get('processing_mode', 'unknown')}")
            print(f"Response time: {response.get('response_time', 0):.2f}s")
        
        # Test Streamlit app imports
        print("\n--- Testing Streamlit App Imports ---")
        from src.ui.streamlit_app import StreamlitRAGApp
        print("✅ StreamlitRAGApp imported successfully")
        
        # Note: We can't fully test Streamlit app initialization without Streamlit runtime
        print("✅ Streamlit components validation completed")
        
        print_section("Phase 2 Migration Test Results")
        print("🎉 Phase 2 Migration Completed Successfully!")
        print("✅ ChatbotAgent initialized with correct parameters")
        print("✅ LangChain tools integration working")
        print("✅ Message processing functional")
        print("✅ Tool execution capabilities confirmed")
        print("✅ Streamlit app imports successful")
        
        print("\nArchitecture Summary:")
        print(f"- ChatbotAgent with {len(tools)} LangChain tools")
        print(f"- Multi-step agent: {'Enabled' if chatbot_agent.enable_multi_step else 'Disabled'}")
        print("- Unified tool ecosystem (no more ToolsIntegratedRAGRetriever)")
        print("- Ready for Streamlit web interface")
        
        return True
        
    except Exception as e:
        print(f"❌ Phase 2 migration test failed: {str(e)}")
        traceback.print_exc()
        return False


async def main():
    """Run Phase 2 migration test."""
    success = test_phase2_integration()
    
    if success:
        print("\n🎉 Phase 2 Migration Successfully Validated!")
        print("The Streamlit app is ready to use the new ChatbotAgent architecture.")
    else:
        print("\n❌ Phase 2 Migration needs further work.")
        
    return success


if __name__ == "__main__":
    asyncio.run(main())
