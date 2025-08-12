"""
SearchService - AI access layer for RAG operations.

Handles AI queries and response generation using document context.
"""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

import structlog

from src.config.settings import Settings
from src.document_management.database_manager import DatabaseManager
from .rag_models import RAGQuery, RAGResponse, SearchResult, SearchContext
from .rag_prompts import RAGPrompts


logger = structlog.get_logger(__name__)


class SearchService:
    """
    Document search service for RAG operations.
    
    Simplified responsibilities:
    - Document search and retrieval
    - Search result formatting and metadata
    - Health checks and availability
    
    Note: AI response generation is now handled by the ChatbotAgent's system prompt.
    This service focuses only on document search and result preparation.
    """
    
    def __init__(self, settings: Settings):
        """
        Initialize search service.
        
        Args:
            settings: Application settings
        """
        self.settings = settings
        self.logger = logger.bind(
            log_type="SYSTEM", 
            component="search_service"
        )
        
        # Initialize database manager for search
        self.database_manager = DatabaseManager(settings)
        
        self.logger.info("Search Service initialized")
    
    async def search_and_generate(
        self,
        query: RAGQuery,
        context: Optional[SearchContext] = None
    ) -> RAGResponse:
        """
        Search documents and prepare formatted context for the agent.
        
        Note: AI response generation is now handled by ChatbotAgent.
        This method only searches documents and formats context.
        
        Args:
            query: RAG query with search parameters
            context: Optional search context for tracking
            
        Returns:
            RAG response with document search results and formatted context
        """
        start_time = datetime.now(timezone.utc)
        
        try:
            self.logger.info(
                "Starting document search",
                query=query.query,
                max_chunks=query.max_chunks,
                use_general_knowledge=query.use_general_knowledge
            )
            
            # Search for relevant documents
            search_results = await self._search_documents(query)
            
            # Format document context for the agent
            if search_results:
                formatted_context = RAGPrompts.build_context_prompt(search_results)
                processing_mode = "document_search_found"
            else:
                formatted_context = "No relevant documents found in the knowledge base."
                processing_mode = "no_documents_found"
            
            # Calculate processing time
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            # Return search results and context for agent to use
            response = RAGResponse(
                content=formatted_context,  # Formatted document context, not AI response
                sources=search_results,
                query=query.query,
                processing_mode=processing_mode,
                metadata={
                    "processing_time": processing_time,
                    "search_params": {
                        "max_chunks": query.max_chunks,
                        "score_threshold": query.score_threshold,
                        "use_general_knowledge": query.use_general_knowledge
                    },
                    "context": context.__dict__ if context else None,
                    "documents_found": len(search_results),
                    "avg_relevance_score": sum(s.score for s in search_results) / len(search_results) if search_results else 0
                }
            )
            
            self.logger.info(
                "Document search completed",
                query=query.query,
                sources_found=len(search_results),
                processing_mode=processing_mode,
                processing_time=processing_time
            )
            
            return response
            
        except Exception as e:
            self.logger.error(
                "Document search failed",
                query=query.query,
                error=str(e)
            )
            
            # Return error response
            return RAGResponse(
                content=f"Error during document search: {str(e)}",
                sources=[],
                query=query.query,
                processing_mode="search_error",
                metadata={"error": str(e)}
            )
    
    async def _search_documents(self, query: RAGQuery) -> List[SearchResult]:
        """
        Search for relevant documents.
        
        Args:
            query: RAG query with search parameters
            
        Returns:
            List of search results
        """
        try:
            # Use database manager for similarity search
            raw_results = await self.database_manager.search_similar(
                query=query.query,
                max_results=query.max_chunks,
                score_threshold=query.score_threshold,
                filters=query.filters
            )
            
            # Convert to SearchResult objects
            search_results = []
            for result in raw_results:
                search_result = SearchResult(
                    content=result['content'],
                    source=result['source'],
                    score=result['score'],
                    metadata=result['metadata'],
                    chunk_id=result.get('chunk_id')
                )
                search_results.append(search_result)
            
            return search_results
            
        except Exception as e:
            self.logger.error("Document search failed", query=query.query, error=str(e))
            return []
    
   
    
    async def get_available_documents(self) -> List[Dict[str, Any]]:
        """
        Get list of available documents for search.
        
        Returns:
            List of document summaries
        """
        try:
            return await self.database_manager.get_documents_summary()
        except Exception as e:
            self.logger.error("Failed to get available documents", error=str(e))
            return []
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on the search service.
        
        Returns:
            Health status information
        """
        try:
            # Check database health
            db_health = await self.database_manager.health_check()
            
            return {
                "status": db_health["status"],
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "components": {
                    "database_manager": db_health["status"],
                    "search_service": "active"
                },
                "database_health": db_health
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(e),
                "components": {
                    "database_manager": "unknown",
                    "search_service": "error"
                }
            }
    
    def is_available(self) -> bool:
        """
        Check if the search service is available.
        
        Returns:
            True if service is ready for operations
        """
        try:
            return self.database_manager.is_available()
        except Exception:
            return False