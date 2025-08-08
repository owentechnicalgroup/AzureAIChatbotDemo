"""
LangChain-native Call Report toolset for dynamic loading.

Provides a coordinated set of Call Report tools that extend langchain.tools.BaseTool
for seamless integration with the dynamic tool loading system.
"""

from typing import List, Dict, Any
import structlog
from langchain.tools import BaseTool

from src.config.settings import Settings
from .bank_lookup_langchain import BankLookupTool
from .call_report_data_langchain import CallReportDataTool  
from .bank_analysis_langchain import BankAnalysisTool
from .mock_api_client import CallReportMockAPI

logger = structlog.get_logger(__name__).bind(log_type="SYSTEM")


class LangChainCallReportToolset:
    """
    LangChain-native Call Report toolset for dynamic loading.
    
    Manages a collection of Call Report tools that properly extend
    langchain.tools.BaseTool for use with the enhanced tool loading system.
    """
    
    def __init__(self, settings: Settings):
        """
        Initialize the LangChain Call Report toolset.
        
        Args:
            settings: Application settings
        """
        self.settings = settings
        self.logger = logger.bind(component="langchain_call_report_toolset")
        
        # Initialize shared API client
        self.api_client = CallReportMockAPI()
        
        # Initialize tools
        self._tools = None
        self._initialize_tools()
        
        self.logger.info(
            "LangChain Call Report toolset initialized",
            tools_count=len(self._tools),
            tool_names=[tool.name for tool in self._tools]
        )
    
    def _initialize_tools(self) -> None:
        """Initialize all LangChain Call Report tools."""
        try:
            # Create LangChain-native tools
            bank_lookup = BankLookupTool()
            call_report_data = CallReportDataTool(api_client=self.api_client)
            bank_analysis = BankAnalysisTool()
            
            self._tools = [bank_lookup, call_report_data, bank_analysis]
            
            self.logger.info(
                "LangChain Call Report tools initialized",
                tool_count=len(self._tools)
            )
            
        except Exception as e:
            self.logger.error("Failed to initialize LangChain Call Report tools", error=str(e))
            self._tools = []
    
    def get_tools(self) -> List[BaseTool]:
        """
        Get all LangChain Call Report tools.
        
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
        Check if the Call Report toolset is available.
        
        Returns:
            True if tools are available and API is accessible
        """
        return (
            len(self._tools) > 0 and 
            self.api_client.is_available()
        )
    
    def get_health_status(self) -> Dict[str, Any]:
        """
        Get health status of the toolset.
        
        Returns:
            Dictionary with health status information
        """
        return {
            "available": self.is_available(),
            "tools_count": len(self._tools),
            "tool_names": [tool.name for tool in self._tools],
            "api_available": self.api_client.is_available(),
            "toolset_type": "langchain_native"
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