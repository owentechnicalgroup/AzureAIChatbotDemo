#!/usr/bin/env python3
"""
Test script to verify Streamlit integration with Call Report tools.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

async def test_streamlit_integration():
    """Test that the ToolsIntegratedRAGRetriever works with the expected interface."""
    print("Testing Streamlit integration with Call Report tools...")
    
    try:
        from rag.tools_integration import ToolsIntegratedRAGRetriever
        from rag.chromadb_manager import ChromaDBManager
        from config.settings import Settings
        
        print("Successfully imported modules")
        
        # Initialize components (similar to Streamlit app)
        settings = Settings()
        chromadb_manager = ChromaDBManager(settings)
        rag_retriever = ToolsIntegratedRAGRetriever(settings, chromadb_manager)
        
        print("Successfully initialized RAG retriever with tools")
        
        # Test the method call that Streamlit will use - test composite tool
        test_query = "Get total assets for Bank of America"
        print(f"Testing composite tool query: '{test_query}'")
        
        response = await rag_retriever.generate_response(
            query=test_query,
            retrieval_k=3,
            score_threshold=0.2,
            include_sources=True,
            use_tools=True
        )
        
        print("Successfully generated response!")
        print(f"Answer length: {len(response.answer)} characters")
        print(f"Sources: {len(response.sources) if response.sources else 0}")
        print(f"Tools used: {len(response.tool_results) if hasattr(response, 'tool_results') else 0}")
        
        # Show a snippet of the response
        print(f"Response preview: {response.answer[:200]}...")
        
        return True
        
    except Exception as e:
        print(f"Error in integration test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_streamlit_integration())
    if success:
        print("\nStreamlit integration test passed! The app should work now.")
    else:
        print("\nStreamlit integration test failed. Check the errors above.")
        sys.exit(1)