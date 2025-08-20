"""
Enhanced LangChain-native Banking toolset with FDIC integration.

Provides a coordinated set of banking tools with FDIC BankFind Suite API integration
that extend langchain.tools.BaseTool for seamless integration with the dynamic tool loading system.
"""

from typing import List, Dict, Any
import structlog
from langchain.tools import BaseTool

from src.config.settings import Settings
from ...atomic.bank_lookup_tool import BankLookupTool
from ...atomic.call_report_data_tool import CallReportDataTool  
from ...composite.bank_analysis_tool import BankAnalysisTool
from ..banking.call_report_api import CallReportMockAPI

logger = structlog.get_logger(__name__).bind(log_type="SYSTEM")


class BankingToolset:
    """
    Enhanced LangChain-native Banking toolset with FDIC API integration.
    
    Manages a collection of banking tools with FDIC BankFind Suite API integration
    that properly extend langchain.tools.BaseTool for use with the enhanced tool loading system.
    """
    
    def __init__(self, settings: Settings):
        """
        Initialize the LangChain Banking toolset.
        
        Args:
            settings: Application settings
        """
        self.settings = settings
        self.logger = logger.bind(component="banking_toolset")
        
        # Initialize shared API client
        self.api_client = CallReportMockAPI()
        
        # Initialize tools
        self._tools = None
        self._initialize_tools()
        
        self.logger.info(
            "Enhanced LangChain Banking toolset initialized with FDIC integration",
            tools_count=len(self._tools),
            tool_names=[tool.name for tool in self._tools],
            has_fdic_api_key=bool(settings.fdic_api_key)
        )
    
    def _initialize_tools(self) -> None:
        """Initialize all enhanced LangChain Banking tools with FDIC integration."""
        try:
            # Create FDIC-enhanced LangChain-native tools
            bank_lookup = BankLookupTool(settings=self.settings)
            call_report_data = CallReportDataTool(api_client=self.api_client)
            bank_analysis = BankAnalysisTool()  # Uses enhanced BankLookupTool internally
            
            self._tools = [bank_lookup, call_report_data, bank_analysis]
            
            self.logger.info(
                "Enhanced LangChain Banking tools with FDIC integration initialized",
                tool_count=len(self._tools),
                fdic_integration=True
            )
            
        except Exception as e:
            self.logger.error("Failed to initialize LangChain Banking tools", error=str(e))
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
        call_report_available = self.api_client.is_available()
        
        # Check if FDIC-enhanced bank lookup tool is available
        bank_lookup_tool = self.get_tool_by_name("bank_lookup")
        fdic_available = (
            bank_lookup_tool is not None and 
            bank_lookup_tool.is_available()
        )
        
        return tools_available and call_report_available and fdic_available
    
    def get_health_status(self) -> Dict[str, Any]:
        """
        Get health status of the enhanced toolset with FDIC integration.
        
        Returns:
            Dictionary with health status information
        """
        # Check FDIC API availability
        bank_lookup_tool = self.get_tool_by_name("bank_lookup")
        fdic_available = (
            bank_lookup_tool is not None and 
            bank_lookup_tool.is_available()
        )
        
        return {
            "available": self.is_available(),
            "tools_count": len(self._tools),
            "tool_names": [tool.name for tool in self._tools],
            "call_report_api_available": self.api_client.is_available(),
            "fdic_api_available": fdic_available,
            "fdic_integration": True,
            "has_fdic_api_key": bool(self.settings.fdic_api_key),
            "toolset_type": "langchain_native_enhanced"
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