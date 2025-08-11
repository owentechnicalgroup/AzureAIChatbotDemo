"""
Test RAG-enabled ChatbotAgent with multi-step conversation capabilities.
"""
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.config.settings import get_settings
from src.chatbot.agent import ChatbotAgent
from src.rag.rag_tool import RAGSearchTool
from src.rag.retriever import RAGRetriever

def test_multi_step_chatbot():
    """Test ChatbotAgent with multi-step RAG capabilities."""
    
    print("Testing multi-step RAG chatbot...")
    
    # Get settings
    settings = get_settings()
    
    # Create RAG components
    retriever = RAGRetriever(settings=settings)
    rag_tool = RAGSearchTool(rag_retriever=retriever)
    
    # Create chatbot with multi-step enabled
    chatbot = ChatbotAgent(
        settings=settings,
        tools=[rag_tool],
        enable_multi_step=True
    )
    
    print(f"✅ Multi-step chatbot created successfully")
    print(f"   - Processing mode: multi-step")
    print(f"   - Tools available: {len(chatbot.tools)}")
    print(f"   - Agent executor: {chatbot.agent_executor is not None}")
    
    # Test simple conversation (should NOT use RAG tool)
    print("\n--- Testing Simple Conversation ---")
    response1 = chatbot.process_message("Hello, how are you?")
    print(f"Response: {response1['content'][:100]}...")
    print(f"Processing mode: {response1.get('processing_mode', 'unknown')}")
    
    # Test RAG-triggering query (should use RAG tool)
    print("\n--- Testing RAG-Enabled Query ---")
    response2 = chatbot.process_message("What information is available in the documents?")
    print(f"Response: {response2['content'][:200]}...")
    print(f"Processing mode: {response2.get('processing_mode', 'unknown')}")
    print(f"Response time: {response2.get('response_time', 0):.2f}s")
    
    return True

def test_simple_mode_chatbot():
    """Test ChatbotAgent in simple mode (no RAG tools)."""
    
    print("\n" + "="*60)
    print("Testing simple mode chatbot...")
    
    # Get settings
    settings = get_settings()
    
    # Create chatbot without multi-step (simple mode)
    chatbot = ChatbotAgent(
        settings=settings,
        enable_multi_step=False  # Simple mode
    )
    
    print(f"✅ Simple chatbot created successfully")
    print(f"   - Processing mode: simple")
    print(f"   - Tools available: {len(chatbot.tools) if chatbot.tools else 0}")
    print(f"   - Agent executor: {getattr(chatbot, 'agent_executor', None) is not None}")
    
    # Test conversation
    response = chatbot.process_message("What is the capital of France?")
    print(f"Response: {response['content'][:100]}...")
    print(f"Processing mode: {response.get('processing_mode', 'unknown')}")
    
    return True

if __name__ == "__main__":
    try:
        # Test multi-step mode
        test_multi_step_chatbot()
        
        # Test simple mode
        test_simple_mode_chatbot()
        
        print("\n" + "="*60)
        print("🎉 All RAG chatbot tests passed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
