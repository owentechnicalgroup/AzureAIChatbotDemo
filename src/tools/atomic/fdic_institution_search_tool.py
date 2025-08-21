"""
Atomic FDIC Institution Search Tool.

Clean, focused tool for searching FDIC institutions using the BankFind Suite API.
Returns structured data with CERT numbers for use in financial data queries.
"""

import asyncio
from typing import Optional, Type, List, Dict, Any
from datetime import datetime, timezone

import structlog
from pydantic import BaseModel, Field
from langchain.tools import BaseTool
from langchain.callbacks.manager import (
    AsyncCallbackManagerForToolRun,
    CallbackManagerForToolRun,
)

from ..infrastructure.banking.fdic_api_client import FDICAPIClient
from ..infrastructure.banking.fdic_models import FDICInstitution

logger = structlog.get_logger(__name__).bind(log_type="SYSTEM")


class FDICInstitutionSearchInput(BaseModel):
    """Clean input schema for FDIC institution search."""
    
    name: Optional[str] = Field(
        None,
        description="Institution name to search for (e.g., 'Wells Fargo', 'Chase Bank')"
    )
    city: Optional[str] = Field(
        None,
        description="City filter (e.g., 'New York', 'Los Angeles')"
    )
    state: Optional[str] = Field(
        None,
        description="State abbreviation (e.g., 'CA', 'NY', 'TX')"
    )
    active_only: bool = Field(
        True,
        description="Only return active institutions"
    )
    limit: int = Field(
        5,
        description="Maximum results to return (1-50)",
        ge=1,
        le=50
    )

    @property 
    def has_search_criteria(self) -> bool:
        """Check if any search criteria provided."""
        return bool(self.name or self.city or self.state)


