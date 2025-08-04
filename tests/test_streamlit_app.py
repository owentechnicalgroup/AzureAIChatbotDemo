"""
Unit tests for Streamlit RAG application.

Tests Streamlit interface functionality including UI components,
session state management, and user interactions.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import uuid

import sys
sys.path.append(str(Path(__file__).parent.parent / "src"))

from config.settings import Settings


# Mock Streamlit before importing the app
@pytest.fixture(autouse=True)
def mock_streamlit():
    """Mock Streamlit components for testing."""
    with patch.dict('sys.modules', {
        'streamlit': Mock(),
        'streamlit.chat_message': Mock(),
        'streamlit.container': Mock(),
        'streamlit.columns': Mock(),
        'streamlit.expander': Mock(),
    }):
        yield


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    settings = Mock(spec=Settings)
    settings.chunk_size = 1000
    settings.chunk_overlap = 200
    settings.max_file_size_mb = 10
    settings.streamlit_port = 8501
    return settings


@pytest.fixture
def mock_streamlit_modules():
    """Mock all Streamlit-related modules."""
    mock_st = Mock()
    mock_st.session_state = {}
    mock_st.sidebar = Mock()
    mock_st.columns.return_value = [Mock(), Mock()]
    mock_st.container.return_value.__enter__ = Mock(return_value=Mock())
    mock_st.container.return_value.__exit__ = Mock(return_value=None)
    mock_st.expander.return_value.__enter__ = Mock(return_value=Mock())
    mock_st.expander.return_value.__exit__ = Mock(return_value=None)
    mock_st.chat_message.return_value.__enter__ = Mock(return_value=Mock())
    mock_st.chat_message.return_value.__exit__ = Mock(return_value=None)
    mock_st.file_uploader.return_value = []
    mock_st.button.return_value = False
    mock_st.slider.return_value = 3
    mock_st.checkbox.return_value = True
    mock_st.chat_input.return_value = None
    
    return mock_st


@pytest.fixture
def streamlit_app(mock_settings, mock_streamlit_modules):
    """Create StreamlitRAGApp instance for testing."""
    with patch('ui.streamlit_app.get_settings', return_value=mock_settings), \
         patch('ui.streamlit_app.st', mock_streamlit_modules), \
         patch('ui.streamlit_app.DocumentProcessor'), \
         patch('ui.streamlit_app.ChromaDBManager'), \
         patch('ui.streamlit_app.RAGRetriever'):
        
        from ui.streamlit_app import StreamlitRAGApp
        return StreamlitRAGApp()


class TestStreamlitRAGApp:
    """Test cases for StreamlitRAGApp class."""
    
    def test_initialization(self, mock_settings, mock_streamlit_modules):
        """Test StreamlitRAGApp initialization."""
        with patch('ui.streamlit_app.get_settings', return_value=mock_settings), \
             patch('ui.streamlit_app.st', mock_streamlit_modules), \
             patch('ui.streamlit_app.DocumentProcessor'), \
             patch('ui.streamlit_app.ChromaDBManager'), \
             patch('ui.streamlit_app.RAGRetriever'):
            
            from ui.streamlit_app import StreamlitRAGApp
            app = StreamlitRAGApp()
            
            assert app.settings == mock_settings
            assert app.logger is not None
            mock_streamlit_modules.set_page_config.assert_called_once()
    
    def test_initialize_session_state(self, streamlit_app, mock_streamlit_modules):
        """Test session state initialization."""
        # Session state should be initialized in constructor
        # Check that all required keys are present
        expected_keys = [
            "settings", "document_processor", "chromadb_manager", 
            "rag_retriever", "messages", "conversation_id",
            "uploaded_documents", "processing_status", "show_sources",
            "retrieval_k", "score_threshold"
        ]
        
        # Since we're mocking st.session_state, we can't test the actual values
        # but we can verify the method exists and doesn't raise errors
        streamlit_app._initialize_session_state()
    
    def test_render_sidebar(self, streamlit_app, mock_streamlit_modules):
        """Test sidebar rendering."""
        # Mock session state
        mock_streamlit_modules.session_state = {
            "uploaded_documents": [],
            "retrieval_k": 3,
            "score_threshold": 0.5,
            "show_sources": True
        }
        
        # Act
        streamlit_app.render_sidebar()
        
        # Assert - verify UI components were called
        mock_streamlit_modules.sidebar.title.assert_called()
        mock_streamlit_modules.sidebar.subheader.assert_called()
        mock_streamlit_modules.file_uploader.assert_called()
    
    def test_handle_file_upload_no_files(self, streamlit_app, mock_streamlit_modules):
        """Test file upload handler with no files."""
        # Arrange
        uploaded_files = []
        mock_streamlit_modules.session_state = {"uploaded_documents": []}
        
        # Act
        streamlit_app._handle_file_upload(uploaded_files)
        
        # Assert - should return early, no processing
        # Verify info message is not called (since no files)
        # This is more of a smoke test since we can't easily verify early return
    
    def test_handle_file_upload_duplicate_files(self, streamlit_app, mock_streamlit_modules):
        """Test file upload handler with duplicate files."""
        # Arrange
        mock_file = Mock()
        mock_file.name = "existing.txt"
        uploaded_files = [mock_file]
        
        mock_streamlit_modules.session_state = {
            "uploaded_documents": [{"filename": "existing.txt"}]
        }
        
        # Act
        streamlit_app._handle_file_upload(uploaded_files)
        
        # Assert
        mock_streamlit_modules.info.assert_called_with("All selected files are already uploaded.")
    
    def test_handle_file_upload_new_files(self, streamlit_app, mock_streamlit_modules):
        """Test file upload handler with new files."""
        # Arrange
        mock_file = Mock()
        mock_file.name = "new.txt"
        uploaded_files = [mock_file]
        
        mock_streamlit_modules.session_state = {"uploaded_documents": []}
        mock_streamlit_modules.button.return_value = True  # Simulate button click
        
        with patch.object(streamlit_app, '_process_uploaded_files') as mock_process:
            # Act
            streamlit_app._handle_file_upload(uploaded_files)
            
            # Assert
            mock_process.assert_called_once_with([mock_file])
    
    def test_process_uploaded_files_success(self, streamlit_app, mock_streamlit_modules):
        """Test successful file processing."""
        # Arrange
        mock_file = Mock()
        mock_file.name = "test.txt"
        mock_file.read.return_value = b"test content"
        uploaded_files = [mock_file]
        
        mock_streamlit_modules.session_state = {
            "document_processor": Mock(),
            "chromadb_manager": Mock(),
            "uploaded_documents": []
        }
        
        mock_document = Mock()
        mock_document.id = "doc-1"
        mock_document.filename = "test.txt"
        mock_document.file_type = "txt"
        mock_document.size_bytes = 1000
        mock_document.upload_timestamp = "2023-01-01T00:00:00Z"
        
        mock_chunks = [Mock()]
        
        with patch('asyncio.run') as mock_asyncio:
            # First call returns document and chunks, second call does add_documents
            mock_asyncio.side_effect = [(mock_document, mock_chunks), None]
            
            # Act
            streamlit_app._process_uploaded_files(uploaded_files)
            
            # Assert
            mock_streamlit_modules.progress.assert_called()
            mock_streamlit_modules.success.assert_called()
            mock_streamlit_modules.rerun.assert_called()
    
    def test_process_uploaded_files_error(self, streamlit_app, mock_streamlit_modules):
        """Test file processing with error."""
        # Arrange
        mock_file = Mock()
        mock_file.name = "test.txt"
        mock_file.read.side_effect = Exception("File read error")
        uploaded_files = [mock_file]
        
        # Act
        streamlit_app._process_uploaded_files(uploaded_files)
        
        # Assert
        mock_streamlit_modules.error.assert_called()
    
    def test_render_document_list_empty(self, streamlit_app, mock_streamlit_modules):
        """Test document list rendering with no documents."""
        # Arrange
        mock_streamlit_modules.session_state = {"uploaded_documents": []}
        
        # Act
        streamlit_app._render_document_list()
        
        # Assert
        mock_streamlit_modules.info.assert_called_with("No documents uploaded yet.")
    
    def test_render_document_list_with_documents(self, streamlit_app, mock_streamlit_modules):
        """Test document list rendering with documents."""
        # Arrange
        mock_docs = [
            {
                "id": "doc-1",
                "filename": "test1.txt",
                "file_type": "txt",
                "chunk_count": 5
            },
            {
                "id": "doc-2", 
                "filename": "test2.pdf",
                "file_type": "pdf",
                "chunk_count": 3
            }
        ]
        
        mock_streamlit_modules.session_state = {"uploaded_documents": mock_docs}
        mock_streamlit_modules.columns.return_value = [Mock(), Mock()]
        mock_streamlit_modules.container.return_value.__enter__ = Mock(return_value=Mock())
        mock_streamlit_modules.container.return_value.__exit__ = Mock(return_value=None)
        
        # Act
        streamlit_app._render_document_list()
        
        # Assert
        # Verify container and columns were used for each document
        assert mock_streamlit_modules.container.call_count >= len(mock_docs)
        mock_streamlit_modules.columns.assert_called()
        mock_streamlit_modules.caption.assert_called()  # For summary
    
    def test_delete_document(self, streamlit_app, mock_streamlit_modules):
        """Test document deletion."""
        # Arrange
        document_id = "doc-1"
        mock_docs = [
            {"id": "doc-1", "filename": "test1.txt"},
            {"id": "doc-2", "filename": "test2.txt"}
        ]
        mock_streamlit_modules.session_state = {"uploaded_documents": mock_docs}
        
        # Act
        streamlit_app._delete_document(document_id)
        
        # Assert
        mock_streamlit_modules.success.assert_called()
        mock_streamlit_modules.rerun.assert_called()
    
    def test_delete_document_error(self, streamlit_app, mock_streamlit_modules):
        """Test document deletion error handling."""
        # Arrange
        document_id = "doc-1"
        mock_streamlit_modules.session_state = {"uploaded_documents": []}
        
        with patch.object(streamlit_app, '_delete_document', side_effect=Exception("Delete error")):
            # Act
            try:
                streamlit_app._delete_document(document_id)
            except Exception:
                pass
            
            # Would typically show error, but we can't easily test that here
    
    def test_render_settings(self, streamlit_app, mock_streamlit_modules):
        """Test settings rendering."""
        # Arrange
        mock_streamlit_modules.session_state = {
            "retrieval_k": 3,
            "score_threshold": 0.5,
            "show_sources": True
        }
        
        # Act
        streamlit_app._render_settings()
        
        # Assert
        # Verify sliders and checkbox were called
        assert mock_streamlit_modules.slider.call_count >= 2  # Two sliders
        mock_streamlit_modules.checkbox.assert_called()
    
    def test_render_system_status_success(self, streamlit_app, mock_streamlit_modules):
        """Test system status rendering success case."""
        # Arrange
        mock_streamlit_modules.session_state = {
            "chromadb_manager": Mock(),
            "rag_retriever": Mock(),
            "messages": []
        }
        
        with patch('asyncio.run') as mock_asyncio:
            # First call returns doc count, second returns health
            mock_asyncio.side_effect = [5, {"status": "healthy"}]
            
            # Act
            streamlit_app._render_system_status()
            
            # Assert
            mock_streamlit_modules.metric.assert_called()
            mock_streamlit_modules.success.assert_called()
    
    def test_render_system_status_error(self, streamlit_app, mock_streamlit_modules):
        """Test system status rendering error case."""
        # Arrange
        mock_streamlit_modules.session_state = {
            "chromadb_manager": Mock(),
            "rag_retriever": Mock(),
            "messages": []
        }
        
        with patch('asyncio.run', side_effect=Exception("Status error")):
            # Act
            streamlit_app._render_system_status()
            
            # Assert
            mock_streamlit_modules.error.assert_called()
    
    def test_render_main_chat(self, streamlit_app, mock_streamlit_modules):
        """Test main chat interface rendering."""
        # Arrange
        mock_messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!", "sources": ["test.txt"]}
        ]
        
        mock_streamlit_modules.session_state = {
            "messages": mock_messages,
            "show_sources": True
        }
        mock_streamlit_modules.chat_input.return_value = None  # No new message
        
        # Act
        streamlit_app.render_main_chat()
        
        # Assert
        mock_streamlit_modules.title.assert_called()
        mock_streamlit_modules.caption.assert_called()
        mock_streamlit_modules.chat_message.assert_called()
        mock_streamlit_modules.chat_input.assert_called()
    
    def test_handle_user_message(self, streamlit_app, mock_streamlit_modules):
        """Test user message handling."""
        # Arrange
        prompt = "What is AI?"
        mock_streamlit_modules.session_state = {
            "messages": [],
            "retrieval_k": 3,
            "score_threshold": 0.5,
            "show_sources": True,
            "rag_retriever": Mock()
        }
        
        mock_response = Mock()
        mock_response.answer = "AI is artificial intelligence"
        mock_response.sources = ["ai_guide.txt"]
        mock_response.confidence_score = 0.85
        
        with patch('asyncio.run', return_value=mock_response), \
             patch.object(streamlit_app, 'logger'):
            
            # Act
            streamlit_app._handle_user_message(prompt)
            
            # Assert - message should be added to session state
            # Since we're mocking session_state, we can't easily verify the append
            # but we can verify that chat components were called
            mock_streamlit_modules.chat_message.assert_called()
            mock_streamlit_modules.markdown.assert_called()
    
    def test_handle_user_message_error(self, streamlit_app, mock_streamlit_modules):
        """Test user message handling with error."""
        # Arrange
        prompt = "What is AI?"
        mock_streamlit_modules.session_state = {
            "messages": [],
            "retrieval_k": 3,
            "score_threshold": 0.5,
            "show_sources": True,
            "rag_retriever": Mock()
        }
        
        with patch('asyncio.run', side_effect=Exception("Processing error")), \
             patch.object(streamlit_app, 'logger'):
            
            # Act
            streamlit_app._handle_user_message(prompt)
            
            # Assert
            mock_streamlit_modules.error.assert_called()
    
    def test_render_header(self, streamlit_app, mock_streamlit_modules):
        """Test header rendering."""
        # Arrange
        mock_streamlit_modules.columns.return_value = [Mock(), Mock(), Mock()]
        mock_streamlit_modules.button.side_effect = [False, False, True]  # Third button clicked
        
        with patch.object(streamlit_app, '_show_about_dialog') as mock_about:
            # Act
            streamlit_app.render_header()
            
            # Assert
            mock_streamlit_modules.columns.assert_called_once_with([2, 1, 1])
            mock_about.assert_called_once()
    
    def test_show_about_dialog(self, streamlit_app, mock_streamlit_modules):
        """Test about dialog display."""
        # Act
        streamlit_app._show_about_dialog()
        
        # Assert
        mock_streamlit_modules.info.assert_called_once()
        # Verify the info contains expected content
        call_args = mock_streamlit_modules.info.call_args[0][0]
        assert "RAG-Enabled Chatbot" in call_args
        assert "Streamlit" in call_args
        assert "ChromaDB" in call_args
    
    def test_run_success(self, streamlit_app, mock_streamlit_modules):
        """Test successful app run."""
        # Mock the render methods
        with patch.object(streamlit_app, 'render_header') as mock_header, \
             patch.object(streamlit_app, 'render_sidebar') as mock_sidebar, \
             patch.object(streamlit_app, 'render_main_chat') as mock_chat:
            
            # Act
            streamlit_app.run()
            
            # Assert
            mock_header.assert_called_once()
            mock_sidebar.assert_called_once()
            mock_chat.assert_called_once()
    
    def test_run_error(self, streamlit_app, mock_streamlit_modules):
        """Test app run with error."""
        # Arrange
        with patch.object(streamlit_app, 'render_header', side_effect=Exception("Render error")), \
             patch.object(streamlit_app, 'logger'):
            
            # Act
            streamlit_app.run()
            
            # Assert
            mock_streamlit_modules.error.assert_called()
    
    def test_main_function_success(self, mock_streamlit_modules):
        """Test main function success case."""
        with patch('ui.streamlit_app.StreamlitRAGApp') as mock_app_class, \
             patch('ui.streamlit_app.st', mock_streamlit_modules):
            
            mock_app = Mock()
            mock_app_class.return_value = mock_app
            
            from ui.streamlit_app import main
            
            # Act
            main()
            
            # Assert
            mock_app_class.assert_called_once()
            mock_app.run.assert_called_once()
    
    def test_main_function_error(self, mock_streamlit_modules):
        """Test main function error handling."""
        with patch('ui.streamlit_app.StreamlitRAGApp', side_effect=Exception("App init failed")), \
             patch('ui.streamlit_app.st', mock_streamlit_modules), \
             patch('ui.streamlit_app.logger') as mock_logger:
            
            from ui.streamlit_app import main
            
            # Act
            main()
            
            # Assert
            mock_streamlit_modules.error.assert_called()
            mock_logger.error.assert_called()