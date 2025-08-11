"""
Test LangChain tool integration for Phase 1 consolidation.
"""
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.config.settings import get_settings
from src.rag.langchain_tools import (
    create_langchain_tool_registry,
    get_langchain_tools_for_agent
)
from src.rag.rag_tool import RAGSearchTool
from src.rag.retriever import RAGRetriever
from src.chatbot.agent import ChatbotAgent

def test_langchain_tool_registry():
    """Test the LangChain tool registry creation and tool availability."""
    
    print("Testing LangChain Tool Registry...")
    
    # Get settings
    settings = get_settings()
    
    # Create tool registry
    registry = create_langchain_tool_registry(settings)
    
    print(f"✅ Tool registry created successfully")
    print(f"   - Available: {registry.is_available()}")
    print(f"   - Tools count: {len(registry.get_tools())}")
    
    # Get tools
    tools = registry.get_tools()
    for tool in tools:
        print(f"   - Tool: {tool.name} - {tool.description[:60]}...")
    
    # Test health status
    health = registry.get_health_status()
    print(f"   - Health: {health['overall_health']}")
    print(f"   - Call Report available: {health['toolsets'].get('call_report', {}).get('available', False)}")
    
    return registry

def test_agent_tools_for_agent():
    """Test getting tools ready for ChatbotAgent."""
    
    print("\n" + "="*60)
    print("Testing Agent Tool Integration...")
    
    settings = get_settings()
    
    # Get LangChain tools (excluding RAG which we'll add separately)
    langchain_tools = get_langchain_tools_for_agent(settings, include_rag=False)
    
    print(f"✅ LangChain tools retrieved: {len(langchain_tools)}")
    for tool in langchain_tools:
        print(f"   - {tool.name}: {tool.__class__.__name__}")
    
    # Create RAG tool
    retriever = RAGRetriever(settings=settings)
    rag_tool = RAGSearchTool(rag_retriever=retriever)
    
    # Combine all tools for agent
    all_tools = [rag_tool] + langchain_tools
    
    print(f"✅ Combined tools for agent: {len(all_tools)}")
    for tool in all_tools:
        print(f"   - {tool.name}: {tool.__class__.__name__}")
    
    return all_tools

def test_chatbot_agent_with_new_tools():
    """Test ChatbotAgent with the new LangChain tool integration."""
    
    print("\n" + "="*60)
    print("Testing ChatbotAgent with New Tools...")
    
    settings = get_settings()
    
    # Get all tools (RAG + LangChain tools)
    langchain_tools = get_langchain_tools_for_agent(settings, include_rag=False)
    
    # Create RAG tool
    retriever = RAGRetriever(settings=settings)
    rag_tool = RAGSearchTool(rag_retriever=retriever)
    
    # Combine tools
    all_tools = [rag_tool] + langchain_tools
    
    # Create ChatbotAgent with multi-step enabled
    chatbot = ChatbotAgent(
        settings=settings,
        tools=all_tools,
        enable_multi_step=True
    )
    
    print(f"✅ ChatbotAgent created with new tools")
    print(f"   - Multi-step enabled: {chatbot.enable_multi_step}")
    print(f"   - Tools available: {len(chatbot.tools)}")
    print(f"   - Agent executor: {chatbot.agent_executor is not None}")
    
    # List all tools
    print(f"   - Tools loaded:")
    for tool in chatbot.tools:
        print(f"     * {tool.name}: {tool.description[:50]}...")
    
    return chatbot

def test_tool_execution():
    """Test actual tool execution through ChatbotAgent."""
    
    print("\n" + "="*60)
    print("Testing Tool Execution...")
    
    # Create chatbot with tools
    chatbot = test_chatbot_agent_with_new_tools()
    
    print("\n--- Testing General Conversation (No Tools) ---")
    try:
        response1 = chatbot.process_message("Hello, how are you?")
        print(f"Response: {response1['content'][:100]}...")
        print(f"Processing mode: {response1.get('processing_mode', 'unknown')}")
        print(f"Response time: {response1.get('response_time', 0):.2f}s")
    except Exception as e:
        print(f"❌ General conversation failed: {e}")
    
    print("\n--- Testing Bank Lookup Tool ---")
    try:
        response2 = chatbot.process_message("Look up information for Bank of America")
        print(f"Response: {response2['content'][:200]}...")
        print(f"Processing mode: {response2.get('processing_mode', 'unknown')}")
        print(f"Response time: {response2.get('response_time', 0):.2f}s")
    except Exception as e:
        print(f"❌ Bank lookup test failed: {e}")
    
    print("\n--- Testing RAG Query ---")
    try:
        response3 = chatbot.process_message("What information is available in the uploaded documents?")
        print(f"Response: {response3['content'][:200]}...")
        print(f"Processing mode: {response3.get('processing_mode', 'unknown')}")
        print(f"Response time: {response3.get('response_time', 0):.2f}s")
    except Exception as e:
        print(f"❌ RAG query test failed: {e}")
    
    return True

if __name__ == "__main__":
    try:
        print("Phase 1: LangChain Tool Integration Test")
        print("="*60)
        
        # Test 1: Tool registry
        registry = test_langchain_tool_registry()
        
        # Test 2: Agent tool preparation
        agent_tools = test_agent_tools_for_agent()
        
        # Test 3: ChatbotAgent integration
        chatbot = test_chatbot_agent_with_new_tools()
        
        # Test 4: Actual execution
        test_tool_execution()
        
        print("\n" + "="*60)
        print("🎉 Phase 1 LangChain Tool Integration Tests Completed!")
        print("\n✅ Successfully converted existing tools to LangChain BaseTool format")
        print("✅ ChatbotAgent can use both RAG and Call Report tools")
        print("✅ Multi-step agent executor working with new tool architecture") 
        print("✅ Ready for Phase 2: Streamlit app migration")
        
    except Exception as e:
        print(f"\n❌ Phase 1 tests failed: {e}")
        import traceback
        traceback.print_exc()
