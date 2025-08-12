"""
LangChain-compatible Call Report data retrieval tool.

Provides FFIEC Call Report field data retrieval using LangChain BaseTool interface
for integration with AI agents and multi-step workflows.
"""

import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Type
import structlog
from pydantic import BaseModel, Field
from langchain.tools import BaseTool
from langchain.callbacks.manager import (
    AsyncCallbackManagerForToolRun,
    CallbackManagerForToolRun,
)

from .mock_api_client import CallReportMockAPI

logger = structlog.get_logger(__name__).bind(log_type="SYSTEM")


class CallReportDataInput(BaseModel):
    """Input schema for Call Report data tool."""
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
    
    args_schema: Type[BaseModel] = CallReportDataInput
    
    def __init__(self, api_client: Optional[CallReportMockAPI] = None, **kwargs):
        """Initialize Call Report data tool."""
        super().__init__(**kwargs)
        
        # Use private attribute to avoid Pydantic conflicts
        object.__setattr__(self, '_api_client', api_client or CallReportMockAPI())
        
        logger.info("CallReportDataTool initialized")
    
    @property
    def api_client(self) -> CallReportMockAPI:
        """Get the API client."""
        return getattr(self, '_api_client')
    
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
            logger.info(
                "Executing Call Report data query",
                rssd_id=rssd_id,
                schedule=schedule,
                field_id=field_id
            )
            
            # Validate inputs
            if not rssd_id or not schedule or not field_id:
                return "Error: All parameters (rssd_id, schedule, field_id) are required"
            
            # Execute the API call
            data = await self.api_client.execute(
                rssd_id=rssd_id,
                schedule=schedule,
                field_id=field_id
            )
            
            return f"""Call Report Data Retrieved:
Bank RSSD ID: {rssd_id}
Schedule: {schedule}
Field: {field_id}
Value: {data.get('value', 'Not available')}
Date: {data.get('date', 'Not available')}
Units: {data.get('units', 'Not specified')}

Source: FFIEC Call Report data"""
                
        except Exception as e:
            logger.error("Call Report data query failed", error=str(e))
            return f"Error: Failed to retrieve Call Report data - {str(e)}"
    
    def is_available(self) -> bool:
        """Check if the Call Report API is available."""
        return self.api_client.is_available()