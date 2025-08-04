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
from datetime import datetime

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
            
            # Document management section
            st.subheader("📋 Document Database")
            self._render_document_database()
            
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
            
            # Use toast notification for document upload success
            st.toast(f"📄 Successfully processed {total_files} documents!", icon="✅")
            st.rerun()
            
        except Exception as e:
            # Use toast notification for document upload errors
            st.toast(f"❌ Error processing documents: {str(e)}", icon="🚨")
            self.logger.error(
                "Document processing failed in Streamlit",
                error=str(e)
            )
    
    def _render_document_database(self):
        """Render the comprehensive document database management interface."""
        try:
            # Get documents from ChromaDB
            documents = asyncio.run(st.session_state.chromadb_manager.get_documents_summary())
            
            if not documents:
                st.info("No documents in database yet. Upload some documents to get started!")
                return
            
            # Show refresh button
            col1, col2 = st.columns([1, 3])
            with col1:
                if st.button("🔄 Refresh", help="Refresh document list"):
                    st.rerun()
            
            # Documents table
            st.write("**Documents in ChromaDB:**")
            
            for doc in documents:
                with st.container():
                    # Create expandable section for each document
                    with st.expander(f"📄 {doc['filename']} ({doc['chunk_count']} chunks)"):
                        col1, col2 = st.columns([3, 1])
                        
                        with col1:
                            # Document details
                            st.write(f"**Filename:** {doc['filename']}")
                            st.write(f"**Type:** {doc['file_type'].upper()}")
                            st.write(f"**Chunks:** {doc['chunk_count']}")
                            
                            # Size formatting
                            size_mb = doc['size_bytes'] / (1024 * 1024) if doc['size_bytes'] > 0 else 0
                            st.write(f"**Size:** {size_mb:.2f} MB")
                            
                            # Upload timestamp formatting
                            upload_time = doc['upload_timestamp']
                            if upload_time != 'Unknown':
                                try:
                                    if isinstance(upload_time, str):
                                        # Try to parse ISO format
                                        dt = datetime.fromisoformat(upload_time.replace('Z', '+00:00'))
                                        upload_time = dt.strftime("%Y-%m-%d %H:%M:%S")
                                except:
                                    pass  # Keep original format if parsing fails
                            
                            st.write(f"**Uploaded:** {upload_time}")
                            st.write(f"**Document ID:** {doc['document_id']}")
                        
                        with col2:
                            # Delete button
                            delete_key = f"delete_db_{doc['filename']}_{doc['document_id']}"
                            if st.button("🗑️ Delete", key=delete_key, help="Delete this document from database"):
                                self._delete_document_from_database(doc['filename'])
            
            # Summary statistics
            total_docs = len(documents)
            total_chunks = sum(doc['chunk_count'] for doc in documents)
            total_size = sum(doc['size_bytes'] for doc in documents) / (1024 * 1024)
            
            st.divider()
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Documents", total_docs)
            with col2:
                st.metric("Total Chunks", total_chunks)
            with col3:
                st.metric("Total Size", f"{total_size:.1f} MB")
            
            # Danger zone - clear all documents
            with st.expander("⚠️ Danger Zone"):
                st.warning("**Warning:** This will delete ALL documents from the database!")
                if st.button("🗑️ Delete All Documents", type="secondary"):
                    if st.session_state.get('confirm_delete_all', False):
                        self._delete_all_documents()
                    else:
                        st.session_state.confirm_delete_all = True
                        st.info("Click again to confirm deletion of ALL documents.")
                        st.rerun()
                
                if st.session_state.get('confirm_delete_all', False):
                    if st.button("❌ Cancel", type="primary"):
                        st.session_state.confirm_delete_all = False
                        st.rerun()
            
        except Exception as e:
            st.error(f"Error loading document database: {str(e)}")
            self.logger.error("Error rendering document database", error=str(e))
    
    def _delete_document_from_database(self, filename: str):
        """Delete a document from ChromaDB database."""
        try:
            with st.spinner(f"Deleting {filename}..."):
                # Delete from ChromaDB
                success = asyncio.run(st.session_state.chromadb_manager.delete_document_by_filename(filename))
                
                if success:
                    # Use toast notification for success - much more readable!
                    st.toast(f"✅ Successfully deleted {filename}!", icon="🗑️")
                    
                    # Also remove from session state if it exists
                    st.session_state.uploaded_documents = [
                        doc for doc in st.session_state.uploaded_documents 
                        if doc.get('filename') != filename
                    ]
                    
                    # Reset confirmation state
                    if 'confirm_delete_all' in st.session_state:
                        del st.session_state.confirm_delete_all
                    
                    st.rerun()
                else:
                    # Use toast notification for failure
                    st.toast(f"❌ Failed to delete {filename}", icon="⚠️")
            
        except Exception as e:
            # Use toast notification for errors
            st.toast(f"⚠️ Error deleting {filename}: {str(e)}", icon="🚨")
            self.logger.error("Error deleting document from database", filename=filename, error=str(e))
    
    def _delete_all_documents(self):
        """Delete all documents from ChromaDB database."""
        try:
            with st.spinner("Deleting all documents..."):
                # Get all documents first
                documents = asyncio.run(st.session_state.chromadb_manager.get_documents_summary())
                
                deleted_count = 0
                for doc in documents:
                    try:
                        success = asyncio.run(st.session_state.chromadb_manager.delete_document_by_filename(doc['filename']))
                        if success:
                            deleted_count += 1
                    except Exception as e:
                        self.logger.error(f"Failed to delete {doc['filename']}", error=str(e))
                
                # Clear session state
                st.session_state.uploaded_documents = []
                st.session_state.confirm_delete_all = False
                
                if deleted_count > 0:
                    # Use toast notification for bulk delete success
                    st.toast(f"🗑️ Successfully deleted {deleted_count} documents!", icon="✅")
                else:
                    # Use toast notification for no deletion
                    st.toast("⚠️ No documents were deleted", icon="📭")
                
                st.rerun()
            
        except Exception as e:
            # Use toast notification for bulk delete errors
            st.toast(f"🚨 Error deleting documents: {str(e)}", icon="❌")
            self.logger.error("Error deleting all documents", error=str(e))
    
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