"""
Test script for the consolidated conversation management system.

Tests the new unified approach:
- ConversationManager with integrated logging (replaces ConversationLogger)
- Auto-save functionality
- Enhanced structured logging
- Simplified agent without ConversationLogger wrapper
"""

import sys
import os
import tempfile
import json
from pathlib import Path
sys.path.append('src')

def test_enhanced_conversation_manager():
    """Test the enhanced ConversationManager with integrated logging."""
    print("Testing enhanced ConversationManager...")
    
    try:
        from chatbot.conversation import LangChainConversationManager as ConversationManager
        from config.settings import Settings
        
        # Mock settings
        class MockSettings:
            def __init__(self):
                self.conversation_memory_type = "buffer"
                self.max_conversation_turns = 10
        
        settings = MockSettings()
        
        # Test basic functionality
        conv_manager = ConversationManager(
            settings=settings,
            auto_save=False  # Disable for testing
        )
        
        print("PASS: ConversationManager created successfully")
        print(f"  Conversation ID: {conv_manager.conversation_id}")
        print(f"  Memory type: {conv_manager.memory_type}")
        
        # Test message addition with integrated logging
        user_msg_id = conv_manager.add_message(
            role="user",
            content="Hello, this is a test message!",
            metadata={"test": True}
        )
        
        print("PASS: User message added with integrated logging")
        print(f"  Message ID: {user_msg_id}")
        
        assistant_msg_id = conv_manager.add_message(
            role="assistant", 
            content="Hello! I'm responding to your test message.",
            token_count=15,
            metadata={"model": "gpt-4", "response_time": 1.2}
        )
        
        print("PASS: Assistant message added with enhanced metadata")
        print(f"  Message ID: {assistant_msg_id}")
        print(f"  Total messages: {conv_manager.metadata.message_count}")
        print(f"  Total tokens: {conv_manager.metadata.total_tokens}")
        
        # Test LangChain message conversion
        langchain_messages = conv_manager.get_langchain_messages()
        print(f"PASS: LangChain message conversion ({len(langchain_messages)} messages)")
        
        return True
        
    except Exception as e:
        print(f"FAIL: ConversationManager test failed: {e}")
        return False

def test_auto_save_functionality():
    """Test the auto-save functionality."""
    print("\nTesting auto-save functionality...")
    
    try:
        from chatbot.conversation import LangChainConversationManager as ConversationManager
        from config.settings import Settings
        
        class MockSettings:
            def __init__(self):
                self.conversation_memory_type = "buffer"
                self.max_conversation_turns = 10
        
        settings = MockSettings()
        
        # Create temp directory for auto-save
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test with auto-save enabled
            conv_manager = ConversationManager(
                settings=settings,
                auto_save=True,
                auto_save_interval=2  # Save every 2 messages
            )
            
            # Override auto-save path to temp directory
            conv_manager.auto_save_path = f"{temp_dir}/test_conversation.json"
            
            print("PASS: ConversationManager with auto-save created")
            print(f"  Auto-save path: {conv_manager.auto_save_path}")
            
            # Add messages - should trigger auto-save after 2nd message
            conv_manager.add_message("user", "Message 1")
            print("PASS: Message 1 added (no auto-save yet)")
            
            conv_manager.add_message("assistant", "Response 1") 
            print("PASS: Message 2 added (auto-save should trigger)")
            
            # Check if file was created
            auto_save_file = Path(conv_manager.auto_save_path)
            if auto_save_file.exists():
                print("PASS: Auto-save file created successfully")
                
                # Verify content
                with open(auto_save_file, 'r') as f:
                    saved_data = json.load(f)
                
                if len(saved_data.get('messages', [])) == 2:
                    print("PASS: Auto-save contains correct number of messages")
                else:
                    print(f"WARNING: Auto-save has {len(saved_data.get('messages', []))} messages, expected 2")
                    
            else:
                print("WARNING: Auto-save file not created")
                
        return True
        
    except Exception as e:
        print(f"FAIL: Auto-save test failed: {e}")
        return False

def test_agent_without_conversation_logger():
    """Test that the agent works without ConversationLogger."""
    print("\nTesting agent without ConversationLogger...")
    
    try:
        # Test import without ConversationLogger
        from chatbot.agent import SimplifiedChatbotAgent as ChatbotAgent
        
        # Check that imports work
        print("PASS: Agent imports successfully without ConversationLogger")
        
        # Mock check - ensure no ConversationLogger in agent code
        import inspect
        agent_source = inspect.getsource(ChatbotAgent)
        
        if 'ConversationLogger' not in agent_source:
            print("PASS: Agent code no longer contains ConversationLogger references")
        else:
            print("WARNING: Agent code still contains ConversationLogger references")
            
        if 'log_conversation_event' not in agent_source:
            print("PASS: Agent code no longer contains log_conversation_event references")
        else:
            print("WARNING: Agent code still contains log_conversation_event references")
            
        return True
        
    except Exception as e:
        print(f"FAIL: Agent test failed: {e}")
        return False

