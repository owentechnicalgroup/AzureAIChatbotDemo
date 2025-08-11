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
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're already in an async context, create new event loop
                import nest_asyncio
                nest_asyncio.apply()
                result = asyncio.run(self._arun(query, max_chunks, use_general_knowledge, **kwargs))
            else:
                result = loop.run_until_complete(
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
            
            # Format response for LangChain
            # Only show sources if they were actually used AND not already included in response
            if (response.has_sources and 
                self._response_actually_used_sources(response.content) and 
                not self._response_already_has_sources(response.content)):
                
                source_info = f"\n\nSources used ({response.source_count}):\n"
                for i, source in enumerate(response.sources, 1):
                    source_info += f"• {source.source} (relevance: {source.score:.2f})\n"
                
                return response.content + source_info
            else:
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
    
    def _response_actually_used_sources(self, response_content: str) -> bool:
        """
        Determine if the AI response actually used the retrieved sources.
        
        Args:
            response_content: The AI's response text
            
        Returns:
            bool: True if sources were actually used, False otherwise
        """
        # Keywords that indicate the AI couldn't find relevant information
        no_info_indicators = [
            "I'm sorry, but",
            "I don't have information",
            "There is no information",
            "None of the provided documents contain",
            "I am unable to answer",
            "I cannot answer",
            "no relevant information",
            "not mentioned in provided documents",
            "The documents do not contain"
        ]
        
        response_lower = response_content.lower()
        
        # If response contains indicators that no relevant info was found, sources weren't used
        for indicator in no_info_indicators:
            if indicator.lower() in response_lower:
                return False
        
        # If we get here, the response likely used the sources
        return True
    
    def _response_already_has_sources(self, response_content: str) -> bool:
        """
        Check if the AI response already includes source citations.
        
        Args:
            response_content: The AI's response text
            
        Returns:
            bool: True if sources are already included in the response, False otherwise
        """
        # Look for various source citation formats that the AI might use
        source_indicators = [
            "Sources used:",
            "Sources:",
            "[Source",
            "Based on:",
            "According to:",
            "From the documents:",
            "• ", # Bullet points often indicate sources
            "- ", # Dash points often indicate sources
        ]
        
        # Check if response contains any source indicators
        for indicator in source_indicators:
            if indicator in response_content:
                return True
        
        # Check for document references (filename patterns)
        import re
        # Look for patterns like "filename.docx", "filename.pdf", etc.
        doc_pattern = r'\b\w+\.(docx|pdf|txt|doc|xlsx)\b'
        if re.search(doc_pattern, response_content, re.IGNORECASE):
            return True
        
        return False