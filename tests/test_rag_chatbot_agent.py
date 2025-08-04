"""
Unit tests for RAGChatbotAgent class.

Tests RAG chatbot functionality including document processing,
message handling, and conversation management.
"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime, timezone

import sys
sys.path.append(str(Path(__file__).parent.parent / "src"))

from chatbot.rag_agent import RAGChatbotAgent
from rag import RAGResponse, DocumentChunk, Document
from config.settings import Settings


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    settings = Mock(spec=Settings)
    settings.azure_openai_endpoint = "https://test.openai.azure.com"
    settings.azure_openai_api_key = "test-key"
    settings.chunk_size = 1000
    settings.chunk_overlap = 200
    settings.max_file_size_mb = 10
    return settings


@pytest.fixture
def mock_document():
    """Mock document for testing."""
    return Document(
        id="test-doc-id",
        filename="test.txt",
        file_type="txt",
        size_bytes=1000,
        upload_timestamp=datetime.now(timezone.utc).isoformat(),
        source_path="test.txt"
    )


@pytest.fixture
def mock_chunks():
    """Mock document chunks for testing."""
    return [
        DocumentChunk(
            id="chunk-1",
            document_id="test-doc-id",
            content="This is test content about artificial intelligence.",
            chunk_index=0,
            source="test.txt",
            metadata={}
        )
    ]


@pytest.fixture
def rag_agent(mock_settings):
    """Create RAGChatbotAgent instance for testing."""
    with patch('chatbot.rag_agent.DocumentProcessor') as mock_doc_proc, \
         patch('chatbot.rag_agent.ChromaDBManager') as mock_chromadb, \
         patch('chatbot.rag_agent.RAGRetriever') as mock_retriever:
        
        agent = RAGChatbotAgent(mock_settings)
        agent.document_processor = mock_doc_proc.return_value
        agent.chromadb_manager = mock_chromadb.return_value
        agent.rag_retriever = mock_retriever.return_value
        return agent


class TestRAGChatbotAgent:
    """Test cases for RAGChatbotAgent class."""
    
    def test_initialization(self, mock_settings):
        """Test RAGChatbotAgent initialization."""
        with patch('chatbot.rag_agent.DocumentProcessor'), \
             patch('chatbot.rag_agent.ChromaDBManager'), \
             patch('chatbot.rag_agent.RAGRetriever'):
            
            agent = RAGChatbotAgent(mock_settings)
            
            assert agent.settings == mock_settings
            assert agent.conversation_id is not None
            assert agent._message_count == 0
            assert agent._total_response_time == 0.0
            assert agent._is_active is True
            assert agent._last_error is None
    
    def test_initialization_error(self, mock_settings):
        """Test RAGChatbotAgent initialization error handling."""
        with patch('chatbot.rag_agent.DocumentProcessor', side_effect=Exception("Init failed")):
            
            with pytest.raises(Exception, match="Init failed"):
                RAGChatbotAgent(mock_settings)
    
    @pytest.mark.asyncio
    async def test_process_documents_success(self, rag_agent, mock_document, mock_chunks):
        """Test successful document processing."""
        # Arrange
        file_data = [("test.txt", b"Test file content")]
        progress_callback = Mock()
        
        rag_agent.document_processor.process_file.return_value = (mock_document, mock_chunks)
        rag_agent.chromadb_manager.add_documents.return_value = None
        
        # Act
        result = await rag_agent.process_documents(file_data, progress_callback)
        
        # Assert
        assert result["success"] is True
        assert result["processed_count"] == 1
        assert result["total_chunks"] == 1
        assert result["failed_count"] == 0
        assert result["processing_time"] > 0
        
        rag_agent.document_processor.process_file.assert_called_once()
        rag_agent.chromadb_manager.add_documents.assert_called_once()
        
        # Check progress callback was called
        assert progress_callback.call_count >= 2  # Start and end
    
    @pytest.mark.asyncio
    async def test_process_documents_partial_failure(self, rag_agent, mock_document, mock_chunks):
        """Test document processing with some failures."""
        # Arrange
        file_data = [
            ("success.txt", b"Good content"),
            ("failure.txt", b"Bad content")
        ]
        
        # First file succeeds, second fails
        def mock_process_file(file_path, file_content, source_name):
            if "failure" in str(file_path):
                raise Exception("Processing failed")
            return (mock_document, mock_chunks)
        
        rag_agent.document_processor.process_file.side_effect = mock_process_file
        rag_agent.chromadb_manager.add_documents.return_value = None
        
        # Act
        result = await rag_agent.process_documents(file_data)
        
        # Assert
        assert result["success"] is True
        assert result["processed_count"] == 1
        assert result["failed_count"] == 1
        assert len(result["failed_files"]) == 1
        assert result["failed_files"][0]["filename"] == "failure.txt"
        assert "Processing failed" in result["failed_files"][0]["error"]
    
    @pytest.mark.asyncio
    async def test_process_documents_complete_failure(self, rag_agent):
        """Test document processing complete failure."""
        # Arrange
        file_data = [("test.txt", b"Content")]
        rag_agent.document_processor.process_file.side_effect = Exception("Critical error")
        
        # Act
        result = await rag_agent.process_documents(file_data)
        
        # Assert
        assert result["success"] is False
        assert "error" in result
        assert "Critical error" in result["error"]
        assert result["processed_count"] == 0
        assert result["failed_count"] == 1
    
    @pytest.mark.asyncio
    async def test_process_rag_message_success(self, rag_agent):
        """Test successful RAG message processing."""
        # Arrange
        user_message = "What is artificial intelligence?"
        
        mock_rag_response = RAGResponse(
            answer="AI is a field of computer science focused on creating intelligent machines.",
            sources=["ai_guide.txt"],
            retrieved_chunks=[],
            confidence_score=0.85,
            token_usage={"total_tokens": 100}
        )
        
        rag_agent.rag_retriever.generate_rag_response.return_value = mock_rag_response
        
        with patch('chatbot.rag_agent.ConversationLogger'):
            # Act
            response = await rag_agent.process_rag_message(user_message)
            
            # Assert
            assert response["success"] is True
            assert response["answer"] == mock_rag_response.answer
            assert response["sources"] == mock_rag_response.sources
            assert response["confidence_score"] == mock_rag_response.confidence_score
            assert response["token_usage"] == mock_rag_response.token_usage
            assert response["conversation_id"] == rag_agent.conversation_id
            assert "timestamp" in response
            assert "response_time" in response
    
    @pytest.mark.asyncio
    async def test_process_rag_message_empty_message(self, rag_agent):
        """Test processing empty message."""
        # Arrange
        user_message = "   "  # Whitespace only
        
        with patch('chatbot.rag_agent.ConversationLogger'):
            # Act
            response = await rag_agent.process_rag_message(user_message)
            
            # Assert
            assert response["success"] is False
            assert "Empty message received" in response["answer"]
            assert response["confidence_score"] == 0.0
    
    @pytest.mark.asyncio
    async def test_process_rag_message_rag_error(self, rag_agent):
        """Test RAG message processing with retriever error."""
        # Arrange
        user_message = "What is AI?"
        rag_agent.rag_retriever.generate_rag_response.side_effect = Exception("RAG failed")
        
        with patch('chatbot.rag_agent.ConversationLogger'):
            # Act
            response = await rag_agent.process_rag_message(user_message)
            
            # Assert
            assert response["success"] is False
            assert "trouble accessing the document database" in response["answer"]
            assert response["error"] == "RAG failed"
            assert response["confidence_score"] == 0.0
    
    @pytest.mark.asyncio
    async def test_process_rag_message_azure_error(self, rag_agent):
        """Test RAG message processing with Azure OpenAI error."""
        # Arrange
        user_message = "What is AI?"
        rag_agent.rag_retriever.generate_rag_response.side_effect = Exception("Azure API error")
        
        with patch('chatbot.rag_agent.ConversationLogger'):
            # Act
            response = await rag_agent.process_rag_message(user_message)
            
            # Assert
            assert response["success"] is False
            assert "trouble connecting to the AI service" in response["answer"]
            assert response["error"] == "Azure API error"
    
    @pytest.mark.asyncio
    async def test_process_rag_message_custom_parameters(self, rag_agent):
        """Test RAG message processing with custom parameters."""
        # Arrange
        user_message = "What is AI?"
        retrieval_k = 5
        score_threshold = 0.8
        include_sources = False
        
        mock_rag_response = RAGResponse(
            answer="AI answer",
            sources=[],
            retrieved_chunks=[],
            confidence_score=0.9,
            token_usage={}
        )
        
        rag_agent.rag_retriever.generate_rag_response.return_value = mock_rag_response
        
        with patch('chatbot.rag_agent.ConversationLogger'):
            # Act
            response = await rag_agent.process_rag_message(
                user_message, 
                retrieval_k=retrieval_k,
                score_threshold=score_threshold,
                include_sources=include_sources
            )
            
            # Assert
            assert response["success"] is True
            # Verify RAG query was called with correct parameters
            call_args = rag_agent.rag_retriever.generate_rag_response.call_args[0][0]
            assert call_args.k == retrieval_k
            assert call_args.score_threshold == score_threshold
            assert call_args.include_sources == include_sources
    
    def test_handle_processing_error_chromadb(self, rag_agent):
        """Test error handling for ChromaDB errors."""
        # Arrange
        error = Exception("ChromaDB connection failed")
        user_message = "Test message"
        response_time = 1.5
        message_id = "test-id"
        
        with patch('chatbot.rag_agent.log_conversation_event'):
            # Act
            response = rag_agent._handle_processing_error(error, user_message, response_time, message_id)
            
            # Assert
            assert response["success"] is False
            assert "trouble accessing the document database" in response["answer"]
            assert response["error"] == "ChromaDB connection failed"
            assert response["response_time"] == response_time
    
    def test_handle_processing_error_azure(self, rag_agent):
        """Test error handling for Azure OpenAI errors."""
        # Arrange
        error = Exception("Azure OpenAI rate limit exceeded")
        user_message = "Test message"
        response_time = 2.0
        message_id = "test-id"
        
        with patch('chatbot.rag_agent.log_conversation_event'):
            # Act
            response = rag_agent._handle_processing_error(error, user_message, response_time, message_id)
            
            # Assert
            assert response["success"] is False
            assert "trouble connecting to the AI service" in response["answer"]
            assert response["error"] == "Azure OpenAI rate limit exceeded"
    
    def test_handle_processing_error_generic(self, rag_agent):
        """Test error handling for generic errors."""
        # Arrange
        error = Exception("Unknown error")
        user_message = "Test message"
        response_time = 1.0
        message_id = "test-id"
        
        with patch('chatbot.rag_agent.log_conversation_event'):
            # Act
            response = rag_agent._handle_processing_error(error, user_message, response_time, message_id)
            
            # Assert
            assert response["success"] is False
            assert "unexpected issue" in response["answer"]
            assert response["error"] == "Unknown error"
    
    def test_update_performance_metrics(self, rag_agent):
        """Test performance metrics update."""
        # Arrange
        response_time = 1.5
        token_usage = {"total_tokens": 100}
        
        with patch('chatbot.rag_agent.log_performance_metrics') as mock_log:
            # Act
            rag_agent._update_performance_metrics(response_time, token_usage)
            
            # Assert
            assert rag_agent._message_count == 1
            assert rag_agent._total_response_time == response_time
            mock_log.assert_called_once()
            
            # Check logged metrics
            call_args = mock_log.call_args
            assert call_args[1]["message_count"] == 1
            assert call_args[1]["average_response_time"] == response_time
            assert call_args[1]["total_tokens"] == 100
    
    @pytest.mark.asyncio
    async def test_get_document_list_success(self, rag_agent):
        """Test successful document list retrieval."""
        # Arrange
        expected_docs = [
            {"id": "doc-1", "filename": "test1.txt", "file_type": "txt"},
            {"id": "doc-2", "filename": "test2.pdf", "file_type": "pdf"}
        ]
        rag_agent.chromadb_manager.list_documents.return_value = expected_docs
        
        # Act
        documents = await rag_agent.get_document_list()
        
        # Assert
        assert documents == expected_docs
        rag_agent.chromadb_manager.list_documents.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_document_list_error(self, rag_agent):
        """Test document list retrieval error handling."""
        # Arrange
        rag_agent.chromadb_manager.list_documents.side_effect = Exception("Database error")
        
        # Act
        documents = await rag_agent.get_document_list()
        
        # Assert
        assert documents == []
    
    @pytest.mark.asyncio
    async def test_delete_document_success(self, rag_agent):
        """Test successful document deletion."""
        # Arrange
        document_id = "doc-1"
        rag_agent.chromadb_manager.delete_documents.return_value = True
        
        # Act
        result = await rag_agent.delete_document(document_id)
        
        # Assert
        assert result is True
        rag_agent.chromadb_manager.delete_documents.assert_called_once_with([document_id])
    
    @pytest.mark.asyncio
    async def test_delete_document_failure(self, rag_agent):
        """Test document deletion failure."""
        # Arrange
        document_id = "doc-1"
        rag_agent.chromadb_manager.delete_documents.side_effect = Exception("Delete failed")
        
        # Act
        result = await rag_agent.delete_document(document_id)
        
        # Assert
        assert result is False
    
    @pytest.mark.asyncio
    async def test_get_conversation_statistics_success(self, rag_agent):
        """Test successful conversation statistics retrieval."""
        # Arrange
        rag_agent._message_count = 5
        rag_agent._total_response_time = 10.0
        rag_agent.chromadb_manager.get_document_count.return_value = 3
        
        # Act
        stats = await rag_agent.get_conversation_statistics()
        
        # Assert
        assert stats["conversation_id"] == rag_agent.conversation_id
        assert stats["message_count"] == 5
        assert stats["average_response_time"] == 2.0  # 10.0 / 5
        assert stats["total_response_time"] == 10.0
        assert stats["documents_in_store"] == 3
        assert stats["is_active"] is True
        assert stats["last_error"] is None
        assert "session_duration" in stats
        assert "timestamp" in stats
    
    @pytest.mark.asyncio
    async def test_get_conversation_statistics_error(self, rag_agent):
        """Test conversation statistics error handling."""
        # Arrange
        rag_agent.chromadb_manager.get_document_count.side_effect = Exception("Stats error")
        
        # Act
        stats = await rag_agent.get_conversation_statistics()
        
        # Assert
        assert "error" in stats
        assert "Stats error" in stats["error"]
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, rag_agent):
        """Test successful health check."""
        # Arrange
        rag_health = {"status": "healthy"}
        rag_agent.rag_retriever.health_check.return_value = rag_health
        
        # Act
        health = await rag_agent.health_check()
        
        # Assert
        assert health["status"] == "healthy"
        assert health["rag_retriever"] == rag_health
        assert "agent" in health
        assert health["agent"]["is_active"] is True
        assert health["agent"]["message_count"] == 0
        assert health["conversation_id"] == rag_agent.conversation_id
    
    @pytest.mark.asyncio
    async def test_health_check_degraded(self, rag_agent):
        """Test health check with degraded status."""
        # Arrange
        rag_health = {"status": "degraded"}
        rag_agent.rag_retriever.health_check.return_value = rag_health
        
        # Act
        health = await rag_agent.health_check()
        
        # Assert
        assert health["status"] == "degraded"
    
    @pytest.mark.asyncio
    async def test_health_check_error(self, rag_agent):
        """Test health check error handling."""
        # Arrange
        rag_agent.rag_retriever.health_check.side_effect = Exception("Health check failed")
        
        # Act
        health = await rag_agent.health_check()
        
        # Assert
        assert health["status"] == "unhealthy"
        assert "error" in health
        assert "Health check failed" in health["error"]
    
    def test_shutdown(self, rag_agent):
        """Test agent shutdown."""
        # Act
        rag_agent.shutdown()
        
        # Assert
        assert rag_agent._is_active is False
    
    def test_repr(self, rag_agent):
        """Test string representation."""
        # Arrange
        rag_agent._message_count = 3
        
        # Act
        repr_str = repr(rag_agent)
        
        # Assert
        assert "RAGChatbotAgent" in repr_str
        assert rag_agent.conversation_id[:8] in repr_str
        assert "messages=3" in repr_str
        assert "active=True" in repr_str