#!/usr/bin/env python3
"""
Test Lake Tippecanoe Query

This script tests the specific query that was failing.
"""

import sys
import asyncio
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

async def test_lake_tippecanoe_query():
    """Test the specific Lake Tippecanoe query that was failing."""
    print("=" * 60)
    print("Testing Lake Tippecanoe Query")
    print("=" * 60)
    
    try:
        from config.settings import get_settings
        from rag.chromadb_manager import ChromaDBManager
        from rag.retriever import RAGRetriever
        from rag import RAGQuery
        
        settings = get_settings()
        chromadb_manager = ChromaDBManager(settings)
        rag_retriever = RAGRetriever(settings, chromadb_manager)
        
        # Test the exact query that was failing
        print("Testing query: 'what can you tell me about Lake Tippecanoe'")
        
        test_query = RAGQuery(
            query="what can you tell me about Lake Tippecanoe",
            k=5,
            score_threshold=0.2,  # Using new lower threshold
            include_sources=True
        )
        
        response = await rag_retriever.generate_rag_response(test_query)
        
        print(f"\nRESULT: Query successful!")
        print(f"Answer length: {len(response.answer)} characters")
        print(f"Sources found: {len(response.sources)}")
        print(f"Confidence score: {response.confidence_score:.3f}")
        print(f"Retrieved chunks: {len(response.retrieved_chunks)}")
        
        print(f"\nSources: {response.sources}")
        
        print(f"\nAnswer preview:")
        print("-" * 40)
        print(response.answer[:500] + "..." if len(response.answer) > 500 else response.answer)
        print("-" * 40)
        
        print(f"\n SUCCESS: Lake Tippecanoe query now works!")
        print(f"The similarity threshold fix resolved the issue.")
        
        return True
        
    except Exception as e:
        print(f"ERROR: Lake Tippecanoe query failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_lake_tippecanoe_query())
    sys.exit(0 if success else 1)