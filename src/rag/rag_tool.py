"""
RAG Search Tool for LangChain Agent Integration.
Azure OpenAI optimized tool for document retrieval in multi-step conversations.
"""

from typing import Optional, Dict, Any, Type
import asyncio
import structlog

from langchain.tools import BaseTool
from langchain.callbacks.manager import (
    AsyncCallbackManagerForToolRun,
    CallbackManagerForToolRun,
)
from pydantic import BaseModel, Field

from . import RAGQuery, RAGResponse
from .retriever import RAGRetriever

logger = structlog.get_logger(__name__)


class RAGSearchInput(BaseModel):
    """Input schema for RAG search tool."""
    query: str = Field(description="Search query for document retrieval")
    max_chunks: int = Field(default=3, description="Maximum number of document chunks to retrieve")
    score_threshold: float = Field(default=0.2, description="Minimum similarity score threshold")
    include_sources: bool = Field(default=True, description="Whether to include source attribution")


class RAGSearchTool(BaseTool):
    """
    LangChain tool for RAG document search - Azure OpenAI optimized.
    
    This tool allows LangChain agents to search through uploaded documents
    and retrieve relevant information for answering user questions.
    
    Features:
    - Semantic document search using Azure OpenAI embeddings
    - Source attribution and confidence scoring
    - Configurable retrieval parameters
    - Async support for Azure OpenAI integration
    """
    
    name: str = "document_search"
    description: str = """Search uploaded documents for relevant information to answer user questions.

Use this tool when:
- User asks about specific documents, policies, or procedures
- User references information that might be in uploaded files
- You need factual information from the knowledge base
- User asks "what does the document say about..." or similar

Input should be a clear search query describing what information you're looking for.

Examples:
- "vacation policy and time off procedures" 
- "employee handbook disciplinary actions"
- "project requirements and specifications"
- "safety protocols and emergency procedures"

The tool will return relevant document excerpts with source attribution."""

    args_schema: Type[BaseModel] = RAGSearchInput
    
    # RAG retriever instance - excluded from serialization
    rag_retriever: RAGRetriever = Field(exclude=True)
    
    def __init__(self, rag_retriever: RAGRetriever, **kwargs):
        """Initialize RAG search tool with retriever instance."""
        super().__init__(rag_retriever=rag_retriever, **kwargs)
        # Store logger separately to avoid Pydantic field issues
        object.__setattr__(
            self, 
            '_logger', 
            logger.bind(log_type="TOOL", component="rag_search_tool")
        )
    
    @property
    def logger(self):
        """Access logger instance."""
        return getattr(self, '_logger', logger)
    
    def _run(
        self,
        query: str,
        max_chunks: int = 3,
        score_threshold: float = 0.2,
        include_sources: bool = True,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """
        Synchronous tool execution - not recommended for Azure OpenAI production.
        
        For Azure OpenAI, use the async version (_arun) to avoid blocking.
        This method is provided for compatibility but will use asyncio.run().
        """
        self.logger.warning("Synchronous RAG tool execution - consider using async version")
        
        try:
            # Run async version in new event loop
            return asyncio.run(self._arun(
                query=query,
                max_chunks=max_chunks,
                score_threshold=score_threshold,
                include_sources=include_sources,
                run_manager=None
            ))
        except Exception as e:
            error_msg = f"RAG search failed: {str(e)}"
            self.logger.error("Synchronous RAG search failed", error=str(e))
            return error_msg
    
    async def _arun(
        self,
        query: str,
        max_chunks: int = 3,
        score_threshold: float = 0.2,
        include_sources: bool = True,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ) -> str:
        """
        Asynchronous RAG search execution - Azure OpenAI optimized.
        
        This is the primary method for Azure OpenAI integration as it
        properly handles async/await patterns for optimal performance.
        """
        self.logger.info(
            "Executing RAG search",
            query_length=len(query),
            max_chunks=max_chunks,
            score_threshold=score_threshold
        )
        
        try:
            # Create RAG query with specified parameters
            rag_query = RAGQuery(
                query=query,
                k=max_chunks,
                score_threshold=score_threshold,
                include_sources=include_sources,
                use_general_knowledge=False  # Tool focuses on documents only
            )
            
            # Execute RAG search
            response: RAGResponse = await self.rag_retriever.generate_rag_response(rag_query)
            
            # Format response for agent consumption
            result_parts = []
            
            # Add main answer
            result_parts.append(f"Document Search Results:\n{response.answer}")
            
            # Add source attribution if available
            if response.sources and include_sources:
                sources_text = ", ".join(response.sources)
                result_parts.append(f"\nSources: {sources_text}")
            
            # Add confidence information for agent decision-making
            if response.confidence_score > 0:
                confidence_text = f"Confidence: {response.confidence_score:.2f}"
                result_parts.append(f"\n{confidence_text}")
            
            # Add chunk count information
            chunk_count = len(response.retrieved_chunks)
            if chunk_count > 0:
                result_parts.append(f"\nRetrieved {chunk_count} relevant document segments")
            
            formatted_result = "\n".join(result_parts)
            
            self.logger.info(
                "RAG search completed successfully",
                response_length=len(response.answer),
                source_count=len(response.sources),
                confidence=response.confidence_score,
                chunks_retrieved=chunk_count
            )
            
            return formatted_result
            
        except Exception as e:
            error_msg = f"Document search encountered an error: {str(e)}"
            self.logger.error(
                "RAG search failed",
                query=query,
                error=str(e),
                error_type=type(e).__name__
            )
            return error_msg
    
    def get_tool_info(self) -> Dict[str, Any]:
        """Get tool information for debugging and monitoring."""
        return {
            "name": self.name,
            "description": self.description,
            "rag_retriever_initialized": self.rag_retriever is not None,
            "chromadb_status": "connected" if hasattr(self.rag_retriever, 'chromadb_manager') else "unknown"
        }
