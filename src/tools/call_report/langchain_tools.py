"""
LangChain tool wrappers for Call Report functionality.

Provides LangChain-compatible tool wrappers that integrate Call Report
services with the AI agent's tool registry and execution framework.
"""

from typing import Dict, Any, List, Optional
import structlog

from src.tools.base import BaseTool, ToolExecutionResult, ToolStatus
from src.config.settings import Settings
from .mock_api_client import CallReportMockAPI
from .bank_lookup import BankLookupTool as BaseBankLookupTool
from .bank_analysis_tool import BankAnalysisTool

logger = structlog.get_logger(__name__).bind(log_type="SYSTEM")


class CallReportDataTool(BaseTool):
    """
    LangChain-compatible wrapper for Call Report data retrieval.
    
    Provides a unified interface for retrieving FFIEC Call Report data
    that integrates with the AI agent's tool execution framework.
    """
    
    def __init__(self, api_client: Optional[CallReportMockAPI] = None):
        """
        Initialize Call Report data tool.
        
        Args:
            api_client: Optional CallReportMockAPI instance
        """
        super().__init__(
            name="call_report_data",
            description="Retrieve FFIEC Call Report field data for banks using RSSD ID, schedule, and field ID"
        )
        
        self.api_client = api_client or CallReportMockAPI()
        
        self.logger.info("CallReportDataTool initialized")
    
    async def execute(
        self,
        rssd_id: str,
        schedule: str,
        field_id: str
    ) -> ToolExecutionResult:
        """
        Execute Call Report data retrieval.
        
        Args:
            rssd_id: Bank identifier (RSSD ID)
            schedule: FFIEC schedule identifier (e.g., "RC", "RI")
            field_id: Field identifier (e.g., "RCON2170")
            
        Returns:
            ToolExecutionResult with field data
        """
        self.logger.info(
            "Executing Call Report data retrieval",
            rssd_id=rssd_id,
            schedule=schedule,
            field_id=field_id
        )
        
        return await self.api_client.execute(
            rssd_id=rssd_id,
            schedule=schedule,
            field_id=field_id
        )
    
    def get_schema(self) -> Dict[str, Any]:
        """Get OpenAI function schema for this tool."""
        return self.api_client.get_schema()


class BankLookupTool(BaseTool):
    """
    LangChain-compatible wrapper for bank lookup functionality.
    
    Provides bank identification and RSSD ID lookup capabilities
    integrated with the AI agent's tool execution framework.
    """
    
    def __init__(self, lookup_service: Optional[BaseBankLookupTool] = None):
        """
        Initialize bank lookup tool.
        
        Args:
            lookup_service: Optional BaseBankLookupTool instance
        """
        super().__init__(
            name="bank_lookup", 
            description="Look up bank RSSD ID and information from legal name with fuzzy matching"
        )
        
        self.lookup_service = lookup_service or BaseBankLookupTool()
        
        self.logger.info("BankLookupTool initialized")
    
    async def execute(
        self,
        search_term: str,
        fuzzy_match: bool = True,
        max_results: int = 10
    ) -> ToolExecutionResult:
        """
        Execute bank lookup.
        
        Args:
            search_term: Bank name or identifier to search for
            fuzzy_match: Enable fuzzy matching (default: True)
            max_results: Maximum number of results (default: 10)
            
        Returns:
            ToolExecutionResult with matching banks
        """
        self.logger.info(
            "Executing bank lookup",
            search_term=search_term,
            fuzzy_match=fuzzy_match,
            max_results=max_results
        )
        
        return await self.lookup_service.execute(
            search_term=search_term,
            fuzzy_match=fuzzy_match,
            max_results=max_results
        )
    
    def get_schema(self) -> Dict[str, Any]:
        """Get OpenAI function schema for this tool."""
        return self.lookup_service.get_schema()


