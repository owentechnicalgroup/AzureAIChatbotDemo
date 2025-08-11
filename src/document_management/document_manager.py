"""
DocumentManager - Main orchestrator for document lifecycle management.

Handles all document-related operations independently from AI access layer.
"""

import asyncio
import uuid
from pathlib import Path
from typing import List, Optional, Dict, Any, Union
from datetime import datetime, timezone

import structlog

from src.config.settings import Settings
from .document_models import (
    DocumentInfo, DocumentStats, UploadResult, DeleteResult, DocumentStatus
)
from .database_manager import DatabaseManager

logger = structlog.get_logger(__name__)


class DocumentManager:
    """
    Main orchestrator for document lifecycle management.
    
    Responsibilities:
    - Document upload and processing coordination
    - Document storage and indexing management
    - Document metadata and lifecycle tracking
    - Document deletion and cleanup operations
    - Statistics and health monitoring
    
    Separation of Concerns:
    - Does NOT handle AI queries or response generation
    - Focuses purely on document management operations
    - Used by UI components, admin interfaces, and document APIs
    """
    
    def __init__(self, settings: Settings):
        """
        Initialize document manager.
        
        Args:
            settings: Application settings
        """
        self.settings = settings
        self.logger = logger.bind(
            log_type="SYSTEM",
            component="document_manager"
        )
        
        # Initialize database manager (handles ChromaDB operations)
        self.database_manager = DatabaseManager(settings)
        
        # Track upload operations
        self._active_uploads: Dict[str, DocumentStatus] = {}
        
        self.logger.info("Document Manager initialized")
    
    async def upload_document(
        self,
        file_path: Path,
        file_content: Optional[bytes] = None,
        source_name: Optional[str] = None,
        additional_metadata: Optional[Dict[str, Any]] = None
    ) -> UploadResult:
        """
        Upload and process a document into the system.
        
        Args:
            file_path: Path to the document file
            file_content: Optional file content (for uploaded files)
            source_name: Optional source name override
            additional_metadata: Additional metadata to store
            
        Returns:
            UploadResult with success status and document info
        """
        operation_id = str(uuid.uuid4())
        start_time = datetime.now(timezone.utc)
        
        try:
            self._active_uploads[operation_id] = DocumentStatus.PROCESSING
            
            self.logger.info(
                "Starting document upload",
                operation_id=operation_id,
                file_path=str(file_path),
                source_name=source_name
            )
            
            # Import here to avoid circular imports
            from .document_processor import DocumentProcessor
            
            # Process the document into chunks
            processor = DocumentProcessor(self.settings)
            chunks = await processor.process_file(
                file_path=file_path,
                file_content=file_content,
                source_name=source_name or file_path.name
            )
            
            if not chunks:
                self._active_uploads[operation_id] = DocumentStatus.FAILED
                return UploadResult(
                    success=False,
                    error="No content extracted from document"
                )
            
            # Store chunks in database
            document_ids = await self.database_manager.add_documents(chunks)
            
            # Create document info
            first_chunk_metadata = chunks[0].metadata
            document_info = DocumentInfo(
                document_id=first_chunk_metadata.get('document_id'),
                filename=first_chunk_metadata.get('filename'),
                file_type=first_chunk_metadata.get('file_type'),
                size_bytes=first_chunk_metadata.get('file_size', 0),
                chunk_count=len(chunks),
                upload_timestamp=first_chunk_metadata.get('upload_timestamp'),
                status=DocumentStatus.COMPLETED,
                chunk_ids=document_ids,
                metadata=additional_metadata
            )
            
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            self._active_uploads[operation_id] = DocumentStatus.COMPLETED
            
            self.logger.info(
                "Document upload completed successfully",
                operation_id=operation_id,
                document_id=document_info.document_id,
                filename=document_info.filename,
                chunk_count=document_info.chunk_count,
                processing_time=processing_time
            )
            
            return UploadResult(
                success=True,
                document_info=document_info,
                processing_time=processing_time
            )
            
        except Exception as e:
            self._active_uploads[operation_id] = DocumentStatus.FAILED
            self.logger.error(
                "Document upload failed",
                operation_id=operation_id,
                file_path=str(file_path),
                error=str(e)
            )
            return UploadResult(
                success=False,
                error=str(e)
            )
        finally:
            # Clean up tracking
            self._active_uploads.pop(operation_id, None)
    
    async def delete_document(self, filename: str) -> DeleteResult:
        """
        Delete a document and all its chunks from the system.
        
        Args:
            filename: Name of the file to delete
            
        Returns:
            DeleteResult with success status and details
        """
        try:
            self.logger.info("Deleting document", filename=filename)
            
            success = await self.database_manager.delete_document_by_filename(filename)
            
            if success:
                self.logger.info("Document deleted successfully", filename=filename)
                return DeleteResult(
                    success=True,
                    message=f"Document '{filename}' deleted successfully",
                    deleted_count=1
                )
            else:
                return DeleteResult(
                    success=False,
                    error=f"Failed to delete document '{filename}'"
                )
                
        except Exception as e:
            self.logger.error(
                "Document deletion failed",
                filename=filename,
                error=str(e)
            )
            return DeleteResult(
                success=False,
                error=str(e)
            )
    
    async def delete_all_documents(self) -> DeleteResult:
        """
        Delete all documents from the system.
        
        Returns:
            DeleteResult with bulk deletion results
        """
        try:
            self.logger.info("Starting bulk document deletion")
            
            # Get all documents first
            documents = await self.list_documents()
            
            deleted_count = 0
            errors = []
            
            for doc in documents:
                try:
                    result = await self.delete_document(doc["filename"])
                    if result.success:
                        deleted_count += 1
                    else:
                        errors.append(f"{doc['filename']}: {result.error}")
                except Exception as e:
                    errors.append(f"{doc['filename']}: {str(e)}")
            
            self.logger.info(
                "Bulk document deletion completed",
                deleted_count=deleted_count,
                error_count=len(errors)
            )
            
            return DeleteResult(
                success=len(errors) == 0,
                deleted_count=deleted_count,
                message=f"Deleted {deleted_count} documents" + 
                       (f" with {len(errors)} errors" if errors else ""),
                error="; ".join(errors) if errors else None
            )
            
        except Exception as e:
            self.logger.error("Bulk document deletion failed", error=str(e))
            return DeleteResult(
                success=False,
                error=str(e),
                deleted_count=0
            )
    
    async def list_documents(self) -> List[Dict[str, Any]]:
        """
        Get a list of all documents in the system.
        
        Returns:
            List of document summaries with metadata
        """
        try:
            return await self.database_manager.get_documents_summary()
        except Exception as e:
            self.logger.error("Failed to list documents", error=str(e))
            return []
    
    async def get_document_info(self, filename: str) -> Optional[DocumentInfo]:
        """
        Get detailed information about a specific document.
        
        Args:
            filename: Name of the document
            
        Returns:
            DocumentInfo if found, None otherwise
        """
        try:
            documents = await self.list_documents()
            
            for doc in documents:
                if doc.get('filename') == filename:
                    return DocumentInfo(
                        document_id=doc.get('document_id'),
                        filename=doc.get('filename'),
                        file_type=doc.get('file_type'),
                        size_bytes=doc.get('size_bytes', 0),
                        chunk_count=doc.get('chunk_count', 0),
                        upload_timestamp=doc.get('upload_timestamp'),
                        status=DocumentStatus.COMPLETED,
                        chunk_ids=doc.get('chunk_ids', [])
                    )
            
            return None
            
        except Exception as e:
            self.logger.error("Failed to get document info", filename=filename, error=str(e))
            return None
    
    async def get_statistics(self) -> DocumentStats:
        """
        Get comprehensive statistics about the document collection.
        
        Returns:
            DocumentStats with collection information
        """
        try:
            documents = await self.list_documents()
            chunk_count = await self.database_manager.get_document_count()
            
            total_size = sum(doc.get('size_bytes', 0) for doc in documents)
            file_types = {}
            
            for doc in documents:
                file_type = doc.get('file_type', 'unknown')
                file_types[file_type] = file_types.get(file_type, 0) + 1
            
            return DocumentStats(
                total_documents=len(documents),
                total_chunks=chunk_count,
                total_size_bytes=total_size,
                file_types=file_types,
                avg_chunks_per_document=round(chunk_count / len(documents), 1) if documents else 0.0
            )
            
        except Exception as e:
            self.logger.error("Failed to get document statistics", error=str(e))
            return DocumentStats(
                total_documents=0,
                total_chunks=0,
                total_size_bytes=0,
                file_types={}
            )
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on the document management system.
        
        Returns:
            Health status information
        """
        try:
            # Check database health
            db_health = await self.database_manager.health_check()
            
            # Get basic stats
            stats = await self.get_statistics()
            
            # Check active operations
            active_ops = len(self._active_uploads)
            
            return {
                "status": "healthy" if db_health["status"] == "healthy" else "unhealthy",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "database_health": db_health,
                "document_stats": {
                    "total_documents": stats.total_documents,
                    "total_chunks": stats.total_chunks,
                    "total_size_mb": stats.total_size_mb
                },
                "active_operations": active_ops,
                "components": {
                    "database_manager": db_health["status"],
                    "document_processor": "available"
                }
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(e),
                "components": {
                    "database_manager": "unknown",
                    "document_processor": "unknown"
                }
            }
    
    def is_available(self) -> bool:
        """
        Check if the document management system is available.
        
        Returns:
            True if the system is ready for operations
        """
        try:
            return self.database_manager is not None
        except Exception:
            return False