"""
RAGSearchTool - LangChain tool for AI access to RAG system.
"""

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

from langchain.tools import BaseTool

from src.config.settings import Settings
from .search_service import SearchService
from .rag_models import RAGQuery, SearchContext


class RAGSearchInput(BaseModel):
    """Input schema for RAG search tool."""
    query: str = Field(description="The query to search for in documents")
    max_chunks: int = Field(
        default=3,
        description="Maximum number of document chunks to retrieve (1-10)"
    )
    use_general_knowledge: bool = Field(
        default=False,
        description="Whether to supplement with general knowledge if documents are insufficient"
    )


class RAGSearchTool(BaseTool):
    """
    LangChain tool for searching and querying RAG documents.
    
    This tool provides AI agents access to document search and
    AI-generated responses based on uploaded documents.
    """
    
    name: str = "rag_search"
    description: str = (
        "Search through uploaded documents and generate AI responses based on the content. "
        "Use this tool when users ask questions that might be answered by uploaded documents. "
        "The tool will search for relevant document chunks and generate contextual responses."
    )
    args_schema: type[BaseModel] = RAGSearchInput
    
    # Use object.__setattr__ to bypass Pydantic field validation
    def __init__(self, settings: Settings, **kwargs):
        super().__init__(**kwargs)
        object.__setattr__(self, '_search_service', SearchService(settings))
        object.__setattr__(self, '_settings', settings)
    
    def _run(
        self,
        query: str,
        max_chunks: int = 3,
        use_general_knowledge: bool = False,
        **kwargs: Any
    ) -> str:
        """
        Execute RAG search synchronously.
        
        Args:
            query: Search query
            max_chunks: Maximum chunks to retrieve
            use_general_knowledge: Whether to use general knowledge fallback
            
        Returns:
            AI-generated response based on document context
        """
        # This will be called by LangChain in sync context
        import asyncio
        
        try:
            # Run async method in sync context
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                # No event loop in current thread
                return asyncio.run(self._arun(query, max_chunks, use_general_knowledge, **kwargs))
            
            if loop.is_running():
                # We're in an async context, need to handle carefully
                # For now, just run in new event loop (may need nest_asyncio in some contexts)
                return asyncio.run(self._arun(query, max_chunks, use_general_knowledge, **kwargs))
            else:
                # No running loop, can use run_until_complete
                return loop.run_until_complete(
                    self._arun(query, max_chunks, use_general_knowledge, **kwargs)
                )
            return result
        except Exception as e:
            return f"RAG search error: {str(e)}"
    
    async def _arun(
        self,
        query: str,
        max_chunks: int = 3,
        use_general_knowledge: bool = False,
        **kwargs: Any
    ) -> str:
        """
        Execute RAG search asynchronously.
        
        Args:
            query: Search query
            max_chunks: Maximum chunks to retrieve
            use_general_knowledge: Whether to use general knowledge fallback
            
        Returns:
            AI-generated response based on document context
        """
        try:
            # Validate input
            if not query or not query.strip():
                return "Please provide a valid search query."
            
            # Clamp max_chunks to reasonable range
            max_chunks = max(1, min(10, max_chunks))
            
            # Create RAG query
            rag_query = RAGQuery(
                query=query.strip(),
                max_chunks=max_chunks,
                score_threshold=0.2,
                use_general_knowledge=use_general_knowledge
            )
            
            # Create search context
            context = SearchContext()
            
            # Execute search and generation
            response = await self._search_service.search_and_generate(rag_query, context)
            
            # Return the AI-generated response directly
            # The AI is instructed via prompts to include sources when appropriate
            return response.content
                
        except Exception as e:
            return f"Error processing RAG search: {str(e)}"
    
    @property
    def is_available(self) -> bool:
        """Check if RAG search is available."""
        try:
            return self._search_service.is_available()
        except Exception:
            return False
    
    async def get_tool_info(self) -> Dict[str, Any]:
        """Get information about this tool's capabilities."""
        try:
            # Get available documents
            documents = await self._search_service.get_available_documents()
            
            # Get health status
            health = await self._search_service.health_check()
            
            return {
                "name": self.name,
                "description": self.description,
                "available": self.is_available,
                "status": health.get("status", "unknown"),
                "documents_available": len(documents),
                "documents": [
                    {
                        "filename": doc.get("filename"),
                        "file_type": doc.get("file_type"),
                        "chunk_count": doc.get("chunk_count", 0)
                    }
                    for doc in documents[:5]  # Show first 5 documents
                ],
                "capabilities": [
                    "Document search and retrieval",
                    "AI response generation with context",
                    "Source citation and relevance scoring",
                    "General knowledge fallback (optional)"
                ]
            }
        except Exception as e:
            return {
                "name": self.name,
                "available": False,
                "error": str(e)
            }