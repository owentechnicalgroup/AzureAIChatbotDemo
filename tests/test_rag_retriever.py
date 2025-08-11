"""
Unit tests for RAGRetriever class.

Tests RAG retrieval functionality including document search,
response generation, and Azure OpenAI integration.
"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime, timezone

import sys
sys.path.append(str(Path(__file__).parent.parent / "src"))

from rag.retriever import RAGRetriever
from rag.chromadb_manager import ChromaDBManager
from rag import RAGQuery, RAGResponse, DocumentChunk
from config.settings import Settings
from services.azure_client import AzureOpenAIClient


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    settings = Mock(spec=Settings)
    settings.azure_openai_endpoint = "https://test.openai.azure.com"
    settings.azure_openai_api_key = "test-key"
    settings.azure_openai_api_version = "2024-02-01"
    settings.azure_openai_deployment = "gpt-4"
    settings.azure_openai_embedding_deployment = "text-embedding-ada-002"
    settings.temperature = 0.7
    settings.max_tokens = 1000
    settings.request_timeout = 30
    return settings


@pytest.fixture
def mock_chromadb_manager():
    """Mock ChromaDBManager for testing."""
    return Mock(spec=ChromaDBManager)


@pytest.fixture
def mock_azure_client():
    """Mock AzureOpenAIClient for testing."""
    return Mock(spec=AzureOpenAIClient)


@pytest.fixture
def mock_chunks():
    """Mock document chunks for testing."""
    return [
        DocumentChunk(
            id="chunk-1",
            document_id="doc-1",
            content="This is the first relevant chunk about artificial intelligence.",
            chunk_index=0,
            source="ai_guide.txt",
            metadata={"page": 1}
        ),
        DocumentChunk(
            id="chunk-2",
            document_id="doc-1",
            content="This is the second relevant chunk about machine learning.",
            chunk_index=1,
            source="ai_guide.txt",
            metadata={"page": 2}
        )
    ]


@pytest.fixture
def rag_retriever(mock_settings, mock_chromadb_manager):
    """Create RAGRetriever instance for testing."""
    with patch('rag.retriever.AzureOpenAIClient'):
        retriever = RAGRetriever(mock_settings, mock_chromadb_manager)
        retriever.chromadb_manager = mock_chromadb_manager
        return retriever


class TestRAGRetriever:
    """Test cases for RAGRetriever class."""
    
    def test_initialization(self, mock_settings, mock_chromadb_manager):
        """Test RAGRetriever initialization."""
        with patch('rag.retriever.AzureOpenAIClient') as mock_client:
            retriever = RAGRetriever(mock_settings, mock_chromadb_manager)
            
            assert retriever.settings == mock_settings
            assert retriever.chromadb_manager == mock_chromadb_manager
            assert retriever.azure_client is not None
            assert retriever.system_prompt is not None
            assert "helpful AI assistant" in retriever.system_prompt
            mock_client.assert_called_once_with(mock_settings)
    
    def test_create_system_prompt(self, rag_retriever):
        """Test system prompt creation."""
        prompt = rag_retriever._create_system_prompt()
        
        assert "helpful AI assistant" in prompt
        assert "provided document context" in prompt
        assert "cite your sources" in prompt
        assert "don't know the answer" in prompt
    
    @pytest.mark.asyncio
    async def test_retrieve_relevant_chunks_success(self, rag_retriever, mock_chunks):
        """Test successful chunk retrieval."""
        # Arrange
        query = "What is artificial intelligence?"
        k = 3
        score_threshold = 0.5
        
        rag_retriever.chromadb_manager.search.return_value = [
            (mock_chunks[0], 0.8),
            (mock_chunks[1], 0.7)
        ]
        
        # Act
        results = await rag_retriever.retrieve_relevant_chunks(query, k, score_threshold)
        
        # Assert
        assert len(results) == 2
        assert results[0][0] == mock_chunks[0]
        assert results[0][1] == 0.8
        assert results[1][0] == mock_chunks[1]
        assert results[1][1] == 0.7
        rag_retriever.chromadb_manager.search.assert_called_once_with(
            query=query, k=k, score_threshold=score_threshold, filter_metadata=None
        )
    
    @pytest.mark.asyncio
    async def test_retrieve_relevant_chunks_no_results(self, rag_retriever):
        """Test chunk retrieval with no results."""
        # Arrange
        query = "What is quantum computing?"
        rag_retriever.chromadb_manager.search.return_value = []
        
        # Act
        results = await rag_retriever.retrieve_relevant_chunks(query)
        
        # Assert
        assert len(results) == 0
    
    @pytest.mark.asyncio
    async def test_retrieve_relevant_chunks_error(self, rag_retriever):
        """Test chunk retrieval error handling."""
        # Arrange
        query = "What is AI?"
        rag_retriever.chromadb_manager.search.side_effect = Exception("Database error")
        
        # Act & Assert
        with pytest.raises(Exception, match="Database error"):
            await rag_retriever.retrieve_relevant_chunks(query)
    
    @pytest.mark.asyncio
    async def test_generate_rag_response_success(self, rag_retriever, mock_chunks):
        """Test successful RAG response generation."""
        # Arrange
        rag_query = RAGQuery(
            query="What is artificial intelligence?",
            k=3,
            score_threshold=0.5,
            include_sources=True
        )
        
        rag_retriever.chromadb_manager.search.return_value = [
            (mock_chunks[0], 0.8),
            (mock_chunks[1], 0.7)
        ]
        
        mock_response_data = {
            'content': 'Artificial intelligence is a field of computer science that focuses on creating intelligent machines.',
            'metadata': {
                'token_usage': {
                    'prompt_tokens': 100,
                    'completion_tokens': 50,
                    'total_tokens': 150
                }
            }
        }
        
        with patch.object(rag_retriever, '_generate_response_with_context', new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = (mock_response_data['content'], mock_response_data['metadata']['token_usage'])
            
            # Act
            response = await rag_retriever.generate_rag_response(rag_query)
            
            # Assert
            assert isinstance(response, RAGResponse)
            assert response.answer == mock_response_data['content']
            assert len(response.sources) == 1  # Unique sources
            assert "ai_guide.txt" in response.sources
            assert len(response.retrieved_chunks) == 2
            assert response.confidence_score == 0.75  # Average of 0.8 and 0.7
            assert response.token_usage == mock_response_data['metadata']['token_usage']
    
    @pytest.mark.asyncio
    async def test_generate_rag_response_no_chunks(self, rag_retriever):
        """Test RAG response generation with no relevant chunks."""
        # Arrange
        rag_query = RAGQuery(
            query="What is quantum computing?",
            k=3,
            score_threshold=0.5
        )
        
        rag_retriever.chromadb_manager.search.return_value = []
        
        # Act
        response = await rag_retriever.generate_rag_response(rag_query)
        
        # Assert
        assert isinstance(response, RAGResponse)
        assert "don't have any relevant documents" in response.answer
        assert len(response.sources) == 0
        assert len(response.retrieved_chunks) == 0
        assert response.confidence_score == 0.0
    
    @pytest.mark.asyncio
    async def test_generate_rag_response_without_sources(self, rag_retriever, mock_chunks):
        """Test RAG response generation without including sources."""
        # Arrange
        rag_query = RAGQuery(
            query="What is AI?",
            k=3,
            score_threshold=0.5,
            include_sources=False
        )
        
        rag_retriever.chromadb_manager.search.return_value = [(mock_chunks[0], 0.8)]
        
        with patch.object(rag_retriever, '_generate_response_with_context', new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = ("AI is artificial intelligence", {})
            
            # Act
            response = await rag_retriever.generate_rag_response(rag_query)
            
            # Assert
            assert len(response.sources) == 0  # Sources not included
            assert len(response.retrieved_chunks) == 1
    
    @pytest.mark.asyncio
    async def test_generate_rag_response_error(self, rag_retriever):
        """Test RAG response generation error handling."""
        # Arrange
        rag_query = RAGQuery(query="What is AI?")
        rag_retriever.chromadb_manager.search.side_effect = Exception("Search failed")
        
        # Act
        response = await rag_retriever.generate_rag_response(rag_query)
        
        # Assert
        assert isinstance(response, RAGResponse)
        assert "encountered an error" in response.answer
        assert "Search failed" in response.answer
        assert response.confidence_score == 0.0
    
    @pytest.mark.asyncio
    async def test_generate_response_with_context_success(self, rag_retriever):
        """Test response generation with context."""
        # Arrange
        query = "What is AI?"
        context = "Source: ai_guide.txt\nContent: AI is artificial intelligence."
        
        mock_response_data = {
            'content': 'According to ai_guide.txt, AI is artificial intelligence.',
            'metadata': {
                'token_usage': {
                    'prompt_tokens': 50,
                    'completion_tokens': 25,
                    'total_tokens': 75
                }
            }
        }
        
        rag_retriever.azure_client.generate_response_async.return_value = mock_response_data
        
        # Act
        response_text, token_usage = await rag_retriever._generate_response_with_context(query, context)
        
        # Assert
        assert response_text == mock_response_data['content']
        assert token_usage == mock_response_data['metadata']['token_usage']
        rag_retriever.azure_client.generate_response_async.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_response_with_context_error(self, rag_retriever):
        """Test response generation error handling."""
        # Arrange
        query = "What is AI?"
        context = "Some context"
        rag_retriever.azure_client.generate_response_async.side_effect = Exception("API error")
        
        # Act & Assert
        with pytest.raises(Exception, match="API error"):
            await rag_retriever._generate_response_with_context(query, context)
    
    @pytest.mark.asyncio
    async def test_get_llm_success(self, rag_retriever):
        """Test LLM instance creation."""
        with patch('rag.retriever.AzureChatOpenAI') as mock_llm:
            mock_llm_instance = Mock()
            mock_llm.return_value = mock_llm_instance
            
            # Act
            llm = await rag_retriever._get_llm()
            
            # Assert
            assert llm == mock_llm_instance
            mock_llm.assert_called_once_with(
                azure_endpoint=rag_retriever.settings.azure_openai_endpoint,
                api_key=rag_retriever.settings.azure_openai_api_key,
                api_version=rag_retriever.settings.azure_openai_api_version,
                azure_deployment=rag_retriever.settings.azure_openai_deployment,
                temperature=rag_retriever.settings.temperature,
                max_tokens=rag_retriever.settings.max_tokens,
                timeout=rag_retriever.settings.request_timeout,
                streaming=False
            )
    
    @pytest.mark.asyncio
    async def test_get_llm_error(self, rag_retriever):
        """Test LLM instance creation error."""
        with patch('rag.retriever.AzureChatOpenAI', side_effect=Exception("LLM init failed")):
            # Act & Assert
            with pytest.raises(Exception, match="LLM init failed"):
                await rag_retriever._get_llm()
    
    @pytest.mark.asyncio
    async def test_create_qa_chain_success(self, rag_retriever):
        """Test QA chain creation."""
        # Arrange
        mock_db = Mock()
        mock_retriever = Mock()
        mock_db.as_retriever.return_value = mock_retriever
        
        rag_retriever.chromadb_manager.initialize_db.return_value = mock_db
        
        with patch.object(rag_retriever, '_get_llm', new_callable=AsyncMock) as mock_get_llm, \
             patch('rag.retriever.RetrievalQAWithSourcesChain') as mock_chain:
            
            mock_llm = Mock()
            mock_get_llm.return_value = mock_llm
            mock_chain_instance = Mock()
            mock_chain.from_chain_type.return_value = mock_chain_instance
            
            # Act
            qa_chain = await rag_retriever.create_qa_chain()
            
            # Assert
            assert qa_chain == mock_chain_instance
            mock_chain.from_chain_type.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_answer_with_sources_success(self, rag_retriever):
        """Test legacy QA chain answer method."""
        # Arrange
        question = "What is AI?"
        expected_result = {
            "answer": "AI is artificial intelligence",
            "sources": "ai_guide.txt"
        }
        
        mock_qa_chain = Mock()
        mock_qa_chain.return_value = expected_result
        
        with patch.object(rag_retriever, 'create_qa_chain', new_callable=AsyncMock) as mock_create_chain, \
             patch('asyncio.get_event_loop') as mock_loop:
            
            mock_create_chain.return_value = mock_qa_chain
            mock_executor = Mock()
            mock_loop.return_value.run_in_executor.return_value = expected_result
            
            # Act
            result = await rag_retriever.answer_with_sources(question)
            
            # Assert
            assert result == expected_result
    
    @pytest.mark.asyncio
    async def test_answer_with_sources_error(self, rag_retriever):
        """Test legacy QA chain answer error handling."""
        # Arrange
        question = "What is AI?"
        
        with patch.object(rag_retriever, 'create_qa_chain', new_callable=AsyncMock) as mock_create_chain:
            mock_create_chain.side_effect = Exception("Chain creation failed")
            
            # Act & Assert
            with pytest.raises(Exception, match="Chain creation failed"):
                await rag_retriever.answer_with_sources(question)
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, rag_retriever):
        """Test successful health check."""
        # Arrange
        chromadb_health = {"status": "healthy"}
        azure_health = {"status": "healthy"}
        
        rag_retriever.chromadb_manager.health_check.return_value = chromadb_health
        rag_retriever.azure_client.health_check.return_value = azure_health
        
        # Act
        health = await rag_retriever.health_check()
        
        # Assert
        assert health["status"] == "healthy"
        assert health["chromadb"] == chromadb_health
        assert health["azure_openai"] == azure_health
        assert "timestamp" in health
    
    @pytest.mark.asyncio
    async def test_health_check_degraded(self, rag_retriever):
        """Test health check with degraded status."""
        # Arrange
        chromadb_health = {"status": "unhealthy"}
        azure_health = {"status": "healthy"}
        
        rag_retriever.chromadb_manager.health_check.return_value = chromadb_health
        rag_retriever.azure_client.health_check.return_value = azure_health
        
        # Act
        health = await rag_retriever.health_check()
        
        # Assert
        assert health["status"] == "degraded"
        assert health["chromadb"] == chromadb_health
        assert health["azure_openai"] == azure_health
    
    @pytest.mark.asyncio
    async def test_health_check_error(self, rag_retriever):
        """Test health check error handling."""
        # Arrange
        rag_retriever.chromadb_manager.health_check.side_effect = Exception("Health check failed")
        
        # Act
        health = await rag_retriever.health_check()
        
        # Assert
        assert health["status"] == "unhealthy"
        assert "error" in health
        assert "Health check failed" in health["error"]
    
    def test_rag_query_validation(self):
        """Test RAGQuery model validation."""
        # Valid query
        query = RAGQuery(query="What is AI?", k=5, score_threshold=0.7)
        assert query.query == "What is AI?"
        assert query.k == 5
        assert query.score_threshold == 0.7
        assert query.include_sources is True  # Default value
        
        # Test with custom values
        query2 = RAGQuery(query="Test", k=3, score_threshold=0.5, include_sources=False)
        assert query2.include_sources is False
    
    def test_rag_response_creation(self, mock_chunks):
        """Test RAGResponse model creation."""
        response = RAGResponse(
            answer="This is the answer",
            sources=["source1.txt", "source2.pdf"],
            retrieved_chunks=mock_chunks,
            confidence_score=0.85,
            token_usage={"total_tokens": 100}
        )
        
        assert response.answer == "This is the answer"
        assert len(response.sources) == 2
        assert len(response.retrieved_chunks) == 2
        assert response.confidence_score == 0.85
        assert response.token_usage["total_tokens"] == 100