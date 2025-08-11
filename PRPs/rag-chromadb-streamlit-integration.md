name: "RAG with ChromaDB and Streamlit UI Replacement"
description: |

## Purpose
Comprehensive PRP for implementing RAG (Retrieval-Augmented Generation) capabilities using local ChromaDB vector database while replacing the existing CLI interface with a modern Streamlit web application.

---

## Goal
Replace the existing CLI chatbot with a Streamlit web application that includes RAG capabilities, allowing users to upload documents, create vector embeddings, and query against those documents through an intuitive web interface.

## Why
- **Enhanced User Experience**: Replace CLI with modern web interface for better accessibility
- **Document-Based Conversations**: Enable users to chat with their own documents (PDFs, DOCX, TXT)
- **Simplified Deployment**: Single web interface reduces complexity compared to dual CLI+Web
- **Better File Management**: Web interface provides intuitive document upload and management
- **Local Development Focus**: ChromaDB deployed locally with containerization planned for later

## What
A complete RAG-enabled Streamlit application featuring:
- Modern web UI replacing the existing CLI interface
- Document upload and processing (PDF, DOCX, TXT)
- Local ChromaDB vector database for persistent document storage
- LangChain integration for document chunking and retrieval
- Streamlit web UI with file upload and chat capabilities
- Integration with existing Azure OpenAI chatbot backend
- Document management features (list, delete uploaded docs)

### Success Criteria
- [ ] Streamlit web application successfully replaces CLI interface
- [ ] Documents can be uploaded and processed into vector embeddings
- [ ] Local ChromaDB runs in persistent mode with proper data retention
- [ ] RAG retrieval returns relevant document chunks with sources
- [ ] Document management features work (upload, list, delete)
- [ ] Integration maintains existing logging and observability patterns
- [ ] All validation gates pass (lint, tests, manual testing)

## All Needed Context

### Documentation & References
```yaml
# MUST READ - Include these in your context window
- url: https://docs.trychroma.com/docs/overview/introduction
  why: ChromaDB official documentation for vector database implementation
  
- url: https://python.langchain.com/docs/integrations/vectorstores/chroma/
  why: LangChain ChromaDB integration patterns and best practices
  
- url: https://docs.streamlit.io/
  why: Streamlit documentation for web UI implementation
  
- url: https://learn.microsoft.com/en-us/samples/azure-samples/container-apps-openai/container-apps-openai/
  why: Microsoft's official RAG implementation example
  
- file: examples/container-apps-openai/src/doc.py
  why: Reference implementation of RAG with ChromaDB and LangChain patterns
  
- file: examples/container-apps-openai/src/chat.py
  why: Chainlit/Streamlit integration patterns for chat interfaces
  
- file: src/chatbot/agent.py
  why: Existing chatbot agent patterns to maintain consistency
  
- file: src/config/settings.py
  why: Configuration management patterns and environment variable handling
  
- file: PLANNING.md
  why: Project architecture constraints and style guidelines
  
- file: CLAUDE.md
  why: Development rules and patterns to follow
```

### Current Codebase Tree
```bash
context-engineering-intro/
├── src/
│   ├── chatbot/
│   │   ├── agent.py              # Main chatbot agent
│   │   ├── conversation.py       # Conversation management
│   │   └── prompts.py           # System prompts
│   ├── config/
│   │   └── settings.py          # Configuration with Azure Key Vault
│   ├── services/
│   │   ├── azure_client.py      # Azure OpenAI client
│   │   └── logging_service.py   # Logging utilities
│   ├── observability/           # Structured logging system
│   └── utils/                   # Utility functions
├── examples/
│   └── container-apps-openai/   # Reference RAG implementation
├── infrastructure/              # Terraform IaC
└── scripts/                     # Deployment automation
```

### Desired Codebase Tree with New Files
```bash
context-engineering-intro/
├── src/
│   ├── rag/
│   │   ├── __init__.py
│   │   ├── document_processor.py    # Document upload and chunking
│   │   ├── vector_store.py          # Local ChromaDB integration
│   │   └── retriever.py             # Document retrieval logic
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── streamlit_app.py         # Main Streamlit application (replaces CLI)
│   │   ├── chat_interface.py        # Chat UI components
│   │   ├── file_upload.py           # File upload handling
│   │   └── document_manager.py      # Document management UI
│   └── chatbot/
│       └── rag_agent.py             # RAG-enabled chatbot agent
├── data/
│   └── chromadb/                    # Local ChromaDB storage
└── requirements-rag.txt             # Additional dependencies
```

