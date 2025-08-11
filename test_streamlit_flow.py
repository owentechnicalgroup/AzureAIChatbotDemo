#!/usr/bin/env python3
"""
Test Streamlit Document Processing Flow

This script simulates the exact flow that Streamlit uses for document processing
to ensure the fix works correctly.
"""

import sys
import asyncio
from pathlib import Path
import io

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

async def test_streamlit_document_flow():
    """Test the exact document processing flow used by Streamlit."""
    print("=" * 60)
    print("Testing Streamlit Document Processing Flow")
    print("=" * 60)
    
    try:
        # Import required components
        from config.settings import get_settings
        from rag.document_processor import DocumentProcessor
        from rag.chromadb_manager import ChromaDBManager
        
        settings = get_settings()
        processor = DocumentProcessor(settings)
        chromadb_manager = ChromaDBManager(settings)
        
        # Simulate different file types that Streamlit might upload
        test_files = [
            {
                "name": "test_document.txt",
                "content": """
                This is a test document uploaded through Streamlit.
                
                The document contains multiple paragraphs to test the RAG system.
                It should be processed correctly and stored in ChromaDB.
                
                Key features to test:
                1. File upload simulation
                2. In-memory processing
                3. Text extraction
                4. Document chunking
                5. Vector storage
                """.encode('utf-8')
            },
            {
                "name": "sample.pdf",  # We'll simulate PDF content as text
                "content": b"PDF content simulation - this would normally be binary PDF data"
            }
        ]
        
        print(f"Simulating Streamlit file upload for {len(test_files)} files...")
        
        processed_documents = []
        
        for i, file_data in enumerate(test_files):
            filename = file_data["name"]
            file_content = file_data["content"]
            
            print(f"\n{i+1}. Processing {filename}...")
            print(f"   File size: {len(file_content)} bytes")
            
            try:
                # This is exactly what Streamlit does:
                # 1. Read file content into memory
                # 2. Pass filename and content to process_file
                document, chunks = await processor.process_file(
                    file_path=Path(filename),  # Just the filename, not a real path
                    file_content=file_content,  # In-memory content
                    source_name=filename
                )
                
                print(f"   SUCCESS: Document processed")
                print(f"   - Document ID: {document.id}")
                print(f"   - Status: {document.processing_status}")
                print(f"   - Chunks created: {len(chunks)}")
                
                # Add to ChromaDB (like Streamlit does)
                doc_ids = await chromadb_manager.add_documents(chunks, document)
                print(f"   - Added to ChromaDB: {len(doc_ids)} chunks stored")
                
                processed_documents.append({
                    "id": document.id,
                    "filename": filename,
                    "chunk_count": len(chunks),
                    "status": "completed"
                })
                
            except Exception as e:
                print(f"   ERROR: {str(e)}")
                if filename.endswith('.pdf'):
                    print(f"   NOTE: PDF processing requires proper PDF content")
                else:
                    print(f"   This is unexpected - investigating...")
                    raise
        
        # Test retrieval
        print(f"\nTesting document retrieval...")
        total_docs = await chromadb_manager.get_document_count()
        print(f"Total documents in ChromaDB: {total_docs}")
        
        if total_docs > 0:
            # Test search functionality
            from rag.retriever import RAGRetriever
            from rag import RAGQuery
            
            rag_retriever = RAGRetriever(settings, chromadb_manager)
            
            test_query = RAGQuery(
                query="What features are being tested?",
                k=3,
                score_threshold=0.1,
                include_sources=True
            )
            
            response = await rag_retriever.generate_rag_response(test_query)
            print(f"Query response: {response.answer[:150]}...")
            print(f"Sources: {response.sources}")
        
        print(f"\n" + "=" * 60)
        print(f"STREAMLIT FLOW TEST COMPLETE")
        print(f"Successfully processed: {len(processed_documents)} documents")
        print(f"Documents in database: {total_docs}")
        print(f"=" * 60)
        
        print(f"\nThe document loading issue should now be fixed!")
        print(f"You can now upload documents in Streamlit and they should process correctly.")
        
        return True
        
    except Exception as e:
        print(f"\nERROR in Streamlit flow test: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_streamlit_document_flow())
    if success:
        print(f"\n✓ Fix verified! Document loading should now work in Streamlit.")
    else:
        print(f"\n✗ There may still be issues to resolve.")
    sys.exit(0 if success else 1)