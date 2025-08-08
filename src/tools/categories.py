"""
Tool categorization system extending LangChain BaseTool with Pydantic integration.

Provides category metadata for existing LangChain tools while maintaining
full compatibility with args_schema patterns and OpenAI function calling.
"""

from enum import Enum
from typing import List, Dict, Any, Optional, Type
from pydantic import BaseModel, Field
import structlog
from langchain.tools import BaseTool

logger = structlog.get_logger(__name__)


class ToolCategory(str, Enum):
    """Tool categories for domain-based organization and dynamic loading."""
    DOCUMENTS = "documents"      # RAG document search, file processing
    BANKING = "banking"          # Call Report, financial analysis
    ANALYSIS = "analysis"        # Calculations, data processing  
    WEB = "web"                  # Web search, external APIs
    UTILITIES = "utilities"      # Time, formatting, general tools


class ToolCategoryMetadata(BaseModel):
    """
    Pydantic model for tool category metadata.
    
    This model stores category information that can be attached to existing
    LangChain BaseTool instances without interfering with their args_schema.
    """
    category: ToolCategory = Field(description="Tool's primary category")
    requires_services: Optional[List[str]] = Field(
        default=None,
        description="Service dependencies for dynamic loading (e.g., ['chromadb'])"
    )
    priority: int = Field(
        default=0,
        description="Loading priority within category (higher loads first)",
        ge=0
    )
    tags: List[str] = Field(
        default_factory=list,
        description="Additional tags for discovery and filtering"
    )
    
    class Config:
        """Pydantic config for enum serialization."""
        use_enum_values = True
        
    def has_service_dependencies(self) -> bool:
        """Check if tool has service dependencies."""
        return bool(self.requires_services)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "category": self.category.value,
            "requires_services": self.requires_services or [],
            "priority": self.priority,
            "tags": self.tags,
            "has_dependencies": self.has_service_dependencies()
        }


def add_category_metadata(
    tool: BaseTool,
    category: ToolCategory,
    requires_services: Optional[List[str]] = None,
    priority: int = 0,
    tags: Optional[List[str]] = None
) -> BaseTool:
    """
    Add category metadata to existing LangChain BaseTool.
    
    This function retrofits existing tools with category information
    without breaking their args_schema or LangChain compatibility.
    
    Args:
        tool: Existing LangChain BaseTool instance
        category: Tool category
        requires_services: Optional service dependencies  
        priority: Loading priority
        tags: Optional tags for discovery
        
    Returns:
        Same tool instance with category metadata added
    """
    # Create metadata instance
    metadata = ToolCategoryMetadata(
        category=category,
        requires_services=requires_services,
        priority=priority,
        tags=tags or []
    )
    
    # Add metadata as private attribute to avoid Pydantic field conflicts
    object.__setattr__(tool, '_category_metadata', metadata)
    
    # Add convenience methods for accessing category info
    def get_category() -> ToolCategory:
        return metadata.category
    
    def get_category_metadata() -> ToolCategoryMetadata:
        return metadata
    
    def has_service_dependencies() -> bool:
        return metadata.has_service_dependencies()
    
    def get_required_services() -> List[str]:
        return metadata.requires_services or []
    
    # Attach methods to tool instance
    object.__setattr__(tool, 'get_category', get_category)
    object.__setattr__(tool, 'get_category_metadata', get_category_metadata)
    object.__setattr__(tool, 'has_service_dependencies', has_service_dependencies)
    object.__setattr__(tool, 'get_required_services', get_required_services)
    
    logger.debug(
        "Added category metadata to tool",
        tool_name=tool.name,
        category=category.value,
        has_dependencies=metadata.has_service_dependencies()
    )
    
    return tool


def get_tool_category(tool: BaseTool) -> ToolCategory:
    """
    Get category for a tool, with fallback classification.
    
    Args:
        tool: LangChain BaseTool instance
        
    Returns:
        Tool category (from metadata or name-based classification)
    """
    # Check if tool has category metadata
    if hasattr(tool, '_category_metadata'):
        return tool._category_metadata.category
    
    # Fallback to name-based classification for compatibility
    return _classify_tool_by_name(tool.name)


def get_tool_metadata(tool: BaseTool) -> Optional[ToolCategoryMetadata]:
    """
    Get category metadata for a tool.
    
    Args:
        tool: LangChain BaseTool instance
        
    Returns:
        ToolCategoryMetadata if available, None otherwise
    """
    return getattr(tool, '_category_metadata', None)