### Known Gotchas & Library Quirks
```python
# CRITICAL: ChromaDB requires specific dependency versions
# ChromaDB 0.4.x has breaking changes from 0.3.x - use latest stable
# LangChain community package splits required: langchain-community for ChromaDB

# CRITICAL: Azure OpenAI embeddings have rate limits
# Use batch processing for large documents and implement retry logic
# Example: AzureOpenAIEmbeddings has chunk_size parameter (default 16)

# CRITICAL: Streamlit file upload limitations
# Default max file size is 200MB, configure via config.toml
# Files are stored in memory - implement streaming for large files

# CRITICAL: ChromaDB persistence requires explicit directory
# Must use persist_directory parameter in Chroma.from_documents()
# Local deployment: Use ./data/chromadb directory for persistence
# Directory must be writable and gitignored

# CRITICAL: LangChain text splitter chunk sizes
# RecursiveCharacterTextSplitter: 500-1000 tokens with 100-200 overlap
# PDF extraction can be messy - use PyPDF2 or pypdf for clean text

# CRITICAL: Our project uses structlog for logging
# All new components must use logger.bind(log_type="CATEGORY") pattern
# RAG operations should use log_type="CONVERSATION" or "SYSTEM"

# CRITICAL: Pydantic v2 compatibility
# Ensure all models use Pydantic v2 syntax (BaseModel, Field)
# Settings class already follows v2 patterns

# CRITICAL: Virtual environment usage
# Always use venv_linux for Python execution per CLAUDE.md rules
# All tests and linting must run in virtual environment
```

## Implementation Blueprint

### Data Models and Structure
```python
# Core data models for type safety and validation
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class DocumentChunk(BaseModel):
    """Individual document chunk with metadata."""
    id: str = Field(..., description="Unique chunk identifier")
    content: str = Field(..., description="Chunk text content")
    source: str = Field(..., description="Source document filename")
    page_number: Optional[int] = Field(None, description="Page number if applicable")
    chunk_index: int = Field(..., description="Index within document")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
class Document(BaseModel):
    """Document metadata and processing status."""
    id: str = Field(..., description="Unique document identifier")
    filename: str = Field(..., description="Original filename")
    file_type: str = Field(..., description="File extension")
    size_bytes: int = Field(..., description="File size in bytes")
    upload_timestamp: datetime = Field(default_factory=datetime.utcnow)
    processing_status: str = Field(default="pending", description="processing|completed|failed")
    chunk_count: int = Field(default=0, description="Number of chunks created")
    error_message: Optional[str] = Field(None, description="Error details if failed")

class RAGQuery(BaseModel):
    """RAG query with retrieval parameters."""
    query: str = Field(..., description="User query text")
    k: int = Field(default=3, description="Number of chunks to retrieve")
    score_threshold: float = Field(default=0.5, description="Minimum similarity score")
    include_sources: bool = Field(default=True, description="Include source references")

class RAGResponse(BaseModel):
    """RAG response with sources and metadata."""
    answer: str = Field(..., description="Generated response")
    sources: List[str] = Field(default_factory=list, description="Source references")
    retrieved_chunks: List[DocumentChunk] = Field(default_factory=list)
    confidence_score: float = Field(..., description="Response confidence 0-1")
    token_usage: Dict[str, int] = Field(default_factory=dict)
```

### List of Tasks to Complete (In Order)

