"""
Document Management System - Separated RAG concern for document lifecycle.

This module handles all document-related operations independently from AI access:
- Document upload and processing
- Document storage and indexing  
- Document metadata management
- Document deletion and cleanup
- Database health and statistics

Used by: Streamlit UI, admin tools, document APIs, bulk operations
"""

from .document_manager import DocumentManager
from .document_models import DocumentInfo, DocumentStats, UploadResult, DeleteResult, DocumentStatus
from .database_manager import DatabaseManager

__all__ = [
    'DocumentManager',
    'DocumentInfo', 
    'DocumentStats',
    'UploadResult',
    'DeleteResult', 
    'DocumentStatus',
    'DatabaseManager'
]