def _classify_tool_by_name(tool_name: str) -> ToolCategory:
    """
    Classify tool by name patterns for backward compatibility.
    
    This ensures tools without explicit metadata still get categorized.
    """
    name_lower = tool_name.lower()
    
    # Document/RAG tools
    if any(keyword in name_lower for keyword in ['document', 'search', 'rag', 'retrieval']):
        return ToolCategory.DOCUMENTS
    
    # Banking tools
    if any(keyword in name_lower for keyword in ['bank', 'call_report', 'financial', 'rssd']):
        return ToolCategory.BANKING
    
    # Analysis tools  
    if any(keyword in name_lower for keyword in ['analysis', 'calculate', 'compute', 'math']):
        return ToolCategory.ANALYSIS
    
    # Web tools
    if any(keyword in name_lower for keyword in ['web', 'http', 'api', 'fetch']):
        return ToolCategory.WEB
    
    # Default to utilities
    return ToolCategory.UTILITIES


def categorize_tools(tools: List[BaseTool]) -> Dict[ToolCategory, List[BaseTool]]:
    """
    Group tools by category.
    
    Args:
        tools: List of LangChain BaseTool instances
        
    Returns:
        Dictionary mapping categories to tool lists
    """
    categorized = {}
    
    for tool in tools:
        category = get_tool_category(tool)
        
        if category not in categorized:
            categorized[category] = []
        
        categorized[category].append(tool)
    
    return categorized


def get_tools_by_category(tools: List[BaseTool], category: ToolCategory) -> List[BaseTool]:
    """
    Filter tools by specific category.
    
    Args:
        tools: List of tools to filter
        category: Category to filter by
        
    Returns:
        List of tools matching the category
    """
    return [tool for tool in tools if get_tool_category(tool) == category]


def sort_tools_by_priority(tools: List[BaseTool]) -> List[BaseTool]:
    """
    Sort tools by priority within their category.
    
    Args:
        tools: List of tools to sort
        
    Returns:
        Tools sorted by priority (highest first)
    """
    def get_priority(tool: BaseTool) -> int:
        metadata = get_tool_metadata(tool)
        return metadata.priority if metadata else 0
    
    return sorted(tools, key=get_priority, reverse=True)


# Service dependency mappings for dynamic loading
SERVICE_CATEGORY_MAPPING = {
    "chromadb": ToolCategory.DOCUMENTS,
    "call_report_api": ToolCategory.BANKING,
    "web_search_api": ToolCategory.WEB
}


def get_categories_requiring_service(service_name: str) -> List[ToolCategory]:
    """
    Get categories that depend on a specific service.
    
    Args:
        service_name: Name of service to check
        
    Returns:
        List of categories that require this service
    """
    categories = []
    
    # Check direct mapping
    if service_name in SERVICE_CATEGORY_MAPPING:
        categories.append(SERVICE_CATEGORY_MAPPING[service_name])
    
    return categories


def filter_tools_by_service_availability(
    tools: List[BaseTool],
    available_services: set[str]
) -> List[BaseTool]:
    """
    Filter tools based on service availability.
    
    Args:
        tools: List of tools to filter
        available_services: Set of available service names
        
    Returns:
        List of tools whose service dependencies are met
    """
    available_tools = []
    
    for tool in tools:
        metadata = get_tool_metadata(tool)
        
        # If no metadata or no dependencies, tool is available
        if not metadata or not metadata.has_service_dependencies():
            available_tools.append(tool)
            continue
        
        # Check if all required services are available
        required_services = set(metadata.requires_services)
        if required_services.issubset(available_services):
            available_tools.append(tool)
    
    return available_tools


def get_tool_summary(tool: BaseTool) -> Dict[str, Any]:
    """
    Get comprehensive summary of tool including category metadata.
    
    Args:
        tool: LangChain BaseTool instance
        
    Returns:
        Dictionary with tool information and metadata
    """
    summary = {
        "name": tool.name,
        "description": tool.description[:100] + "..." if len(tool.description) > 100 else tool.description,
        "category": get_tool_category(tool).value,
        "has_args_schema": hasattr(tool, 'args_schema') and tool.args_schema is not None
    }
    
    # Add metadata if available
    metadata = get_tool_metadata(tool)
    if metadata:
        summary.update({
            "has_metadata": True,
            "requires_services": metadata.requires_services or [],
            "priority": metadata.priority,
            "tags": metadata.tags,
            "has_dependencies": metadata.has_service_dependencies()
        })
    else:
        summary.update({
            "has_metadata": False,
            "requires_services": [],
            "priority": 0,
            "tags": [],
            "has_dependencies": False
        })
    
    return summary