```yaml
Task 1: "Setup RAG Dependencies and Configuration"
MODIFY requirements.txt:
  - ADD: chromadb>=0.4.15
  - ADD: langchain-community>=0.0.38
  - ADD: streamlit>=1.28.0
  - ADD: pypdf>=3.17.0
  - ADD: python-docx>=0.8.11
  - ADD: sentence-transformers>=2.2.2

MODIFY src/config/settings.py:
  - ADD ChromaDB configuration fields (local storage path)
  - ADD Streamlit configuration fields
  - PATTERN: Follow existing field definitions with Field() syntax
  - FOCUS: Local development settings (no container/deployment configs yet)

Task 2: "Create Document Processing Module"
CREATE src/rag/document_processor.py:
  - MIRROR pattern from: examples/container-apps-openai/src/doc.py lines 140-182
  - IMPLEMENT: DocumentProcessor class with async methods
  - METHODS: process_file(), extract_text(), chunk_document()
  - PATTERN: Use RecursiveCharacterTextSplitter from examples
  - ERROR HANDLING: Try/except with structured logging
  - LOGGING: Use logger.bind(log_type="SYSTEM")

CREATE src/rag/vector_store.py:
  - IMPLEMENT: ChromaDBManager class
  - METHODS: initialize_db(), add_documents(), search(), persist()
  - PATTERN: Use Chroma.from_documents pattern from examples
  - CRITICAL: Set persist_directory to ./data/chromadb (local)
  - INTEGRATION: Azure OpenAI embeddings from existing settings

Task 3: "Create RAG Retrieval System"
CREATE src/rag/retriever.py:
  - IMPLEMENT: RAGRetriever class
  - METHOD: retrieve_relevant_chunks(query, k, threshold)
  - PATTERN: Use RetrievalQAWithSourcesChain from examples line 247
  - INTEGRATION: Connect to existing azure_client.py patterns
  - VALIDATION: Score threshold filtering and source tracking

Task 4: "Create Streamlit Web Interface (Primary UI)"
CREATE src/ui/streamlit_app.py:
  - MIRROR pattern from: examples/container-apps-openai/src/doc.py structure
  - IMPLEMENT: Main Streamlit app with file upload
  - FEATURES: Session state management, file upload, chat interface
  - PATTERN: Use st.file_uploader with accept parameter for file types
  - INTEGRATION: Connect to RAG processing pipeline

CREATE src/ui/chat_interface.py:
  - IMPLEMENT: StreamlitChatUI class
  - METHODS: display_chat(), handle_user_input(), stream_response()
  - PATTERN: Use st.chat_message and st.chat_input
  - FEATURES: Message history, typing indicators, source display

CREATE src/ui/file_upload.py:
  - IMPLEMENT: FileUploadHandler class
  - METHODS: validate_file(), process_upload(), show_progress()
  - VALIDATION: File size, type checking, security validation
  - UI: Progress bars and status messages

CREATE src/ui/document_manager.py:
  - IMPLEMENT: DocumentManagerUI class
  - METHODS: list_documents(), delete_document(), show_document_info()
  - FEATURES: Document list display, deletion controls, metadata viewing
  - INTEGRATION: Connect to ChromaDB for document management

Task 5: "Create RAG-Enabled Chatbot Backend"
CREATE src/chatbot/rag_agent.py:
  - IMPLEMENT: RAGChatbotAgent class (simplified from existing agent.py)
  - FOCUS: RAG-specific functionality without CLI complexity
  - METHODS: process_rag_message(), get_relevant_documents()
  - PATTERN: Follow existing error handling and logging patterns
  - INTEGRATION: Connect to Streamlit UI instead of CLI

Task 6: "Replace Main Entry Point"
MODIFY src/main.py:
  - REPLACE: CLI commands with Streamlit app launcher
  - ADD: streamlit run command as default entry point
  - REMOVE: Click-based CLI interface (preserve for reference)
  - INTEGRATION: Launch Streamlit app as primary interface

Task 7: "Create Unit Tests"
CREATE tests/test_rag_document_processor.py:
  - TEST: Document upload, text extraction, chunking
  - PATTERN: Mirror existing test structure from tests/
  - FIXTURES: Sample documents for testing

CREATE tests/test_rag_vector_store.py:
  - TEST: ChromaDB operations, persistence, search
  - MOCKS: ChromaDB client for isolated testing

CREATE tests/test_rag_retriever.py:
  - TEST: Query processing, retrieval accuracy, scoring
  - ASSERTIONS: Verify retrieval quality and source tracking

CREATE tests/test_streamlit_ui.py:
  - TEST: UI components, file upload, session management
  - PATTERN: Streamlit testing patterns

Task 8: "Add Configuration and Documentation"
CREATE .streamlit/config.toml:
  - SET: maxUploadSize for file limits
  - SET: theme and UI preferences
  - SET: server configuration

CREATE data/chromadb/.gitkeep:
  - ENSURE: Local ChromaDB directory exists
  - ADD: .gitignore entry for chromadb/* (except .gitkeep)

UPDATE README.md:
  - REPLACE: CLI usage with Streamlit app instructions
  - ADD: RAG feature documentation and local setup
  - ADD: Document upload and management guide

Task 9: "Final Integration and Validation"
MODIFY src/config/settings.py:
  - VALIDATE: All RAG-related configuration
  - ADD: Validation methods for RAG setup

PREPARE for future containerization:
  - DOCUMENT: Local ChromaDB setup for later container migration
  - NOTE: Containerization planned for future iteration
```

