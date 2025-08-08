"""
Test suite for enhanced LangChain tool registry with category support.

Tests the CRITICAL RAG tool registration fix and category-based tool organization.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch
from typing import List

from src.config.settings import get_settings
from src.rag.langchain_tools import LangChainToolRegistry
from src.tools.categories import ToolCategory, add_category_metadata
from langchain.tools import BaseTool


class MockTool(BaseTool):
    """Mock LangChain BaseTool for testing."""
    
    name: str = "mock_tool"
    description: str = "Mock tool for testing"
    
    def _run(self, *args, **kwargs) -> str:
        return "Mock tool result"
    
    async def _arun(self, *args, **kwargs) -> str:
        return "Mock tool async result"


@pytest.fixture
def settings():
    """Get test settings."""
    return get_settings()


@pytest.fixture
def mock_tool():
    """Create a mock LangChain BaseTool."""
    return MockTool()


@pytest.fixture
def categorized_mock_tool(mock_tool):
    """Create a mock tool with category metadata."""
    return add_category_metadata(
        mock_tool,
        category=ToolCategory.UTILITIES,
        requires_services=["test_service"],
        priority=5,
        tags=["test", "mock"]
    )


class TestEnhancedLangChainToolRegistry:
    """Test enhanced LangChain tool registry functionality."""
    
    def test_registry_initialization_with_dynamic_loading(self, settings):
        """Test registry initializes with dynamic loading enabled."""
        registry = LangChainToolRegistry(settings, enable_dynamic_loading=True)
        
        assert registry.enable_dynamic_loading is True
        assert registry.dynamic_loader is not None
        assert isinstance(registry.tools, list)
        assert isinstance(registry.tools_by_category, dict)
    
    def test_registry_initialization_without_dynamic_loading(self, settings):
        """Test registry initializes with dynamic loading disabled."""
        registry = LangChainToolRegistry(settings, enable_dynamic_loading=False)
        
        assert registry.enable_dynamic_loading is False
        assert registry.dynamic_loader is None
        assert isinstance(registry.tools, list)
    
    @pytest.mark.asyncio
    async def test_critical_rag_tool_registration(self, settings):
        """
        CRITICAL TEST: Verify RAG tool registration fix.
        
        This test validates that the RAG tool (document_search) is properly
        registered, which was the main issue identified in the PRP.
        """
        # Mock ChromaDB availability to ensure RAG tool loads
        with patch('src.tools.dynamic_loader.DynamicToolLoader.check_service_availability') as mock_check:
            mock_check.return_value = {"chromadb"}
            
            registry = LangChainToolRegistry(settings, enable_dynamic_loading=True)
            
            tools = registry.get_tools()
            tool_names = [tool.name for tool in tools]
            
            # CRITICAL ASSERTION: RAG tool must be registered
            assert "document_search" in tool_names, "CRITICAL: RAG tool (document_search) not registered"
            
            # Verify tool is properly categorized
            rag_tools = [tool for tool in tools if tool.name == "document_search"]
            assert len(rag_tools) == 1, "Should have exactly one RAG tool"
            
            # Verify category metadata if available
            rag_tool = rag_tools[0]
            if hasattr(rag_tool, 'get_category'):
                assert rag_tool.get_category() == ToolCategory.DOCUMENTS
    
    def test_get_tools_by_category(self, settings):
        """Test filtering tools by category."""
        registry = LangChainToolRegistry(settings, enable_dynamic_loading=False)
        
        # Add mock tools with categories
        mock_doc_tool = MockTool()
        mock_doc_tool.name = "mock_document_tool"
        mock_doc_tool = add_category_metadata(mock_doc_tool, ToolCategory.DOCUMENTS)
        
        mock_banking_tool = MockTool()
        mock_banking_tool.name = "mock_banking_tool"
        mock_banking_tool = add_category_metadata(mock_banking_tool, ToolCategory.BANKING)
        
        registry.tools = [mock_doc_tool, mock_banking_tool]
        registry.tools_by_category = {
            ToolCategory.DOCUMENTS: [mock_doc_tool],
            ToolCategory.BANKING: [mock_banking_tool]
        }
        
        # Test category filtering
        doc_tools = registry.get_tools_by_category(ToolCategory.DOCUMENTS)
        assert len(doc_tools) == 1
        assert doc_tools[0].name == "mock_document_tool"
        
        banking_tools = registry.get_tools_by_category(ToolCategory.BANKING)
        assert len(banking_tools) == 1
        assert banking_tools[0].name == "mock_banking_tool"
        
        # Test empty category
        web_tools = registry.get_tools_by_category(ToolCategory.WEB)
        assert len(web_tools) == 0
    
    def test_get_available_categories(self, settings):
        """Test getting available categories."""
        registry = LangChainToolRegistry(settings, enable_dynamic_loading=False)
        
        # Setup tools by category
        mock_tool = MockTool()
        registry.tools_by_category = {
            ToolCategory.DOCUMENTS: [mock_tool],
            ToolCategory.BANKING: [],  # Empty category
            ToolCategory.UTILITIES: [mock_tool]
        }
        
        available_categories = registry.get_available_categories()
        
        # Should only include categories with tools
        assert ToolCategory.DOCUMENTS in available_categories
        assert ToolCategory.UTILITIES in available_categories
        assert ToolCategory.BANKING not in available_categories
    
    def test_get_category_summary(self, settings):
        """Test category summary generation."""
        registry = LangChainToolRegistry(settings, enable_dynamic_loading=False)
        
        # Setup mock tools
        doc_tool = MockTool()
        doc_tool.name = "document_search"
        doc_tool = add_category_metadata(doc_tool, ToolCategory.DOCUMENTS)
        
        utility_tool = MockTool()
        utility_tool.name = "utility_tool"
        utility_tool = add_category_metadata(utility_tool, ToolCategory.UTILITIES)
        
        registry.tools = [doc_tool, utility_tool]
        
        summary = registry.get_category_summary()
        
        assert summary["total_tools"] == 2
        assert summary["dynamic_loading_enabled"] is False
        assert "categories" in summary
        
        # Check documents category
        doc_category = summary["categories"].get("documents")
        assert doc_category is not None
        assert doc_category["tool_count"] == 1
        assert "document_search" in doc_category["tool_names"]
        assert doc_category["has_rag_tool"] is True
    
    def test_health_status_includes_rag_check(self, settings):
        """Test health status includes RAG tool registration check."""
        registry = LangChainToolRegistry(settings, enable_dynamic_loading=False)
        
        # Test with RAG tool present
        rag_tool = MockTool()
        rag_tool.name = "document_search"
        registry.tools = [rag_tool]
        
        health_status = registry.get_health_status()
        
        assert health_status["rag_tool_registered"] is True
        assert "critical_warning" not in health_status
        
        # Test without RAG tool
        registry.tools = []
        health_status = registry.get_health_status()
        
        assert health_status["rag_tool_registered"] is False
        assert "critical_warning" in health_status
    
    def test_backward_compatibility(self, settings):
        """Test backward compatibility with existing code."""
        # Test that old factory function still works
        from src.rag.langchain_tools import create_langchain_tool_registry
        
        registry = create_langchain_tool_registry(settings)
        assert isinstance(registry, LangChainToolRegistry)
        
        # Test that get_tools method works
        tools = registry.get_tools()
        assert isinstance(tools, list)
        
        # Test that get_tools_for_agent works
        agent_tools = registry.get_tools_for_agent()
        assert isinstance(agent_tools, list)
    
    @pytest.mark.asyncio
    async def test_reload_tools_functionality(self, settings):
        """Test dynamic tool reloading."""
        with patch('src.tools.dynamic_loader.DynamicToolLoader.load_all_available_tools') as mock_load:
            mock_load.return_value = {ToolCategory.DOCUMENTS: [MockTool()]}
            
            registry = LangChainToolRegistry(settings, enable_dynamic_loading=True)
            
            # Test reload
            success = await registry.reload_tools()
            assert success is True
            mock_load.assert_called()


class TestToolCategoryMetadata:
    """Test tool category metadata functionality."""
    
    def test_add_category_metadata_to_tool(self, mock_tool):
        """Test adding category metadata to existing tool."""
        categorized_tool = add_category_metadata(
            mock_tool,
            category=ToolCategory.DOCUMENTS,
            requires_services=["chromadb"],
            priority=10,
            tags=["test"]
        )
        
        # Verify metadata was added
        assert hasattr(categorized_tool, 'get_category')
        assert hasattr(categorized_tool, 'get_category_metadata')
        assert hasattr(categorized_tool, 'has_service_dependencies')
        assert hasattr(categorized_tool, 'get_required_services')
        
        # Test metadata values
        assert categorized_tool.get_category() == ToolCategory.DOCUMENTS
        assert categorized_tool.has_service_dependencies() is True
        assert categorized_tool.get_required_services() == ["chromadb"]
        
        metadata = categorized_tool.get_category_metadata()
        assert metadata.category == ToolCategory.DOCUMENTS
        assert metadata.priority == 10
        assert "test" in metadata.tags
    
    def test_tool_without_metadata_has_defaults(self, mock_tool):
        """Test that tools without metadata get reasonable defaults."""
        from src.tools.categories import get_tool_category, get_tool_metadata
        
        # Tool without metadata should get classified
        category = get_tool_category(mock_tool)
        assert category in ToolCategory
        
        # Should return None for metadata
        metadata = get_tool_metadata(mock_tool)
        assert metadata is None


@pytest.mark.integration
class TestCriticalRAGIntegration:
    """Integration tests for the CRITICAL RAG tool registration fix."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_rag_tool_availability(self, settings):
        """
        End-to-end test of RAG tool availability in ChatbotAgent.
        
        This is the ultimate test of the CRITICAL fix - ensuring RAG tool
        is available to the ChatbotAgent for multi-step conversations.
        """
        from src.chatbot.agent import ChatbotAgent
        
        # Create enhanced registry
        registry = LangChainToolRegistry(settings, enable_dynamic_loading=True)
        tools = registry.get_tools()
        
        # Should have RAG tool available
        rag_tools = [tool for tool in tools if tool.name == "document_search"]
        assert len(rag_tools) > 0, "RAG tool must be available for agent"
        
        # Create agent with tools
        agent = ChatbotAgent(
            settings=settings,
            tools=tools,
            enable_multi_step=True
        )
        
        # Verify agent setup
        assert agent.enable_multi_step is True
        assert len(agent.tools) > 0
        assert any(tool.name == "document_search" for tool in agent.tools)
        
        # Test that agent can process document-related queries
        # (Note: Full response testing would require actual document content)
        assert agent.agent_executor is not None, "Agent executor should be initialized"
    
    def test_critical_fix_validation_script(self, settings):
        """
        Test that mimics the validation script from the PRP.
        
        This ensures the critical issue identified in the PRP is resolved.
        """
        registry = LangChainToolRegistry(settings)
        tools = registry.get_tools()
        tool_names = [tool.name for tool in tools]
        
        # The critical test from the PRP
        if 'document_search' in tool_names:
            # SUCCESS case
            assert True, "SUCCESS: RAG tool registration fixed!"
        else:
            # FAILURE case - this should not happen after the fix
            pytest.fail("FAILURE: RAG tool still not registered - CRITICAL ISSUE NOT RESOLVED")


if __name__ == "__main__":
    # Run tests directly for quick validation
    import sys
    sys.path.append('src')
    
    print("Running CRITICAL RAG tool registration tests...")
    
    # Quick smoke test
    settings = get_settings()
    registry = LangChainToolRegistry(settings)
    tools = registry.get_tools()
    tool_names = [tool.name for tool in tools]
    
    if 'document_search' in tool_names:
        print("✅ SUCCESS: CRITICAL RAG tool registration test PASSED!")
        print(f"Tools available: {tool_names}")
    else:
        print("❌ FAILURE: CRITICAL RAG tool registration test FAILED!")
        print(f"Tools found: {tool_names}")
        print("The critical issue identified in the PRP is NOT resolved!")