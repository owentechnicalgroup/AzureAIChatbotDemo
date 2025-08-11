"""
Data models for document management system.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any, TYPE_CHECKING
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field

# Import LangChain Document for type hints
if TYPE_CHECKING:
    from langchain_core.documents import Document as LangChainDocument
else:
    # Runtime fallback - Pydantic will handle validation
    LangChainDocument = Any


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


# RAG-specific data models (moved from src/rag)
class DocumentChunk(BaseModel):
    """Individual document chunk with metadata."""
    id: str = Field(..., description="Unique chunk identifier")
    content: str = Field(..., description="Chunk text content")
    source: str = Field(..., description="Source document filename")
    page_number: Optional[int] = Field(None, description="Page number if applicable")
    chunk_index: int = Field(..., description="Index within document")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
class Document(BaseModel):
    """Document metadata and processing status."""
    id: str = Field(..., description="Unique document identifier")
    filename: str = Field(..., description="Original filename")
    file_type: str = Field(..., description="File extension")
    size_bytes: int = Field(..., description="File size in bytes")
    upload_timestamp: datetime = Field(default_factory=datetime.utcnow)
    processing_status: str = Field(default="pending", description="processing|completed|failed")
    chunk_count: int = Field(default=0, description="Number of chunks created")
    error_message: Optional[str] = Field(None, description="Error details if failed")

class RAGQuery(BaseModel):
    """RAG query with retrieval parameters."""
    query: str = Field(..., description="User query text")
    k: int = Field(default=3, description="Number of chunks to retrieve")
    score_threshold: float = Field(default=0.2, description="Minimum similarity score")
    include_sources: bool = Field(default=True, description="Include source references")
    use_general_knowledge: bool = Field(default=False, description="Allow AI to use general knowledge as fallback")

class RAGResponse(BaseModel):
    """RAG response with sources and metadata."""
    answer: str = Field(..., description="Generated response")
    sources: List[str] = Field(default_factory=list, description="Source references")
    retrieved_chunks: List[Any] = Field(default_factory=list, description="Retrieved LangChain document chunks")
    confidence_score: float = Field(..., description="Response confidence 0-1")
    token_usage: Dict[str, Any] = Field(default_factory=dict)