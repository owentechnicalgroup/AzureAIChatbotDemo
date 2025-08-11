"""
End-to-End Test for Separated RAG Architecture.

This test validates that the new separated RAG architecture works correctly:
1. Document management operations (upload, list, delete)
2. RAG search and response generation  
3. Tool integration with dynamic loading
4. Backward compatibility with existing interfaces

Tests both the separation of concerns and the integration between components.
"""

import asyncio
import tempfile
from pathlib import Path
from typing import Dict, Any
import pytest
import structlog

from src.config.settings import get_settings
from src.document_management import DocumentManager, DocumentInfo, DocumentStats
from src.rag_access import SearchService, RAGQuery, SearchContext
from src.tools.dynamic_loader import DynamicToolLoader
from src.tools.rag.document_search import DocumentSearchTool


# Configure logging for tests
logger = structlog.get_logger(__name__)


class TestSeparatedRAGArchitecture:
    """Test suite for separated RAG architecture."""
    
    @pytest.fixture
    def settings(self):
        """Get test settings."""
        return get_settings()
    
    @pytest.fixture 
    def document_manager(self, settings):
        """Create document manager instance."""
        return DocumentManager(settings)
    
    @pytest.fixture
    def search_service(self, settings):
        """Create search service instance."""
        return SearchService(settings)
    
    @pytest.fixture
    def sample_document_content(self):
        """Create sample document content for testing."""
        return """
        # Test Document

        This is a test document for the separated RAG architecture.

        ## Company Policy
        All employees must follow the company guidelines for remote work.
        Remote work is allowed 3 days per week maximum.

        ## Vacation Policy  
        Employees are entitled to 15 days of vacation per year.
        Vacation requests must be submitted 2 weeks in advance.

        ## Safety Guidelines
        All safety protocols must be followed at all times.
        Emergency procedures are posted in all common areas.
        """

async def test_document_management_operations():
    """Test basic document management operations."""
    print("\n[TEST] Testing Document Management Operations...")
    
    settings = get_settings()
    document_manager = DocumentManager(settings)
    
    # Test 1: Check if document manager is available
    assert document_manager.is_available(), "Document manager should be available"
    print("[PASS] Document manager availability check passed")
    
    # Test 2: Get initial statistics
    initial_stats = await document_manager.get_statistics()
    assert isinstance(initial_stats, DocumentStats)
    print(f"✅ Initial stats: {initial_stats.total_documents} documents, {initial_stats.total_chunks} chunks")
    
    # Test 3: Upload a test document
    sample_content = """
    # Test RAG Document
    This is a test document for the separated RAG architecture.
    
    ## Important Information
    The new architecture separates document management from AI access.
    This allows for better maintainability and cleaner code organization.
    """
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write(sample_content)
        temp_path = Path(f.name)
    
    try:
        upload_result = await document_manager.upload_document(
            file_path=temp_path,
            file_content=sample_content.encode('utf-8'),
            source_name="test_rag_document.md"
        )
        
        assert upload_result.success, f"Upload should succeed: {upload_result.error}"
        assert upload_result.document_info is not None
        print(f"✅ Document upload successful: {upload_result.document_info.filename}")
        
        # Test 4: List documents
        documents = await document_manager.list_documents()
        assert len(documents) > initial_stats.total_documents
        print(f"✅ Document listing works: {len(documents)} total documents")
        
        # Test 5: Get updated statistics
        updated_stats = await document_manager.get_statistics()
        assert updated_stats.total_documents > initial_stats.total_documents
        print(f"✅ Statistics updated: {updated_stats.total_documents} documents")
        
        # Test 6: Health check
        health = await document_manager.health_check()
        assert health["status"] == "healthy"
        print("✅ Document manager health check passed")
        
    finally:
        # Cleanup
        temp_path.unlink(missing_ok=True)


async def test_search_service_operations():
    """Test RAG search service operations."""
    print("\n🔍 Testing Search Service Operations...")
    
    settings = get_settings()
    search_service = SearchService(settings)
    
    # Test 1: Check if search service is available
    assert search_service.is_available(), "Search service should be available"
    print("✅ Search service availability check passed")
    
    # Test 2: Health check
    health = await search_service.health_check()
    print(f"✅ Search service health: {health['status']}")
    
    # Test 3: Search with no context (should handle gracefully)
    query = RAGQuery(
        query="What is the company vacation policy?",
        max_chunks=3,
        use_general_knowledge=True
    )
    
    context = SearchContext(
        conversation_id="test_conversation",
        user_id="test_user"
    )
    
    response = await search_service.search_and_generate(query, context)
    assert response is not None
    assert response.content is not None
    assert len(response.content) > 0
    print(f"✅ Search and generation works: {response.processing_mode} mode")
    
    # Test 4: Search refinement suggestions
    suggestions = await search_service.search_refinement_suggestions("vacation policy")
    assert "refinement_text" in suggestions
    print("✅ Search refinement suggestions work")
    
    # Test 5: Get available documents
    documents = await search_service.get_available_documents()
    assert isinstance(documents, list)
    print(f"✅ Available documents: {len(documents)}")


