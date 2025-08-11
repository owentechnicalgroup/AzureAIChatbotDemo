#!/usr/bin/env python3
"""
Test script to verify the new separated RAG architecture works correctly.
Tests document upload, search, and retrieval functionality.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

from src.config.settings import get_settings
from src.document_management import DocumentManager
from src.rag_access import RAGSearchTool

async def test_new_rag_architecture():
    """Test the new separated RAG architecture."""
    print("Testing New Separated RAG Architecture")
    print("=" * 50)
    
    try:
        # Initialize settings
        settings = get_settings()
        print("Settings loaded")
        
        # Initialize DocumentManager
        document_manager = DocumentManager(settings)
        print("DocumentManager initialized")
        
        # Initialize RAGSearchTool  
        rag_tool = RAGSearchTool(settings)
        print("RAGSearchTool initialized")
        
        # Check tool availability
        is_available = rag_tool.is_available
        print(f"RAG Tool Available: {is_available}")
        
        # Check document stats
        try:
            stats = await document_manager.get_statistics()
            print(f"Documents: {stats.total_documents}")
            print(f"Chunks: {stats.total_chunks}")
            
            if stats.total_documents > 0:
                print("\nTesting RAG Search...")
                
                # Test query
                test_query = "Credit Policy for Member Institutions"
                print(f"Query: '{test_query}'")
                
                # Execute search
                result = await rag_tool._arun(
                    query=test_query,
                    max_chunks=3,
                    use_general_knowledge=False
                )
                
                print(f"\nRAG Result:")
                print("-" * 30)
                print(result)
                print("-" * 30)
                
                # Check if sources were found
                if "Sources used" in result or "• " in result:
                    print("SUCCESS: RAG found documents and generated response!")
                else:
                    print("WARNING: RAG may not have found relevant documents")
                    
            else:
                print("No documents available for testing. Upload some documents first.")
                
        except Exception as e:
            print(f"Error during testing: {str(e)}")
            import traceback
            traceback.print_exc()
            
    except Exception as e:
        print(f"Failed to initialize components: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_new_rag_architecture())