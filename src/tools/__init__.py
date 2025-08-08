"""
Tools package for external API integrations and function calling.

This package provides a framework for integrating external tools and APIs
with the RAG chatbot system, enabling dynamic responses beyond document-based RAG.
"""

from .base import BaseTool, ToolRegistry, ToolExecutionResult
from .ratings_tool import RestaurantRatingsTool

# Call Report tools import
try:
    from .call_report.langchain_tools import (
        CallReportDataTool,
        BankLookupTool,
        CallReportToolset,
        create_call_report_toolset
    )
    CALL_REPORT_AVAILABLE = True
except ImportError:
    CALL_REPORT_AVAILABLE = False

__all__ = [
    'BaseTool',
    'ToolRegistry', 
    'ToolExecutionResult',
    'RestaurantRatingsTool'
]

# Add Call Report tools to exports if available
if CALL_REPORT_AVAILABLE:
    __all__.extend([
        'CallReportDataTool',
        'BankLookupTool', 
        'CallReportToolset',
        'create_call_report_toolset'
    ])