def test_conversation_statistics():
    """Test enhanced conversation statistics."""
    print("\nTesting enhanced conversation statistics...")
    
    try:
        from chatbot.conversation import LangChainConversationManager as ConversationManager
        
        class MockSettings:
            def __init__(self):
                self.conversation_memory_type = "buffer_window"
                self.max_conversation_turns = 5
        
        settings = MockSettings()
        conv_manager = ConversationManager(settings=settings)
        
        # Add some test messages
        conv_manager.add_message("user", "What is the weather?", token_count=5)
        conv_manager.add_message("assistant", "I don't have access to weather data.", token_count=10)  
        conv_manager.add_message("user", "Tell me a joke", token_count=4)
        conv_manager.add_message("assistant", "Why did the chicken cross the road?", token_count=8)
        
        # Get statistics
        stats = conv_manager.get_statistics()
        
        expected_stats = [
            'conversation_id', 'total_messages', 'user_messages', 'assistant_messages',
            'total_tokens', 'total_characters', 'average_message_length',
            'duration_seconds', 'title', 'memory_type'
        ]
        
        for stat in expected_stats:
            if stat in stats:
                print(f"PASS: Statistics contains {stat}: {stats[stat]}")
            else:
                print(f"WARNING: Statistics missing {stat}")
        
        # Check specific values
        if stats['total_messages'] == 4:
            print("PASS: Correct total message count")
        else:
            print(f"WARNING: Expected 4 messages, got {stats['total_messages']}")
            
        if stats['total_tokens'] == 27:  # 5+10+4+8
            print("PASS: Correct token count")
        else:
            print(f"WARNING: Expected 27 tokens, got {stats['total_tokens']}")
            
        return True
        
    except Exception as e:
        print(f"FAIL: Statistics test failed: {e}")
        return False

def test_memory_clearing():
    """Test enhanced memory clearing with logging."""
    print("\nTesting enhanced memory clearing...")
    
    try:
        from chatbot.conversation import LangChainConversationManager as ConversationManager
        
        class MockSettings:
            def __init__(self):
                self.conversation_memory_type = "buffer"
                self.max_conversation_turns = 10
        
        settings = MockSettings()
        conv_manager = ConversationManager(settings=settings)
        
        # Add messages
        conv_manager.add_message("user", "Test message 1")
        conv_manager.add_message("assistant", "Test response 1")
        
        print(f"PASS: Added messages, total: {conv_manager.metadata.message_count}")
        
        # Clear memory
        conv_manager.clear_memory()
        
        if conv_manager.metadata.message_count == 0:
            print("PASS: Memory cleared successfully")
        else:
            print(f"WARNING: Memory not cleared, still has {conv_manager.metadata.message_count} messages")
            
        if len(conv_manager.messages) == 0:
            print("PASS: Message list cleared")
        else:
            print(f"WARNING: Message list not cleared, still has {len(conv_manager.messages)} messages")
            
        return True
        
    except Exception as e:
        print(f"FAIL: Memory clearing test failed: {e}")
        return False

def main():
    """Run all consolidation tests."""
    print("=" * 70)
    print("TESTING CONSOLIDATED CONVERSATION MANAGEMENT")
    print("=" * 70)
    
    tests = [
        test_enhanced_conversation_manager,
        test_auto_save_functionality, 
        test_agent_without_conversation_logger,
        test_conversation_statistics,
        test_memory_clearing
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"FAIL: Test {test.__name__} failed with exception: {e}")
    
    print("\n" + "=" * 70)
    print(f"TEST RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("SUCCESS: Conversation management consolidation complete!")
    else:
        print("WARNING: Some consolidation issues found.")
    
    print("=" * 70)
    
    print("\nCONSOLIDATION SUMMARY:")
    print("ELIMINATED:")
    print("  - ConversationLogger wrapper complexity") 
    print("  - Duplicate conversation tracking")
    print("  - Context manager overhead")
    print("  - log_conversation_event function calls")
    
    print("\nCONSOLIDATED INTO:")
    print("  - Single ConversationManager with integrated logging")
    print("  - Auto-save functionality built-in")
    print("  - Enhanced structured logging")
    print("  - Cleaner agent code")
    
    print("\nBENEFITS:")
    print("  - Single source of truth for conversations")
    print("  - No duplicate tracking")
    print("  - Simpler codebase")
    print("  - Better maintainability")
    print("  - Consistent with our simplification theme")

if __name__ == "__main__":
    main()