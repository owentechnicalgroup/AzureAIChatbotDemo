"""
ChromaDBService - Pure ChromaDB interface layer.

Handles all ChromaDB-specific operations including:
- Client initialization and configuration
- Collection management  
- Vector operations (add, search, delete)
- Telemetry suppression and error handling
- Database health and persistence

This class contains ONLY ChromaDB-specific logic and has no knowledge of
document management business logic.
"""

import os
import asyncio
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timezone
import logging
import warnings

import structlog
import chromadb
from chromadb.config import Settings as ChromaSettings
from langchain_chroma import Chroma
from langchain_openai import AzureOpenAIEmbeddings
from langchain_core.documents import Document as LangChainDocument
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config.settings import Settings

# Global ChromaDB telemetry suppression - prevent telemetry errors
os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["CHROMA_TELEMETRY_DISABLED"] = "True"

# Suppress ChromaDB telemetry logging at module level
logging.getLogger("chromadb.telemetry").setLevel(logging.CRITICAL)
logging.getLogger("chromadb").propagate = False

# Suppress warnings related to telemetry
warnings.filterwarnings("ignore", category=UserWarning, module="chromadb")

# Monkeypatch ChromaDB telemetry to prevent capture method signature errors
try:
    import chromadb.telemetry
    # Replace the capture method with a no-op to prevent signature errors
    if hasattr(chromadb.telemetry, 'capture'):
        chromadb.telemetry.capture = lambda *args, **kwargs: None
except ImportError:
    pass  # ChromaDB telemetry module not available

logger = structlog.get_logger(__name__)


