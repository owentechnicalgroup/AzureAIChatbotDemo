"""
Unit tests for ChromaDBManager class.

Tests vector storage functionality including document storage,
retrieval, and ChromaDB operations.
"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime, timezone

import sys
sys.path.append(str(Path(__file__).parent.parent / "src"))

from rag.chromadb_manager import ChromaDBManager
from rag import Document, DocumentChunk
from config.settings import Settings


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    settings = Mock(spec=Settings)
    settings.chromadb_storage_path = "./data/chromadb"
    settings.azure_openai_endpoint = "https://test.openai.azure.com"
    settings.azure_openai_api_key = "test-key"
    settings.azure_openai_api_version = "2024-02-01"
    settings.azure_openai_embedding_deployment = "text-embedding-ada-002"
    settings.request_timeout = 30
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
            content="This is the first chunk of text content.",
            chunk_index=0,
            source="test.txt",
            metadata={"page": 1}
        ),
        DocumentChunk(
            id="chunk-2",
            document_id="test-doc-id",
            content="This is the second chunk of text content.",
            chunk_index=1,
            source="test.txt",
            metadata={"page": 1}
        )
    ]


@pytest.fixture
def chromadb_manager(mock_settings):
    """Create ChromaDBManager instance for testing."""
    with patch('rag.chromadb_manager.AzureOpenAIEmbeddings'):
        return ChromaDBManager(mock_settings)


class TestChromaDBManager:
    """Test cases for ChromaDBManager class."""
    
    def test_initialization(self, mock_settings):
        """Test ChromaDBManager initialization."""
        with patch('rag.chromadb_manager.AzureOpenAIEmbeddings') as mock_embeddings:
            manager = ChromaDBManager(mock_settings)
            
            assert manager.settings == mock_settings
            assert manager.storage_path == Path("./data/chromadb")
            assert manager.collection_name == "documents"
            assert manager.logger is not None
            mock_embeddings.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_initialize_db_success(self, chromadb_manager):
        """Test successful database initialization."""
        with patch('chromadb.PersistentClient') as mock_client:
            mock_collection = Mock()
            mock_client.return_value.get_or_create_collection.return_value = mock_collection
            
            db = await chromadb_manager.initialize_db()
            
            assert chromadb_manager.chroma_client is not None
            assert chromadb_manager.collection == mock_collection
            assert db is not None
            mock_client.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_add_documents_success(self, chromadb_manager, mock_document, mock_chunks):
        """Test successful document addition."""
        # Mock the database initialization and embedding generation
        with patch.object(chromadb_manager, 'initialize_db', new_callable=AsyncMock) as mock_init_db, \
             patch.object(chromadb_manager, '_generate_embeddings', new_callable=AsyncMock) as mock_embeddings, \
             patch.object(chromadb_manager, 'collection') as mock_collection:
            
            mock_embeddings.return_value = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
            
            # Act
            result = await chromadb_manager.add_documents(mock_chunks, mock_document)
            
            # Assert
            assert result is True
            mock_init_db.assert_called_once()
            mock_embeddings.assert_called_once()
            mock_collection.add.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_search_success(self, chromadb_manager):
        """Test successful document search."""
        # Arrange
        query = "test query"
        k = 3
        score_threshold = 0.5
        
        mock_results = {
            'documents': [["chunk content 1", "chunk content 2"]],
            'metadatas': [[{"source": "test.txt", "chunk_index": 0}, {"source": "test.txt", "chunk_index": 1}]],
            'distances': [[0.3, 0.4]],
            'ids': [["chunk-1", "chunk-2"]]
        }
        
        with patch.object(chromadb_manager, 'initialize_db', new_callable=AsyncMock), \
             patch.object(chromadb_manager, '_generate_embeddings', new_callable=AsyncMock) as mock_embeddings, \
             patch.object(chromadb_manager, 'collection') as mock_collection:
            
            mock_embeddings.return_value = [[0.1, 0.2, 0.3]]
            mock_collection.query.return_value = mock_results
            
            # Act
            results = await chromadb_manager.search(query, k, score_threshold)
            
            # Assert
            assert len(results) == 2
            chunk, score = results[0]
            assert isinstance(chunk, DocumentChunk)
            assert chunk.content == "chunk content 1"
            assert chunk.source == "test.txt"
            assert score == 0.7  # 1 - distance
    
    @pytest.mark.asyncio
    async def test_search_no_results(self, chromadb_manager):
        """Test search with no results."""
        # Arrange
        query = "test query"
        mock_results = {
            'documents': [[]],
            'metadatas': [[]],
            'distances': [[]],
            'ids': [[]]
        }
        
        with patch.object(chromadb_manager, 'initialize_db', new_callable=AsyncMock), \
             patch.object(chromadb_manager, '_generate_embeddings', new_callable=AsyncMock), \
             patch.object(chromadb_manager, 'collection') as mock_collection:
            
            mock_collection.query.return_value = mock_results
            
            # Act
            results = await chromadb_manager.search(query)
            
            # Assert
            assert len(results) == 0
    
    @pytest.mark.asyncio
    async def test_search_with_score_filtering(self, chromadb_manager):
        """Test search with score threshold filtering."""
        # Arrange
        query = "test query"
        score_threshold = 0.8  # High threshold
        
        mock_results = {
            'documents': [["chunk content 1", "chunk content 2"]],
            'metadatas': [[{"source": "test.txt", "chunk_index": 0}, {"source": "test.txt", "chunk_index": 1}]],
            'distances': [[0.1, 0.5]],  # First has high similarity (0.9), second low (0.5)
            'ids': [["chunk-1", "chunk-2"]]
        }
        
        with patch.object(chromadb_manager, 'initialize_db', new_callable=AsyncMock), \
             patch.object(chromadb_manager, '_generate_embeddings', new_callable=AsyncMock), \
             patch.object(chromadb_manager, 'collection') as mock_collection:
            
            mock_collection.query.return_value = mock_results
            
            # Act
            results = await chromadb_manager.search(query, score_threshold=score_threshold)
            
            # Assert
            assert len(results) == 1  # Only first chunk meets threshold
            chunk, score = results[0]
            assert chunk.content == "chunk content 1"
            assert score == 0.9
    
    @pytest.mark.asyncio
    async def test_delete_documents_success(self, chromadb_manager):
        """Test successful document deletion."""
        # Arrange
        document_ids = ["doc-1", "doc-2"]
        
        with patch.object(chromadb_manager, 'initialize_db', new_callable=AsyncMock), \
             patch.object(chromadb_manager, 'collection') as mock_collection:
            
            mock_collection.delete.return_value = None
            
            # Act
            result = await chromadb_manager.delete_documents(document_ids)
            
            # Assert
            assert result is True
            mock_collection.delete.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_list_documents_success(self, chromadb_manager):
        """Test successful document listing."""
        # Arrange
        mock_results = {
            'metadatas': [
                {"document_id": "doc-1", "filename": "test1.txt", "file_type": "txt"},
                {"document_id": "doc-2", "filename": "test2.pdf", "file_type": "pdf"}
            ]
        }
        
        with patch.object(chromadb_manager, 'initialize_db', new_callable=AsyncMock), \
             patch.object(chromadb_manager, 'collection') as mock_collection:
            
            mock_collection.get.return_value = mock_results
            
            # Act
            documents = await chromadb_manager.list_documents()
            
            # Assert
            assert len(documents) == 2
            assert documents[0]["filename"] == "test1.txt"
            assert documents[1]["filename"] == "test2.pdf"
    
    @pytest.mark.asyncio
    async def test_get_document_count_success(self, chromadb_manager):
        """Test successful document count retrieval."""
        # Arrange
        expected_count = 5
        
        with patch.object(chromadb_manager, 'initialize_db', new_callable=AsyncMock), \
             patch.object(chromadb_manager, 'collection') as mock_collection:
            
            mock_collection.count.return_value = expected_count
            
            # Act
            count = await chromadb_manager.get_document_count()
            
            # Assert
            assert count == expected_count
    
    @pytest.mark.asyncio
    async def test_generate_embeddings_success(self, chromadb_manager):
        """Test successful embedding generation."""
        # Arrange
        texts = ["text 1", "text 2"]
        expected_embeddings = [[0.1, 0.2], [0.3, 0.4]]
        
        with patch.object(chromadb_manager.embeddings, 'aembed_documents', new_callable=AsyncMock) as mock_embed:
            mock_embed.return_value = expected_embeddings
            
            # Act
            embeddings = await chromadb_manager._generate_embeddings(texts)
            
            # Assert
            assert embeddings == expected_embeddings
            mock_embed.assert_called_once_with(texts)
    
    @pytest.mark.asyncio
    async def test_generate_embeddings_with_retry(self, chromadb_manager):
        """Test embedding generation with retry on failure."""
        # Arrange
        texts = ["text 1"]
        expected_embeddings = [[0.1, 0.2]]
        
        with patch.object(chromadb_manager.embeddings, 'aembed_documents', new_callable=AsyncMock) as mock_embed:
            # First call fails, second succeeds
            mock_embed.side_effect = [Exception("Rate limit"), expected_embeddings]
            
            with patch('asyncio.sleep', new_callable=AsyncMock):
                # Act
                embeddings = await chromadb_manager._generate_embeddings(texts)
                
                # Assert
                assert embeddings == expected_embeddings
                assert mock_embed.call_count == 2
    
    @pytest.mark.asyncio
    async def test_generate_embeddings_max_retries_exceeded(self, chromadb_manager):
        """Test embedding generation failure after max retries."""
        # Arrange
        texts = ["text 1"]
        
        with patch.object(chromadb_manager.embeddings, 'aembed_documents', new_callable=AsyncMock) as mock_embed:
            mock_embed.side_effect = Exception("Persistent error")
            
            with patch('asyncio.sleep', new_callable=AsyncMock):
                # Act & Assert
                with pytest.raises(Exception, match="Persistent error"):
                    await chromadb_manager._generate_embeddings(texts)
                
                assert mock_embed.call_count == 3  # Initial + 2 retries
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, chromadb_manager):
        """Test successful health check."""
        # Arrange
        with patch.object(chromadb_manager, 'initialize_db', new_callable=AsyncMock), \
             patch.object(chromadb_manager, 'collection') as mock_collection:
            
            mock_collection.count.return_value = 10
            
            # Act
            health = await chromadb_manager.health_check()
            
            # Assert
            assert health["status"] == "healthy"
            assert health["document_count"] == 10
            assert "storage_path" in health
            assert "collection_name" in health
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self, chromadb_manager):
        """Test health check failure."""
        # Arrange
        with patch.object(chromadb_manager, 'initialize_db', new_callable=AsyncMock) as mock_init:
            mock_init.side_effect = Exception("Database connection failed")
            
            # Act
            health = await chromadb_manager.health_check()
            
            # Assert
            assert health["status"] == "unhealthy"
            assert "error" in health
            assert "Database connection failed" in health["error"]
    
    def test_convert_distance_to_similarity_score(self, chromadb_manager):
        """Test distance to similarity score conversion."""
        # Test various distances
        assert chromadb_manager._convert_distance_to_similarity_score(0.0) == 1.0
        assert chromadb_manager._convert_distance_to_similarity_score(0.5) == 0.5
        assert chromadb_manager._convert_distance_to_similarity_score(1.0) == 0.0
        assert chromadb_manager._convert_distance_to_similarity_score(2.0) == 0.0  # Clamped to 0
    
    @pytest.mark.asyncio
    async def test_add_documents_empty_chunks(self, chromadb_manager, mock_document):
        """Test adding documents with empty chunks list."""
        # Act & Assert
        with pytest.raises(ValueError, match="No chunks provided"):
            await chromadb_manager.add_documents([], mock_document)
    
    @pytest.mark.asyncio
    async def test_search_empty_query(self, chromadb_manager):
        """Test search with empty query."""
        # Act & Assert
        with pytest.raises(ValueError, match="Empty query"):
            await chromadb_manager.search("")
    
    @pytest.mark.asyncio
    async def test_database_connection_error(self, chromadb_manager):
        """Test database connection error handling."""
        # Arrange
        with patch('chromadb.PersistentClient', side_effect=Exception("Connection failed")):
            # Act & Assert
            with pytest.raises(Exception, match="Connection failed"):
                await chromadb_manager.initialize_db()