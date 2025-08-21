"""
Enhanced LangChain-native Banking toolset with FDIC integration.

Provides a coordinated set of banking tools with FDIC BankFind Suite API integration
that extend langchain.tools.BaseTool for seamless integration with the dynamic tool loading system.
"""

from typing import List, Dict, Any
import structlog
from langchain.tools import BaseTool

from src.config.settings import Settings
from ...atomic.fdic_institution_search_tool import FDICInstitutionSearchTool
from ...atomic.fdic_financial_data_tool import FDICFinancialDataTool
from ...composite.bank_analysis_tool import BankAnalysisTool

logger = structlog.get_logger(__name__).bind(log_type="SYSTEM")


class BankingToolset:
    """
    Enhanced LangChain-native Banking toolset with real FDIC Financial Data API integration.
    
    Provides comprehensive banking analysis capabilities using:
    - FDIC BankFind Suite API for institution lookup and verification
    - FDIC Financial Data API for real-time financial metrics and ratios
    - Enhanced bank analysis with authoritative regulatory data
    
    All tools properly extend langchain.tools.BaseTool for seamless integration
    with AI agents and the dynamic tool loading system.
    """
    
    def __init__(self, settings: Settings):
        """
        Initialize the LangChain Banking toolset.
        
        Args:
            settings: Application settings
        """
        self.settings = settings
        self.logger = logger.bind(component="banking_toolset")
        
        # Initialize tools
        self._tools = None
        self._initialize_tools()
        
        self.logger.info(
            "Enhanced LangChain Banking toolset initialized with real FDIC Financial Data API integration",
            tools_count=len(self._tools),
            tool_names=[tool.name for tool in self._tools],
            has_fdic_api_key=bool(settings.fdic_api_key),
            fdic_financial_api_timeout=settings.fdic_financial_api_timeout,
            fdic_financial_cache_ttl=settings.fdic_financial_cache_ttl
        )
    
    def _initialize_tools(self) -> None:
        """Initialize clean atomic FDIC tools with simplified architecture."""
        try:
            # Create clean atomic FDIC tools
            fdic_institution_search = FDICInstitutionSearchTool(settings=self.settings)
            fdic_financial_data = FDICFinancialDataTool(settings=self.settings)
            bank_analysis = BankAnalysisTool()  # Keep composite tool for backwards compatibility
            
            self._tools = [fdic_institution_search, fdic_financial_data, bank_analysis]
            
            self.logger.info(
                "Clean atomic FDIC tools initialized",
                tool_count=len(self._tools),
                tool_names=[tool.name for tool in self._tools],
                architecture="atomic_with_composite_compatibility"
            )
            
        except Exception as e:
            self.logger.error("Failed to initialize FDIC Financial API banking tools", error=str(e))
            self._tools = []
    
    def get_tools(self) -> List[BaseTool]:
        """
        Get all LangChain Banking tools.
        
        Returns:
            List of LangChain BaseTool instances
        """
        return self._tools.copy()
    
    def get_tool_by_name(self, name: str) -> BaseTool:
        """
        Get a specific tool by name.
        
        Args:
            name: Tool name to search for
            
        Returns:
            BaseTool instance or None if not found
        """
        for tool in self._tools:
            if tool.name == name:
                return tool
        return None
    
    def is_available(self) -> bool:
        """
        Check if the enhanced Banking toolset is available.
        
        Returns:
            True if tools are available and APIs are accessible
        """
        tools_available = len(self._tools) > 0
        
        # Check if FDIC institution search tool is available
        fdic_institution_tool = self.get_tool_by_name("fdic_institution_search")
        fdic_financial_tool = self.get_tool_by_name("fdic_financial_data")
        
        fdic_available = (
            fdic_institution_tool is not None and fdic_institution_tool.is_available() and
            fdic_financial_tool is not None and fdic_financial_tool.is_available()
        )
        
        return tools_available and fdic_available
    
    def get_health_status(self) -> Dict[str, Any]:
        """
        Get health status of the enhanced toolset with FDIC integration.
        
        Returns:
            Dictionary with health status information
        """
        # Check FDIC API availability
        fdic_institution_tool = self.get_tool_by_name("fdic_institution_search")
        fdic_financial_tool = self.get_tool_by_name("fdic_financial_data")
        
        fdic_available = (
            fdic_institution_tool is not None and fdic_institution_tool.is_available() and
            fdic_financial_tool is not None and fdic_financial_tool.is_available()
        )
        
        return {
            "available": self.is_available(),
            "tools_count": len(self._tools),
            "tool_names": [tool.name for tool in self._tools],
            "fdic_institution_available": fdic_institution_tool.is_available() if fdic_institution_tool else False,
            "fdic_financial_available": fdic_financial_tool.is_available() if fdic_financial_tool else False,
            "fdic_integration": True,
            "has_fdic_api_key": bool(self.settings.fdic_api_key),
            "toolset_type": "clean_atomic_fdic_tools"
        }
    
    def get_schemas(self) -> List[Dict[str, Any]]:
        """
        Get schemas for all tools (for OpenAI function calling).
        
        Returns:
            List of tool schemas
        """
        schemas = []
        for tool in self._tools:
            try:
                # LangChain tools have args_schema for function calling
                if hasattr(tool, 'args_schema') and tool.args_schema:
                    schema = {
                        "type": "function",
                        "function": {
                            "name": tool.name,
                            "description": tool.description,
                            "parameters": tool.args_schema.schema()
                        }
                    }
                    schemas.append(schema)
            except Exception as e:
                self.logger.warning(
                    "Failed to get schema for tool",
                    tool_name=tool.name,
                    error=str(e)
                )
        
        return schemas