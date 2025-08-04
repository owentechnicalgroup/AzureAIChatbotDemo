"""
Main Streamlit application for RAG-enabled chatbot.
Replaces the CLI interface with a modern web UI.
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import List, Optional, Dict, Any
import uuid

import streamlit as st
import structlog

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from config.settings import get_settings, clear_settings_cache
from rag.document_processor import DocumentProcessor
from rag.vector_store import ChromaDBManager
from rag.retriever import RAGRetriever
from rag import RAGQuery

# Configure structured logging
logger = structlog.get_logger(__name__)


class StreamlitRAGApp:
    """Main Streamlit RAG application class."""
    
    def __init__(self):
        """Initialize the Streamlit RAG application."""
        # Force clear settings cache to get latest configuration
        clear_settings_cache()
        self.settings = get_settings()
        self.logger = logger.bind(
            log_type="SYSTEM",
            component="streamlit_app"
        )
        
        # Initialize session state
        self._initialize_session_state()
        
        # Configure page
        st.set_page_config(
            page_title="RAG-Enabled Chatbot",
            page_icon="🤖",
            layout="wide",
            initial_sidebar_state="expanded"
        )
        
    def _initialize_session_state(self):
        """Initialize Streamlit session state variables."""
        
        # Core components
        if "settings" not in st.session_state:
            st.session_state.settings = self.settings
        
        if "document_processor" not in st.session_state:
            st.session_state.document_processor = DocumentProcessor(self.settings)
        
        if "chromadb_manager" not in st.session_state:
            st.session_state.chromadb_manager = ChromaDBManager(self.settings)
        
        if "rag_retriever" not in st.session_state:
            st.session_state.rag_retriever = RAGRetriever(
                self.settings, 
                st.session_state.chromadb_manager
            )
        
        # Chat state
        if "messages" not in st.session_state:
            st.session_state.messages = []
        
        if "conversation_id" not in st.session_state:
            st.session_state.conversation_id = str(uuid.uuid4())
        
        # Document management state
        if "uploaded_documents" not in st.session_state:
            st.session_state.uploaded_documents = []
        
        if "processing_status" not in st.session_state:
            st.session_state.processing_status = {}
        
        # UI state
        if "show_sources" not in st.session_state:
            st.session_state.show_sources = True
        
        if "retrieval_k" not in st.session_state:
            st.session_state.retrieval_k = 3
        
        if "score_threshold" not in st.session_state:
            st.session_state.score_threshold = 0.2  # Lower threshold for better retrieval
    
    def render_sidebar(self):
        """Render the sidebar with document upload and management."""
        with st.sidebar:
            st.title("📚 Document Management")
            
            # Document upload section
            st.subheader("Upload Documents")
            uploaded_files = st.file_uploader(
                "Choose files to upload",
                accept_multiple_files=True,
                type=['pdf', 'docx', 'txt'],
                help="Upload PDF, DOCX, or TXT files to chat with your documents"
            )
            
            if uploaded_files:
                self._handle_file_upload(uploaded_files)
            
            # Document list section
            st.subheader("Uploaded Documents")
            self._render_document_list()
            
            # Retrieval settings
            st.subheader("⚙️ Settings")
            self._render_settings()
            
            # System status
            st.subheader("📊 System Status")
            self._render_system_status()
    
    def _handle_file_upload(self, uploaded_files):
        """Handle file upload and processing."""
        if not uploaded_files:
            return
        
        # Check if files are already uploaded
        new_files = []
        for file in uploaded_files:
            if file.name not in [doc["filename"] for doc in st.session_state.uploaded_documents]:
                new_files.append(file)
        
        if not new_files:
            st.info("All selected files are already uploaded.")
            return
        
        # Process new files
        if st.button("📤 Process Documents", key="process_docs"):
            self._process_uploaded_files(new_files)
    
    def _process_uploaded_files(self, uploaded_files):
        """Process uploaded files asynchronously."""
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            total_files = len(uploaded_files)
            
            for i, uploaded_file in enumerate(uploaded_files):
                status_text.text(f"Processing {uploaded_file.name}...")
                progress_bar.progress((i + 1) / total_files)
                
                # Read file content
                file_content = uploaded_file.read()
                
                # Process file
                document, chunks = asyncio.run(
                    st.session_state.document_processor.process_file(
                        file_path=Path(uploaded_file.name),
                        file_content=file_content,
                        source_name=uploaded_file.name
                    )
                )
                
                # Add to ChromaDB
                asyncio.run(
                    st.session_state.chromadb_manager.add_documents(
                        chunks=chunks,
                        document_metadata=document
                    )
                )
                
                # Update session state
                st.session_state.uploaded_documents.append({
                    "id": document.id,
                    "filename": document.filename,
                    "file_type": document.file_type,
                    "size_bytes": document.size_bytes,
                    "chunk_count": len(chunks),
                    "upload_time": document.upload_timestamp,
                    "status": "completed"
                })
            
            progress_bar.progress(1.0)
            status_text.text("✅ All documents processed successfully!")
            
            # Clear the progress indicators after a moment
            import time
            time.sleep(2)
            progress_bar.empty()
            status_text.empty()
            
            st.success(f"Successfully processed {total_files} documents!")
            st.rerun()
            
        except Exception as e:
            st.error(f"Error processing documents: {str(e)}")
            self.logger.error(
                "Document processing failed in Streamlit",
                error=str(e)
            )
    
    def _render_document_list(self):
        """Render the list of uploaded documents."""
        if not st.session_state.uploaded_documents:
            st.info("No documents uploaded yet.")
            return
        
        for doc in st.session_state.uploaded_documents:
            with st.container():
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.write(f"📄 **{doc['filename']}**")
                    st.caption(f"{doc['chunk_count']} chunks • {doc['file_type'].upper()}")
                
                with col2:
                    if st.button("🗑️", key=f"delete_{doc['id']}", help="Delete document"):
                        self._delete_document(doc['id'])
        
        # Document count summary
        total_docs = len(st.session_state.uploaded_documents)
        total_chunks = sum(doc['chunk_count'] for doc in st.session_state.uploaded_documents)
        st.caption(f"**Total: {total_docs} documents, {total_chunks} chunks**")
    
    def _delete_document(self, document_id: str):
        """Delete a document from the system."""
        try:
            # Remove from uploaded documents list
            st.session_state.uploaded_documents = [
                doc for doc in st.session_state.uploaded_documents 
                if doc['id'] != document_id
            ]
            
            # TODO: Remove from ChromaDB (would need to track chunk IDs)
            # For now, we'll just remove from the UI list
            # In a full implementation, we'd need to track chunk IDs per document
            
            st.success("Document removed from list!")
            st.rerun()
            
        except Exception as e:
            st.error(f"Error deleting document: {str(e)}")
    
    def _render_settings(self):
        """Render retrieval settings."""
        st.session_state.retrieval_k = st.slider(
            "Number of chunks to retrieve",
            min_value=1,
            max_value=10,
            value=st.session_state.retrieval_k,
            help="How many document chunks to use for answering questions"
        )
        
        st.session_state.score_threshold = st.slider(
            "Similarity threshold",
            min_value=0.0,
            max_value=1.0,
            value=st.session_state.score_threshold,
            step=0.1,
            help="Minimum similarity score for including chunks"
        )
        
        st.session_state.show_sources = st.checkbox(
            "Show sources",
            value=st.session_state.show_sources,
            help="Display source documents in responses"
        )
    
    def _render_system_status(self):
        """Render system status information."""
        try:
            # Get document count from ChromaDB
            doc_count = asyncio.run(st.session_state.chromadb_manager.get_document_count())
            
            st.metric("Documents in DB", doc_count)
            st.metric("Session Messages", len(st.session_state.messages))
            
            # Health check
            health = asyncio.run(st.session_state.rag_retriever.health_check())
            
            if health["status"] == "healthy":
                st.success("✅ System Healthy")
            else:
                st.warning("⚠️ System Issues")
                
        except Exception as e:
            st.error("❌ System Error")
            self.logger.error("System status check failed", error=str(e))
    
    def render_main_chat(self):
        """Render the main chat interface."""
        st.title("🤖 RAG-Enabled Chatbot")
        st.caption("Chat with your documents using AI-powered retrieval")
        
        # Display chat history
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                
                # Show sources if available and enabled
                if (message["role"] == "assistant" and 
                    st.session_state.show_sources and 
                    message.get("sources")):
                    
                    with st.expander("📚 Sources", expanded=False):
                        for source in message["sources"]:
                            st.caption(f"• {source}")
        
        # Chat input
        if prompt := st.chat_input("Ask a question about your documents..."):
            self._handle_user_message(prompt)
    
    def _handle_user_message(self, prompt: str):
        """Handle user message and generate response."""
        # Add user message to chat history
        st.session_state.messages.append({
            "role": "user",
            "content": prompt
        })
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Generate and display assistant response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    # Create RAG query
                    rag_query = RAGQuery(
                        query=prompt,
                        k=st.session_state.retrieval_k,
                        score_threshold=st.session_state.score_threshold,
                        include_sources=st.session_state.show_sources
                    )
                    
                    # Generate response
                    response = asyncio.run(
                        st.session_state.rag_retriever.generate_rag_response(rag_query)
                    )
                    
                    # Display response
                    st.markdown(response.answer)
                    
                    # Show sources if available and enabled
                    if st.session_state.show_sources and response.sources:
                        with st.expander("📚 Sources", expanded=False):
                            for source in response.sources:
                                st.caption(f"• {source}")
                    
                    # Add assistant message to chat history
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response.answer,
                        "sources": response.sources,
                        "confidence_score": response.confidence_score
                    })
                    
                    # Log the interaction
                    self.logger.info(
                        "RAG response generated in Streamlit",
                        query_length=len(prompt),
                        response_length=len(response.answer),
                        source_count=len(response.sources),
                        confidence_score=response.confidence_score
                    )
                    
                except Exception as e:
                    error_message = f"I encountered an error: {str(e)}"
                    st.error(error_message)
                    
                    # Add error to chat history
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": error_message,
                        "sources": [],
                        "confidence_score": 0.0
                    })
                    
                    self.logger.error(
                        "Error generating RAG response in Streamlit",
                        query=prompt[:100],
                        error=str(e)
                    )
    
    def render_header(self):
        """Render application header with controls."""
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            if st.button("🗑️ Clear Chat", help="Clear chat history"):
                st.session_state.messages = []
                st.rerun()
        
        with col2:
            if st.button("🔄 Refresh", help="Refresh the application"):
                st.rerun()
        
        with col3:
            if st.button("ℹ️ About", help="About this application"):
                self._show_about_dialog()
    
    def _show_about_dialog(self):
        """Show about dialog."""
        st.info("""
        **RAG-Enabled Chatbot**
        
        This application uses Retrieval-Augmented Generation (RAG) to answer questions based on your uploaded documents.
        
        Features:
        - Upload PDF, DOCX, and TXT files
        - AI-powered document search
        - Source attribution
        - Configurable retrieval settings
        
        Built with Streamlit, ChromaDB, and Azure OpenAI.
        """)
    
    def run(self):
        """Run the main Streamlit application."""
        try:
            # Render header controls
            self.render_header()
            
            # Render sidebar
            self.render_sidebar()
            
            # Render main chat interface
            self.render_main_chat()
            
        except Exception as e:
            st.error(f"Application error: {str(e)}")
            self.logger.error(
                "Streamlit application error",
                error=str(e)
            )


def main():
    """Main entry point for the Streamlit application."""
    try:
        app = StreamlitRAGApp()
        app.run()
    except Exception as e:
        st.error(f"Failed to start application: {str(e)}")
        logger.error("Failed to start Streamlit app", error=str(e))


if __name__ == "__main__":
    main()