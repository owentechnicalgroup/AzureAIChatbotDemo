"""
Data models for document management system.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class DocumentStatus(Enum):
    """Document processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class DocumentInfo:
    """Information about a managed document."""
    document_id: str
    filename: str
    file_type: str
    size_bytes: int
    chunk_count: int
    upload_timestamp: str
    status: DocumentStatus = DocumentStatus.COMPLETED
    chunk_ids: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    
    @property
    def size_mb(self) -> float:
        """Get file size in MB."""
        return round(self.size_bytes / (1024 * 1024), 2)


@dataclass 
class DocumentStats:
    """Statistics about the document collection."""
    total_documents: int
    total_chunks: int
    total_size_bytes: int
    file_types: Dict[str, int]
    avg_chunks_per_document: float = 0.0
    
    @property
    def total_size_mb(self) -> float:
        """Get total size in MB."""
        return round(self.total_size_bytes / (1024 * 1024), 2)


@dataclass
class UploadResult:
    """Result of document upload operation."""
    success: bool
    document_info: Optional[DocumentInfo] = None
    error: Optional[str] = None
    processing_time: Optional[float] = None


@dataclass
class DeleteResult:
    """Result of document deletion operation."""
    success: bool
    message: Optional[str] = None
    error: Optional[str] = None
    deleted_count: int = 0