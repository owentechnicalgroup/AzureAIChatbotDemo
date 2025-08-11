"""
DatabaseManager - ChromaDB interface for document management.

Handles all database operations for document storage and retrieval.
"""

import os
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import logging
import warnings

import structlog
import chromadb
from chromadb.config import Settings as ChromaSettings
from langchain_chroma import Chroma
from langchain_openai import AzureOpenAIEmbeddings

from src.config.settings import Settings


logger = structlog.get_logger(__name__)


class DatabaseManager:
    """
    ChromaDB interface for document management operations.
    
    Responsibilities:
    - ChromaDB collection management
    - Document storage and indexing
    - Chunk metadata management
    - Database health monitoring
    
    Separation of Concerns:
    - Pure database operations only
    - No AI query processing
    - No document processing logic
    """
    
    def __init__(self, settings: Settings):
        """
        Initialize database manager.
        
        Args:
            settings: Application settings
        """
        self.settings = settings
        self.logger = logger.bind(
            log_type="SYSTEM",
            component="database_manager"
        )
        
        # Disable ChromaDB telemetry
        os.environ["ANONYMIZED_TELEMETRY"] = "False"
        os.environ["CHROMA_TELEMETRY_DISABLED"] = "True"
        
        # Suppress ChromaDB logging
        logging.getLogger("chromadb").setLevel(logging.ERROR)
        logging.getLogger("chromadb.telemetry").setLevel(logging.CRITICAL)
        warnings.filterwarnings("ignore", category=UserWarning, module="chromadb")
        
        # Setup persistence directory
        self.persist_directory = Path(settings.chromadb_storage_path)
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        
        # Initialize embeddings
        self.embeddings = self._create_embeddings()
        
        # ChromaDB instance (will be initialized lazily)
        self._db: Optional[Chroma] = None
        self._collection_name = "rag_documents"
        
        self.logger.info("Database Manager initialized")
    
    def _create_embeddings(self) -> AzureOpenAIEmbeddings:
        """Create Azure OpenAI embeddings instance."""
        return AzureOpenAIEmbeddings(
            api_key=self.settings.azure_openai_api_key,
            azure_endpoint=self.settings.azure_openai_endpoint,
            azure_deployment=self.settings.azure_embedding_deployment,
            openai_api_version=self.settings.azure_openai_api_version,
            chunk_size=1000
        )
    
    async def _ensure_initialized(self):
        """Ensure ChromaDB instance is initialized."""
        if self._db is None:
            # Create ChromaDB client with persistence
            client = chromadb.PersistentClient(
                path=str(self.persist_directory),
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            # Create Chroma vector store
            self._db = Chroma(
                client=client,
                collection_name=self._collection_name,
                embedding_function=self.embeddings,
                persist_directory=str(self.persist_directory)
            )
    
    async def add_documents(self, documents: List[Any]) -> List[str]:
        """
        Add document chunks to the database.
        
        Args:
            documents: List of document chunks with content and metadata
            
        Returns:
            List of document IDs that were added
        """
        try:
            await self._ensure_initialized()
            
            if not documents:
                return []
            
            # Convert documents to LangChain format if needed
            langchain_docs = []
            for doc in documents:
                if hasattr(doc, 'page_content'):
                    # Already LangChain document
                    langchain_docs.append(doc)
                else:
                    # Convert to LangChain document
                    from langchain_core.documents import Document as LangChainDocument
                    content = str(doc)
                    metadata = getattr(doc, 'metadata', {})
                    langchain_docs.append(LangChainDocument(page_content=content, metadata=metadata))
            
            # Add to vector store
            doc_ids = self._db.add_documents(langchain_docs)
            
            self.logger.info(
                "Documents added to database",
                count=len(documents),
                collection="rag_documents"
            )
            
            return doc_ids or []
            
        except Exception as e:
            self.logger.error("Failed to add documents to database", error=str(e))
            raise
    
    async def delete_document_by_filename(self, filename: str) -> bool:
        """
        Delete all chunks for a specific filename.
        
        Args:
            filename: Name of the file to delete
            
        Returns:
            True if deletion was successful
        """
        try:
            await self._ensure_initialized()
            
            self.logger.info("Starting document deletion", filename=filename)
            
            # First, let's see what documents exist and their metadata
            all_docs = self._db.similarity_search(query="", k=1000)
            self.logger.info("Total documents in DB before deletion", count=len(all_docs))
            
            # Find documents with matching filename
            matching_docs = []
            for doc in all_docs:
                if doc.metadata.get('filename') == filename:
                    matching_docs.append(doc)
            
            self.logger.info("Found matching documents", filename=filename, count=len(matching_docs))
            
            if not matching_docs:
                self.logger.warning("No documents found for filename", filename=filename)
                # Let's also log what filenames we do have
                existing_filenames = [doc.metadata.get('filename', 'No filename') for doc in all_docs[:5]]
                self.logger.info("Existing filenames (first 5)", filenames=existing_filenames)
                return False
            
            # Extract document IDs for deletion
            doc_ids = []
            for doc in matching_docs:
                # Try to get the document ID from metadata
                if 'chunk_id' in doc.metadata:
                    doc_ids.append(doc.metadata['chunk_id'])
                elif hasattr(doc, 'id'):
                    doc_ids.append(doc.id)
            
            self.logger.info("Extracting document IDs for deletion", filename=filename, ids_found=len(doc_ids))
            
            if doc_ids:
                # Delete by IDs using ChromaDB client directly
                try:
                    # Access the underlying ChromaDB collection
                    collection = self._db._collection
                    collection.delete(ids=doc_ids)
                    self.logger.info("Successfully deleted documents from ChromaDB", filename=filename, chunks_deleted=len(doc_ids))
                except Exception as e:
                    self.logger.error("Failed to delete from ChromaDB collection", filename=filename, error=str(e))
                    # Fallback: try to delete by recreating the vector store without these documents
                    return False
            else:
                self.logger.warning("No document IDs found for deletion", filename=filename)
                return False
            
            # Verify deletion worked
            verification_docs = self._db.similarity_search(query="", k=1000)
            remaining_matching = [doc for doc in verification_docs if doc.metadata.get('filename') == filename]
            
            if remaining_matching:
                self.logger.error("Documents still exist after deletion attempt", filename=filename, remaining=len(remaining_matching))
                return False
            else:
                self.logger.info("Document deletion verified successful", filename=filename)
                return True
            
        except Exception as e:
            self.logger.error(
                "Failed to delete document from database",
                filename=filename,
                error=str(e)
            )
            return False
    
    async def get_documents_summary(self) -> List[Dict[str, Any]]:
        """
        Get summary of all documents in the database.
        
        Returns:
            List of document summaries with metadata
        """
        try:
            await self._ensure_initialized()
            
            # Get all documents using similarity search
            all_docs = self._db.similarity_search(
                query="",  # Empty query to get all
                k=1000     # Large number to get all docs
            )
            
            if not all_docs:
                return []
            
            # Group by filename
            documents = {}
            for doc in all_docs:
                metadata = doc.metadata
                filename = metadata.get('filename', 'Unknown')
                
                if filename not in documents:
                    documents[filename] = {
                        'document_id': metadata.get('document_id', f"doc_{filename}"),
                        'filename': filename,
                        'file_type': metadata.get('file_type', 'unknown'),
                        'size_bytes': metadata.get('file_size', 0),
                        'upload_timestamp': metadata.get('upload_timestamp'),
                        'chunk_count': 0,
                        'chunk_ids': []
                    }
                
                documents[filename]['chunk_count'] += 1
            
            return list(documents.values())
            
        except Exception as e:
            self.logger.error("Failed to get documents summary", error=str(e))
            return []
    
    async def get_document_count(self) -> int:
        """
        Get total number of document chunks in the database.
        
        Returns:
            Total chunk count
        """
        try:
            await self._ensure_initialized()
            # Get approximate count using similarity search
            all_docs = self._db.similarity_search(
                query="",  # Empty query
                k=10000    # Large number
            )
            return len(all_docs)
            
        except Exception as e:
            self.logger.error("Failed to get document count", error=str(e))
            return 0
    
    async def search_similar(
        self,
        query: str,
        max_results: int = 3,
        score_threshold: float = 0.2,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar documents using vector similarity.
        
        Args:
            query: Search query
            max_results: Maximum number of results
            score_threshold: Minimum similarity score
            filters: Optional metadata filters
            
        Returns:
            List of similar document chunks with scores
        """
        try:
            await self._ensure_initialized()
            
            # Perform similarity search with scores
            search_kwargs = {
                "query": query,
                "k": max_results
            }
            
            # Only add filter if it's not None and not empty
            if filters and isinstance(filters, dict) and filters:
                search_kwargs["filter"] = filters
                
            docs_with_scores = self._db.similarity_search_with_score(**search_kwargs)
            
            if not docs_with_scores:
                return []
            
            # Format results
            search_results = []
            for doc, score in docs_with_scores:
                # Convert score (lower is more similar in some implementations)
                similarity_score = 1.0 - min(score, 1.0)  # Normalize to 0-1 range
                
                # Apply score threshold
                if similarity_score < score_threshold:
                    continue
                
                result = {
                    'content': doc.page_content,
                    'metadata': doc.metadata,
                    'score': similarity_score,
                    'chunk_id': f"chunk_{hash(doc.page_content)}",
                    'source': doc.metadata.get('filename', 'Unknown')
                }
                search_results.append(result)
            
            self.logger.info(
                "Similarity search completed",
                query_length=len(query),
                results_found=len(search_results),
                max_results=max_results
            )
            
            return search_results
            
        except Exception as e:
            self.logger.error("Similarity search failed", query=query, error=str(e))
            return []
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on the database.
        
        Returns:
            Health status information
        """
        try:
            await self._ensure_initialized()
            
            # Test basic operations
            count = await self.get_document_count()
            
            return {
                "status": "healthy",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "collection_name": "rag_documents",
                "document_count": count,
                "connection": "active"
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(e),
                "connection": "failed"
            }
    
    def is_available(self) -> bool:
        """
        Check if the database is available.
        
        Returns:
            True if database is ready for operations
        """
        try:
            return (
                self.settings.chromadb_storage_path and 
                self.settings.azure_openai_api_key and
                self.settings.azure_embedding_deployment
            )
        except Exception:
            return False