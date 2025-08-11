#!/usr/bin/env python3
"""
Simple test to verify LangChain BaseTool pattern works correctly.
"""

import asyncio
from typing import Type, Optional
from pydantic import BaseModel, Field
from langchain.tools import BaseTool
from langchain.callbacks.manager import AsyncCallbackManagerForToolRun, CallbackManagerForToolRun


class SimpleInput(BaseModel):
    """Simple input schema."""
    text: str = Field(description="Text to process")


class SimpleLangChainTool(BaseTool):
    """Simple test tool for LangChain compatibility."""
    
    name: str = "simple_test"
    description: str = "A simple test tool that processes text"
    args_schema: Type[BaseModel] = SimpleInput
    
    def __init__(self, test_data: str = "default", **kwargs):
        """Initialize with test data."""
        super().__init__(**kwargs)
        # Store test data without interfering with Pydantic
        object.__setattr__(self, '_test_data', test_data)
    
    def _run(
        self,
        text: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Synchronous execution."""
        return f"Processed '{text}' with {self._test_data}"
    
    async def _arun(
        self,
        text: str,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ) -> str:
        """Asynchronous execution."""
        return f"Async processed '{text}' with {self._test_data}"


def test_simple_langchain_tool():
    """Test basic LangChain tool functionality."""
    print("Testing simple LangChain BaseTool pattern...")
    
    # Create tool
    tool = SimpleLangChainTool(test_data="test_value")
    print(f"✅ Tool created: {tool.name}")
    print(f"   Description: {tool.description}")
    print(f"   Test data: {tool._test_data}")
    
    # Test sync execution
    result = tool._run("hello world")
    print(f"✅ Sync execution: {result}")
    
    # Test async execution
    async_result = asyncio.run(tool._arun("hello async"))
    print(f"✅ Async execution: {async_result}")
    
    # Test tool can be used in list (like agent would)
    tools = [tool]
    print(f"✅ Tool in list: {len(tools)} tools available")
    for t in tools:
        print(f"   - {t.name}: {t.description}")
    
    print("\n🎉 Simple LangChain tool test passed!")
    print("✅ The BaseTool pattern works correctly")
    print("✅ Ready to implement full Call Report tools")


if __name__ == "__main__":
    test_simple_langchain_tool()
