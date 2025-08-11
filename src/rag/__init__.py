"""
RAG (Retrieval-Augmented Generation) data models.

This module provides core data models for RAG operations:
- Document metadata and processing status models  
- Query and response data structures
- Chunk representation for document fragments

Implementation classes have been moved to:
- src/document_management/ - Document lifecycle and storage
- src/rag_access/ - AI access and search operations
"""

from typing import TYPE_CHECKING, Any
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime

# Import LangChain Document for type hints
if TYPE_CHECKING:
    from langchain_core.documents import Document as LangChainDocument
else:
    # Runtime fallback - Pydantic will handle validation
    LangChainDocument = Any

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

__all__ = [
    'DocumentChunk',
    'Document', 
    'RAGQuery',
    'RAGResponse',
]