"""
LangChain BaseTool implementations for RAG system integration.
Converts existing custom tools to LangChain-compatible tools for agent use.
"""

from typing import Optional, Dict, Any, Type, List
import asyncio
import structlog
from pydantic import BaseModel, Field

from langchain.tools import BaseTool
from langchain.callbacks.manager import (
    AsyncCallbackManagerForToolRun,
    CallbackManagerForToolRun,
)

from src.config.settings import Settings
from src.tools.call_report.langchain_tools import CallReportToolset
from src.tools.dynamic_loader import DynamicToolLoader
from src.tools.categories import (
    ToolCategory,
    categorize_tools,
    get_tools_by_category,
    add_category_metadata
)

logger = structlog.get_logger(__name__)


class CallReportQueryInput(BaseModel):
    """Input schema for Call Report data query tool."""
    rssd_id: str = Field(description="Bank RSSD ID (e.g., '12345')")
    schedule: str = Field(description="FFIEC schedule code (e.g., 'RC', 'RI')")
    field_id: str = Field(description="Field identifier (e.g., 'RCON2170')")


class CallReportDataTool(BaseTool):
    """
    LangChain BaseTool for FFIEC Call Report data retrieval.
    
    Retrieves specific field data from bank Call Reports using RSSD ID,
    schedule, and field identifiers.
    """
    
    name: str = "call_report_data"
    description: str = """Retrieve FFIEC Call Report field data for banks. 

Use this tool to get specific financial data from bank Call Reports by providing:
- rssd_id: Bank identifier (RSSD ID)
- schedule: FFIEC schedule (e.g., 'RC' for Report of Condition, 'RI' for Report of Income)
- field_id: Field identifier (e.g., 'RCON2170' for Total Assets)

Example usage: Get total assets for Bank of America (RSSD ID: 1073757)
- rssd_id: "1073757"
- schedule: "RC" 
- field_id: "RCON2170"
"""
    
    args_schema: Type[BaseModel] = CallReportQueryInput
    
    def __init__(self, toolset: CallReportToolset, **kwargs):
        """Initialize with Call Report toolset."""
        super().__init__(**kwargs)
        # Store toolset as a private attribute that won't interfere with LangChain
        object.__setattr__(self, '_toolset_instance', toolset)
        object.__setattr__(self, '_logger', logger.bind(
            log_type="TOOL",
            component="call_report_data_tool"
        ))
    
    def _run(
        self,
        rssd_id: str,
        schedule: str,
        field_id: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Synchronous execution."""
        try:
            # Try to get the current event loop
            loop = asyncio.get_running_loop()
            # If we're in an event loop, we need to handle this differently
            import concurrent.futures
            
            # Create a new event loop in a thread pool
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    lambda: asyncio.run(self._arun(rssd_id, schedule, field_id, run_manager))
                )
                return future.result()
                
        except RuntimeError:
            # No event loop running, safe to use asyncio.run
            return asyncio.run(self._arun(rssd_id, schedule, field_id, run_manager))
    
    async def _arun(
        self,
        rssd_id: str,
        schedule: str,
        field_id: str,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ) -> str:
        """
        Execute Call Report data retrieval.
        
        Args:
            rssd_id: Bank RSSD ID
            schedule: FFIEC schedule identifier
            field_id: Field identifier
            run_manager: Optional callback manager
            
        Returns:
            Formatted response with field data
        """
        try:
            self._logger.info(
                "Executing Call Report data query",
                rssd_id=rssd_id,
                schedule=schedule,
                field_id=field_id
            )
            
            # Get the Call Report data tool from toolset
            data_tool = next(
                (tool for tool in self._toolset_instance.get_tools() 
                 if tool.name == "call_report_data"),
                None
            )
            
            if not data_tool:
                return "Error: Call Report data tool not available"
            
            # Execute the tool
            result = await data_tool.execute(
                rssd_id=rssd_id,
                schedule=schedule,
                field_id=field_id
            )
            
            if result.success:
                data = result.data
                return f"""Call Report Data Retrieved:
Bank RSSD ID: {rssd_id}
Schedule: {schedule}
Field: {field_id}
Value: {data.get('value', 'Not available')}
Date: {data.get('date', 'Not available')}
Units: {data.get('units', 'Not specified')}

Source: FFIEC Call Report data"""
            else:
                return f"Error retrieving Call Report data: {result.error}"
                
        except Exception as e:
            self._logger.error("Call Report data query failed", error=str(e))
            return f"Error: Failed to retrieve Call Report data - {str(e)}"


class BankLookupInput(BaseModel):
    """Input schema for bank lookup tool."""
    search_term: str = Field(description="Bank name or identifier to search for")
    fuzzy_match: bool = Field(default=True, description="Enable fuzzy matching")
    max_results: int = Field(default=5, description="Maximum number of results (1-20)")


class BankLookupTool(BaseTool):
    """
    LangChain BaseTool for bank identification and RSSD ID lookup.
    
    Searches for banks by name and returns RSSD IDs and other identifying information.
    """
    
    name: str = "bank_lookup"
    description: str = """Look up bank RSSD ID and information from bank name or identifier.

Use this tool to find banks and get their RSSD IDs before querying Call Report data.
Supports fuzzy matching to find banks even with partial or slightly incorrect names.

Example usage: Find Bank of America
- search_term: "Bank of America"
- fuzzy_match: true
- max_results: 5

Returns bank name, RSSD ID, location, and other identifying information."""
    
    args_schema: Type[BaseModel] = BankLookupInput
    
    def __init__(self, toolset: CallReportToolset, **kwargs):
        """Initialize with Call Report toolset."""
        super().__init__(**kwargs)
        # Store toolset as a private attribute that won't interfere with LangChain
        object.__setattr__(self, '_toolset_instance', toolset)
        object.__setattr__(self, '_logger', logger.bind(
            log_type="TOOL",
            component="bank_lookup_tool"
        ))
    
    def _run(
        self,
        search_term: str,
        fuzzy_match: bool = True,
        max_results: int = 5,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Synchronous execution."""
        try:
            # Try to get the current event loop
            loop = asyncio.get_running_loop()
            # If we're in an event loop, we need to handle this differently
            import concurrent.futures
            
            # Create a new event loop in a thread pool
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    lambda: asyncio.run(self._arun(search_term, fuzzy_match, max_results, run_manager))
                )
                return future.result()
                
        except RuntimeError:
            # No event loop running, safe to use asyncio.run
            return asyncio.run(self._arun(search_term, fuzzy_match, max_results, run_manager))
    
    async def _arun(
        self,
        search_term: str,
        fuzzy_match: bool = True,
        max_results: int = 5,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ) -> str:
        """
        Execute bank lookup.
        
        Args:
            search_term: Bank name or identifier
            fuzzy_match: Enable fuzzy matching
            max_results: Maximum results to return
            run_manager: Optional callback manager
            
        Returns:
            Formatted list of matching banks
        """
        try:
            # Validate parameters
            max_results = max(1, min(20, max_results))
            
            self._logger.info(
                "Executing bank lookup",
                search_term=search_term,
                fuzzy_match=fuzzy_match,
                max_results=max_results
            )
            
            # Get the bank lookup tool from toolset
            lookup_tool = next(
                (tool for tool in self._toolset_instance.get_tools() 
                 if tool.name == "bank_lookup"),
                None
            )
            
            if not lookup_tool:
                return "Error: Bank lookup tool not available"
            
            # Execute the tool
            result = await lookup_tool.execute(
                search_term=search_term,
                fuzzy_match=fuzzy_match,
                max_results=max_results
            )
            
            if result.success:
                banks = result.data.get('banks', [])
                
                if not banks:
                    return f"No banks found matching '{search_term}'"
                
                # Format results
                response = f"Found {len(banks)} bank(s) matching '{search_term}':\n\n"
                
                for i, bank in enumerate(banks[:max_results], 1):
                    response += f"{i}. {bank.get('legal_name', 'Unknown')}\n"
                    response += f"   RSSD ID: {bank.get('rssd_id', 'Unknown')}\n"
                    response += f"   Location: {bank.get('location', 'Unknown')}\n"
                    response += f"   Charter Type: {bank.get('charter_type', 'Unknown')}\n"
                    response += f"   Status: {bank.get('status', 'Unknown')}\n\n"
                
                response += "Use the RSSD ID with the call_report_data tool to get financial data."
                return response
                
            else:
                return f"Error looking up banks: {result.error}"
                
        except Exception as e:
            self._logger.error("Bank lookup failed", error=str(e))
            return f"Error: Failed to lookup banks - {str(e)}"


