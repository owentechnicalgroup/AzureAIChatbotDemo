#!/usr/bin/env python3
"""
Simple RAG System Test Script

This script tests the RAG document loading system without Unicode characters.
"""

import sys
import os
import asyncio
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

async def test_basic_functionality():
    """Test basic RAG functionality."""
    print("=" * 60)
    print("Testing RAG System Basic Functionality")
    print("=" * 60)
    
    try:
        # Test configuration
        print("1. Testing configuration...")
        from config.settings import get_settings
        settings = get_settings()
        print(f"   Environment: {settings.environment}")
        print(f"   RAG enabled: {settings.enable_rag}")
        print(f"   ChromaDB path: {settings.chromadb_storage_path}")
        print(f"   Azure OpenAI endpoint configured: {bool(settings.azure_openai_endpoint)}")
        print(f"   PASS - Configuration loaded")
        
        # Test ChromaDB connection
        print("\n2. Testing ChromaDB connection...")
        from rag.chromadb_manager import ChromaDBManager
        chromadb_manager = ChromaDBManager(settings)
        
        # Initialize the database
        db = await chromadb_manager.initialize_db()
        doc_count = await chromadb_manager.get_document_count()
        print(f"   ChromaDB initialized successfully")
        print(f"   Documents in database: {doc_count}")
        print(f"   PASS - ChromaDB connection successful")
        
        # Test document processor
        print("\n3. Testing document processor...")
        from rag.document_processor import DocumentProcessor
        processor = DocumentProcessor(settings)
        
        # Test with sample text
        sample_text = "This is a test document for the RAG system. It should be processed correctly."
        chunks = await processor.chunk_document(sample_text, "test_doc")
        print(f"   Created {len(chunks)} chunks from sample text")
        print(f"   PASS - Document processor working")
        
        # Test RAG retriever if we have documents
        print("\n4. Testing RAG retriever...")
        from rag.retriever import RAGRetriever
        from rag import RAGQuery
        
        rag_retriever = RAGRetriever(settings, chromadb_manager)
        health = await rag_retriever.health_check()
        print(f"   RAG retriever health: {health['status']}")
        
        if doc_count > 0:
            print("   Testing query against existing documents...")
            test_query = RAGQuery(
                query="What is this document about?",
                k=2,
                score_threshold=0.1,
                include_sources=True
            )
            
            try:
                response = await rag_retriever.generate_rag_response(test_query)
                print(f"   Query successful - Answer length: {len(response.answer)} chars")
                print(f"   Sources found: {len(response.sources)}")
                print(f"   Confidence score: {response.confidence_score}")
                print(f"   PASS - RAG retrieval working")
            except Exception as query_error:
                print(f"   Query failed: {str(query_error)}")
                print(f"   This might indicate Azure OpenAI connectivity issues")
                return False
        else:
            print("   No documents in database - testing with new document...")
            
            # Add a test document
            test_content = """
            Test Document for RAG System
            
            This is a test document created to validate the RAG system.
            It contains information about testing and validation procedures.
            The system should be able to process this document and answer questions about it.
            """
            
            # Process and add document
            document, chunks = await processor.process_file(
                file_path="test.txt",
                file_content=test_content.encode('utf-8'),
                source_name="test.txt"
            )
            
            await chromadb_manager.add_documents(chunks, document)
            print(f"   Added test document with {len(chunks)} chunks")
            
            # Test query
            test_query = RAGQuery(
                query="What is this document about?",
                k=2,
                score_threshold=0.1,
                include_sources=True
            )
            
            response = await rag_retriever.generate_rag_response(test_query)
            print(f"   Query successful - Answer: {response.answer[:100]}...")
            print(f"   PASS - End-to-end RAG functionality working")
        
        print("\n" + "=" * 60)
        print("SUCCESS: All RAG system tests passed!")
        print("The document loading system appears to be working correctly.")
        print("\nIf you're still having issues in Streamlit:")
        print("1. Check that you're uploading supported file types (PDF, DOCX, TXT)")
        print("2. Verify files are not too large (check max_file_size_mb setting)")
        print("3. Look for error messages in the Streamlit interface")
        print("4. Check the application logs for detailed error information")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\nERROR: RAG system test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        
        print("\nCommon issues and solutions:")
        print("1. Azure OpenAI configuration - Run: scripts\\setup-env.ps1")
        print("2. ChromaDB permissions - Check data directory permissions")
        print("3. Missing dependencies - Run: pip install -r requirements.txt")
        print("4. Key Vault access - Verify Azure authentication")
        
        return False

if __name__ == "__main__":
    success = asyncio.run(test_basic_functionality())
    sys.exit(0 if success else 1)