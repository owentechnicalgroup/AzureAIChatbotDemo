"""
SearchService - AI access layer for RAG operations.

Handles AI queries and response generation using document context.
"""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

import structlog
from openai import AsyncAzureOpenAI

from src.config.settings import Settings
from src.document_management.database_manager import DatabaseManager
from .rag_models import RAGQuery, RAGResponse, SearchResult, SearchContext
from .rag_prompts import RAGPrompts


logger = structlog.get_logger(__name__)


class SearchService:
    """
    AI access layer for RAG operations.
    
    Responsibilities:
    - Document search and retrieval
    - AI response generation with context
    - Query processing and refinement
    - Response formatting and metadata
    
    Separation of Concerns:
    - Only handles AI queries and response generation
    - Uses DocumentManager for document operations
    - Focuses on the AI access layer only
    """
    
    def __init__(self, settings: Settings):
        """
        Initialize search service.
        
        Args:
            settings: Application settings
        """
        self.settings = settings
        self.logger = logger.bind(
            log_type="AZURE_OPENAI",
            component="search_service"
        )
        
        # Initialize database manager for search
        self.database_manager = DatabaseManager(settings)
        
        # Initialize Azure OpenAI client
        self.openai_client = AsyncAzureOpenAI(
            azure_endpoint=self.settings.azure_openai_endpoint,
            api_key=self.settings.azure_openai_api_key,
            api_version=self.settings.azure_openai_api_version
        )
        
        self.logger.info("Search Service initialized")
    
    async def search_and_generate(
        self,
        query: RAGQuery,
        context: Optional[SearchContext] = None
    ) -> RAGResponse:
        """
        Search documents and generate AI response.
        
        Args:
            query: RAG query with search parameters
            context: Optional search context for tracking
            
        Returns:
            RAG response with generated content and sources
        """
        start_time = datetime.now(timezone.utc)
        
        try:
            self.logger.info(
                "Starting RAG search and generation",
                query=query.query,
                max_chunks=query.max_chunks,
                use_general_knowledge=query.use_general_knowledge
            )
            
            # Search for relevant documents
            search_results = await self._search_documents(query)
            
            # Generate response with context
            if search_results or query.use_general_knowledge:
                response_content = await self._generate_response(query, search_results)
                processing_mode = self._determine_processing_mode(search_results, query.use_general_knowledge)
            else:
                response_content = RAGPrompts.get_no_context_prompt(
                    query.query, 
                    query.use_general_knowledge
                )
                processing_mode = "no_context"
            
            # Calculate processing time
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            # Always include all search results - let UI decide what to show
            response = RAGResponse(
                content=response_content,
                sources=search_results,  # Always include what we found
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
                "RAG search and generation completed",
                query=query.query,
                sources_found=len(search_results),
                processing_mode=processing_mode,
                processing_time=processing_time
            )
            
            return response
            
        except Exception as e:
            self.logger.error(
                "RAG search and generation failed",
                query=query.query,
                error=str(e)
            )
            
            # Return error response
            return RAGResponse(
                content=f"Sorry, I encountered an error processing your query: {str(e)}",
                sources=[],
                query=query.query,
                processing_mode="error",
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
    
    async def _generate_response(
        self,
        query: RAGQuery,
        search_results: List[SearchResult]
    ) -> str:
        """
        Generate AI response using search results as context.
        
        This is where the prompt switching happens based on use_general_knowledge flag.
        
        Args:
            query: Original RAG query
            search_results: Document search results
            
        Returns:
            Generated response content
        """
        try:
            # Determine the appropriate system prompt based on search results and flag
            if search_results:
                # We have documents - choose system prompt based on use_general_knowledge flag
                if query.use_general_knowledge:
                    system_prompt = RAGPrompts.get_system_prompt_with_general_knowledge()
                    self.logger.info("Using hybrid mode prompt (documents + general knowledge allowed)")
                else:
                    system_prompt = RAGPrompts.get_system_prompt_document_only()
                    self.logger.info("Using document-only mode prompt")
                
                # Build context from search results
                context_prompt = RAGPrompts.build_context_prompt(search_results)
                
            else:
                # No documents found - behavior depends on flag
                if query.use_general_knowledge:
                    system_prompt = RAGPrompts.get_system_prompt_general_knowledge_only()
                    context_prompt = "No relevant documents found. You may use your general knowledge to help answer the question."
                    self.logger.info("Using general knowledge only prompt (no documents found)")
                else:
                    # Return early with "no documents" response - don't call AI
                    self.logger.info("No documents found and general knowledge disabled - returning standard response")
                    return RAGPrompts.get_no_documents_response(query.query)
            
            # Generate response with selected prompts
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "system", "content": context_prompt},
                {"role": "user", "content": query.query}
            ]
            
            self.logger.info("Generating AI response", prompt_type=system_prompt[:50])
            
            response = await self.openai_client.chat.completions.create(
                model=self.settings.azure_openai_deployment,
                messages=messages,
                temperature=0.3,
                max_tokens=1500
            )
            
            generated_content = response.choices[0].message.content
            
            self.logger.info(
                "AI response generated successfully",
                query=query.query,
                sources_used=len(search_results),
                tokens_used=response.usage.total_tokens if response.usage else 0
            )
            
            return generated_content
            
        except Exception as e:
            self.logger.error("AI response generation failed", query=query.query, error=str(e))
            return f"I apologize, but I encountered an error generating a response: {str(e)}"
    
    def _determine_processing_mode(
        self,
        search_results: List[SearchResult],
        use_general_knowledge: bool
    ) -> str:
        """
        Determine the processing mode based on results and settings.
        
        Args:
            search_results: Document search results
            use_general_knowledge: Whether general knowledge is enabled
            
        Returns:
            Processing mode string
        """
        if search_results:
            # We found documents - AI will use them (and maybe general knowledge if enabled)
            return "document_based" if not use_general_knowledge else "hybrid"
        else:
            # No documents found
            return "general_knowledge" if use_general_knowledge else "no_context"
   
    
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
            
            # Test OpenAI connection (simple ping)
            try:
                test_response = await self.openai_client.chat.completions.create(
                    model=self.settings.azure_openai_deployment,
                    messages=[{"role": "user", "content": "ping"}],
                    max_tokens=5
                )
                openai_status = "healthy"
            except Exception:
                openai_status = "unhealthy"
            
            return {
                "status": "healthy" if db_health["status"] == "healthy" and openai_status == "healthy" else "unhealthy",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "components": {
                    "database_manager": db_health["status"],
                    "azure_openai": openai_status,
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
                    "azure_openai": "unknown",
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
            return (
                self.database_manager.is_available() and
                bool(self.settings.azure_openai_endpoint) and
                bool(self.settings.azure_openai_api_key) and
                bool(self.settings.azure_openai_deployment)
            )
        except Exception:
            return False