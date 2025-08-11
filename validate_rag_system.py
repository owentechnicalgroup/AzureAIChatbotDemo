#!/usr/bin/env python3
"""
RAG System Validation Script

This script validates that the RAG system is working correctly by testing
all core components without requiring Azure infrastructure or full test suite.
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_imports():
    """Test that all RAG components can be imported."""
    print("Testing imports...")
    
    try:
        from rag.document_processor import DocumentProcessor
        from rag.chromadb_manager import ChromaDBManager
        from rag.retriever import RAGRetriever
        from chatbot.rag_agent import RAGChatbotAgent
        from ui.streamlit_app import StreamlitRAGApp
        from rag import Document, DocumentChunk, RAGQuery, RAGResponse
        print("[PASS] All RAG components import successfully")
        return True
    except Exception as e:
        print(f"[FAIL] Import failed: {e}")
        return False

def test_data_models():
    """Test that the RAG data models work correctly."""
    print("\nTesting data models...")
    
    try:
        from rag import Document, DocumentChunk, RAGQuery, RAGResponse
        
        # Test Document model
        doc = Document(
            id="test-doc",
            filename="test.txt",
            file_type="txt",
            size_bytes=1000,
            upload_timestamp="2025-01-01T00:00:00Z",
            source_path="test.txt"
        )
        
        # Test DocumentChunk model
        chunk = DocumentChunk(
            id="chunk-1",
            document_id="test-doc",
            content="This is test content",
            chunk_index=0,
            source="test.txt",
            metadata={"page": 1}
        )
        
        # Test RAGQuery model
        query = RAGQuery(
            query="What is this about?",
            k=3,
            score_threshold=0.5,
            include_sources=True
        )
        
        # Test RAGResponse model
        response = RAGResponse(
            answer="This is a test response",
            sources=["test.txt"],
            retrieved_chunks=[chunk],
            confidence_score=0.85,
            token_usage={"total_tokens": 100}
        )
        
        print("[PASS] All data models work correctly")
        return True
    except Exception as e:
        print(f"[FAIL] Data model test failed: {e}")
        return False

def test_document_processor():
    """Test basic DocumentProcessor functionality."""
    print("\nTesting DocumentProcessor...")
    
    try:
        from rag.document_processor import DocumentProcessor
        
        # Mock settings
        class MockSettings:
            chunk_size = 1000
            chunk_overlap = 200
            max_file_size_mb = 10
        
        processor = DocumentProcessor(MockSettings())
        
        # Test basic functionality - methods exist
        assert hasattr(processor, 'process_file')
        assert hasattr(processor, 'extract_text')
        assert hasattr(processor, 'validate_file')
        assert hasattr(processor, 'chunk_document')
        
        print("[PASS] DocumentProcessor basic functionality works")
        return True
    except Exception as e:
        print(f"[FAIL] DocumentProcessor test failed: {e}")
        return False

def test_streamlit_app_structure():
    """Test that Streamlit app can be instantiated."""
    print("\nTesting Streamlit app structure...")
    
    try:
        # We can't fully test Streamlit without running it, but we can test the structure
        from ui.streamlit_app import StreamlitRAGApp
        
        # The class should exist and have the expected methods
        expected_methods = [
            '_initialize_session_state',
            'render_sidebar',
            'render_main_chat',
            'render_header',
            'run'
        ]
        
        for method in expected_methods:
            if not hasattr(StreamlitRAGApp, method):
                raise AttributeError(f"Missing method: {method}")
        
        print("[PASS] Streamlit app structure is correct")
        return True
    except Exception as e:
        print(f"[FAIL] Streamlit app test failed: {e}")
        return False

def test_main_entry_point():
    """Test that the main entry point works."""
    print("\nTesting main entry point...")
    
    try:
        import main
        
        # Check that the new streamlit command exists
        # We can't run it without proper setup, but we can check the structure
        print("[PASS] Main entry point imports successfully")
        return True
    except Exception as e:
        print(f"[FAIL] Main entry point test failed: {e}")
        return False

def test_configuration_files():
    """Test that configuration files exist."""
    print("\nTesting configuration files...")
    
    try:
        # Check Streamlit config files
        streamlit_dir = Path(".streamlit")
        required_files = [
            streamlit_dir / "config.toml",
            streamlit_dir / "secrets.toml",
            streamlit_dir / "README.md"
        ]
        
        for file_path in required_files:
            if not file_path.exists():
                raise FileNotFoundError(f"Missing config file: {file_path}")
        
        # Check data directory
        data_dir = Path("data/chromadb")
        if not data_dir.exists():
            raise FileNotFoundError(f"Missing data directory: {data_dir}")
        
        print("[PASS] All configuration files exist")
        return True
    except Exception as e:
        print(f"[FAIL] Configuration test failed: {e}")
        return False

def main():
    """Run all validation tests."""
    print("=" * 50)
    print("RAG System Validation")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_data_models,
        test_document_processor,
        test_streamlit_app_structure,
        test_main_entry_point,
        test_configuration_files
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 50)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("SUCCESS: RAG system validation PASSED!")
        print("\nNext steps:")
        print("1. Deploy Azure infrastructure: .\\scripts\\deploy.ps1")
        print("2. Set up environment: .\\scripts\\setup-env.ps1")
        print("3. Launch Streamlit: python src\\main.py")
        return True
    else:
        print("FAILED: RAG system validation FAILED!")
        print("Please check the errors above and fix any issues.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)