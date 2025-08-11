"""
DatabaseManager - Document management business logic layer.

Handles document management operations using ChromaDBService for persistence.
Provides business logic and maintains API compatibility.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

import structlog

from src.config.settings import Settings
from .chromadb_service import ChromaDBService


logger = structlog.get_logger(__name__)


class DatabaseManager:
    """
    Document management business logic layer using ChromaDBService.
    
    Responsibilities:
    - Document lifecycle management business logic
    - Metadata processing and validation
    - Search result formatting and filtering
    - Business rule enforcement
    - Statistics and reporting
    
    Separation of Concerns:
    - Uses ChromaDBService for all ChromaDB operations
    - Contains only business logic, no ChromaDB-specific code
    - Maintains API compatibility with existing code
    """
    
    def __init__(self, settings: Settings):
        """
        Initialize database manager with ChromaDB service.
        
        Args:
            settings: Application settings
        """
        self.settings = settings
        self.logger = logger.bind(
            log_type="SYSTEM",
            component="database_manager"
        )
        
        # Use ChromaDBService for all ChromaDB operations
        self.chromadb = ChromaDBService(settings)
        
        self.logger.info("Database Manager initialized with ChromaDBService")
    
    async def add_documents(self, documents: List[Any]) -> List[str]:
        """
        Add document chunks to the database with business logic processing.
        
        Args:
            documents: List of document chunks with content and metadata
            
        Returns:
            List of document IDs that were added
        """
        try:
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
                    
                    # Add business logic: ensure required metadata fields
                    if 'upload_timestamp' not in metadata:
                        metadata['upload_timestamp'] = datetime.now(timezone.utc).isoformat()
                    
                    langchain_docs.append(LangChainDocument(page_content=content, metadata=metadata))
            
            # Delegate to ChromaDB service
            doc_ids = await self.chromadb.add_documents(langchain_docs)
            
            self.logger.info(
                "Documents processed and added to database",
                count=len(documents),
                successful_ids=len(doc_ids)
            )
            
            return doc_ids
            
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
            if not filename or not filename.strip():
                self.logger.warning("Empty filename provided for deletion")
                return False
            
            self.logger.info("Starting document deletion", filename=filename)
            
            # Use ChromaDB service to delete by filter
            filter_criteria = {"filename": filename}
            success = await self.chromadb.delete_documents_by_filter(filter_criteria)
            
            if success:
                self.logger.info("Document deletion completed successfully", filename=filename)
            else:
                self.logger.warning("Document deletion failed or no documents found", filename=filename)
            
            return success
            
        except Exception as e:
            self.logger.error(
                "Failed to delete document from database",
                filename=filename,
                error=str(e)
            )
            return False
    
    async def get_documents_summary(self) -> List[Dict[str, Any]]:
        """
        Get summary of all documents in the database with business logic formatting.
        
        Returns:
            List of document summaries with metadata
        """
        try:
            # Get all documents from ChromaDB service
            all_docs = await self.chromadb.get_all_documents()
            
            if not all_docs:
                return []
            
            # Business logic: Group by filename and format for UI
            documents = {}
            for doc in all_docs:
                metadata = doc.get('metadata', {})
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
                if 'chunk_id' in metadata:
                    documents[filename]['chunk_ids'].append(metadata['chunk_id'])
            
            # Sort by upload timestamp (newest first)
            document_list = list(documents.values())
            document_list.sort(
                key=lambda x: x.get('upload_timestamp', ''), 
                reverse=True
            )
            
            return document_list
            
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
            count = await self.chromadb.get_document_count()
            self.logger.debug("Document count retrieved", count=count)
            return count
            
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
        Search for similar documents with business logic formatting.
        
        Args:
            query: Search query
            max_results: Maximum number of results
            score_threshold: Minimum similarity score
            filters: Optional metadata filters
            
        Returns:
            List of similar document chunks with scores
        """
        try:
            if not query or not query.strip():
                self.logger.warning("Empty query provided for search")
                return []
            
            # ChromaDB doesn't accept empty filter dict, pass None instead
            search_filters = filters if filters else None
            
            # Delegate to ChromaDB service
            raw_results = await self.chromadb.search_similar(
                query=query,
                k=max_results,
                score_threshold=score_threshold,
                filter_metadata=search_filters
            )
            
            # Business logic: Format results for document management UI
            formatted_results = []
            for result in raw_results:
                formatted_result = {
                    'content': result.get('content', ''),
                    'metadata': result.get('metadata', {}),
                    'score': result.get('score', 0.0),
                    'chunk_id': result['metadata'].get('chunk_id', f"chunk_{hash(result.get('content', ''))}"),
                    'source': result.get('source', 'Unknown'),
                    'filename': result['metadata'].get('filename', 'Unknown'),
                    'file_type': result['metadata'].get('file_type', 'unknown')
                }
                formatted_results.append(formatted_result)
            
            # Sort by score (highest first)
            formatted_results.sort(key=lambda x: x['score'], reverse=True)
            
            self.logger.info(
                "Document search completed",
                query_length=len(query),
                results_found=len(formatted_results),
                max_results=max_results
            )
            
            return formatted_results
            
        except Exception as e:
            self.logger.error("Document search failed", query=query[:100], error=str(e))
            return []
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform comprehensive health check on the database manager.
        
        Returns:
            Health status information
        """
        try:
            # Get health status from ChromaDB service
            chromadb_health = await self.chromadb.health_check()
            
            # Add business logic health checks
            document_count = await self.get_document_count()
            
            # Determine overall health
            is_healthy = (
                chromadb_health.get("status") == "healthy" and
                self.chromadb.is_available()
            )
            
            return {
                "status": "healthy" if is_healthy else "unhealthy",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "component": "database_manager",
                "document_count": document_count,
                "chromadb_service": chromadb_health,
                "business_logic": {
                    "settings_configured": bool(
                        self.settings.chromadb_storage_path and
                        self.settings.azure_openai_api_key and
                        self.settings.azure_embedding_deployment
                    )
                }
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "component": "database_manager", 
                "error": str(e),
                "chromadb_service": "unavailable"
            }
    
    def is_available(self) -> bool:
        """
        Check if the database manager is available for operations.
        
        Returns:
            True if database is ready for operations
        """
        try:
            return (
                self.chromadb.is_available() and
                bool(self.settings.chromadb_storage_path) and 
                bool(self.settings.azure_openai_api_key) and
                bool(self.settings.azure_embedding_deployment)
            )
        except Exception as e:
            self.logger.warning("Database availability check failed", error=str(e))
            return False
    
    # Additional business logic methods
    
    async def get_unique_filenames(self) -> List[str]:
        """
        Get list of unique filenames in the database.
        
        Returns:
            List of unique filenames
        """
        try:
            documents_summary = await self.get_documents_summary()
            filenames = [doc['filename'] for doc in documents_summary if doc['filename'] != 'Unknown']
            return sorted(list(set(filenames)))
            
        except Exception as e:
            self.logger.error("Failed to get unique filenames", error=str(e))
            return []
    
    async def get_document_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive document statistics.
        
        Returns:
            Document statistics
        """
        try:
            documents_summary = await self.get_documents_summary()
            total_chunks = await self.get_document_count()
            
            # Calculate statistics
            total_files = len(documents_summary)
            total_size = sum(doc.get('size_bytes', 0) for doc in documents_summary)
            
            file_types = {}
            for doc in documents_summary:
                file_type = doc.get('file_type', 'unknown')
                file_types[file_type] = file_types.get(file_type, 0) + 1
            
            return {
                "total_files": total_files,
                "total_chunks": total_chunks,
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "file_types": file_types,
                "average_chunks_per_file": round(total_chunks / max(total_files, 1), 1)
            }
            
        except Exception as e:
            self.logger.error("Failed to get document statistics", error=str(e))
            return {
                "total_files": 0,
                "total_chunks": 0,
                "total_size_bytes": 0,
                "total_size_mb": 0.0,
                "file_types": {},
                "average_chunks_per_file": 0.0
            }