class FDICInstitutionSearchTool(BaseTool):
    """
    Atomic tool for searching FDIC institutions.
    
    Provides clean, focused institution lookup using FDIC BankFind Suite API.
    Returns structured data with CERT numbers for downstream financial queries.
    
    Key Features:
    - Name-based search with fuzzy matching
    - Location filtering (city, state)
    - Active institution filtering
    - Returns structured data (no string parsing needed)
    - CERT numbers included for financial data queries
    
    Example Usage:
    - name="Wells Fargo" → Find Wells Fargo institutions
    - city="Chicago", state="IL" → Find banks in Chicago
    - name="Community Bank", state="TX" → Find Community Banks in Texas
    
    Output: Structured list with institution details and CERT numbers
    """
    
    name: str = "fdic_institution_search"
    description: str = """Search for FDIC-insured financial institutions.

This atomic tool searches the FDIC BankFind Suite database for banking institutions using flexible criteria.
Returns structured data including CERT numbers needed for financial data queries.

Search Parameters:
- name: Institution name with intelligent matching (e.g., "Wells Fargo", "JPMorgan Chase")
- city: City filter for location-based search (e.g., "New York", "Los Angeles")  
- state: State abbreviation filter (e.g., "CA", "NY", "TX")
- active_only: Filter for active institutions only (default: true)
- limit: Maximum number of results (1-50, default: 5)

Returns structured data for each institution:
- Institution name and location details
- FDIC Certificate number (CERT) - required for financial data queries
- Status and regulatory information
- Asset size and branch count

Use Cases:
1. Find specific bank: name="Bank of America"
2. Location search: city="Houston", state="TX"
3. Discover banks: name="Community", state="CA"

Output is structured JSON, not text - no parsing required for downstream tools."""
    
    args_schema: Type[BaseModel] = FDICInstitutionSearchInput
    
    def __init__(self, **kwargs):
        """Initialize FDIC institution search tool."""
        super().__init__(**kwargs)
        
        # Get settings
        from src.config.settings import get_settings
        settings = kwargs.get('settings') or get_settings()
        
        # Initialize FDIC client - use private attribute to avoid Pydantic conflicts
        object.__setattr__(self, '_fdic_client', FDICAPIClient(
            api_key=settings.fdic_api_key,
            timeout=getattr(settings, 'fdic_api_timeout', 30.0),  # Use default if not available
            cache_ttl=getattr(settings, 'fdic_cache_ttl', 900)     # Use default if not available
        ))
        
        logger.info("FDIC institution search tool initialized")
    
    @property
    def fdic_client(self) -> FDICAPIClient:
        """Get the FDIC API client."""
        return getattr(self, '_fdic_client')
    
    def _run(
        self,
        name: Optional[str] = None,
        city: Optional[str] = None,
        state: Optional[str] = None,
        active_only: bool = True,
        limit: int = 5,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Synchronous execution wrapper."""
        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    lambda: asyncio.run(self._arun(name, city, state, active_only, limit, run_manager))
                )
                return future.result()
                
        except RuntimeError:
            return asyncio.run(self._arun(name, city, state, active_only, limit, run_manager))
    
    async def _arun(
        self,
        name: Optional[str] = None,
        city: Optional[str] = None,
        state: Optional[str] = None,
        active_only: bool = True,
        limit: int = 5,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ) -> str:
        """
        Search for FDIC institutions with clean, simple interface.
        
        Returns:
            Structured JSON string with institution data
        """
        try:
            start_time = datetime.now(timezone.utc)
            
            logger.info(
                "Searching FDIC institutions",
                name=name,
                city=city,
                state=state,
                active_only=active_only,
                limit=limit
            )
            
            # Validate input
            if not any([name, city, state]):
                return self._format_error("At least one search parameter required (name, city, or state)")
            
            if state and len(state) != 2:
                return self._format_error("State must be 2-character abbreviation (e.g., 'CA', 'NY')")
            
            # Search institutions using FDIC API
            response = await self.fdic_client.search_institutions(
                name=name,
                city=city,
                state=state,
                active_only=active_only,
                limit=limit
            )
            
            if not response.success:
                return self._format_error(f"FDIC search failed: {response.error_message}")
            
            if not response.data:
                return self._format_no_results(name, city, state)
            
            # Format structured results
            result = self._format_structured_results(response.data)
            
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            logger.info(
                "FDIC institution search completed",
                results_count=len(response.data),
                execution_time=execution_time
            )
            
            return result
            
        except Exception as e:
            logger.error("FDIC institution search failed", error=str(e))
            return self._format_error(f"Search failed: {str(e)}")
    
    def _format_structured_results(self, institutions: List[FDICInstitution]) -> str:
        """Format institutions as structured JSON for downstream tools."""
        results = {
            "success": True,
            "count": len(institutions),
            "institutions": []
        }
        
        for institution in institutions:
            # Create clean institution record
            inst_data = {
                "name": institution.name,
                "cert": institution.cert,
                "location": {
                    "city": institution.city,
                    "county": institution.county,
                    "state": institution.stname,
                    "state_abbr": institution.stalp
                },
                "status": "Active" if institution.active else "Inactive",
                "financial": {
                    "total_assets_thousands": float(institution.asset) if institution.asset else None,
                    "total_deposits_thousands": float(institution.dep) if institution.dep else None,
                    "offices": institution.offices
                }
            }
            
            results["institutions"].append(inst_data)
        
        import json
        return json.dumps(results, indent=2)
    
    def _format_no_results(self, name: Optional[str], city: Optional[str], state: Optional[str]) -> str:
        """Format no results message as structured JSON."""
        search_criteria = []
        if name:
            search_criteria.append(f"name '{name}'")
        if city:
            search_criteria.append(f"city '{city}'")
        if state:
            search_criteria.append(f"state '{state}'")
        
        result = {
            "success": True,
            "count": 0,
            "institutions": [],
            "message": f"No institutions found matching {' and '.join(search_criteria)}"
        }
        
        import json
        return json.dumps(result, indent=2)
    
    def _format_error(self, error_message: str) -> str:
        """Format error as structured JSON."""
        result = {
            "success": False,
            "error": error_message,
            "count": 0,
            "institutions": []
        }
        
        import json
        return json.dumps(result, indent=2)
    
    def is_available(self) -> bool:
        """Check if FDIC institution search is available."""
        return self.fdic_client.is_available()