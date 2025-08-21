"""
Simple test to verify FDIC tool registration (no emojis for Windows compatibility).
"""

def test_tool_registration():
    """Test that new FDIC tools are properly registered."""
    print("FDIC Tool Registration Test")
    print("=" * 40)
    
    try:
        # Test banking toolset
        from src.config.settings import get_settings
        from src.tools.infrastructure.toolsets.banking_toolset import BankingToolset
        
        settings = get_settings()
        toolset = BankingToolset(settings)
        tools = toolset.get_tools()
        
        print(f"Banking toolset loaded {len(tools)} tools:")
        tool_names = []
        for tool in tools:
            print(f"  - {tool.name}")
            tool_names.append(tool.name)
        
        # Check for new tools
        expected_tools = ["fdic_institution_search", "fdic_financial_data"]
        found_tools = [name for name in expected_tools if name in tool_names]
        missing_tools = [name for name in expected_tools if name not in tool_names]
        
        print(f"\nExpected tools found: {found_tools}")
        if missing_tools:
            print(f"Missing tools: {missing_tools}")
            return False
        
        # Test agent access
        from src.chatbot.agent import ChatbotAgent
        
        agent = ChatbotAgent(
            settings=settings,
            tools=tools,
            enable_multi_step=True,
            use_general_knowledge=False
        )
        
        agent_tool_names = [tool.name for tool in agent.tools]
        agent_found_tools = [name for name in expected_tools if name in agent_tool_names]
        
        print(f"\nAgent has tools: {agent_tool_names}")
        print(f"Agent has new FDIC tools: {agent_found_tools}")
        
        if len(agent_found_tools) == len(expected_tools):
            print("\nSUCCESS: All new FDIC tools are properly registered!")
            print("- Banking toolset loads the new tools")
            print("- ChatbotAgent can access the tools")
            print("- Multi-step mode is enabled")
            return True
        else:
            print(f"\nFAILED: Agent missing tools: {set(expected_tools) - set(agent_found_tools)}")
            return False
            
    except Exception as e:
        print(f"\nFAILED: Registration test error: {e}")
        return False


if __name__ == "__main__":
    success = test_tool_registration()
    if success:
        print("\nCONCLUSION: New FDIC tools are ready for agent use!")
    else:
        print("\nCONCLUSION: Tool registration has issues.")
    exit(0 if success else 1)