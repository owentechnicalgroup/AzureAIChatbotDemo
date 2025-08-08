"""
Dynamic tool loading system based on service availability and dependencies.

Checks service availability and dynamically loads LangChain tools based on
their requirements, following the existing async patterns in the codebase.
"""

import asyncio
from typing import Dict, List, Set, Any, Optional, Callable
from datetime import datetime, timedelta
import structlog
from langchain.tools import BaseTool

from src.config.settings import Settings
from .categories import (
    ToolCategory,
    get_tool_category,
    get_tool_metadata,
    filter_tools_by_service_availability
)

logger = structlog.get_logger(__name__)


class ServiceAvailabilityChecker:
    """
    Checks availability of services required by tools.
    
    Follows the existing codebase patterns for async service checking
    with caching to avoid repeated expensive checks.
    """
    
    def __init__(self, settings: Settings, cache_ttl_seconds: int = 300):
        """
        Initialize service availability checker.
        
        Args:
            settings: Application settings
            cache_ttl_seconds: Cache time-to-live in seconds
        """
        self.settings = settings
        self.cache_ttl = timedelta(seconds=cache_ttl_seconds)
        self.logger = logger.bind(
            log_type="SYSTEM",
            component="service_availability_checker"
        )
        
        # Cache for availability results with timestamps
        self._availability_cache: Dict[str, tuple[bool, datetime]] = {}
        
        # Service check methods mapping
        self._service_checkers = self._initialize_service_checkers()
        
        self.logger.info(
            "Service availability checker initialized",
            cache_ttl_seconds=cache_ttl_seconds,
            available_checkers=list(self._service_checkers.keys())
        )
    
    def _initialize_service_checkers(self) -> Dict[str, Callable]:
        """
        Initialize mapping of service names to checker methods.
        
        Returns:
            Dictionary mapping service names to async checker methods
        """
        return {
            "chromadb": self._check_chromadb_availability,
            "call_report_api": self._check_call_report_api_availability,
            "web_search_api": self._check_web_search_api_availability,
        }
    
    async def check_service_availability(self, service_name: str) -> bool:
        """
        Check if a service is available, with caching.
        
        Args:
            service_name: Name of service to check
            
        Returns:
            True if service is available and functional
        """
        # Check cache first
        if service_name in self._availability_cache:
            availability, timestamp = self._availability_cache[service_name]
            if datetime.now() - timestamp < self.cache_ttl:
                self.logger.debug(
                    "Service availability from cache",
                    service=service_name,
                    available=availability
                )
                return availability
        
        # Get checker method
        checker = self._service_checkers.get(service_name)
        if not checker:
            self.logger.warning(
                "No checker available for service",
                service=service_name
            )
            return False
        
        # Perform availability check
        try:
            availability = await checker()
            
            # Cache result
            self._availability_cache[service_name] = (availability, datetime.now())
            
            self.logger.info(
                "Service availability checked",
                service=service_name,
                available=availability
            )
            
            return availability
            
        except Exception as e:
            self.logger.error(
                "Service availability check failed",
                service=service_name,
                error=str(e)
            )
            
            # Cache negative result for shorter time
            self._availability_cache[service_name] = (False, datetime.now())
            return False
    
    async def check_multiple_services(self, service_names: List[str]) -> Dict[str, bool]:
        """
        Check availability of multiple services concurrently.
        
        Args:
            service_names: List of service names to check
            
        Returns:
            Dictionary mapping service names to availability status
        """
        tasks = [
            self.check_service_availability(service_name)
            for service_name in service_names
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        availability_map = {}
        for service_name, result in zip(service_names, results):
            if isinstance(result, Exception):
                self.logger.error(
                    "Service check task failed",
                    service=service_name,
                    error=str(result)
                )
                availability_map[service_name] = False
            else:
                availability_map[service_name] = result
        
        return availability_map
    
    async def _check_chromadb_availability(self) -> bool:
        """
        Check ChromaDB availability for document tools.
        
        Follows the existing pattern in chromadb_manager.py.
        """
        try:
            from src.rag.chromadb_manager import ChromaDBManager
            
            # Initialize ChromaDB manager
            chromadb_manager = ChromaDBManager(self.settings)
            
            # Test basic functionality - get document count
            doc_count = await chromadb_manager.get_document_count()
            
            # ChromaDB is available if we can get count (even if 0)
            is_available = doc_count >= 0
            
            self.logger.debug(
                "ChromaDB availability check",
                available=is_available,
                document_count=doc_count
            )
            
            return is_available
            
        except ImportError as e:
            self.logger.warning("ChromaDB not installed", error=str(e))
            return False
        except Exception as e:
            self.logger.warning("ChromaDB check failed", error=str(e))
            return False
    
    async def _check_call_report_api_availability(self) -> bool:
        """
        Check Call Report API availability.
        
        Follows the existing pattern in call_report tools.
        """
        try:
            from src.tools.call_report.mock_api_client import CallReportMockAPI
            
            # Initialize mock API client
            api_client = CallReportMockAPI()
            
            # Check if API is available
            is_available = api_client.is_available()
            
            self.logger.debug(
                "Call Report API availability check",
                available=is_available
            )
            
            return is_available
            
        except ImportError as e:
            self.logger.warning("Call Report API not available", error=str(e))
            return False
        except Exception as e:
            self.logger.warning("Call Report API check failed", error=str(e))
            return False
    
    async def _check_web_search_api_availability(self) -> bool:
        """
        Check web search API availability.
        
        Placeholder for future web search tools.
        """
        # For now, web search is not implemented
        return False
    
    def clear_cache(self):
        """Clear the availability cache to force fresh checks."""
        self._availability_cache.clear()
        self.logger.info("Service availability cache cleared")
    
    def get_cache_status(self) -> Dict[str, Any]:
        """
        Get current cache status for monitoring.
        
        Returns:
            Dictionary with cache statistics
        """
        now = datetime.now()
        cache_status = {
            "total_entries": len(self._availability_cache),
            "cache_ttl_seconds": self.cache_ttl.total_seconds(),
            "entries": {}
        }
        
        for service, (available, timestamp) in self._availability_cache.items():
            age_seconds = (now - timestamp).total_seconds()
            cache_status["entries"][service] = {
                "available": available,
                "age_seconds": age_seconds,
                "is_fresh": age_seconds < self.cache_ttl.total_seconds()
            }
        
        return cache_status


class DynamicToolLoader:
    """
    Dynamically loads tools based on service availability and category configuration.
    
    Integrates with the existing LangChain tool patterns while adding
    intelligent loading based on service dependencies.
    """
    
    def __init__(self, settings: Settings):
        """
        Initialize dynamic tool loader.
        
        Args:
            settings: Application settings
        """
        self.settings = settings
        self.availability_checker = ServiceAvailabilityChecker(settings)
        self.logger = logger.bind(
            log_type="SYSTEM",
            component="dynamic_tool_loader"
        )
        
        # Track loaded tools by category
        self._loaded_tools: Dict[ToolCategory, List[BaseTool]] = {}
        self._available_services: Set[str] = set()
        
        self.logger.info("Dynamic tool loader initialized")
    
    async def check_service_availability(self) -> Set[str]:
        """
        Check availability of all known services.
        
        Returns:
            Set of available service names
        """
        # Get all known service names from service checkers
        service_names = list(self.availability_checker._service_checkers.keys())
        
        # Check all services concurrently
        availability_map = await self.availability_checker.check_multiple_services(service_names)
        
        # Build set of available services
        available_services = {
            service for service, available in availability_map.items()
            if available
        }
        
        self._available_services = available_services
        
        self.logger.info(
            "Service availability check completed",
            total_services=len(service_names),
            available_services=len(available_services),
            available_list=list(available_services)
        )
        
        return available_services
    
    async def load_tools_by_category(self, category: ToolCategory) -> List[BaseTool]:
        """
        Load tools for a specific category based on service availability.
        
        Args:
            category: Tool category to load
            
        Returns:
            List of loaded BaseTool instances
        """
        self.logger.info(
            "Loading tools for category",
            category=category.value
        )
        
        # Ensure we have current service availability
        if not self._available_services:
            await self.check_service_availability()
        
        tools = []
        
        try:
            if category == ToolCategory.DOCUMENTS:
                tools.extend(await self._load_document_tools())
            elif category == ToolCategory.BANKING:
                tools.extend(await self._load_banking_tools())
            elif category == ToolCategory.ANALYSIS:
                tools.extend(await self._load_analysis_tools())
            elif category == ToolCategory.WEB:
                tools.extend(await self._load_web_tools())
            elif category == ToolCategory.UTILITIES:
                tools.extend(await self._load_utility_tools())
        
        except Exception as e:
            self.logger.error(
                "Failed to load tools for category",
                category=category.value,
                error=str(e)
            )
        
        # Filter tools based on service availability
        available_tools = filter_tools_by_service_availability(
            tools, 
            self._available_services
        )
        
        # Cache loaded tools
        self._loaded_tools[category] = available_tools
        
        self.logger.info(
            "Tools loaded for category",
            category=category.value,
            total_tools=len(tools),
            available_tools=len(available_tools)
        )
        
        return available_tools
    
    async def _load_document_tools(self) -> List[BaseTool]:
        """Load document category tools (RAG, file processing)."""
        tools = []
        
        # Load RAG tool if ChromaDB is available
        if "chromadb" in self._available_services:
            try:
                from src.rag.rag_tool import RAGSearchTool
                from src.rag.retriever import RAGRetriever
                from .categories import add_category_metadata, ToolCategory
                
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
                
                self.logger.info("RAG tool loaded successfully")
                
            except Exception as e:
                self.logger.error("Failed to load RAG tool", error=str(e))
        
        return tools
    
    async def _load_banking_tools(self) -> List[BaseTool]:
        """Load banking category tools (Call Report, financial analysis)."""
        tools = []
        
        # Load Call Report tools if API is available
        if "call_report_api" in self._available_services:
            try:
                from src.tools.call_report.langchain_tools import CallReportToolset
                from .categories import add_category_metadata, ToolCategory
                
                # Initialize Call Report toolset
                call_report_toolset = CallReportToolset(self.settings)
                base_tools = call_report_toolset.get_tools()
                
                # Add category metadata to each tool
                for tool in base_tools:
                    # Skip if tool is not a LangChain BaseTool
                    if not isinstance(tool, BaseTool):
                        continue
                    
                    # Add banking category metadata
                    tool = add_category_metadata(
                        tool,
                        category=ToolCategory.BANKING,
                        requires_services=["call_report_api"],
                        priority=5,
                        tags=["banking", "financial", "call_report"]
                    )
                    
                    tools.append(tool)
                
                self.logger.info(
                    "Call Report tools loaded successfully",
                    tool_count=len(tools)
                )
                
            except Exception as e:
                self.logger.error("Failed to load Call Report tools", error=str(e))
        
        return tools
    
    async def _load_analysis_tools(self) -> List[BaseTool]:
        """Load analysis category tools (calculations, data processing)."""
        tools = []
        
        # Analysis tools would be loaded here
        # For now, returning empty list as no analysis tools are implemented
        
        return tools
    
    async def _load_web_tools(self) -> List[BaseTool]:
        """Load web category tools (search, APIs)."""
        tools = []
        
        # Web tools would be loaded here
        # For now, returning empty list as web tools are not implemented
        
        return tools
    
    async def _load_utility_tools(self) -> List[BaseTool]:
        """Load utility category tools (time, formatting, general)."""
        tools = []
        
        # Utility tools would be loaded here
        # These typically don't have service dependencies
        
        return tools
    
    async def load_all_available_tools(self) -> Dict[ToolCategory, List[BaseTool]]:
        """
        Load all tools across all categories based on service availability.
        
        Returns:
            Dictionary mapping categories to available tools
        """
        self.logger.info("Loading all available tools")
        
        # Check service availability first
        await self.check_service_availability()
        
        # Load tools for each category
        all_tools = {}
        for category in ToolCategory:
            tools = await self.load_tools_by_category(category)
            if tools:  # Only include categories with available tools
                all_tools[category] = tools
        
        total_tools = sum(len(tools) for tools in all_tools.values())
        
        self.logger.info(
            "All available tools loaded",
            total_categories=len(all_tools),
            total_tools=total_tools,
            categories=list(all_tools.keys())
        )
        
        return all_tools
    
    def get_loaded_tools(self, category: Optional[ToolCategory] = None) -> List[BaseTool]:
        """
        Get previously loaded tools.
        
        Args:
            category: Optional category filter
            
        Returns:
            List of loaded tools
        """
        if category:
            return self._loaded_tools.get(category, [])
        
        # Return all loaded tools across categories
        all_tools = []
        for tools in self._loaded_tools.values():
            all_tools.extend(tools)
        
        return all_tools
    
    def get_loading_status(self) -> Dict[str, Any]:
        """
        Get current loading status for monitoring.
        
        Returns:
            Dictionary with loading statistics
        """
        status = {
            "available_services": list(self._available_services),
            "loaded_categories": len(self._loaded_tools),
            "total_loaded_tools": sum(len(tools) for tools in self._loaded_tools.values()),
            "categories": {}
        }
        
        for category, tools in self._loaded_tools.items():
            status["categories"][category.value] = {
                "tool_count": len(tools),
                "tool_names": [tool.name for tool in tools]
            }
        
        return status
    
    async def reload_tools(self) -> Dict[ToolCategory, List[BaseTool]]:
        """
        Reload all tools after clearing caches.
        
        Returns:
            Dictionary mapping categories to reloaded tools
        """
        self.logger.info("Reloading all tools")
        
        # Clear caches
        self.availability_checker.clear_cache()
        self._loaded_tools.clear()
        self._available_services.clear()
        
        # Reload all tools
        return await self.load_all_available_tools()