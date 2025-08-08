"""
Base classes for the tools system.

Provides the foundation for all external tools and API integrations.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime, timezone
import time
import asyncio
from enum import Enum

import structlog

logger = structlog.get_logger(__name__)


class ToolStatus(Enum):
    """Tool execution status."""
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    NOT_AVAILABLE = "not_available"


@dataclass
class ToolExecutionResult:
    """Result of a tool execution."""
    
    status: ToolStatus
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    execution_time: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    tool_name: str = ""
    
    @property
    def success(self) -> bool:
        """Check if the tool execution was successful."""
        return self.status == ToolStatus.SUCCESS
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "status": self.status.value,
            "data": self.data,
            "error": self.error,
            "execution_time": self.execution_time,
            "timestamp": self.timestamp.isoformat(),
            "tool_name": self.tool_name,
            "success": self.success
        }


class BaseTool(ABC):
    """
    Abstract base class for all tools.
    
    Tools are external integrations that can be called by the AI chatbot
    to retrieve real-time information or perform actions beyond RAG.
    """
    
    def __init__(self, name: str, description: str):
        """
        Initialize the base tool.
        
        Args:
            name: Unique identifier for the tool
            description: Human-readable description of what the tool does
        """
        self.name = name
        self.description = description
        self.logger = logger.bind(
            log_type="SYSTEM",
            component="tool",
            tool_name=name
        )
        self._enabled = True
        self._timeout = 30.0  # Default timeout in seconds
    
    @abstractmethod
    async def execute(self, **kwargs) -> ToolExecutionResult:
        """
        Execute the tool with given parameters.
        
        Args:
            **kwargs: Tool-specific parameters
            
        Returns:
            ToolExecutionResult containing the execution result
        """
        pass
    
    @abstractmethod
    def get_schema(self) -> Dict[str, Any]:
        """
        Get the JSON schema for OpenAI function calling.
        
        Returns:
            Dictionary containing the function schema for OpenAI
        """
        pass
    
    def is_available(self) -> bool:
        """
        Check if the tool is available for use.
        
        Returns:
            True if the tool can be executed
        """
        return self._enabled
    
    def enable(self):
        """Enable the tool."""
        self._enabled = True
        self.logger.info("Tool enabled")
    
    def disable(self):
        """Disable the tool."""
        self._enabled = False
        self.logger.info("Tool disabled")
    
    def set_timeout(self, timeout: float):
        """
        Set the execution timeout for the tool.
        
        Args:
            timeout: Timeout in seconds
        """
        self._timeout = timeout
        self.logger.info("Tool timeout updated", timeout=timeout)
    
    async def execute_with_timeout(self, **kwargs) -> ToolExecutionResult:
        """
        Execute the tool with timeout protection.
        
        Args:
            **kwargs: Tool-specific parameters
            
        Returns:
            ToolExecutionResult with timeout handling
        """
        if not self.is_available():
            return ToolExecutionResult(
                status=ToolStatus.NOT_AVAILABLE,
                error=f"Tool '{self.name}' is not available",
                tool_name=self.name
            )
        
        start_time = time.time()
        
        try:
            # Execute with timeout
            result = await asyncio.wait_for(
                self.execute(**kwargs),
                timeout=self._timeout
            )
            
            result.execution_time = time.time() - start_time
            result.tool_name = self.name
            
            self.logger.info(
                "Tool executed successfully",
                execution_time=result.execution_time,
                status=result.status.value
            )
            
            return result
            
        except asyncio.TimeoutError:
            execution_time = time.time() - start_time
            
            self.logger.error(
                "Tool execution timeout",
                timeout=self._timeout,
                execution_time=execution_time
            )
            
            return ToolExecutionResult(
                status=ToolStatus.TIMEOUT,
                error=f"Tool '{self.name}' timed out after {self._timeout} seconds",
                execution_time=execution_time,
                tool_name=self.name
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            self.logger.error(
                "Tool execution failed",
                error=str(e),
                execution_time=execution_time
            )
            
            return ToolExecutionResult(
                status=ToolStatus.ERROR,
                error=str(e),
                execution_time=execution_time,
                tool_name=self.name
            )
    
    def __repr__(self) -> str:
        """String representation of the tool."""
        return f"{self.__class__.__name__}(name='{self.name}', enabled={self._enabled})"


class ToolRegistry:
    """
    Registry for managing available tools.
    
    Provides centralized management of tools including registration,
    discovery, and execution coordination.
    """
    
    def __init__(self):
        """Initialize the tool registry."""
        self.tools: Dict[str, BaseTool] = {}
        self.logger = logger.bind(
            log_type="SYSTEM",
            component="tool_registry" 
        )
    
    def register_tool(self, tool: BaseTool):
        """
        Register a tool with the registry.
        
        Args:
            tool: Tool instance to register
        """
        if not isinstance(tool, BaseTool):
            raise ValueError(f"Tool must inherit from BaseTool, got {type(tool)}")
        
        if tool.name in self.tools:
            self.logger.warning(
                "Tool already registered, replacing",
                tool_name=tool.name
            )
        
        self.tools[tool.name] = tool
        
        self.logger.info(
            "Tool registered successfully",
            tool_name=tool.name,
            total_tools=len(self.tools)
        )
    
    def unregister_tool(self, tool_name: str):
        """
        Unregister a tool from the registry.
        
        Args:
            tool_name: Name of the tool to unregister
        """
        if tool_name in self.tools:
            del self.tools[tool_name]
            self.logger.info(
                "Tool unregistered",
                tool_name=tool_name,
                total_tools=len(self.tools)
            )
        else:
            self.logger.warning(
                "Attempted to unregister unknown tool",
                tool_name=tool_name
            )
    
    def get_tool(self, tool_name: str) -> Optional[BaseTool]:
        """
        Get a tool by name.
        
        Args:
            tool_name: Name of the tool to retrieve
            
        Returns:
            Tool instance or None if not found
        """
        return self.tools.get(tool_name)
    
    def list_tools(self, available_only: bool = True) -> List[BaseTool]:
        """
        List all registered tools.
        
        Args:
            available_only: Only return available tools
            
        Returns:
            List of tool instances
        """
        tools = list(self.tools.values())
        
        if available_only:
            tools = [tool for tool in tools if tool.is_available()]
        
        return tools
    
    def get_function_schemas(self) -> List[Dict[str, Any]]:
        """
        Get OpenAI function schemas for all available tools.
        
        Returns:
            List of function schemas for OpenAI function calling
        """
        schemas = []
        
        for tool in self.list_tools(available_only=True):
            try:
                schema = tool.get_schema()
                schemas.append(schema)
            except Exception as e:
                self.logger.error(
                    "Failed to get schema for tool",
                    tool_name=tool.name,
                    error=str(e)
                )
        
        self.logger.debug(
            "Generated function schemas",
            schema_count=len(schemas)
        )
        
        return schemas
    
    async def execute_tool(
        self, 
        tool_name: str, 
        **kwargs
    ) -> ToolExecutionResult:
        """
        Execute a tool by name.
        
        Args:
            tool_name: Name of the tool to execute
            **kwargs: Parameters to pass to the tool
            
        Returns:
            ToolExecutionResult containing the execution result
        """
        tool = self.get_tool(tool_name)
        
        if not tool:
            return ToolExecutionResult(
                status=ToolStatus.ERROR,
                error=f"Tool '{tool_name}' not found",
                tool_name=tool_name
            )
        
        self.logger.info(
            "Executing tool",
            tool_name=tool_name,
            parameters=list(kwargs.keys())
        )
        
        return await tool.execute_with_timeout(**kwargs)
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get registry statistics.
        
        Returns:
            Dictionary containing registry stats
        """
        total_tools = len(self.tools)
        available_tools = len([t for t in self.tools.values() if t.is_available()])
        
        return {
            "total_tools": total_tools,
            "available_tools": available_tools,
            "disabled_tools": total_tools - available_tools,
            "tool_names": list(self.tools.keys())
        }
    
    def __len__(self) -> int:
        """Get the number of registered tools."""
        return len(self.tools)
    
    def __contains__(self, tool_name: str) -> bool:
        """Check if a tool is registered."""
        return tool_name in self.tools