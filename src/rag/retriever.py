"""
RAG retrieval system for combining document search with language model generation.
Orchestrates ChromaDB search and Azure OpenAI response generation.
"""

import asyncio
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timezone

import structlog
from langchain.chains import RetrievalQAWithSourcesChain
from langchain.prompts.chat import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)
from langchain_openai import AzureChatOpenAI

from config.settings import Settings
from services.azure_client import AzureOpenAIClient
from .import RAGQuery, RAGResponse, DocumentChunk
from .vector_store import ChromaDBManager

logger = structlog.get_logger(__name__)


class RAGRetriever:
    """
    Handles retrieval-augmented generation using ChromaDB and Azure OpenAI.
    
    Features:
    - Document similarity search
    - Context-aware response generation
    - Source attribution and citation
    - Configurable retrieval parameters
    - Integration with existing Azure OpenAI patterns
    """
    
    def __init__(self, settings: Settings, chromadb_manager: Optional[ChromaDBManager] = None):
        """
        Initialize RAG retriever.
        
        Args:
            settings: Application settings
            chromadb_manager: Optional ChromaDB manager instance
        """
        self.settings = settings
        self.logger = logger.bind(
            log_type="CONVERSATION",
            component="rag_retriever"
        )
        
        # Initialize ChromaDB manager
        self.chromadb_manager = chromadb_manager or ChromaDBManager(settings)
        
        # Initialize Azure OpenAI client for generation
        self.azure_client = AzureOpenAIClient(settings)
        
        # Note: system prompt is now created dynamically based on query parameters
        
        # Initialize LangChain components
        self._llm = None
        self._qa_chain = None
        
        self.logger.info(
            "RAGRetriever initialized",
            azure_endpoint=settings.azure_openai_endpoint
        )
    
    def _create_system_prompt(self, use_general_knowledge: bool = False) -> str:
        """Create system prompt for RAG responses.
        
        Args:
            use_general_knowledge: Whether to allow AI to use general knowledge as fallback
        """
        if use_general_knowledge:
            return """You are a helpful AI assistant that answers questions based on provided document context.

INSTRUCTIONS:
1. First, try to answer using only the provided document context
2. If the context is insufficient, you may supplement with general knowledge as a fallback
3. Always be clear about your sources:
   - For context: "According to [source name]..." or "Based on the information in [source name]..."
   - For general knowledge: "Based on general knowledge (not from your documents)..." or "From what I know generally..."
4. Prefer document context over general knowledge when both are available
5. Be concise but comprehensive in your responses
6. If multiple documents contain relevant information, synthesize the information coherently

When combining sources, clearly separate document-based information from general knowledge.

Context will be provided below, followed by the user's question."""
        else:
            return """You are a helpful AI assistant that answers questions based on provided document context.

INSTRUCTIONS:
1. Use only the information provided in the context to answer questions
2. If you cannot find relevant information in the context, say "I don't have enough information to answer that question based on the provided documents"
3. Always cite your sources by mentioning the document name or source
4. Be concise but comprehensive in your responses
5. If multiple documents contain relevant information, synthesize the information coherently

When referencing sources, use this format: "According to [source name]..." or "Based on the information in [source name]..."

Context will be provided below, followed by the user's question."""
    
    async def _get_llm(self) -> AzureChatOpenAI:
        """Get or create Azure OpenAI LangChain LLM instance."""
        if self._llm is None:
            try:
                self._llm = AzureChatOpenAI(
                    azure_endpoint=self.settings.azure_openai_endpoint,
                    api_key=self.settings.azure_openai_api_key,
                    api_version=self.settings.azure_openai_api_version,
                    azure_deployment=self.settings.azure_openai_deployment,
                    temperature=self.settings.temperature,
                    max_tokens=self.settings.max_tokens,
                    timeout=self.settings.request_timeout,
                    streaming=False  # For now, disable streaming in RAG chain
                )
                
                self.logger.debug("Azure OpenAI LLM initialized for RAG")
                
            except Exception as e:
                self.logger.error(
                    "Failed to initialize Azure OpenAI LLM",
                    error=str(e)
                )
                raise
        
        return self._llm
    
    async def retrieve_relevant_chunks(
        self, 
        query: str, 
        k: int = 3, 
        score_threshold: float = 0.2,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[DocumentChunk, float]]:
        """
        Retrieve relevant document chunks for a query.
        
        Args:
            query: Search query
            k: Number of chunks to retrieve
            score_threshold: Minimum similarity score
            filter_metadata: Optional metadata filters
            
        Returns:
            List of (DocumentChunk, similarity_score) tuples
        """
        try:
            self.logger.info(
                "Retrieving relevant chunks",
                query_length=len(query),
                k=k,
                score_threshold=score_threshold
            )
            
            # Search ChromaDB for relevant chunks
            results = await self.chromadb_manager.search(
                query=query,
                k=k,
                score_threshold=score_threshold,
                filter_metadata=filter_metadata
            )
            
            self.logger.info(
                "Retrieved relevant chunks",
                result_count=len(results),
                avg_score=sum(score for _, score in results) / len(results) if results else 0
            )
            
            return results
            
        except Exception as e:
            self.logger.error(
                "Failed to retrieve relevant chunks",
                query=query[:100],
                error=str(e)
            )
            raise
    
    async def generate_rag_response(self, rag_query: RAGQuery) -> RAGResponse:
        """
        Generate a RAG response for the given query.
        
        Args:
            rag_query: RAG query parameters
            
        Returns:
            RAG response with answer and sources
        """
        try:
            self.logger.info(
                "Generating RAG response",
                query_length=len(rag_query.query),
                k=rag_query.k,
                score_threshold=rag_query.score_threshold
            )
            
            # Retrieve relevant chunks
            retrieved_chunks = await self.retrieve_relevant_chunks(
                query=rag_query.query,
                k=rag_query.k,
                score_threshold=rag_query.score_threshold
            )
            
            if not retrieved_chunks:
                # No relevant documents found
                response = RAGResponse(
                    answer="I don't have any relevant documents to answer your question. Please upload some documents first or try rephrasing your question.",
                    sources=[],
                    retrieved_chunks=[],
                    confidence_score=0.0,
                    token_usage={}
                )
                
                self.logger.warning(
                    "No relevant chunks found for query",
                    query=rag_query.query[:100]
                )
                
                return response
            
            # Prepare context from retrieved chunks
            context_parts = []
            sources = set()
            chunk_objects = []
            
            for chunk, score in retrieved_chunks:
                context_parts.append(f"Source: {chunk.source}\nContent: {chunk.content}\n")
                sources.add(chunk.source)
                chunk_objects.append(chunk)
            
            context = "\n---\n".join(context_parts)
            
            # Generate response using Azure OpenAI
            response_text, token_usage = await self._generate_response_with_context(
                query=rag_query.query,
                context=context,
                use_general_knowledge=rag_query.use_general_knowledge
            )
            
            # Calculate confidence score based on retrieval scores
            avg_retrieval_score = sum(score for _, score in retrieved_chunks) / len(retrieved_chunks)
            confidence_score = min(avg_retrieval_score, 1.0)
            
            response = RAGResponse(
                answer=response_text,
                sources=list(sources) if rag_query.include_sources else [],
                retrieved_chunks=chunk_objects,
                confidence_score=confidence_score,
                token_usage=token_usage
            )
            
            self.logger.info(
                "RAG response generated successfully",
                response_length=len(response_text),
                source_count=len(sources),
                confidence_score=confidence_score
            )
            
            return response
            
        except Exception as e:
            self.logger.error(
                "Failed to generate RAG response",
                query=rag_query.query[:100],
                error=str(e)
            )
            
            # Return error response
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
        """
        Generate response using Azure OpenAI with provided context.
        
        Args:
            query: User query
            context: Retrieved document context
            use_general_knowledge: Whether to allow general knowledge fallback
            
        Returns:
            Tuple of (response_text, token_usage)
        """
        try:
            # Create dynamic system prompt based on settings
            system_prompt = self._create_system_prompt(use_general_knowledge)
            
            # Use the existing Azure OpenAI client for consistency
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Context: {context}\n\nQuestion: {query}"}
            ]
            
            # Generate response
            response_data = await self.azure_client.generate_response_async(
                messages=messages,
                conversation_id=f"rag_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )
            
            response_text = response_data.get('content', '')
            token_usage = response_data.get('metadata', {}).get('token_usage', {})
            
            return response_text, token_usage
            
        except Exception as e:
            self.logger.error(
                "Failed to generate response with context",
                error=str(e)
            )
            raise
    
    async def create_qa_chain(self) -> RetrievalQAWithSourcesChain:
        """
        Create LangChain QA chain with sources (legacy support).
        
        Note: This is kept for compatibility but the main RAG flow
        uses the direct Azure OpenAI client integration.
        
        Returns:
            RetrievalQAWithSourcesChain instance
        """
        try:
            if self._qa_chain is None:
                # Get ChromaDB as retriever
                db = await self.chromadb_manager.initialize_db()
                retriever = db.as_retriever(
                    search_type="similarity_score_threshold",
                    search_kwargs={
                        "k": 3,
                        "score_threshold": 0.2
                    }
                )
                
                # Get LLM
                llm = await self._get_llm()
                
                # Create prompt template
                system_template = """Use the following pieces of context to answer the users question. 
If you don't know the answer, just say that you don't know, don't try to make up an answer.
ALWAYS return a "SOURCES" part in your answer.
The "SOURCES" part should be a reference to the source of the document from which you got your answer.

Example of your response should be:

```
The answer is foo
SOURCES: xyz
```

Begin!
----------------
{summaries}"""
                
                messages = [
                    SystemMessagePromptTemplate.from_template(system_template),
                    HumanMessagePromptTemplate.from_template("{question}"),
                ]
                prompt = ChatPromptTemplate.from_messages(messages)
                
                self._qa_chain = RetrievalQAWithSourcesChain.from_chain_type(
                    llm=llm,
                    chain_type="stuff",
                    retriever=retriever,
                    return_source_documents=True,
                    chain_type_kwargs={"prompt": prompt}
                )
                
                self.logger.info("QA chain with sources created")
            
            return self._qa_chain
            
        except Exception as e:
            self.logger.error(
                "Failed to create QA chain",
                error=str(e)
            )
            raise
    
    async def answer_with_sources(self, question: str) -> Dict[str, Any]:
        """
        Answer question using LangChain QA chain (legacy method).
        
        Args:
            question: User question
            
        Returns:
            Dictionary with answer and sources
        """
        try:
            qa_chain = await self.create_qa_chain()
            
            # Run the chain in a thread to avoid blocking
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: qa_chain({"question": question})
            )
            
            self.logger.info(
                "QA chain response generated",
                question_length=len(question),
                answer_length=len(result.get("answer", "")),
                sources=result.get("sources", "")
            )
            
            return result
            
        except Exception as e:
            self.logger.error(
                "QA chain failed",
                question=question[:100],
                error=str(e)
            )
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on RAG retriever components.
        
        Returns:
            Health status dictionary
        """
        try:
            # Check ChromaDB health
            chromadb_health = await self.chromadb_manager.health_check()
            
            # Check Azure OpenAI client health
            azure_health = self.azure_client.health_check()
            
            overall_status = "healthy" if (
                chromadb_health["status"] == "healthy" and
                azure_health["status"] == "healthy"
            ) else "degraded"
            
            return {
                "status": overall_status,
                "chromadb": chromadb_health,
                "azure_openai": azure_health,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }