"""
Data models for RAG access system.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime


@dataclass
class RAGQuery:
    """Query for RAG search operations."""
    query: str
    max_chunks: int = 3
    score_threshold: float = 0.2
    include_sources: bool = True
    use_general_knowledge: bool = False
    filters: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.filters is None:
            self.filters = {}


@dataclass
class SearchResult:
    """Individual search result from document retrieval."""
    content: str
    source: str
    score: float
    metadata: Dict[str, Any]
    chunk_id: Optional[str] = None


@dataclass 
class RAGResponse:
    """Response from RAG search and generation."""
    content: str
    sources: List[SearchResult]
    query: str
    processing_mode: str  # 'document_based', 'general_knowledge', 'hybrid'
    confidence_score: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None
    
    @property
    def has_sources(self) -> bool:
        """Check if response has document sources."""
        return len(self.sources) > 0
    
    @property
    def source_count(self) -> int:
        """Get number of sources used."""
        return len(self.sources)


@dataclass
class SearchContext:
    """Context for RAG search operations."""
    conversation_id: Optional[str] = None
    user_id: Optional[str] = None
    session_data: Optional[Dict[str, Any]] = None
    timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
        if self.session_data is None:
            self.session_data = {}