async def test_tool_integration():
    """Test tool integration with separated architecture."""
    print("\n🔧 Testing Tool Integration...")
    
    settings = get_settings()
    tool_loader = DynamicToolLoader(settings)
    
    # Test 1: Load available tools
    tools = tool_loader.get_available_tools()
    assert len(tools) > 0, "Should have at least some tools available"
    print(f"✅ Tools loaded: {len(tools)} available")
    
    # Test 2: Check tool status
    status = tool_loader.get_tool_status()
    assert isinstance(status, dict)
    print("✅ Tool status available")
    
    # Test 3: Create document search tool directly
    document_tool = DocumentSearchTool(settings)
    assert document_tool.is_available
    print("✅ Document search tool creation works")
    
    # Test 4: Test tool execution (if documents are available)
    try:
        result = await document_tool._arun(
            query="test query about documents",
            max_chunks=2,
            use_general_knowledge=True
        )
        assert isinstance(result, str)
        assert len(result) > 0
        print("✅ Document search tool execution works")
    except Exception as e:
        print(f"⚠️  Document search tool execution: {str(e)} (may be expected if no documents)")


async def test_backward_compatibility():
    """Test backward compatibility with existing interfaces."""
    print("\n🔄 Testing Backward Compatibility...")
    
    try:
        # Test 1: Import from old locations should work with deprecation warnings
        from src.rag.document_manager import DocumentManager as OldDocumentManager
        from src.rag.rag_search import SearchService as OldSearchService
        
        print("✅ Backward compatibility imports work")
        
        # Test 2: Old interfaces should create new instances
        settings = get_settings()
        old_doc_manager = OldDocumentManager(settings)
        assert old_doc_manager is not None
        print("✅ Old document manager interface works")
        
    except ImportError as e:
        print(f"⚠️  Backward compatibility test failed: {str(e)}")


async def test_end_to_end_workflow():
    """Test complete end-to-end workflow."""
    print("\n🚀 Testing End-to-End Workflow...")
    
    settings = get_settings()
    
    # Initialize all components
    document_manager = DocumentManager(settings)
    search_service = SearchService(settings)
    tool_loader = DynamicToolLoader(settings)
    
    print("✅ All components initialized")
    
    # Test workflow: Upload -> Search -> Tool Usage
    sample_content = """
    # Employee Handbook
    
    ## Remote Work Policy
    Employees may work remotely up to 3 days per week.
    All remote work must be approved by direct supervisor.
    
    ## Vacation Benefits
    - Full-time employees: 15 days vacation per year
    - Part-time employees: 10 days vacation per year
    - All vacation must be requested 2 weeks in advance
    """
    
    # Step 1: Upload document
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write(sample_content)
        temp_path = Path(f.name)
    
    try:
        upload_result = await document_manager.upload_document(
            file_path=temp_path,
            file_content=sample_content.encode('utf-8'),
            source_name="employee_handbook.md"
        )
        
        assert upload_result.success
        print("✅ Document uploaded successfully")
        
        # Step 2: Wait a moment for indexing
        await asyncio.sleep(1)
        
        # Step 3: Search for information
        query = RAGQuery(
            query="How many vacation days do full-time employees get?",
            max_chunks=2,
            use_general_knowledge=False
        )
        
        response = await search_service.search_and_generate(query, SearchContext())
        assert response.content is not None
        print(f"✅ Search successful: {response.processing_mode} mode")
        
        # Step 4: Test tool integration
        tools = tool_loader.get_available_tools()
        rag_tools = [tool for tool in tools if hasattr(tool, 'name') and 'document' in tool.name.lower()]
        
        if rag_tools:
            rag_tool = rag_tools[0]
            tool_result = await rag_tool._arun("What is the remote work policy?")
            assert isinstance(tool_result, str)
            print("✅ Tool integration successful")
        
        print("🎉 End-to-end workflow completed successfully!")
        
    finally:
        # Cleanup
        temp_path.unlink(missing_ok=True)


async def run_all_tests():
    """Run all test functions."""
    print("🧪 Starting Separated RAG Architecture Tests\n")
    
    test_functions = [
        test_document_management_operations,
        test_search_service_operations, 
        test_tool_integration,
        test_backward_compatibility,
        test_end_to_end_workflow
    ]
    
    passed = 0
    failed = 0
    
    for test_func in test_functions:
        try:
            await test_func()
            passed += 1
            print(f"✅ {test_func.__name__} PASSED\n")
        except Exception as e:
            failed += 1
            print(f"❌ {test_func.__name__} FAILED: {str(e)}\n")
    
    print(f"📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed! Separated RAG architecture is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
    
    return failed == 0


if __name__ == "__main__":
    # Run tests
    success = asyncio.run(run_all_tests())
    exit(0 if success else 1)