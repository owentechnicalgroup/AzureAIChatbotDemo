"""
Test script to verify that the new FDIC tools are properly registered for agent use.
"""

import asyncio
from src.config.settings import get_settings
from src.tools.infrastructure.toolsets.banking_toolset import BankingToolset
from src.chatbot.agent import ChatbotAgent


def test_banking_toolset_tools():
    """Test that banking toolset returns the new tools."""
    print("Testing Banking Toolset Tool Registration")
    print("=" * 50)
    
    try:
        # Get settings
        settings = get_settings()
        
        # Create banking toolset
        toolset = BankingToolset(settings)
        tools = toolset.get_tools()
        
        print(f"Banking toolset loaded {len(tools)} tools:")
        for tool in tools:
            print(f"  - {tool.name}: {tool.description[:100]}...")
        
        # Check for specific new tools
        tool_names = [tool.name for tool in tools]
        expected_tools = ["fdic_institution_search", "fdic_financial_data"]
        
        found_tools = []
        missing_tools = []
        
        for expected in expected_tools:
            if expected in tool_names:
                found_tools.append(expected)
            else:
                missing_tools.append(expected)
        
        print(f"\nExpected tools found: {found_tools}")
        if missing_tools:
            print(f"Missing tools: {missing_tools}")
            return False
        else:
            print("✅ All new FDIC tools found in banking toolset!")
            return True
            
    except Exception as e:
        print(f"❌ Banking toolset test failed: {e}")
        return False


def test_agent_tool_access():
    """Test that ChatbotAgent can access the tools."""
    print("\nTesting ChatbotAgent Tool Access")
    print("=" * 50)
    
    try:
        # Get settings
        settings = get_settings()
        
        # Create banking toolset
        toolset = BankingToolset(settings)
        tools = toolset.get_tools()
        
        if not tools:
            print("❌ No tools available from banking toolset")
            return False
        
        # Create agent with tools
        agent = ChatbotAgent(
            settings=settings,
            tools=tools,
            enable_multi_step=True,
            use_general_knowledge=False
        )
        
        print(f"Agent created with {len(agent.tools)} tools:")
        for tool in agent.tools:
            print(f"  - {tool.name}")
        
        # Check if agent executor is set up
        if hasattr(agent, 'agent_executor') and agent.agent_executor:
            print("✅ Agent executor configured for multi-step tool use")
        else:
            print("⚠️  Agent executor not configured")
        
        # Check if new tools are in agent
        agent_tool_names = [tool.name for tool in agent.tools]
        expected_tools = ["fdic_institution_search", "fdic_financial_data"]
        
        found_in_agent = [name for name in expected_tools if name in agent_tool_names]
        
        if len(found_in_agent) == len(expected_tools):
            print(f"✅ All new FDIC tools available to agent: {found_in_agent}")
            return True
        else:
            print(f"❌ Missing tools in agent: {set(expected_tools) - set(found_in_agent)}")
            return False
            
    except Exception as e:
        print(f"❌ Agent tool access test failed: {e}")
        return False


def test_streamlit_integration():
    """Test the Streamlit integration pattern."""
    print("\nTesting Streamlit Integration Pattern")
    print("=" * 50)
    
    try:
        # Simulate Streamlit app logic
        from src.config.settings import get_settings
        from src.tools.infrastructure.toolsets.banking_toolset import BankingToolset
        
        settings = get_settings()
        
        # Banking tools (from streamlit_app.py line 80-86)
        banking_tools = []
        try:
            toolset = BankingToolset(settings)
            if toolset.is_available():
                banking_tools.extend(toolset.get_tools())
        except Exception as e:
            print(f"Banking tools not available: {e}")
            return False
        
        print(f"Streamlit would load {len(banking_tools)} banking tools:")
        for tool in banking_tools:
            print(f"  - {tool.name}")
        
        # Check availability
        if not banking_tools:
            print("❌ No banking tools would be available to Streamlit")
            return False
        
        # Check for new tools
        tool_names = [tool.name for tool in banking_tools]
        expected_tools = ["fdic_institution_search", "fdic_financial_data"]
        
        found_tools = [name for name in expected_tools if name in tool_names]
        
        if len(found_tools) == len(expected_tools):
            print(f"✅ New FDIC tools available to Streamlit: {found_tools}")
            return True
        else:
            missing = set(expected_tools) - set(found_tools)
            print(f"❌ Tools missing from Streamlit: {missing}")
            return False
            
    except Exception as e:
        print(f"❌ Streamlit integration test failed: {e}")
        return False


def run_registration_tests():
    """Run all registration tests."""
    print("FDIC Tool Registration Test Suite")
    print("=" * 60)
    
    tests = [
        ("Banking Toolset", test_banking_toolset_tools),
        ("Agent Tool Access", test_agent_tool_access), 
        ("Streamlit Integration", test_streamlit_integration),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("REGISTRATION TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tools are properly registered!")
        print("✅ New FDIC tools are available to agents")
        print("✅ Streamlit will load the new tools")
        print("✅ ChatbotAgent can access the tools")
    else:
        print(f"\n⚠️  {total - passed} registration issues found")
        print("Some tools may not be available to the agent")
    
    return passed == total


if __name__ == "__main__":
    success = run_registration_tests()
    exit(0 if success else 1)