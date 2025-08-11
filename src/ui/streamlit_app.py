"""
Final Streamlit RAG Application with User-Controlled General Knowledge Toggle.

This application allows users to choose between:
1. Strict Document-Only Mode (RAG only)
2. General Knowledge Mode (RAG + fallback to general knowledge)

The user can toggle this setting in real-time to control the chatbot behavior.
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

from src.config.settings import get_settings, clear_settings_cache
from src.chatbot.agent import ChatbotAgent

# Import new separated RAG architecture components
from src.document_management import DocumentManager
from src.rag_access.rag_tool import RAGSearchTool

# Configure structured logging
logger = structlog.get_logger(__name__)


class FlexibleRAGStreamlitApp:
    """Streamlit RAG application with user-controlled general knowledge toggle."""
    
    def __init__(self):
        """Initialize the Streamlit RAG application."""
        clear_settings_cache()
        self.settings = get_settings()
        self.logger = logger.bind(
            log_type="SYSTEM",
            component="flexible_rag_streamlit_app"
        )
        
        self._initialize_session_state()
        
        st.set_page_config(
            page_title="RAG Chatbot - Flexible Mode",
            page_icon="🤖",
            layout="wide",
            initial_sidebar_state="expanded"
        )
        
    def _initialize_session_state(self):
        """Initialize Streamlit session state variables."""
        
        if "settings" not in st.session_state:
            st.session_state.settings = self.settings
        
        # Document management - using new separated architecture
        if "document_manager" not in st.session_state:
            st.session_state.document_manager = DocumentManager(self.settings)
        
        # RAG tool - using new separated architecture
        if "rag_tool" not in st.session_state:
            st.session_state.rag_tool = RAGSearchTool(self.settings)
        
        # Banking tools
        if "banking_tools" not in st.session_state:
            banking_tools = []
            try:
                from src.tools.call_report.langchain_toolset import LangChainCallReportToolset
                toolset = LangChainCallReportToolset(self.settings)
                if toolset.is_available():
                    banking_tools.extend(toolset.get_tools())
            except Exception as e:
                self.logger.warning("Banking tools not available", error=str(e))
            st.session_state.banking_tools = banking_tools
        
        # ChatbotAgent with flexible configuration
        if "chatbot_agent" not in st.session_state:
            self._create_chatbot_agent()
        
        # Chat state
        if "messages" not in st.session_state:
            st.session_state.messages = []
        
        if "conversation_id" not in st.session_state:
            st.session_state.conversation_id = str(uuid.uuid4())
        
        # Document state
        if "uploaded_documents" not in st.session_state:
            st.session_state.uploaded_documents = []
        
        # UI control state
        if "use_general_knowledge" not in st.session_state:
            st.session_state.use_general_knowledge = False  # Default to strict mode
        
        if "show_sources" not in st.session_state:
            st.session_state.show_sources = True
    
    def _create_chatbot_agent(self):
        """Create or recreate the chatbot agent with current settings."""
        # Collect all available tools
        all_tools = []
        
        # Add RAG tool if available
        if st.session_state.rag_tool.is_available:
            all_tools.append(st.session_state.rag_tool)
        
        # Add banking tools
        all_tools.extend(st.session_state.banking_tools)
        
        # Create agent with standard configuration
        st.session_state.chatbot_agent = ChatbotAgent(
            settings=self.settings,
            tools=all_tools,
            enable_multi_step=True,
            conversation_id=st.session_state.get('conversation_id', str(uuid.uuid4()))
        )
    
    def _get_rag_mode_description(self) -> str:
        """Get description of current RAG mode."""
        if st.session_state.use_general_knowledge:
            return "**Hybrid Mode**: Documents first, general knowledge if needed"
        else:
            return "**Document-Only Mode**: Only responds based on uploaded documents"
    
    def run(self):
        """Run the main Streamlit application."""
        st.title("🤖 RAG Chatbot - Flexible Mode")
        st.markdown("**Control whether the chatbot uses only documents or can fall back to general knowledge.**")
        
        # Show current mode prominently
        mode_description = self._get_rag_mode_description()
        if st.session_state.use_general_knowledge:
            st.info(f"🔄 {mode_description}")
        else:
            st.warning(f"🔒 {mode_description}")
        
        # Show control and status
        self._show_rag_controls()
        
        # Create tabs
        tab1, tab2, tab3, tab4 = st.tabs(["💬 Chat", "📚 Documents", "🧪 Testing", "⚙️ System"])
        
        with tab1:
            self._render_chat_interface()
        
        with tab2:
            self._render_document_management()
        
        with tab3:
            self._render_testing_interface()
        
        with tab4:
            self._render_system_status()
    
    def _show_rag_controls(self):
        """Show RAG mode controls and status."""
        with st.container():
            col1, col2, col3 = st.columns([2, 2, 2])
            
            with col1:
                # Main control toggle
                new_general_knowledge = st.checkbox(
                    "🧠 Use AI General Knowledge",
                    value=st.session_state.use_general_knowledge,
                    help="When enabled: Use documents first, fall back to general knowledge if no documents found.\n"
                         "When disabled: Only respond based on uploaded documents, refuse general knowledge questions.",
                    key="general_knowledge_toggle"
                )
                
                # If the setting changed, update the RAG tool configuration
                if new_general_knowledge != st.session_state.use_general_knowledge:
                    st.session_state.use_general_knowledge = new_general_knowledge
                    # Note: We'll apply this setting when making RAG queries
            
            with col2:
                # RAG tool status
                rag_available = st.session_state.rag_tool.is_available
                if rag_available:
                    st.success("✅ RAG Tool: Available")
                else:
                    st.error("❌ RAG Tool: Not Available")
                
                # Document count
                try:
                    stats = asyncio.run(st.session_state.document_manager.get_statistics())
                    doc_count = stats.total_documents
                    if doc_count > 0:
                        st.metric("Documents", doc_count)
                    else:
                        st.info("📄 No documents uploaded")
                except Exception:
                    st.warning("📄 Documents: Unknown")
            
            with col3:
                # Agent status
                agent = st.session_state.chatbot_agent
                tool_count = len(agent.tools) if hasattr(agent, 'tools') else 0
                st.metric("Agent Tools", tool_count)
                
                # Show current effective mode
                if st.session_state.use_general_knowledge:
                    st.success("🔄 Hybrid Mode Active")
                else:
                    st.warning("🔒 Strict Mode Active")
    
    def _render_chat_interface(self):
        """Render the main chat interface."""
        
        # Settings in sidebar
        with st.sidebar:
            st.header("⚙️ Chat Settings")
            
            # Show current mode
            mode_color = "blue" if st.session_state.use_general_knowledge else "orange"
            mode_text = "Hybrid" if st.session_state.use_general_knowledge else "Document-Only"
            st.markdown(f"**Current Mode:** :{mode_color}[{mode_text}]")
            
            # Additional settings
            st.session_state.show_sources = st.checkbox(
                "📚 Show Sources", 
                value=st.session_state.show_sources,
                help="Display document sources in responses"
            )
            
            st.divider()
            
            # Quick test buttons
            st.subheader("🧪 Quick Tests")
            
            if st.button("📄 Test: Document Query"):
                self._test_document_query()
            
            if st.button("🧠 Test: General Knowledge"):
                self._test_general_knowledge_query()
        
        # Display chat messages
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                
                # Show processing mode and sources
                if "processing_mode" in message and message["role"] == "assistant":
                    mode = message["processing_mode"]
                    
                    # Show mode indicator
                    if mode == "multi-step":
                        if message.get("used_documents", False):
                            st.success("📚 Used documents")
                        else:
                            st.info("🧠 Used general knowledge")
                    
                    # Show sources if available
                    if st.session_state.show_sources and "sources" in message:
                        sources = message["sources"]
                        if sources:
                            with st.expander(f"📚 Sources ({len(sources)})"):
                                for i, source in enumerate(sources, 1):
                                    st.markdown(f"{i}. {source}")
        
        # Chat input
        if prompt := st.chat_input("Ask about your documents or general topics..."):
            self._handle_chat_input(prompt)
    
    def _handle_chat_input(self, prompt: str):
        """Handle user chat input with flexible RAG mode."""
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Generate response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..." if st.session_state.use_general_knowledge else "Searching documents only..."):
                try:
                    # For the flexible mode, we'll use a custom approach
                    response_data = self._generate_flexible_response(prompt)
                    
                    # Extract response content and metadata
                    response_content = response_data.get('content', 'I apologize, but I couldn\'t generate a response.')
                    processing_mode = response_data.get('processing_mode', 'unknown')
                    used_documents = response_data.get('used_documents', False)
                    sources = response_data.get('sources', [])
                    
                    # Display response
                    st.markdown(response_content)
                    
                    # Show processing mode info
                    if st.session_state.use_general_knowledge:
                        if used_documents:
                            st.success("📚 Found relevant documents and used them for the response")
                        else:
                            st.info("🧠 No relevant documents found, used general knowledge")
                    else:
                        if used_documents:
                            st.success("📚 Response based on uploaded documents")
                        else:
                            st.warning("🔒 No relevant documents found, cannot provide general knowledge")
                    
                    # Store message with metadata
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": response_content,
                        "processing_mode": processing_mode,
                        "used_documents": used_documents,
                        "sources": sources
                    })
                    
                except Exception as e:
                    error_msg = f"Sorry, I encountered an error: {str(e)}"
                    st.error(error_msg)
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": error_msg,
                        "processing_mode": "error"
                    })
    
    def _generate_flexible_response(self, prompt: str) -> Dict[str, Any]:
        """Generate response with flexible RAG mode control."""
        try:
            if st.session_state.use_general_knowledge:
                # Hybrid mode: Try documents first, fall back to general knowledge
                return self._generate_hybrid_response(prompt)
            else:
                # Strict mode: Documents only
                return self._generate_strict_response(prompt)
                
        except Exception as e:
            return {
                "content": f"I encountered an error: {str(e)}",
                "processing_mode": "error",
                "used_documents": False,
                "sources": []
            }
    
    def _generate_hybrid_response(self, prompt: str) -> Dict[str, Any]:
        """Generate response in hybrid mode (documents + general knowledge)."""
        # Try RAG tool with general knowledge enabled in hybrid mode
        try:
            rag_result = asyncio.run(st.session_state.rag_tool._arun(
                query=prompt,
                max_chunks=3,
                use_general_knowledge=True  # Enable general knowledge for hybrid mode
            ))
            
            # The key insight: with my SearchService fix, when using general knowledge
            # with low-relevance docs, the response WON'T contain "Sources used" 
            # because the SearchService filters them out
            has_relevant_documents = "Sources used" in rag_result
            
            # Extract sources only if they were actually included in the response
            sources = []
            if has_relevant_documents:
                sources = self._extract_sources_from_rag_result(rag_result)
            
            return {
                "content": rag_result,
                "processing_mode": "hybrid_documents_found" if has_relevant_documents else "hybrid_general_knowledge", 
                "used_documents": has_relevant_documents,
                "sources": sources
            }
                
        except Exception as e:
            # Fallback to agent
            response_data = st.session_state.chatbot_agent.process_message(
                user_message=prompt,
                conversation_id=st.session_state.conversation_id
            )
            
            return {
                "content": response_data.get('content', ''),
                "processing_mode": "hybrid_fallback",
                "used_documents": False,
                "sources": []
            }
    
    def _generate_strict_response(self, prompt: str) -> Dict[str, Any]:
        """Generate response in strict mode (documents only)."""
        try:
            # Use RAG tool with strict settings
            rag_result = asyncio.run(st.session_state.rag_tool._arun(
                query=prompt,
                max_chunks=3,
                use_general_knowledge=False  # Never use general knowledge
            ))
            
            # Check if we found documents by looking for sources
            has_documents = "Sources used" in rag_result or "• " in rag_result
            
            if has_documents:
                sources = self._extract_sources_from_rag_result(rag_result)
                return {
                    "content": rag_result,
                    "processing_mode": "strict_documents_found", 
                    "used_documents": True,
                    "sources": sources
                }
            else:
                # No documents found, provide strict refusal
                return {
                    "content": (
                        f"I don't have relevant documents in my knowledge base to answer your question about '{prompt}'. "
                        f"I'm in document-only mode and cannot provide general knowledge responses. "
                        f"Please upload relevant documents or enable general knowledge mode if you want broader answers."
                    ),
                    "processing_mode": "strict_no_documents",
                    "used_documents": False,
                    "sources": []
                }
                
        except Exception as e:
            return {
                "content": (
                    f"I encountered an error while searching documents: {str(e)}. "
                    f"I cannot provide general knowledge responses in document-only mode."
                ),
                "processing_mode": "strict_error",
                "used_documents": False,
                "sources": []
            }
    
    def _extract_sources_from_rag_result(self, rag_result: str) -> List[str]:
        """Extract sources from RAG result text."""
        sources = []
        lines = rag_result.split('\n')
        
        in_sources = False
        for line in lines:
            if 'Sources used' in line or 'sources found' in line.lower():
                in_sources = True
                continue
            elif in_sources and line.strip().startswith('•'):
                sources.append(line.strip())
            elif in_sources and not line.strip():
                break
        
        return sources
    
    def _test_document_query(self):
        """Test with a document-specific query."""
        test_prompt = "What documents are available in the knowledge base?"
        st.info(f"Testing with: '{test_prompt}'")
        
        try:
            response = self._generate_flexible_response(test_prompt)
            
            with st.expander("📊 Test Result", expanded=True):
                st.write(f"**Mode**: {response['processing_mode']}")
                st.write(f"**Used Documents**: {response['used_documents']}")
                st.write(f"**Sources**: {len(response.get('sources', []))}")
                st.text_area("Response", response['content'], height=150)
                
        except Exception as e:
            st.error(f"Test failed: {str(e)}")
    
    def _test_general_knowledge_query(self):
        """Test with a general knowledge query."""
        test_prompt = "What is the capital of France?"  # This should NOT be in banking documents
        st.info(f"Testing with: '{test_prompt}' (should not find documents)")
        st.info(f"Current toggle state: {'Hybrid Mode' if st.session_state.use_general_knowledge else 'Document-Only Mode'}")
        
        try:
            response = self._generate_flexible_response(test_prompt)
            
            with st.expander("📊 Test Result", expanded=True):
                st.write(f"**Mode**: {response['processing_mode']}")
                st.write(f"**Used Documents**: {response['used_documents']}")
                st.write(f"**Sources**: {len(response.get('sources', []))}")
                st.write(f"**Toggle State**: {st.session_state.use_general_knowledge}")
                
                if st.session_state.use_general_knowledge:
                    if response['used_documents']:
                        st.success("✅ Found documents and used them")
                    else:
                        st.info("ℹ️ No documents found, used general knowledge")
                else:
                    if response['used_documents']:
                        st.success("✅ Found documents and used them")
                    else:
                        st.warning("⚠️ No documents found, refused general knowledge")
                
                st.text_area("Response", response['content'], height=150)
                
        except Exception as e:
            st.error(f"Test failed: {str(e)}")
    
    def _render_document_management(self):
        """Render document management interface."""
        st.subheader("📚 Document Management")
        st.markdown("Upload documents to enable document-based responses.")
        
        # File upload
        uploaded_files = st.file_uploader(
            "Choose files to upload",
            accept_multiple_files=True,
            type=['pdf', 'docx', 'txt', 'md'],
            help="Upload documents to enable RAG responses"
        )
        
        if uploaded_files:
            if st.button("📤 Process Documents", type="primary"):
                self._process_uploaded_files(uploaded_files)
        
        # Show current documents
        st.subheader("📋 Current Documents")
        try:
            documents = asyncio.run(st.session_state.document_manager.list_documents())
            
            if documents:
                for i, doc in enumerate(documents):
                    with st.expander(f"📄 {doc['filename']} ({doc['chunk_count']} chunks)"):
                        col1, col2 = st.columns([3, 1])
                        
                        with col1:
                            st.write(f"**Type**: {doc['file_type'].upper()}")
                            st.write(f"**Chunks**: {doc['chunk_count']}")
                            st.write(f"**Size**: {doc['size_bytes'] / (1024*1024):.2f} MB")
                            st.write(f"**Uploaded**: {doc['upload_timestamp']}")
                        
                        with col2:
                            if st.button("🗑️ Delete", key=f"delete_{i}"):
                                self._delete_document(doc['filename'])
            else:
                st.info("📄 No documents uploaded yet.")
                
        except Exception as e:
            st.error(f"Error loading documents: {str(e)}")
    
    def _process_uploaded_files(self, uploaded_files):
        """Process uploaded files."""
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            total_files = len(uploaded_files)
            
            for i, uploaded_file in enumerate(uploaded_files):
                status_text.text(f"Processing {uploaded_file.name}...")
                progress_bar.progress((i + 1) / total_files)
                
                # Read file content
                file_content = uploaded_file.read()
                
                # Use the new DocumentManager to upload and process
                result = asyncio.run(
                    st.session_state.document_manager.upload_document(
                        file_path=Path(uploaded_file.name),
                        file_content=file_content,
                        source_name=uploaded_file.name
                    )
                )
                
                if result.success:
                    st.success(f"✅ Processed {uploaded_file.name} - {result.chunks_created} chunks")
                else:
                    st.warning(f"⚠️ Failed to process {uploaded_file.name}: {result.error}")
            
            progress_bar.progress(1.0)
            status_text.text("✅ All documents processed!")
            
            # Clear progress after a moment
            import time
            time.sleep(2)
            progress_bar.empty()
            status_text.empty()
            
            st.success("🎉 Documents processed! You can now ask questions about them.")
            st.balloons()
            st.rerun()
            
        except Exception as e:
            st.error(f"Error processing documents: {str(e)}")
    
    def _delete_document(self, filename: str):
        """Delete a document."""
        try:
            st.info(f"🗑️ Attempting to delete: {filename}")
            with st.spinner(f"Deleting {filename}..."):
                result = asyncio.run(
                    st.session_state.document_manager.delete_document(filename)
                )
            
            st.info(f"Delete result: success={result.success}, message={result.message}, error={result.error}")
            
            if result.success:
                st.success(f"✅ Deleted {filename}")
                # Force refresh of the page to update document list
                st.rerun()
            else:
                error_msg = result.error or result.message or "Unknown error"
                st.error(f"❌ Failed to delete {filename}: {error_msg}")
                
        except Exception as e:
            st.error(f"Error deleting document: {str(e)}")
            import traceback
            st.error(f"Traceback: {traceback.format_exc()}")
    
    def _render_testing_interface(self):
        """Render testing interface for both modes."""
        st.subheader("🧪 RAG Mode Testing")
        st.markdown("Test how the chatbot behaves in different modes with different types of questions.")
        
        # Current mode display
        current_mode = "Hybrid (Documents + General Knowledge)" if st.session_state.use_general_knowledge else "Document-Only"
        st.info(f"**Current Mode**: {current_mode}")
        
        # Test scenarios
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**📄 Document-Based Questions**")
            st.caption("These should find documents if available")
            
            if st.button("Test: Available Documents", key="test_docs"):
                self._test_document_query()
            
            if st.button("Test: Document Content", key="test_content"):
                test_prompt = "What is the main topic of the uploaded documents?"
                st.info(f"Testing: '{test_prompt}'")
                response = self._generate_flexible_response(test_prompt)
                st.text_area("Result", response['content'], height=100, key="content_result")
        
        with col2:
            st.write("**🧠 General Knowledge Questions**")
            st.caption("These require general knowledge if no docs available")
            
            if st.button("Test: Credit Compliance", key="test_credit"):
                self._test_general_knowledge_query()
            
            if st.button("Test: General Topic", key="test_general"):
                test_prompt = "What is artificial intelligence?"
                st.info(f"Testing: '{test_prompt}'")
                response = self._generate_flexible_response(test_prompt)
                st.text_area("Result", response['content'], height=100, key="general_result")
        
        # Mode comparison
        st.subheader("🔄 Mode Comparison")
        st.markdown("See how the same question is handled in different modes:")
        
        comparison_query = st.text_input("Enter a question to test in both modes:", 
                                       placeholder="What are the main requirements?")
        
        if comparison_query and st.button("🔍 Compare Modes"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Document-Only Mode**")
                original_mode = st.session_state.use_general_knowledge
                st.session_state.use_general_knowledge = False
                strict_response = self._generate_flexible_response(comparison_query)
                st.text_area("Document-Only Result", strict_response['content'], height=150, key="strict_compare")
                st.caption(f"Used documents: {strict_response['used_documents']}")
            
            with col2:
                st.write("**Hybrid Mode**")
                st.session_state.use_general_knowledge = True
                hybrid_response = self._generate_flexible_response(comparison_query)
                st.text_area("Hybrid Result", hybrid_response['content'], height=150, key="hybrid_compare")
                st.caption(f"Used documents: {hybrid_response['used_documents']}")
            
            # Restore original mode
            st.session_state.use_general_knowledge = original_mode
    
    def _render_system_status(self):
        """Render system status information."""
        st.subheader("⚙️ System Status")
        
        # Component status
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.write("**RAG Components**")
            rag_available = st.session_state.rag_tool.is_available
            st.metric("RAG Tool", "✅ Available" if rag_available else "❌ Not Available")
            
            try:
                stats = asyncio.run(st.session_state.document_manager.get_statistics())
                st.metric("Total Chunks", stats.total_chunks)
            except Exception:
                st.metric("Total Chunks", "Error")
        
        with col2:
            st.write("**Agent Configuration**")
            agent = st.session_state.chatbot_agent
            tool_count = len(agent.tools) if hasattr(agent, 'tools') else 0
            st.metric("Tools Loaded", tool_count)
            st.metric("Multi-step", "✅ Enabled" if agent.enable_multi_step else "❌ Disabled")
        
        with col3:
            st.write("**Current Session**")
            st.metric("Messages", len(st.session_state.messages))
            current_mode = "Hybrid" if st.session_state.use_general_knowledge else "Document-Only"
            st.metric("Current Mode", current_mode)
        
        # Detailed component info
        with st.expander("🔧 Detailed Component Information"):
            st.json({
                "rag_tool_available": st.session_state.rag_tool.is_available,
                "banking_tools_count": len(st.session_state.banking_tools),
                "agent_tool_count": len(st.session_state.chatbot_agent.tools) if hasattr(st.session_state.chatbot_agent, 'tools') else 0,
                "conversation_id": st.session_state.conversation_id,
                "use_general_knowledge": st.session_state.use_general_knowledge,
                "show_sources": st.session_state.show_sources
            })


def main():
    """Main entry point for the flexible RAG Streamlit application."""
    app = FlexibleRAGStreamlitApp()
    app.run()


if __name__ == "__main__":
    main()