class LangChainToolRegistry:
    """
    Enhanced registry for LangChain-compatible tools with category support.
    
    Manages the conversion and registration of existing tools to LangChain BaseTool format
    for use with ChatbotAgent multi-step workflows. Now includes dynamic tool loading
    based on service availability and category-based organization.
    
    CRITICAL FIX: Now properly registers RAG tool (document_search) which was missing.
    """
    
    def __init__(self, settings: Settings, enable_dynamic_loading: bool = True):
        """
        Initialize enhanced LangChain tool registry.
        
        Args:
            settings: Application settings
            enable_dynamic_loading: Enable dynamic tool loading based on service availability
        """
        self.settings = settings
        self.enable_dynamic_loading = enable_dynamic_loading
        self.logger = logger.bind(
            log_type="SYSTEM",
            component="langchain_tool_registry"
        )
        
        # Initialize dynamic loader if enabled
        self.dynamic_loader = None
        if enable_dynamic_loading:
            self.dynamic_loader = DynamicToolLoader(settings)
        
        # Initialize underlying toolsets (backward compatibility)
        self.call_report_toolset = None
        if getattr(settings, 'call_report_enabled', True):
            try:
                self.call_report_toolset = CallReportToolset(settings)
                self.logger.info("Call Report toolset initialized for LangChain")
            except Exception as e:
                self.logger.error("Failed to initialize Call Report toolset", error=str(e))
        
        # Create LangChain tools (both legacy and dynamic)
        self.tools = []
        self.tools_by_category = {}
        self._initialize_tools()
        
        self.logger.info(
            "Enhanced LangChain tool registry initialized",
            tools_count=len(self.tools),
            dynamic_loading=enable_dynamic_loading,
            call_report_available=self.call_report_toolset is not None
        )
    
    def _initialize_tools(self):
        """
        Initialize tools using both legacy and dynamic loading methods.
        
        CRITICAL FIX: This method now properly includes RAG tool registration.
        """
        if self.enable_dynamic_loading and self.dynamic_loader:
            # Check if we're already in an event loop
            try:
                loop = asyncio.get_running_loop()
                # If we're in an event loop, run in thread pool
                import threading
                import concurrent.futures
                
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        lambda: asyncio.run(self._load_tools_dynamically())
                    )
                    future.result()  # Wait for completion
                    
            except RuntimeError:
                # No event loop running, safe to use asyncio.run
                asyncio.run(self._load_tools_dynamically())
        else:
            # Fallback to legacy tool creation
            self.tools = self._create_legacy_langchain_tools()
            self.tools_by_category = categorize_tools(self.tools)
    
    async def _load_tools_dynamically(self):
        """
        Load tools dynamically based on service availability.
        
        This method fixes the critical RAG tool registration issue.
        """
        try:
            # Load all available tools by category
            tools_by_category = await self.dynamic_loader.load_all_available_tools()
            
            # Flatten to single list while preserving category info
            all_tools = []
            for category, tools in tools_by_category.items():
                all_tools.extend(tools)
            
            self.tools = all_tools
            self.tools_by_category = tools_by_category
            
            # Log critical RAG tool registration status
            rag_tools = [tool for tool in all_tools if tool.name == "document_search"]
            if rag_tools:
                self.logger.info(
                    "CRITICAL FIX: RAG tool successfully registered",
                    rag_tool_count=len(rag_tools)
                )
            else:
                self.logger.warning(
                    "CRITICAL ISSUE: RAG tool still not registered - ChromaDB may not be available"
                )
            
            self.logger.info(
                "Dynamic tool loading completed",
                total_tools=len(all_tools),
                categories=list(tools_by_category.keys()),
                tools_by_category={k.value: len(v) for k, v in tools_by_category.items()}
            )
            
        except Exception as e:
            self.logger.error("Dynamic tool loading failed, falling back to legacy", error=str(e))
            # Fallback to legacy loading
            self.tools = self._create_legacy_langchain_tools()
            self.tools_by_category = categorize_tools(self.tools)
    
    def _create_legacy_langchain_tools(self) -> List[BaseTool]:
        """
        Create LangChain BaseTool instances using legacy method.
        
        CRITICAL FIX: Now includes RAG tool registration that was missing.
        
        Returns:
            List of LangChain-compatible BaseTool instances
        """
        tools = []
        
        # CRITICAL FIX: Add RAG tool that was missing in original implementation
        try:
            from src.rag.rag_tool import RAGSearchTool
            from src.rag.retriever import RAGRetriever
            
            # Initialize RAG components
            rag_retriever = RAGRetriever(self.settings)
            rag_tool = RAGSearchTool(rag_retriever)
            
            # Add category metadata
            rag_tool = add_category_metadata(
                rag_tool,
                category=ToolCategory.DOCUMENTS,
                requires_services=["chromadb"],
                priority=10,
                tags=["document_search", "rag", "retrieval"]
            )
            
            tools.append(rag_tool)
            
            self.logger.info("CRITICAL FIX: RAG tool registered successfully in legacy mode")
            
        except Exception as e:
            self.logger.error("CRITICAL: Failed to register RAG tool in legacy mode", error=str(e))
        
        # Add Call Report tools if available
        if self.call_report_toolset and self.call_report_toolset.is_available():
            try:
                # Create LangChain wrappers for Call Report tools
                call_report_data_tool = CallReportDataTool(self.call_report_toolset)
                bank_lookup_tool = BankLookupTool(self.call_report_toolset)
                
                # Add category metadata
                call_report_data_tool = add_category_metadata(
                    call_report_data_tool,
                    category=ToolCategory.BANKING,
                    requires_services=["call_report_api"],
                    priority=5,
                    tags=["banking", "financial", "call_report"]
                )
                
                bank_lookup_tool = add_category_metadata(
                    bank_lookup_tool,
                    category=ToolCategory.BANKING,
                    requires_services=["call_report_api"],
                    priority=6,
                    tags=["banking", "lookup", "rssd"]
                )
                
                tools.extend([call_report_data_tool, bank_lookup_tool])
                
                self.logger.info(
                    "Call Report LangChain tools created with categories",
                    tools_added=2
                )
                
            except Exception as e:
                self.logger.error("Failed to create Call Report LangChain tools", error=str(e))
        
        return tools
    
    def get_tools_by_category(self, category: ToolCategory) -> List[BaseTool]:
        """
        Get tools filtered by specific category.
        
        Args:
            category: Tool category to filter by
            
        Returns:
            List of tools in the specified category
        """
        if self.tools_by_category:
            return self.tools_by_category.get(category, [])
        else:
            # Fallback to runtime categorization
            return get_tools_by_category(self.tools, category)
    
    def get_available_categories(self) -> List[ToolCategory]:
        """
        Get list of categories with available tools.
        
        Returns:
            List of categories that have tools available
        """
        if self.tools_by_category:
            return [cat for cat, tools in self.tools_by_category.items() if tools]
        else:
            # Fallback to runtime categorization
            categorized = categorize_tools(self.tools)
            return list(categorized.keys())
    
    def get_category_summary(self) -> Dict[str, Any]:
        """
        Get summary of tools organized by category.
        
        Returns:
            Dictionary with category information and tool counts
        """
        if not self.tools_by_category:
            self.tools_by_category = categorize_tools(self.tools)
        
        summary = {
            "total_tools": len(self.tools),
            "total_categories": len(self.tools_by_category),
            "categories": {},
            "dynamic_loading_enabled": self.enable_dynamic_loading
        }
        
        for category, tools in self.tools_by_category.items():
            summary["categories"][category.value] = {
                "tool_count": len(tools),
                "tool_names": [tool.name for tool in tools],
                "has_rag_tool": any(tool.name == "document_search" for tool in tools)
            }
        
        return summary
    
    async def reload_tools(self) -> bool:
        """
        Reload all tools by refreshing dynamic loader.
        
        Returns:
            True if reload was successful
        """
        try:
            if self.enable_dynamic_loading and self.dynamic_loader:
                # Clear current tools
                self.tools.clear()
                self.tools_by_category.clear()
                
                # Reload using dynamic loader
                await self._load_tools_dynamically()
                
                self.logger.info(
                    "Tools reloaded successfully",
                    tools_count=len(self.tools)
                )
                return True
            else:
                # Recreate legacy tools
                self.tools = self._create_legacy_langchain_tools()
                self.tools_by_category = categorize_tools(self.tools)
                
                self.logger.info(
                    "Legacy tools reloaded",
                    tools_count=len(self.tools)
                )
                return True
                
        except Exception as e:
            self.logger.error("Failed to reload tools", error=str(e))
            return False
    
    def get_tools(self) -> List[BaseTool]:
        """
        Get all available LangChain tools.
        
        Returns:
            List of LangChain BaseTool instances ready for agent use
        """
        return self.tools.copy()
    
    def get_tools_for_agent(self, include_rag: bool = True) -> List[BaseTool]:
        """
        Get tools configured for ChatbotAgent use.
        
        CRITICAL FIX: RAG tool is now properly included in the registry,
        no longer requiring external addition.
        
        Args:
            include_rag: Whether to include RAG tool (now handled internally)
            
        Returns:
            List of tools ready for ChatbotAgent
        """
        tools = self.get_tools()
        
        # Filter RAG tool if requested (though it should normally be included)
        if not include_rag:
            tools = [tool for tool in tools if tool.name != "document_search"]
        
        # Verify RAG tool inclusion
        rag_tools = [tool for tool in tools if tool.name == "document_search"]
        has_rag = len(rag_tools) > 0
        
        self.logger.info(
            "Tools prepared for agent",
            tool_count=len(tools),
            tool_names=[tool.name for tool in tools],
            rag_tool_included=has_rag,
            include_rag_requested=include_rag
        )
        
        return tools
    
    def is_available(self) -> bool:
        """
        Check if the tool registry is available and has tools.
        
        Returns:
            True if tools are available
        """
        return len(self.tools) > 0
    
    def get_tool_by_name(self, name: str) -> Optional[BaseTool]:
        """
        Get a specific tool by name.
        
        Args:
            name: Tool name to search for
            
        Returns:
            BaseTool instance or None if not found
        """
        return next((tool for tool in self.tools if tool.name == name), None)
    
    def get_health_status(self) -> Dict[str, Any]:
        """
        Get health status for all tools and toolsets.
        
        Returns:
            Health status information
        """
        status = {
            "registry_available": self.is_available(),
            "tools_count": len(self.tools),
            "tool_names": [tool.name for tool in self.tools],
            "toolsets": {}
        }
        
        # Add Call Report toolset status
        if self.call_report_toolset:
            status["toolsets"]["call_report"] = self.call_report_toolset.get_health_status()
        else:
            status["toolsets"]["call_report"] = {"available": False, "reason": "Not initialized"}
        
        # Add dynamic loader status
        if self.dynamic_loader:
            status["dynamic_loader"] = self.dynamic_loader.get_loading_status()
        
        # Add category information
        status["categories"] = self.get_category_summary()
        
        # CRITICAL: Check RAG tool registration status
        rag_tools = [tool for tool in self.tools if tool.name == "document_search"]
        status["rag_tool_registered"] = len(rag_tools) > 0
        
        if not status["rag_tool_registered"]:
            status["critical_warning"] = "RAG tool (document_search) not registered - this was the main issue to fix"
        
        status["overall_health"] = "healthy" if self.is_available() else "no_tools_available"
        
        return status


def create_langchain_tool_registry(settings: Settings, enable_dynamic_loading: bool = True) -> LangChainToolRegistry:
    """
    Factory function to create LangChain tool registry.
    
    Args:
        settings: Application settings
        
    Returns:
        Configured LangChainToolRegistry instance
    """
    return LangChainToolRegistry(settings, enable_dynamic_loading)


def get_langchain_tools_for_agent(settings: Settings, include_rag: bool = True, enable_dynamic_loading: bool = True) -> List[BaseTool]:
    """
    Convenience function to get LangChain tools for ChatbotAgent.
    
    Args:
        settings: Application settings
        include_rag: Whether to include space for RAG tool (caller responsibility)
        
    Returns:
        List of LangChain BaseTool instances ready for agent use
    """
    registry = create_langchain_tool_registry(settings, enable_dynamic_loading)
    return registry.get_tools_for_agent(include_rag=include_rag)