### Per Task Pseudocode

```python
# Task 2: Document Processing
class DocumentProcessor:
    def __init__(self, settings: Settings):
        self.logger = logger.bind(log_type="SYSTEM", component="document_processor")
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk_size or 1000,
            chunk_overlap=settings.chunk_overlap or 200
        )
    
    async def process_file(self, file_path: str) -> List[DocumentChunk]:
        # PATTERN: Always validate input first
        self._validate_file(file_path)
        
        # PATTERN: Extract text based on file type
        text = await self._extract_text(file_path)
        
        # PATTERN: Chunk with metadata preservation
        chunks = self.text_splitter.split_text(text)
        
        # PATTERN: Create structured chunk objects
        return [DocumentChunk(
            id=f"{file_path}_{i}",
            content=chunk,
            source=file_path,
            chunk_index=i
        ) for i, chunk in enumerate(chunks)]

# Task 3: Vector Store Integration (Local)
class ChromaDBManager:
    def __init__(self, settings: Settings):
        # CRITICAL: Local directory for ChromaDB persistence
        self.persist_directory = "./data/chromadb"  # Local storage
        self.embeddings = AzureOpenAIEmbeddings(
            # PATTERN: Use existing Azure client configuration
            **settings.get_azure_openai_config()
        )
    
    async def add_documents(self, chunks: List[DocumentChunk]):
        # GOTCHA: ChromaDB requires texts and metadatas as separate lists
        texts = [chunk.content for chunk in chunks]
        metadatas = [chunk.model_dump() for chunk in chunks]
        
        # PATTERN: Use existing retry logic for API calls
        @retry(attempts=3, backoff=exponential)
        async def _store():
            self.db = await Chroma.from_texts(
                texts=texts,
                embeddings=self.embeddings,
                metadatas=metadatas,
                persist_directory=self.persist_directory
            )
            self.db.persist()  # CRITICAL: Explicit persistence
        
        await _store()

# Task 4: Streamlit Interface (Primary UI)
def main_streamlit_app():
    st.set_page_config(page_title="RAG Chatbot", layout="wide")
    
    # PATTERN: Initialize session state for RAG chatbot
    if "rag_agent" not in st.session_state:
        st.session_state.rag_agent = RAGChatbotAgent(settings)
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # SIDEBAR: Document management
    with st.sidebar:
        st.title("Document Management")
        uploaded_files = st.file_uploader(
            "Upload documents",
            accept_multiple_files=True,
            type=['pdf', 'docx', 'txt']
        )
        
        if uploaded_files:
            process_uploaded_files(uploaded_files)
    
    # MAIN: Chat interface
    st.title("RAG-Enabled Chatbot")
    
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            # Show sources if available
            if message.get("sources"):
                st.caption(f"Sources: {', '.join(message['sources'])}")
    
    # Chat input
    if prompt := st.chat_input("Ask about your documents..."):
        # Process with RAG agent
        response = st.session_state.rag_agent.process_rag_message(prompt)
        # Add to chat history
        st.session_state.messages.append({
            "role": "user", 
            "content": prompt
        })
        st.session_state.messages.append({
            "role": "assistant", 
            "content": response["answer"],
            "sources": response.get("sources", [])
        })
```

### Integration Points
```yaml
DATABASE:
  - local_storage: "Create ./data/chromadb directory for local persistence"
  - gitignore: "Add chromadb data to .gitignore"
  
CONFIG:
  - add to: src/config/settings.py
  - pattern: "chromadb_storage_path: str = Field('./data/chromadb', env='CHROMADB_STORAGE_PATH')"
  - pattern: "streamlit_port: int = Field(8501, env='STREAMLIT_PORT')"
  - pattern: "max_file_size_mb: int = Field(100, env='MAX_FILE_SIZE_MB')"
  
ENTRY_POINT:
  - replace: src/main.py CLI with Streamlit launcher
  - command: "streamlit run src/ui/streamlit_app.py"
  
LOGGING:
  - integrate with: src/observability/ patterns
  - pattern: "Use structured logging with log_type categorization"
  
FUTURE:
  - containerization: "Planned for later iteration"
  - deployment: "Local development focus for now"
```

## Validation Loop

### Level 1: Syntax & Style
```bash
# Run these FIRST - fix any errors before proceeding
ruff check src/rag/ --fix
ruff check src/ui/ --fix
mypy src/rag/
mypy src/ui/

# Expected: No errors. If errors, READ the error and fix.
```

