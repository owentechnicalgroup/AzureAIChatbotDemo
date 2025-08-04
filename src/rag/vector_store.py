"""
ChromaDB vector store manager for RAG implementation.
Handles vector storage, document persistence, and similarity search.
"""

import os
import asyncio
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timezone

import structlog
from langchain_chroma import Chroma
from langchain_openai import AzureOpenAIEmbeddings
from langchain_core.documents import Document as LangChainDocument
from tenacity import retry, stop_after_attempt, wait_exponential
import chromadb
from chromadb.config import Settings as ChromaSettings

from config.settings import Settings
from .import DocumentChunk, Document

logger = structlog.get_logger(__name__)


class ChromaDBManager:
    """
    Manages ChromaDB vector store for document embeddings and retrieval.
    
    Features:
    - Local persistence with ChromaDB
    - Azure OpenAI embeddings integration
    - Document metadata management
    - Similarity search and retrieval
    - Error handling and retry logic
    """
    
    def __init__(self, settings: Settings):
        """
        Initialize ChromaDB manager with settings.
        
        Args:
            settings: Application settings containing ChromaDB and Azure OpenAI configuration
        """
        self.settings = settings
        self.logger = logger.bind(
            log_type="SYSTEM",
            component="chromadb_manager"
        )
        
        # Disable ChromaDB telemetry to avoid telemetry capture errors
        os.environ["ANONYMIZED_TELEMETRY"] = "False"
        
        # Setup persistence directory
        self.persist_directory = Path(settings.chromadb_storage_path)
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        
        self.logger.info(
            "ChromaDB persist directory created",
            persist_directory=str(self.persist_directory)
        )
        
        # Initialize Azure OpenAI embeddings
        self.embeddings = self._create_embeddings()
        
        # ChromaDB instance (will be initialized lazily)
        self._db: Optional[Chroma] = None
        self._collection_name = "rag_documents"
        
        self.logger.info(
            "ChromaDBManager initialized",
            persist_directory=str(self.persist_directory),
            collection_name=self._collection_name
        )
    
    def _create_embeddings(self) -> AzureOpenAIEmbeddings:
        """Create Azure OpenAI embeddings instance."""
        try:
            # Use configurable embedding deployment name or fallback to default
            embedding_deployment = (
                self.settings.azure_embedding_deployment or 
                "text-embedding-ada-002"
            )
            
            embeddings = AzureOpenAIEmbeddings(
                azure_endpoint=self.settings.azure_openai_endpoint,
                api_key=self.settings.azure_openai_api_key,
                api_version=self.settings.azure_openai_api_version,
                azure_deployment=embedding_deployment,
                chunk_size=16,  # Batch size for embedding requests
                max_retries=3,
                timeout=30.0
            )
            
            self.logger.info(
                "Azure OpenAI embeddings initialized",
                api_version=self.settings.azure_openai_api_version,
                endpoint=self.settings.azure_openai_endpoint,
                embedding_deployment=embedding_deployment
            )
            
            return embeddings
            
        except Exception as e:
            self.logger.error(
                "Failed to initialize Azure OpenAI embeddings",
                error=str(e),
                error_type=type(e).__name__
            )
            raise
    
    async def initialize_db(self) -> Chroma:
        """
        Initialize or load existing ChromaDB instance.
        
        Returns:
            ChromaDB instance
        """
        if self._db is not None:
            return self._db
        
        try:
            self.logger.info("Initializing ChromaDB instance")
            
            # Create ChromaDB client with telemetry disabled
            chroma_client = chromadb.PersistentClient(
                path=str(self.persist_directory),
                settings=ChromaSettings(
                    anonymized_telemetry=False,  # Disable telemetry to avoid issues
                    allow_reset=True
                )
            )
            
            # Create ChromaDB instance with persistence
            self._db = Chroma(
                collection_name=self._collection_name,
                embedding_function=self.embeddings,
                client=chroma_client
            )
            
            # Check if collection exists and get basic stats
            try:
                collection_count = self._db._collection.count()
                self.logger.info(
                    "ChromaDB initialized successfully",
                    collection_name=self._collection_name,
                    existing_documents=collection_count
                )
            except Exception as stats_error:
                self.logger.warning(
                    "Could not retrieve collection stats",
                    error=str(stats_error)
                )
            
            return self._db
            
        except Exception as e:
            self.logger.error(
                "Failed to initialize ChromaDB",
                error=str(e),
                error_type=type(e).__name__
            )
            raise
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    async def add_documents(
        self, 
        chunks: List[DocumentChunk], 
        document_metadata: Optional[Document] = None
    ) -> List[str]:
        """
        Add document chunks to ChromaDB with retry logic.
        
        Args:
            chunks: List of DocumentChunk objects to add
            document_metadata: Optional document metadata
            
        Returns:
            List of document IDs added to the database
        """
        if not chunks:
            self.logger.warning("No chunks provided for adding to ChromaDB")
            return []
        
        try:
            # Ensure DB is initialized
            db = await self.initialize_db()
            
            self.logger.info(
                "Adding documents to ChromaDB",
                chunk_count=len(chunks),
                document_id=document_metadata.id if document_metadata else None
            )
            
            # Convert DocumentChunk objects to LangChain documents
            langchain_docs = []
            doc_ids = []
            
            for chunk in chunks:
                # Prepare metadata
                metadata = {
                    "source": chunk.source,
                    "chunk_index": chunk.chunk_index,
                    "chunk_id": chunk.id,
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
                
                # Add page number if available
                if chunk.page_number is not None:
                    metadata["page_number"] = chunk.page_number
                
                # Add document metadata if provided
                if document_metadata:
                    metadata.update({
                        "document_id": document_metadata.id,
                        "filename": document_metadata.filename,
                        "file_type": document_metadata.file_type,
                        "upload_timestamp": document_metadata.upload_timestamp.isoformat()
                    })
                
                # Add chunk metadata
                metadata.update(chunk.metadata)
                
                # Create LangChain document
                langchain_doc = LangChainDocument(
                    page_content=chunk.content,
                    metadata=metadata
                )
                langchain_docs.append(langchain_doc)
                doc_ids.append(chunk.id)
            
            # Add documents to ChromaDB
            # Run the synchronous method in a thread to avoid blocking
            added_ids = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: db.add_documents(documents=langchain_docs, ids=doc_ids)
            )
            
            self.logger.info(
                "Documents added to ChromaDB successfully",
                added_count=len(added_ids) if added_ids else len(doc_ids),
                document_id=document_metadata.id if document_metadata else None
            )
            
            return added_ids or doc_ids
            
        except Exception as e:
            self.logger.error(
                "Failed to add documents to ChromaDB",
                chunk_count=len(chunks),
                error=str(e),
                error_type=type(e).__name__
            )
            raise
    
    async def search(
        self, 
        query: str, 
        k: int = 3, 
        score_threshold: float = 0.2,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[DocumentChunk, float]]:
        """
        Search for similar documents in ChromaDB.
        
        Args:
            query: Search query text
            k: Number of results to return
            score_threshold: Minimum similarity score (0-1)
            filter_metadata: Optional metadata filters
            
        Returns:
            List of (DocumentChunk, similarity_score) tuples
        """
        try:
            # Ensure DB is initialized
            db = await self.initialize_db()
            
            self.logger.debug(
                "Searching ChromaDB",
                query_length=len(query),
                k=k,
                score_threshold=score_threshold,
                filter_metadata=filter_metadata
            )
            
            # Perform similarity search with scores
            search_kwargs = {"k": k}
            if filter_metadata:
                search_kwargs["filter"] = filter_metadata
            
            # Run the synchronous search in a thread
            results = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: db.similarity_search_with_score(query, **search_kwargs)
            )
            
            # Filter by score threshold and convert to DocumentChunk objects
            filtered_results = []
            for doc, score in results:
                if score >= score_threshold:
                    # Convert LangChain document back to DocumentChunk
                    chunk = DocumentChunk(
                        id=doc.metadata.get("chunk_id", f"unknown_{len(filtered_results)}"),
                        content=doc.page_content,
                        source=doc.metadata.get("source", "unknown"),
                        page_number=doc.metadata.get("page_number"),
                        chunk_index=doc.metadata.get("chunk_index", 0),
                        metadata=doc.metadata
                    )
                    filtered_results.append((chunk, score))
            
            self.logger.info(
                "ChromaDB search completed",
                query_length=len(query),
                total_results=len(results),
                filtered_results=len(filtered_results),
                score_threshold=score_threshold
            )
            
            return filtered_results
            
        except Exception as e:
            self.logger.error(
                "ChromaDB search failed",
                query=query[:100],  # Truncate query for logging
                error=str(e),
                error_type=type(e).__name__
            )
            raise
    
    async def delete_documents(self, document_ids: List[str]) -> bool:
        """
        Delete documents from ChromaDB by their IDs.
        
        Args:
            document_ids: List of document IDs to delete
            
        Returns:
            True if deletion was successful
        """
        try:
            if not document_ids:
                self.logger.warning("No document IDs provided for deletion")
                return True
            
            # Ensure DB is initialized
            db = await self.initialize_db()
            
            self.logger.info(
                "Deleting documents from ChromaDB",
                document_count=len(document_ids)
            )
            
            # Delete documents
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: db.delete(ids=document_ids)
            )
            
            self.logger.info(
                "Documents deleted from ChromaDB successfully",
                deleted_count=len(document_ids)
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                "Failed to delete documents from ChromaDB",
                document_ids=document_ids,
                error=str(e)
            )
            raise
    
    async def delete_document_by_filename(self, filename: str) -> bool:
        """
        Delete all chunks from a specific document by filename.
        
        Args:
            filename: Name of the file to delete
            
        Returns:
            True if deletion was successful
        """
        try:
            self.logger.info(f"Deleting document by filename: {filename}")
            
            # Get all documents for this filename
            documents = await self.list_documents(filter_metadata={"filename": filename})
            
            if not documents:
                self.logger.warning(f"No documents found with filename: {filename}")
                return True
            
            # Extract document IDs
            doc_ids = [doc["id"] for doc in documents]
            
            self.logger.info(
                f"Found {len(doc_ids)} chunks for document {filename}",
                chunk_ids=doc_ids
            )
            
            # Delete all chunks
            success = await self.delete_documents(doc_ids)
            
            if success:
                self.logger.info(f"Successfully deleted document: {filename}")
            
            return success
            
        except Exception as e:
            self.logger.error(
                f"Failed to delete document by filename: {filename}",
                error=str(e)
            )
            raise
    
    async def get_documents_summary(self) -> List[Dict[str, Any]]:
        """
        Get a summary of all documents in the database grouped by filename.
        
        Returns:
            List of document summaries with metadata
        """
        try:
            # Get all documents
            all_documents = await self.list_documents()
            
            # Group by filename
            doc_summary = {}
            
            for doc in all_documents:
                metadata = doc.get('metadata', {})
                filename = metadata.get('filename', 'Unknown')
                
                if filename not in doc_summary:
                    doc_summary[filename] = {
                        'filename': filename,
                        'file_type': metadata.get('file_type', 'unknown'),
                        'chunk_count': 0,
                        'size_bytes': metadata.get('file_size', 0),
                        'upload_timestamp': metadata.get('upload_timestamp', 'Unknown'),
                        'document_id': metadata.get('document_id', 'Unknown'),
                        'chunk_ids': []
                    }
                
                doc_summary[filename]['chunk_count'] += 1
                doc_summary[filename]['chunk_ids'].append(doc['id'])
                
                # Use the largest size found (should be the same for all chunks)
                if 'file_size' in metadata:
                    doc_summary[filename]['size_bytes'] = max(
                        doc_summary[filename]['size_bytes'], 
                        metadata.get('file_size', 0)
                    )
            
            # Convert to list and sort by upload timestamp
            summary_list = list(doc_summary.values())
            summary_list.sort(key=lambda x: x['upload_timestamp'], reverse=True)
            
            self.logger.info(
                "Generated documents summary",
                unique_documents=len(summary_list),
                total_chunks=sum(doc['chunk_count'] for doc in summary_list)
            )
            
            return summary_list
            
        except Exception as e:
            self.logger.error(
                "Failed to get documents summary",
                error=str(e)
            )
            raise
    
    async def get_document_count(self) -> int:
        """
        Get the total number of documents in the collection.
        
        Returns:
            Number of documents in the collection
        """
        try:
            db = await self.initialize_db()
            
            count = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: db._collection.count()
            )
            
            self.logger.debug("Retrieved document count", count=count)
            return count
            
        except Exception as e:
            self.logger.error(
                "Failed to get document count",
                error=str(e)
            )
            raise
    
    async def list_documents(
        self, 
        limit: Optional[int] = None,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        List documents with their metadata.
        
        Args:
            limit: Maximum number of documents to return
            filter_metadata: Optional metadata filters
            
        Returns:
            List of document metadata dictionaries
        """
        try:
            db = await self.initialize_db()
            
            # Get documents with metadata
            # Note: ChromaDB doesn't have a direct "list" method, so we'll use get()
            get_kwargs = {}
            if limit:
                get_kwargs["limit"] = limit
            if filter_metadata:
                get_kwargs["where"] = filter_metadata
            
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: db._collection.get(**get_kwargs)
            )
            
            # Format results
            documents = []
            if result and "metadatas" in result:
                for i, metadata in enumerate(result["metadatas"]):
                    doc_info = {
                        "id": result["ids"][i] if "ids" in result else f"doc_{i}",
                        "metadata": metadata or {}
                    }
                    documents.append(doc_info)
            
            self.logger.info(
                "Listed documents",
                document_count=len(documents),
                limit=limit
            )
            
            return documents
            
        except Exception as e:
            self.logger.error(
                "Failed to list documents",
                error=str(e)
            )
            raise
    
    async def persist(self) -> bool:
        """
        Explicitly persist the ChromaDB collection to disk.
        
        Returns:
            True if persistence was successful
        """
        try:
            if self._db is None:
                self.logger.warning("ChromaDB not initialized, nothing to persist")
                return True
            
            # ChromaDB with persist_directory automatically persists,
            # but we can call persist() explicitly for immediate persistence
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._db.persist()  # This method may not exist in newer versions
            )
            
            self.logger.info("ChromaDB persisted successfully")
            return True
            
        except AttributeError:
            # persist() method might not exist in newer ChromaDB versions
            # as persistence is automatic with persist_directory
            self.logger.info("ChromaDB persistence is automatic with persist_directory")
            return True
        except Exception as e:
            self.logger.error(
                "Failed to persist ChromaDB",
                error=str(e)
            )
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on ChromaDB.
        
        Returns:
            Health status dictionary
        """
        try:
            db = await self.initialize_db()
            count = await self.get_document_count()
            
            return {
                "status": "healthy",
                "collection_name": self._collection_name,
                "document_count": count,
                "persist_directory": str(self.persist_directory),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    def __del__(self):
        """Cleanup resources when the manager is destroyed."""
        try:
            if self._db is not None:
                # Ensure final persistence
                asyncio.create_task(self.persist())
        except Exception:
            pass  # Ignore cleanup errors