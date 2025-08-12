"""
RAG Access System - Separated RAG concern for AI tool integration.

This module handles AI-specific RAG operations:
- Search query processing
- Document retrieval and ranking
- Response generation with context
- LangChain tool integration

Used by: ChatbotAgent, LangChain workflows, AI agents, multi-step reasoning
"""

from .search_service import SearchService
from .rag_models import RAGQuery, RAGResponse, SearchResult, SearchContext
from .rag_tool import RAGSearchTool
from .rag_prompts import RAGPrompts

__all__ = [
    'SearchService',
    'RAGQuery',
    'RAGResponse', 
    'SearchResult',
    'SearchContext',
    'RAGSearchTool',
    'RAGPrompts'
]