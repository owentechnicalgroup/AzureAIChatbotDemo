"""
Unit tests for DocumentProcessor class.

Tests document processing functionality including file parsing,
text extraction, and chunking for various file formats.
"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from io import BytesIO

import sys
sys.path.append(str(Path(__file__).parent.parent / "src"))

from rag.document_processor import DocumentProcessor
from rag import Document, DocumentChunk
from config.settings import Settings


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    settings = Mock(spec=Settings)
    settings.chunk_size = 1000
    settings.chunk_overlap = 200
    settings.max_file_size_mb = 10
    return settings


@pytest.fixture
def document_processor(mock_settings):
    """Create DocumentProcessor instance for testing."""
    return DocumentProcessor(mock_settings)


class TestDocumentProcessor:
    """Test cases for DocumentProcessor class."""
    
    def test_initialization(self, mock_settings):
        """Test DocumentProcessor initialization."""
        processor = DocumentProcessor(mock_settings)
        
        assert processor.settings == mock_settings
        assert processor.chunk_size == 1000
        assert processor.chunk_overlap == 200
        assert processor.max_file_size_mb == 10
        assert processor.logger is not None
    
    @pytest.mark.asyncio
    async def test_process_text_file_success(self, document_processor):
        """Test successful text file processing."""
        # Arrange
        file_content = b"This is a test text file.\nIt has multiple lines.\nThis should be processed correctly."
        filename = "test.txt"
        
        # Act
        document, chunks = await document_processor.process_file(
            file_path=Path(filename),
            file_content=file_content,
            source_name=filename
        )
        
        # Assert
        assert isinstance(document, Document)
        assert document.filename == filename
        assert document.file_type == "txt"
        assert document.size_bytes == len(file_content)
        assert len(chunks) > 0
        assert all(isinstance(chunk, DocumentChunk) for chunk in chunks)
        assert all(chunk.document_id == document.id for chunk in chunks)
    
    @pytest.mark.asyncio
    async def test_process_pdf_file_success(self, document_processor):
        """Test successful PDF file processing."""
        # Arrange
        filename = "test.pdf"
        file_content = b"Mock PDF content"
        
        with patch('pypdf.PdfReader') as mock_pdf_reader:
            mock_page = Mock()
            mock_page.extract_text.return_value = "This is extracted PDF text content."
            mock_pdf_reader.return_value.pages = [mock_page]
            
            # Act
            document, chunks = await document_processor.process_file(
                file_path=Path(filename),
                file_content=file_content,
                source_name=filename
            )
            
            # Assert
            assert document.filename == filename
            assert document.file_type == "pdf"
            assert len(chunks) > 0
            mock_pdf_reader.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_docx_file_success(self, document_processor):
        """Test successful DOCX file processing."""
        # Arrange
        filename = "test.docx"
        file_content = b"Mock DOCX content"
        
        with patch('docx.Document') as mock_docx:
            mock_paragraph = Mock()
            mock_paragraph.text = "This is extracted DOCX text content."
            mock_docx.return_value.paragraphs = [mock_paragraph]
            
            # Act
            document, chunks = await document_processor.process_file(
                file_path=Path(filename),
                file_content=file_content,
                source_name=filename
            )
            
            # Assert
            assert document.filename == filename
            assert document.file_type == "docx"
            assert len(chunks) > 0
            mock_docx.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_file_unsupported_format(self, document_processor):
        """Test processing unsupported file format raises error."""
        # Arrange
        filename = "test.xyz"
        file_content = b"Some content"
        
        # Act & Assert
        with pytest.raises(ValueError, match="Unsupported file type"):
            await document_processor.process_file(
                file_path=Path(filename),
                file_content=file_content,
                source_name=filename
            )
    
    @pytest.mark.asyncio
    async def test_process_file_too_large(self, document_processor):
        """Test processing file exceeding size limit raises error."""
        # Arrange
        filename = "large_file.txt"
        # Create content larger than max_file_size_mb (10MB in mock settings)
        large_content = b"x" * (11 * 1024 * 1024)  # 11MB
        
        # Act & Assert
        with pytest.raises(ValueError, match="File size exceeds maximum"):
            await document_processor.process_file(
                file_path=Path(filename),
                file_content=large_content,
                source_name=filename
            )
    
    @pytest.mark.asyncio
    async def test_process_empty_file(self, document_processor):
        """Test processing empty file raises error."""
        # Arrange
        filename = "empty.txt"
        file_content = b""
        
        # Act & Assert
        with pytest.raises(ValueError, match="Empty file content"):
            await document_processor.process_file(
                file_path=Path(filename),
                file_content=file_content,
                source_name=filename
            )
    
    @pytest.mark.asyncio
    async def test_extract_text_from_pdf_error(self, document_processor):
        """Test PDF text extraction error handling."""
        # Arrange
        file_content = b"Invalid PDF content"
        
        with patch('pypdf.PdfReader', side_effect=Exception("PDF parsing error")):
            # Act & Assert
            with pytest.raises(Exception, match="PDF parsing error"):
                await document_processor._extract_text_from_pdf(file_content)
    
    @pytest.mark.asyncio
    async def test_extract_text_from_docx_error(self, document_processor):
        """Test DOCX text extraction error handling."""
        # Arrange
        file_content = b"Invalid DOCX content"
        
        with patch('docx.Document', side_effect=Exception("DOCX parsing error")):
            # Act & Assert
            with pytest.raises(Exception, match="DOCX parsing error"):
                await document_processor._extract_text_from_docx(file_content)
    
    @pytest.mark.asyncio
    async def test_create_chunks_small_text(self, document_processor):
        """Test chunking with text smaller than chunk size."""
        # Arrange
        text = "This is a small text that should fit in one chunk."
        source = "test.txt"
        document_id = "test-doc-id"
        
        # Act
        chunks = await document_processor._create_chunks(text, source, document_id)
        
        # Assert
        assert len(chunks) == 1
        assert chunks[0].content == text
        assert chunks[0].source == source
        assert chunks[0].document_id == document_id
        assert chunks[0].chunk_index == 0
    
    @pytest.mark.asyncio
    async def test_create_chunks_large_text(self, document_processor):
        """Test chunking with text larger than chunk size."""
        # Arrange
        # Create text larger than chunk_size (1000 chars)
        text = "This is a sentence. " * 100  # ~2000 chars
        source = "test.txt"
        document_id = "test-doc-id"
        
        # Act
        chunks = await document_processor._create_chunks(text, source, document_id)
        
        # Assert
        assert len(chunks) > 1
        assert all(isinstance(chunk, DocumentChunk) for chunk in chunks)
        assert all(chunk.document_id == document_id for chunk in chunks)
        assert all(chunk.source == source for chunk in chunks)
        # Check chunk indices are sequential
        for i, chunk in enumerate(chunks):
            assert chunk.chunk_index == i
    
    def test_get_file_type_txt(self, document_processor):
        """Test file type detection for TXT files."""
        assert document_processor._get_file_type(Path("test.txt")) == "txt"
        assert document_processor._get_file_type(Path("test.TXT")) == "txt"
    
    def test_get_file_type_pdf(self, document_processor):
        """Test file type detection for PDF files."""
        assert document_processor._get_file_type(Path("test.pdf")) == "pdf"
        assert document_processor._get_file_type(Path("test.PDF")) == "pdf"
    
    def test_get_file_type_docx(self, document_processor):
        """Test file type detection for DOCX files."""
        assert document_processor._get_file_type(Path("test.docx")) == "docx"
        assert document_processor._get_file_type(Path("test.DOCX")) == "docx"
    
    def test_get_file_type_unsupported(self, document_processor):
        """Test file type detection for unsupported files."""
        with pytest.raises(ValueError, match="Unsupported file type"):
            document_processor._get_file_type(Path("test.xyz"))
    
    @pytest.mark.asyncio
    async def test_detect_encoding_utf8(self, document_processor):
        """Test encoding detection for UTF-8 content."""
        content = "Hello world! 🌍".encode('utf-8')
        encoding = await document_processor._detect_encoding(content)
        assert encoding.lower() in ['utf-8', 'ascii']  # chardet might return ascii for simple text
    
    @pytest.mark.asyncio
    async def test_detect_encoding_latin1(self, document_processor):
        """Test encoding detection for Latin-1 content."""
        content = "Café résumé".encode('latin-1')
        encoding = await document_processor._detect_encoding(content)
        assert encoding is not None  # Should detect some encoding
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, document_processor):
        """Test successful health check."""
        health = await document_processor.health_check()
        
        assert health["status"] == "healthy"
        assert "chunk_size" in health
        assert "max_file_size_mb" in health
        assert "supported_formats" in health
        assert health["supported_formats"] == ["txt", "pdf", "docx"]