class CallReportToolset:
    """
    Coordinated toolset for Call Report analysis.
    
    Manages the collection of Call Report tools and provides
    registration and coordination capabilities.
    """
    
    def __init__(self, settings: Settings):
        """
        Initialize Call Report toolset.
        
        Args:
            settings: Application settings
        """
        self.settings = settings
        self.logger = logger.bind(component="call_report_toolset")
        
        # Initialize core services
        self.api_client = CallReportMockAPI()
        self.lookup_service = BaseBankLookupTool()
        
        # Create tool wrappers
        self.tools = self._create_tools()
        
        self.logger.info(
            "CallReportToolset initialized",
            tools_count=len(self.tools),
            enabled=getattr(settings, 'call_report_enabled', True)
        )
    
    def _create_tools(self) -> List[BaseTool]:
        """
        Create and configure all Call Report tools.
        
        Returns:
            List of configured BaseTool instances
        """
        tools = []
        
        # Add bank lookup tool
        bank_lookup_tool = BankLookupTool(self.lookup_service)
        tools.append(bank_lookup_tool)
        
        # Add Call Report data tool
        call_report_data_tool = CallReportDataTool(self.api_client)
        tools.append(call_report_data_tool)
        
        # Add composite bank analysis tool for multi-step queries
        bank_analysis_tool = BankAnalysisTool()
        tools.append(bank_analysis_tool)
        
        self.logger.debug(
            "Call Report tools created",
            tool_names=[tool.name for tool in tools]
        )
        
        return tools
    
    def get_tools(self) -> List[BaseTool]:
        """
        Get all Call Report tools for registration.
        
        Returns:
            List of BaseTool instances ready for registration
        """
        return self.tools.copy()
    
    def register_with_registry(self, tool_registry) -> None:
        """
        Register all Call Report tools with a tool registry.
        
        Args:
            tool_registry: ToolRegistry instance to register with
        """
        if not getattr(self.settings, 'call_report_enabled', True):
            self.logger.info("Call Report tools disabled in settings")
            return
        
        registered_count = 0
        
        for tool in self.tools:
            try:
                tool_registry.register_tool(tool)
                registered_count += 1
                
                self.logger.debug(
                    "Registered Call Report tool",
                    tool_name=tool.name
                )
                
            except Exception as e:
                self.logger.error(
                    "Failed to register Call Report tool",
                    tool_name=tool.name,
                    error=str(e)
                )
        
        self.logger.info(
            "Call Report tools registration completed",
            registered_count=registered_count,
            total_tools=len(self.tools)
        )
    
    def is_available(self) -> bool:
        """
        Check if Call Report toolset is available.
        
        Returns:
            True if toolset is ready for use
        """
        if not getattr(self.settings, 'call_report_enabled', True):
            return False
        
        # Check if core services are available
        api_available = self.api_client.is_available()
        lookup_available = self.lookup_service.is_available()
        
        return api_available and lookup_available
    
    def get_health_status(self) -> Dict[str, Any]:
        """
        Get health status for all Call Report services.
        
        Returns:
            Health status information
        """
        status = {
            "toolset_enabled": getattr(self.settings, 'call_report_enabled', True),
            "tools_count": len(self.tools),
            "services": {
                "api_client": {
                    "available": self.api_client.is_available(),
                    "banks_available": len(self.api_client.get_available_banks())
                },
                "lookup_service": {
                    "available": self.lookup_service.is_available(),
                    "banks_directory_size": len(self.lookup_service.get_all_banks())
                }
            },
            "overall_health": "healthy" if self.is_available() else "degraded"
        }
        
        return status
    
    def get_available_banks_summary(self) -> Dict[str, Any]:
        """
        Get summary of available banks across all services.
        
        Returns:
            Summary of available bank data
        """
        # Get banks from API client
        api_banks = self.api_client.get_available_banks()
        
        # Get banks from lookup service
        lookup_banks = self.lookup_service.get_all_banks()
        
        return {
            "api_data_banks": len(api_banks),
            "lookup_directory_banks": len(lookup_banks),
            "sample_banks": [
                {
                    "rssd_id": bank.rssd_id,
                    "name": bank.legal_name,
                    "location": bank.location
                }
                for bank in lookup_banks[:5]  # First 5 banks as sample
            ]
        }


def create_call_report_toolset(settings: Settings) -> CallReportToolset:
    """
    Factory function to create Call Report toolset.
    
    Args:
        settings: Application settings
        
    Returns:
        Configured CallReportToolset instance
    """
    return CallReportToolset(settings)