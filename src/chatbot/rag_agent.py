"""
RAG-enabled chatbot agent for Streamlit interface.
Simplified version focused on RAG functionality without CLI complexity.
"""

import asyncio
import time
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

import structlog

from config.settings import Settings
from rag.document_processor import DocumentProcessor
from rag.vector_store import ChromaDBManager
from rag.retriever import RAGRetriever
from rag import RAGQuery, RAGResponse, DocumentChunk, Document
from services.logging_service import log_conversation_event, ConversationLogger

logger = structlog.get_logger(__name__)


class RAGChatbotAgent:
    """
    RAG-enabled chatbot agent optimized for Streamlit interface.
    
    Features:
    - Document processing and storage
    - RAG-based response generation
    - Conversation tracking and logging
    - Error handling with graceful degradation
    - Performance monitoring
    """
    
    def __init__(self, settings: Settings):
        """
        Initialize RAG chatbot agent.
        
        Args:
            settings: Application settings
        """
        self.settings = settings
        self.conversation_id = str(uuid.uuid4())
        
        self.logger = logger.bind(
            log_type="CONVERSATION",
            component="rag_chatbot_agent",
            conversation_id=self.conversation_id
        )
        
        # Initialize RAG components
        try:
            self.document_processor = DocumentProcessor(settings)
            self.chromadb_manager = ChromaDBManager(settings)
            self.rag_retriever = RAGRetriever(settings, self.chromadb_manager)
            
            self.logger.info("RAG chatbot agent initialized successfully")
            
        except Exception as e:
            self.logger.error(
                "Failed to initialize RAG chatbot agent",
                error=str(e),
                error_type=type(e).__name__
            )
            raise
        
        # Performance tracking
        self._conversation_start_time = time.time()
        self._message_count = 0
        self._total_response_time = 0.0
        
        # State management
        self._is_active = True
        self._last_error = None
    
    async def process_documents(
        self, 
        file_data: List[tuple[str, bytes]],
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Process multiple documents and add them to the vector store.
        
        Args:
            file_data: List of (filename, file_content) tuples
            progress_callback: Optional callback for progress updates
            
        Returns:
            Processing results dictionary
        """
        processing_start = time.time()
        
        try:
            self.logger.info(
                "Starting document processing",
                file_count=len(file_data)
            )
            
            processed_documents = []
            total_chunks = 0
            failed_files = []
            
            for i, (filename, file_content) in enumerate(file_data):
                try:
                    if progress_callback:
                        progress_callback(i / len(file_data), f"Processing {filename}...")
                    
                    # Process individual file
                    document, chunks = await self.document_processor.process_file(
                        file_path=filename,
                        file_content=file_content,
                        source_name=filename
                    )
                    
                    # Add to ChromaDB
                    await self.chromadb_manager.add_documents(
                        chunks=chunks,
                        document_metadata=document
                    )
                    
                    processed_documents.append(document)
                    total_chunks += len(chunks)
                    
                    self.logger.info(
                        "Document processed successfully",
                        filename=filename,
                        chunk_count=len(chunks)
                    )
                    
                except Exception as e:
                    failed_files.append({
                        "filename": filename,
                        "error": str(e)
                    })
                    
                    self.logger.error(
                        "Failed to process document",
                        filename=filename,
                        error=str(e)
                    )
            
            if progress_callback:
                progress_callback(1.0, "Processing complete!")
            
            processing_time = time.time() - processing_start
            
            result = {
                "success": True,
                "processed_count": len(processed_documents),
                "total_chunks": total_chunks,
                "failed_count": len(failed_files),
                "failed_files": failed_files,
                "processing_time": processing_time,
                "documents": processed_documents
            }
            
            self.logger.info(
                "Document processing completed",
                **{k: v for k, v in result.items() if k != "documents"}
            )
            
            return result
            
        except Exception as e:
            self.logger.error(
                "Document processing failed",
                error=str(e),
                file_count=len(file_data)
            )
            
            return {
                "success": False,
                "error": str(e),
                "processed_count": 0,
                "failed_count": len(file_data),
                "processing_time": time.time() - processing_start
            }
    
    async def process_rag_message(
        self, 
        user_message: str,
        retrieval_k: int = 3,
        score_threshold: float = 0.5,
        include_sources: bool = True
    ) -> Dict[str, Any]:
        """
        Process user message with RAG and generate response.
        
        Args:
            user_message: User's input message
            retrieval_k: Number of chunks to retrieve
            score_threshold: Minimum similarity score
            include_sources: Whether to include source references
            
        Returns:
            Response dictionary with answer and metadata
        """
        start_time = time.time()
        message_id = str(uuid.uuid4())
        
        with ConversationLogger(
            conversation_id=self.conversation_id,
            user_id="streamlit_user"  # Generic user ID for Streamlit
        ) as conv_logger:
            
            try:
                if not user_message.strip():
                    raise ValueError("Empty message received")
                
                conv_logger.info(
                    "Processing RAG message",
                    message_length=len(user_message),
                    message_id=message_id,
                    retrieval_k=retrieval_k,
                    score_threshold=score_threshold
                )
                
                # Create RAG query
                rag_query = RAGQuery(
                    query=user_message,
                    k=retrieval_k,
                    score_threshold=score_threshold,
                    include_sources=include_sources
                )
                
                # Generate RAG response
                rag_response = await self.rag_retriever.generate_rag_response(rag_query)
                
                # Calculate response time
                response_time = time.time() - start_time
                
                # Update performance metrics
                self._update_performance_metrics(
                    response_time=response_time,
                    token_usage=rag_response.token_usage
                )
                
                # Log conversation event
                log_conversation_event(
                    event="rag_response_generated",
                    conversation_id=self.conversation_id,
                    user_message=user_message,
                    assistant_response=rag_response.answer,
                    token_usage=rag_response.token_usage,
                    response_time=response_time,
                    source_count=len(rag_response.sources),
                    confidence_score=rag_response.confidence_score
                )
                
                # Prepare response
                response = {
                    "success": True,
                    "answer": rag_response.answer,
                    "sources": rag_response.sources,
                    "confidence_score": rag_response.confidence_score,
                    "retrieved_chunks": len(rag_response.retrieved_chunks),
                    "response_time": response_time,
                    "token_usage": rag_response.token_usage,
                    "message_id": message_id,
                    "conversation_id": self.conversation_id,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                conv_logger.info(
                    "RAG message processed successfully",
                    response_time=response_time,
                    response_length=len(rag_response.answer),
                    source_count=len(rag_response.sources)
                )
                
                return response
                
            except Exception as e:
                # Handle errors with graceful degradation
                response_time = time.time() - start_time
                
                error_response = self._handle_processing_error(
                    error=e,
                    user_message=user_message,
                    response_time=response_time,
                    message_id=message_id
                )
                
                conv_logger.error(
                    "RAG message processing failed",
                    error=str(e),
                    response_time=response_time
                )
                
                return error_response
    
    def _handle_processing_error(
        self,
        error: Exception,
        user_message: str,
        response_time: float,
        message_id: str
    ) -> Dict[str, Any]:
        """Handle processing errors with graceful degradation."""
        
        self._last_error = error
        
        # Log the error
        log_conversation_event(
            event="error_occurred",
            conversation_id=self.conversation_id,
            user_message=user_message,
            error=str(error),
            processing_time=response_time
        )
        
        # Generate graceful error response based on error type
        if "chromadb" in str(error).lower() or "vector" in str(error).lower():
            error_message = "I'm having trouble accessing the document database. Please try again or check if documents are properly uploaded."
        elif "azure" in str(error).lower() or "openai" in str(error).lower():
            error_message = "I'm having trouble connecting to the AI service. Please try again in a moment."
        elif "document" in str(error).lower() or "file" in str(error).lower():
            error_message = "There was an issue processing your documents. Please try re-uploading them."
        else:
            error_message = "I encountered an unexpected issue. Please try rephrasing your question or contact support if the problem persists."
        
        return {
            "success": False,
            "answer": error_message,
            "sources": [],
            "confidence_score": 0.0,
            "retrieved_chunks": 0,
            "response_time": response_time,
            "token_usage": {},
            "error": str(error),
            "error_type": type(error).__name__,
            "message_id": message_id,
            "conversation_id": self.conversation_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    def _update_performance_metrics(
        self,
        response_time: float,
        token_usage: Optional[Dict[str, Any]] = None
    ):
        """Update performance tracking metrics."""
        self._message_count += 1
        self._total_response_time += response_time
        
        # Log performance metrics
        from services.logging_service import log_performance_metrics
        
        metrics = {
            'message_count': self._message_count,
            'average_response_time': self._total_response_time / self._message_count,
            'conversation_duration': time.time() - self._conversation_start_time
        }
        
        if token_usage:
            metrics.update(token_usage)
        
        log_performance_metrics(
            operation="rag_message_processing",
            duration=response_time,
            success=True,
            **metrics
        )
    
    async def get_document_list(self) -> List[Dict[str, Any]]:
        """
        Get list of documents in the vector store.
        
        Returns:
            List of document metadata dictionaries
        """
        try:
            documents = await self.chromadb_manager.list_documents()
            
            self.logger.debug(
                "Retrieved document list",
                document_count=len(documents)
            )
            
            return documents
            
        except Exception as e:
            self.logger.error(
                "Failed to retrieve document list",
                error=str(e)
            )
            return []
    
    async def delete_document(self, document_id: str) -> bool:
        """
        Delete a document from the vector store.
        
        Args:
            document_id: ID of document to delete
            
        Returns:
            True if deletion was successful
        """
        try:
            success = await self.chromadb_manager.delete_documents([document_id])
            
            self.logger.info(
                "Document deleted",
                document_id=document_id,
                success=success
            )
            
            return success
            
        except Exception as e:
            self.logger.error(
                "Failed to delete document",
                document_id=document_id,
                error=str(e)
            )
            return False
    
    async def get_conversation_statistics(self) -> Dict[str, Any]:
        """Get comprehensive conversation statistics."""
        try:
            # Get ChromaDB statistics
            doc_count = await self.chromadb_manager.get_document_count()
            
            # Calculate agent statistics
            stats = {
                'conversation_id': self.conversation_id,
                'message_count': self._message_count,
                'average_response_time': (
                    self._total_response_time / self._message_count 
                    if self._message_count > 0 else 0.0
                ),
                'total_response_time': self._total_response_time,
                'session_duration': time.time() - self._conversation_start_time,
                'documents_in_store': doc_count,
                'last_error': str(self._last_error) if self._last_error else None,
                'is_active': self._is_active,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            return stats
            
        except Exception as e:
            self.logger.error(
                "Failed to get conversation statistics",
                error=str(e)
            )
            return {
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform comprehensive health check.
        
        Returns:
            Health status dictionary
        """
        try:
            # Check RAG retriever health
            rag_health = await self.rag_retriever.health_check()
            
            # Overall health assessment
            is_healthy = (
                rag_health['status'] == 'healthy' and
                self._is_active
            )
            
            return {
                'status': 'healthy' if is_healthy else 'degraded',
                'rag_retriever': rag_health,
                'agent': {
                    'is_active': self._is_active,
                    'message_count': self._message_count,
                    'last_error': str(self._last_error) if self._last_error else None,
                    'uptime': time.time() - self._conversation_start_time
                },
                'conversation_id': self.conversation_id,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'conversation_id': self.conversation_id,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    def shutdown(self):
        """Gracefully shutdown the agent."""
        self.logger.info("Shutting down RAG chatbot agent")
        self._is_active = False
    
    def __repr__(self) -> str:
        """String representation of the RAG chatbot agent."""
        return (
            f"RAGChatbotAgent("
            f"id={self.conversation_id[:8]}, "
            f"messages={self._message_count}, "
            f"active={self._is_active}"
            f")"
        )