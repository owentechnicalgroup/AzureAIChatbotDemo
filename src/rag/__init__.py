"""
RAG (Retrieval-Augmented Generation) module for document processing and vector search.

This module provides:
- Document processing and chunking
- ChromaDB vector storage management
- Document retrieval and similarity search
- Integration with Azure OpenAI embeddings
"""

from typing import TYPE_CHECKING

# Core data models
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

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

class RAGResponse(BaseModel):
    """RAG response with sources and metadata."""
    answer: str = Field(..., description="Generated response")
    sources: List[str] = Field(default_factory=list, description="Source references")
    retrieved_chunks: List[DocumentChunk] = Field(default_factory=list)
    confidence_score: float = Field(..., description="Response confidence 0-1")
    token_usage: Dict[str, int] = Field(default_factory=dict)

# Conditional imports for implementation classes
if TYPE_CHECKING:
    from .document_processor import DocumentProcessor
    from .vector_store import ChromaDBManager
    from .retriever import RAGRetriever

__all__ = [
    'DocumentChunk',
    'Document', 
    'RAGQuery',
    'RAGResponse',
    'DocumentProcessor',
    'ChromaDBManager',
    'RAGRetriever',
]