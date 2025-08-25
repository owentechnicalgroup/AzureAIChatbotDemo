"""
Tools module - organized by atomic, composite, and infrastructure components.

This module provides a clean organization of LangChain tools:
- atomic: Single-purpose, focused tools (FDIC API, RAG search)
- composite: Multi-step workflow orchestration tools  
- infrastructure: Supporting services, data models, and tool collections
"""

# Import production tool collections
from .atomic import FDICInstitutionSearchTool, FDICFinancialDataTool, RAGSearchTool
# BankAnalysisTool has been deprecated in favor of atomic tool composition via agent executor
from .infrastructure.toolsets import BankingToolset

# Tool management utilities
from .categories import (
    ToolCategory,
    get_tool_category,
    get_tool_metadata,
    filter_tools_by_service_availability
)
from .dynamic_loader import DynamicToolLoader, ServiceAvailabilityChecker

__all__ = [
    # Atomic tools - Production
    "FDICInstitutionSearchTool",
    "FDICFinancialDataTool", 
    "RAGSearchTool",
    
    # Composite tools - deprecated
    # "BankAnalysisTool",  # Deprecated: Use atomic tools with agent executor
    
    # Infrastructure
    "BankingToolset",
    
    # Tool management
    "ToolCategory",
    "get_tool_category",
    "get_tool_metadata", 
    "filter_tools_by_service_availability",
    "DynamicToolLoader",
    "ServiceAvailabilityChecker"
]