class ChromaDBService:
    """
    Pure ChromaDB interface service.
    
    Responsibilities:
    - ChromaDB client initialization and configuration
    - Collection management and persistence
    - Vector operations (CRUD)
    - Embedding integration
    - Error handling and retry logic
    - Telemetry suppression
    
    This class contains ONLY ChromaDB-specific logic.
    """
    
    def __init__(self, settings: Settings):
        """
        Initialize ChromaDB service with settings.
        
        Args:
            settings: Application settings containing ChromaDB configuration
        """
        self.settings = settings
        self.logger = logger.bind(
            log_type="SYSTEM",
            component="chromadb_service"
        )
        
        # Additional telemetry suppression
        os.environ["ANONYMIZED_TELEMETRY"] = "False"
        os.environ["CHROMA_TELEMETRY_DISABLED"] = "True"
        
        # Suppress ChromaDB internal logging
        logging.getLogger("chromadb").setLevel(logging.ERROR)
        logging.getLogger("chromadb.telemetry").setLevel(logging.CRITICAL)
        
        # Setup persistence directory
        self.persist_directory = Path(settings.chromadb_storage_path)
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        
        # Initialize Azure OpenAI embeddings
        self.embeddings = self._create_embeddings()
        
        # ChromaDB instance (initialized lazily)
        self._db: Optional[Chroma] = None
        self._collection_name = "rag_documents"
        
        self.logger.info(
            "ChromaDBService initialized",
            persist_directory=str(self.persist_directory),
            collection_name=self._collection_name
        )
    
    def _create_embeddings(self) -> AzureOpenAIEmbeddings:
        """
        Create Azure OpenAI embeddings client.
        
        Returns:
            Configured AzureOpenAIEmbeddings instance
        """
        try:
            embeddings = AzureOpenAIEmbeddings(
                azure_endpoint=self.settings.azure_openai_endpoint,
                api_key=self.settings.azure_openai_api_key,
                azure_deployment=self.settings.azure_embedding_deployment,
                api_version=self.settings.azure_openai_api_version,
                chunk_size=1000  # Optimize for batch processing
            )
            
            self.logger.info(
                "Azure OpenAI embeddings initialized",
                deployment=self.settings.azure_embedding_deployment
            )
            return embeddings
            
        except Exception as e:
            self.logger.error(
                "Failed to initialize Azure OpenAI embeddings",
                error=str(e),
                endpoint=self.settings.azure_openai_endpoint
            )
            raise
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def initialize_collection(self) -> Chroma:
        """
        Initialize ChromaDB collection with retry logic.
        
        Returns:
            Initialized Chroma instance
            
        Raises:
            Exception: If initialization fails after retries
        """
        if self._db is not None:
            return self._db
        
        try:
            # Configure ChromaDB settings with telemetry disabled
            chroma_settings = ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True,
                is_persistent=True
            )
            
            # Initialize ChromaDB client
            client = chromadb.PersistentClient(
                path=str(self.persist_directory),
                settings=chroma_settings
            )
            
            # Create LangChain Chroma instance
            self._db = Chroma(
                client=client,
                collection_name=self._collection_name,
                embedding_function=self.embeddings,
                persist_directory=str(self.persist_directory)
            )
            
            # Test the collection
            collection_count = await self._get_collection_count()
            
            self.logger.info(
                "ChromaDB collection initialized successfully",
                collection_name=self._collection_name,
                document_count=collection_count,
                persist_directory=str(self.persist_directory)
            )
            
            return self._db
            
        except Exception as e:
            self.logger.error(
                "Failed to initialize ChromaDB collection",
                error=str(e),
                collection_name=self._collection_name
            )
            self._db = None
            raise
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def add_documents(
        self,
        documents: List[LangChainDocument],
        batch_size: int = 100
    ) -> List[str]:
        """
        Add documents to ChromaDB collection with batch processing.
        
        Args:
            documents: List of LangChain documents to add
            batch_size: Number of documents to process in each batch
            
        Returns:
            List of document IDs that were added
            
        Raises:
            Exception: If adding documents fails
        """
        if not documents:
            return []
        
        db = await self.initialize_collection()
        added_ids = []
        
        try:
            # Process documents in batches
            for i in range(0, len(documents), batch_size):
                batch = documents[i:i + batch_size]
                
                # Add batch to collection
                batch_ids = db.add_documents(batch)
                added_ids.extend(batch_ids)
                
                self.logger.debug(
                    "Added document batch to ChromaDB",
                    batch_size=len(batch),
                    batch_start=i,
                    total_documents=len(documents)
                )
            
            # Force persistence
            await self.persist()
            
            self.logger.info(
                "Successfully added documents to ChromaDB",
                document_count=len(documents),
                added_ids_count=len(added_ids)
            )
            
            return added_ids
            
        except Exception as e:
            self.logger.error(
                "Failed to add documents to ChromaDB",
                error=str(e),
                document_count=len(documents)
            )
            raise
    
    async def search_similar(
        self,
        query: str,
        k: int = 4,
        score_threshold: float = 0.2,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar documents in ChromaDB.
        
        Args:
            query: Search query text
            k: Number of results to return
            score_threshold: Minimum similarity score
            filter_metadata: Optional metadata filters
            
        Returns:
            List of search results with content and metadata
        """
        db = await self.initialize_collection()
        
        try:
            # Perform similarity search
            results = db.similarity_search_with_score(
                query=query,
                k=k,
                filter=filter_metadata
            )
            
            # Filter by score threshold and format results
            filtered_results = []
            for doc, score in results:
                if score >= score_threshold:
                    filtered_results.append({
                        "content": doc.page_content,
                        "metadata": doc.metadata,
                        "score": score,
                        "source": doc.metadata.get("source", "unknown")
                    })
            
            self.logger.debug(
                "ChromaDB similarity search completed",
                query_length=len(query),
                results_found=len(results),
                results_after_filtering=len(filtered_results),
                score_threshold=score_threshold
            )
            
            return filtered_results
            
        except Exception as e:
            self.logger.error(
                "ChromaDB similarity search failed",
                error=str(e),
                query_length=len(query)
            )
            raise
    
    async def delete_documents_by_filter(
        self,
        filter_metadata: Dict[str, Any]
    ) -> bool:
        """
        Delete documents from ChromaDB collection by metadata filter.
        
        Args:
            filter_metadata: Metadata filter criteria
            
        Returns:
            True if deletion was successful
        """
        db = await self.initialize_collection()
        
        try:
            # ChromaDB doesn't have direct filter delete, so we need to:
            # 1. Search for documents matching filter
            # 2. Delete by IDs
            collection = db._collection
            
            # Get documents matching filter
            results = collection.get(where=filter_metadata)
            
            if results['ids']:
                collection.delete(ids=results['ids'])
                await self.persist()
                
                self.logger.info(
                    "Documents deleted from ChromaDB",
                    deleted_count=len(results['ids']),
                    filter=filter_metadata
                )
            else:
                self.logger.info(
                    "No documents found matching filter",
                    filter=filter_metadata
                )
            
            return True
            
        except Exception as e:
            self.logger.error(
                "Failed to delete documents from ChromaDB",
                error=str(e),
                filter=filter_metadata
            )
            return False
    
    async def delete_documents_by_ids(self, document_ids: List[str]) -> bool:
        """
        Delete documents from ChromaDB by their IDs.
        
        Args:
            document_ids: List of document IDs to delete
            
        Returns:
            True if deletion was successful
        """
        if not document_ids:
            return True
        
        db = await self.initialize_collection()
        
        try:
            collection = db._collection
            collection.delete(ids=document_ids)
            await self.persist()
            
            self.logger.info(
                "Documents deleted from ChromaDB by IDs",
                deleted_count=len(document_ids)
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                "Failed to delete documents by IDs",
                error=str(e),
                document_ids_count=len(document_ids)
            )
            return False
    
    async def get_all_documents(
        self,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get all documents from ChromaDB collection.
        
        Args:
            limit: Maximum number of documents to return
            offset: Number of documents to skip
            
        Returns:
            List of document data with metadata
        """
        db = await self.initialize_collection()
        
        try:
            collection = db._collection
            results = collection.get(
                limit=limit,
                offset=offset,
                include=['documents', 'metadatas']  # 'ids' is returned by default
            )
            
            # Format results
            documents = []
            for i, doc_id in enumerate(results['ids']):
                documents.append({
                    "id": doc_id,
                    "content": results['documents'][i] if results['documents'] else "",
                    "metadata": results['metadatas'][i] if results['metadatas'] else {}
                })
            
            self.logger.debug(
                "Retrieved documents from ChromaDB",
                document_count=len(documents),
                limit=limit,
                offset=offset
            )
            
            return documents
            
        except Exception as e:
            self.logger.error(
                "Failed to get documents from ChromaDB",
                error=str(e)
            )
            return []
    
    async def _get_collection_count(self) -> int:
        """
        Get the count of documents in the collection safely.
        
        Returns:
            Number of documents in collection
        """
        if self._db is None:
            return 0
        
        try:
            collection = self._db._collection
            return collection.count()
        except Exception as e:
            self.logger.warning(
                "Failed to get collection count",
                error=str(e)
            )
            return 0
    
    async def get_document_count(self) -> int:
        """
        Get total number of documents in ChromaDB collection.
        
        Returns:
            Document count
        """
        await self.initialize_collection()
        return await self._get_collection_count()
    
    async def persist(self) -> bool:
        """
        Force ChromaDB persistence to disk.
        
        Returns:
            True if persistence was successful
        """
        if self._db is None:
            return False
        
        try:
            # Force persistence - ChromaDB should auto-persist but this ensures it
            if hasattr(self._db, 'persist'):
                self._db.persist()
            
            self.logger.debug("ChromaDB persistence completed")
            return True
            
        except Exception as e:
            self.logger.warning(
                "ChromaDB persistence failed",
                error=str(e)
            )
            return False
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on ChromaDB service.
        
        Returns:
            Health status information
        """
        try:
            db = await self.initialize_collection()
            doc_count = await self._get_collection_count()
            
            # Test basic operations
            test_results = {
                "collection_accessible": True,
                "document_count": doc_count,
                "embeddings_configured": self.embeddings is not None,
                "persist_directory_exists": self.persist_directory.exists(),
                "persist_directory_writable": os.access(self.persist_directory, os.W_OK)
            }
            
            overall_healthy = all([
                test_results["collection_accessible"],
                test_results["embeddings_configured"],
                test_results["persist_directory_exists"],
                test_results["persist_directory_writable"]
            ])
            
            return {
                "status": "healthy" if overall_healthy else "unhealthy",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "details": test_results
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    def is_available(self) -> bool:
        """
        Check if ChromaDB service is available.
        
        Returns:
            True if service is available
        """
        return (
            self.persist_directory.exists() and
            os.access(self.persist_directory, os.W_OK) and
            self.embeddings is not None
        )
    
    def __del__(self):
        """Cleanup ChromaDB resources."""
        try:
            if self._db is not None:
                # Ensure final persistence
                if hasattr(self._db, 'persist'):
                    self._db.persist()
        except Exception:
            pass  # Ignore cleanup errors