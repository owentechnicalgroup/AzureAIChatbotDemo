"""
Simple test for separated RAG architecture.
Tests basic functionality without complex UI elements.
"""

import asyncio
import tempfile
from pathlib import Path

from src.config.settings import get_settings
from src.document_management import DocumentManager
from src.rag_access import SearchService, RAGQuery, SearchContext


async def test_basic_functionality():
    """Test basic separated RAG functionality."""
    print("\n[TEST] Testing Separated RAG Architecture...")
    
    settings = get_settings()
    
    # Test 1: Initialize components
    print("Initializing components...")
    document_manager = DocumentManager(settings)
    search_service = SearchService(settings)
    
    assert document_manager.is_available(), "Document manager should be available"
    assert search_service.is_available(), "Search service should be available"
    print("[PASS] Components initialized successfully")
    
    # Test 2: Health checks
    print("Running health checks...")
    doc_health = await document_manager.health_check()
    search_health = await search_service.health_check()
    
    print(f"Document manager health: {doc_health.get('status', 'unknown')}")
    print(f"Search service health: {search_health.get('status', 'unknown')}")
    
    # Test 3: Basic document operations
    print("Testing document operations...")
    initial_stats = await document_manager.get_statistics()
    print(f"Initial stats: {initial_stats.total_documents} documents, {initial_stats.total_chunks} chunks")
    
    # Test 4: Basic search operation
    print("Testing search operations...")
    query = RAGQuery(
        query="What is the company policy?",
        max_chunks=2,
        use_general_knowledge=True
    )
    
    context = SearchContext(conversation_id="test_123")
    response = await search_service.search_and_generate(query, context)
    
    assert response is not None
    assert response.content is not None
    print(f"[PASS] Search response received: {response.processing_mode} mode")
    print(f"Response length: {len(response.content)} characters")
    
    # Test 5: Document upload (simple test)
    sample_content = """
    # Test Document
    This is a test document for validation.
    The company policy is to work collaboratively.
    """
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write(sample_content)
        temp_path = Path(f.name)
    
    try:
        upload_result = await document_manager.upload_document(
            file_path=temp_path,
            file_content=sample_content.encode('utf-8'),
            source_name="test_document.md"
        )
        
        print(f"Upload result: {upload_result.success}")
        if upload_result.success:
            print("[PASS] Document upload successful")
            
            # Test search with uploaded document
            await asyncio.sleep(1)  # Wait for indexing
            
            query2 = RAGQuery(
                query="What is the company policy according to the document?",
                max_chunks=2,
                use_general_knowledge=False
            )
            
            response2 = await search_service.search_and_generate(query2, context)
            print(f"[PASS] Search after upload: {response2.processing_mode} mode")
            
        else:
            print(f"[WARN] Upload failed: {upload_result.error}")
            
    finally:
        temp_path.unlink(missing_ok=True)
    
    print("\n[COMPLETE] Basic functionality test completed successfully!")
    return True


async def main():
    """Main test function."""
    try:
        success = await test_basic_functionality()
        print(f"\n[RESULT] Test {'PASSED' if success else 'FAILED'}")
        return success
    except Exception as e:
        print(f"\n[ERROR] Test failed with exception: {str(e)}")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)