### Level 2: Unit Tests
```python
# CREATE comprehensive test suite
def test_document_processing_happy_path():
    """Test successful document upload and chunking"""
    processor = DocumentProcessor(settings)
    chunks = await processor.process_file("test.pdf")
    assert len(chunks) > 0
    assert all(chunk.content for chunk in chunks)

def test_chromadb_persistence():
    """Test ChromaDB data persistence"""
    manager = ChromaDBManager(settings)
    await manager.add_documents(test_chunks)
    # Recreate manager to test persistence
    manager2 = ChromaDBManager(settings)
    results = await manager2.search("test query")
    assert len(results) > 0

def test_rag_retrieval_accuracy():
    """Test retrieval returns relevant results"""
    retriever = RAGRetriever(settings)
    results = await retriever.retrieve_relevant_chunks("specific query", k=3)
    assert len(results) <= 3
    assert all(r.confidence_score >= 0.5 for r in results)

def test_streamlit_file_upload():
    """Test Streamlit file upload handling"""
    with patch('streamlit.file_uploader') as mock_upload:
        mock_upload.return_value = [mock_file]
        app = StreamlitApp()
        processed = app.handle_file_upload()
        assert processed is True
```

```bash
# Run and iterate until passing:
pytest tests/test_rag*.py -v
pytest tests/test_ui*.py -v
# If failing: Read error, understand root cause, fix code, re-run
```

### Level 3: Integration Test
```bash
# Test Streamlit app (primary interface)
streamlit run src/ui/streamlit_app.py
# Navigate to http://localhost:8501
# Upload test document, ask questions, verify responses

# Test ChromaDB persistence
# Stop Streamlit app, restart, verify documents still available

# Test document management
# Upload multiple documents, delete some, verify UI updates

# Expected: Streamlit UI works, documents persist, RAG retrieval accurate
```

## Final Validation Checklist
- [ ] All tests pass: `pytest tests/ -v`
- [ ] No linting errors: `ruff check src/`
- [ ] No type errors: `mypy src/`
- [ ] Streamlit app launches and displays correctly
- [ ] Document upload works via Streamlit UI
- [ ] Local ChromaDB persists data across app restarts
- [ ] RAG retrieval returns relevant sources with citations
- [ ] Document management features work (list, delete)
- [ ] Chat interface maintains conversation history
- [ ] Structured logging follows project patterns
- [ ] Configuration follows settings.py patterns
- [ ] Error handling provides graceful degradation

---

## Anti-Patterns to Avoid
- ❌ Don't create new authentication patterns - use existing Azure patterns
- ❌ Don't skip ChromaDB local persistence configuration - data will be lost
- ❌ Don't ignore file size limits - implement proper validation
- ❌ Don't use sync functions in async contexts - maintain async patterns
- ❌ Don't hardcode file paths - use configuration management
- ❌ Don't skip structured logging - follow established log_type patterns
- ❌ Don't ignore rate limits - implement retry logic for embeddings
- ❌ Don't overcomplicate the UI - keep Streamlit interface simple and focused
- ❌ Don't break existing backend patterns - maintain observability integration
- ❌ Don't skip local testing - validate ChromaDB persistence before deployment

---

## Updated Confidence Score: 9.5/10

This updated PRP provides enhanced confidence for successful implementation:
- ✅ Simplified scope: Single UI interface instead of dual CLI+Web
- ✅ Clear local deployment strategy with containerization deferred
- ✅ Removed Chain of Thought complexity while maintaining core RAG functionality
- ✅ Complete reference implementations from container-apps-openai example
- ✅ Detailed existing codebase patterns to follow
- ✅ Specific gotchas and library quirks identified
- ✅ Executable validation loops with specific commands
- ✅ Clear task breakdown with implementation order (reduced from 10 to 9 tasks)
- ✅ Integration points with existing architecture
- ✅ Comprehensive testing strategy focused on Streamlit UI

**Risk Reduction Summary:**
- **Eliminated dual interface complexity** (-0.3 risk)
- **Removed Chain of Thought implementation** (-0.2 risk)  
- **Simplified to local deployment** (-0.2 risk)
- **Focused on proven Streamlit patterns** (-0.1 risk)

**New Risk Assessment: -0.2 (minimal remaining complexity)**
The simplified scope and clear local deployment strategy significantly reduce implementation complexity while maintaining full RAG functionality.