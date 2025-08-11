"""
Simplified RAG retrieval system for Azure OpenAI chatbot.
Focused on core functionality without unnecessary complexity.
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timezone

import structlog
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.documents import Document as LangChainDocument

from src.config.settings import Settings
from src.utils.azure_langchain import create_azure_chat_openai
from . import RAGQuery, RAGResponse
from .chromadb_manager import ChromaDBManager

logger = structlog.get_logger(__name__)


class RAGRetriever:
    """
    Simplified RAG retriever using ChromaDB and Azure OpenAI.
    
    Features:
    - Document similarity search
    - Context-aware response generation  
    - Source attribution
    - Clean Azure OpenAI integration
    """
    
    def __init__(self, settings: Settings, chromadb_manager: Optional[ChromaDBManager] = None):
        """Initialize RAG retriever with simplified architecture."""
        self.settings = settings
        self.logger = logger.bind(log_type="CONVERSATION", component="rag_retriever")
        
        # Initialize ChromaDB manager
        self.chromadb_manager = chromadb_manager or ChromaDBManager(settings)
        
        # Single LLM instance - no dual management complexity
        self.llm = create_azure_chat_openai(settings)
        
        self.logger.info("RAGRetriever initialized", azure_endpoint=settings.azure_openai_endpoint)
    
    def _create_system_prompt(self, use_general_knowledge: bool = False) -> str:
        """Create system prompt for RAG responses."""
        base_prompt = """You are a helpful AI assistant that answers questions based on provided document context.

INSTRUCTIONS:
1. Use the provided document context to answer questions
2. Always cite your sources: "According to [source name]..."  
3. Be concise but comprehensive
4. Synthesize information from multiple sources when relevant

Context will be provided below, followed by the user's question."""
        
        if use_general_knowledge:
            return base_prompt + "\n\nNote: If context is insufficient, you may supplement with general knowledge, but clearly distinguish between document-based and general information."
        
        return base_prompt + "\n\nNote: If you cannot find relevant information in the context, say 'I don't have enough information to answer that question based on the provided documents.'"
    
    async def retrieve_relevant_chunks(
        self, 
        query: str, 
        k: int = 3,
        score_threshold: float = 0.2,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[LangChainDocument, float]]:
        """Retrieve relevant document chunks for a query."""
        self.logger.info("Retrieving relevant chunks", query_length=len(query), k=k)
        
        results = await self.chromadb_manager.search(
            query=query,
            k=k,
            score_threshold=score_threshold,
            filter_metadata=filter_metadata
        )
        
        self.logger.info("Retrieved relevant chunks", result_count=len(results))
        return results
    
    async def generate_rag_response(self, rag_query: RAGQuery) -> RAGResponse:
        """Generate a RAG response for the given query."""
        self.logger.info("Generating RAG response", query_length=len(rag_query.query))
        
        try:
            # Retrieve relevant chunks
            retrieved_chunks = await self.retrieve_relevant_chunks(
                query=rag_query.query,
                k=rag_query.k,
                score_threshold=rag_query.score_threshold
            )
            
            if not retrieved_chunks:
                return RAGResponse(
                    answer="I don't have any relevant documents to answer your question. Please upload some documents first or try rephrasing your question.",
                    sources=[],
                    retrieved_chunks=[],
                    confidence_score=0.0,
                    token_usage={}
                )
            
            # Prepare context from retrieved chunks
            context_parts = []
            sources = set()
            
            for doc, score in retrieved_chunks:
                # Access LangChain Document properties
                source = doc.metadata.get("source", "unknown")
                context_parts.append(f"Source: {source}\nContent: {doc.page_content}\n")
                sources.add(source)
            
            context = "\n---\n".join(context_parts)
            
            # Generate response
            response_text, token_usage = await self._generate_response_with_context(
                query=rag_query.query,
                context=context,
                use_general_knowledge=rag_query.use_general_knowledge
            )
            
            # Calculate confidence score
            avg_retrieval_score = sum(score for _, score in retrieved_chunks) / len(retrieved_chunks)
            confidence_score = min(avg_retrieval_score, 1.0)
            
            # Extract just the documents for the response
            retrieved_docs = [doc for doc, score in retrieved_chunks]
            
            response = RAGResponse(
                answer=response_text,
                sources=list(sources) if rag_query.include_sources else [],
                retrieved_chunks=retrieved_docs,
                confidence_score=confidence_score,
                token_usage=token_usage
            )
            
            self.logger.info("RAG response generated successfully", 
                           response_length=len(response_text), 
                           source_count=len(sources))
            return response
            
        except Exception as e:
            self.logger.error("Failed to generate RAG response", error=str(e))
            return RAGResponse(
                answer=f"I encountered an error while processing your question: {str(e)}",
                sources=[],
                retrieved_chunks=[],
                confidence_score=0.0,
                token_usage={}
            )
    
    async def _generate_response_with_context(
        self, 
        query: str, 
        context: str,
        use_general_knowledge: bool = False
    ) -> Tuple[str, Dict[str, int]]:
        """Embeds RAG response as context into message and uses System Prompt to control the LLM"""
        try:
            system_prompt = self._create_system_prompt(use_general_knowledge)
            
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"Context: {context}\n\nQuestion: {query}")
            ]
            
            # Generate response using LangChain directly
            response = await self.llm.ainvoke(messages)
            
            response_text = response.content
            token_usage = getattr(response, 'response_metadata', {}).get('token_usage', {})
            
            return response_text, token_usage
            
        except Exception as e:
            self.logger.error("Failed to generate response with context", error=str(e))
            raise

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on RAG retriever components."""
        try:
            # Check ChromaDB health
            chromadb_health = await self.chromadb_manager.health_check()
            
            # Check LLM health
            llm_health = {
                "status": "healthy" if self.llm is not None else "unhealthy",
                "model": getattr(self.llm, 'model_name', 'unknown')
            }
            
            overall_status = "healthy" if (
                chromadb_health["status"] == "healthy" and
                llm_health["status"] == "healthy"
            ) else "degraded"
            
            return {
                "status": overall_status,
                "chromadb": chromadb_health,
                "llm": llm_health,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }