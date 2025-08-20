"""
Enhanced LangChain-compatible Bank lookup service using FDIC BankFind Suite API.

Provides real-time bank identification and lookup capabilities with fuzzy matching
to support natural language queries from AI agents, using LangChain BaseTool.
"""

import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Type
import re
from difflib import SequenceMatcher

import structlog
from pydantic import BaseModel, Field
from langchain.tools import BaseTool
from langchain.callbacks.manager import (
    AsyncCallbackManagerForToolRun,
    CallbackManagerForToolRun,
)

from src.config.settings import get_settings
from ..infrastructure.banking.fdic_api_client import FDICAPIClient
from ..infrastructure.banking.fdic_models import (
    BankLookupInput,
    FDICInstitution
)

logger = structlog.get_logger(__name__).bind(log_type="SYSTEM")


class BankLookupTool(BaseTool):
    """
    Enhanced LangChain-compatible bank lookup tool using FDIC BankFind Suite API.
    
    Provides real-time bank identification with comprehensive search capabilities
    including name, city, county, and state filters with fuzzy matching support.
    """
    
    name: str = "bank_lookup"
    description: str = """Look up bank information using FDIC BankFind Suite API with real-time data.

This tool searches the FDIC database for banking institutions and returns comprehensive information
including RSSD IDs, FDIC certificate numbers, locations, and financial data.

Enhanced Search Capabilities:
- Institution name search with fuzzy matching
- Location-based filtering (city, county, state)
- Active/inactive status filtering
- Comprehensive institution details

Example Usage:

1. Search by bank name:
   - search_term: "Wells Fargo"
   - fuzzy_match: true
   - max_results: 5

2. Search by location:
   - search_term: "First National"
   - city: "Chicago"
   - state: "IL"
   - max_results: 3

3. Find banks in specific area:
   - city: "New York"
   - state: "NY"
   - active_only: true
   - max_results: 10

4. County-based search:
   - search_term: "Community Bank"
   - county: "Cook County"
   - state: "IL"

Returns: Detailed bank information including name, RSSD ID, FDIC certificate number, 
location, charter type, assets, and status for use with other banking tools."""
    
    args_schema: Type[BaseModel] = BankLookupInput
    
    def __init__(self, settings=None, **kwargs):
        """Initialize the enhanced bank lookup tool with FDIC API integration."""
        super().__init__(**kwargs)
        
        # Get settings
        if settings is None:
            settings = get_settings()
        
        # Initialize FDIC API client - use private attribute to avoid Pydantic conflicts
        fdic_client = FDICAPIClient(
            api_key=settings.fdic_api_key,
            timeout=settings.tools_timeout_seconds,
            cache_ttl=settings.tools_cache_ttl_minutes * 60
        )
        object.__setattr__(self, '_fdic_client', fdic_client)
        object.__setattr__(self, '_settings', settings)
        
        logger.info(
            "Enhanced BankLookupTool initialized with FDIC API",
            has_api_key=bool(settings.fdic_api_key),
            timeout_seconds=settings.tools_timeout_seconds
        )
    
    @property
    def fdic_client(self) -> FDICAPIClient:
        """Get the FDIC API client."""
        return getattr(self, '_fdic_client')
    
    @property
    def settings(self):
        """Get the application settings."""
        return getattr(self, '_settings')
    
    def _normalize_bank_name(self, name: str) -> str:
        """
        Normalize bank name for better matching.
        
        Args:
            name: Bank name to normalize
            
        Returns:
            Normalized bank name
        """
        # Convert to lowercase and remove common banking suffixes/prefixes
        normalized = name.lower().strip()
        
        # Remove common legal entity suffixes
        suffixes_to_remove = [
            ", national association",
            ", n.a.",
            " national association",
            " n.a.",
            ", national bank",
            " national bank", 
            ", n.b.",
            " n.b.",
            " bank",
            " corp",
            " corporation",
            " company",
            " co.",
            ", fsb",
            " fsb"
        ]
        
        for suffix in suffixes_to_remove:
            if normalized.endswith(suffix):
                normalized = normalized[:-len(suffix)].strip()
        
        # Remove extra whitespace and punctuation
        normalized = re.sub(r'[^\w\s]', ' ', normalized)
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        return normalized
    
    def _calculate_similarity(self, search_term: str, bank_name: str) -> float:
        """
        Calculate similarity score between search term and bank name.
        
        Args:
            search_term: User's search term
            bank_name: Bank name to compare against
            
        Returns:
            Similarity score between 0.0 and 1.0
        """
        # Normalize both names
        normalized_search = self._normalize_bank_name(search_term)
        normalized_bank = self._normalize_bank_name(bank_name)
        
        # Exact match gets highest score
        if normalized_search == normalized_bank:
            return 1.0
            
        # Check if search term is contained in bank name
        if normalized_search in normalized_bank:
            return 0.9
            
        # Check if bank name is contained in search term  
        if normalized_bank in normalized_search:
            return 0.85
            
        # Use sequence matching for fuzzy comparison
        similarity = SequenceMatcher(None, normalized_search, normalized_bank).ratio()
        
        # Boost score for word-level matches
        search_words = set(normalized_search.split())
        bank_words = set(normalized_bank.split())
        
        if search_words:
            word_overlap = len(search_words.intersection(bank_words)) / len(search_words)
            similarity = max(similarity, word_overlap * 0.8)
        
        return similarity
    
    def _apply_fuzzy_matching(
        self, 
        institutions: List[FDICInstitution], 
        search_term: str
    ) -> List[FDICInstitution]:
        """
        Apply fuzzy matching to FDIC API results.
        
        Args:
            institutions: List of institutions from FDIC API
            search_term: Original search term
            
        Returns:
            Filtered and sorted list based on similarity
        """
        if not search_term:
            return institutions
        
        scored_institutions = []
        
        for institution in institutions:
            similarity = self._calculate_similarity(search_term, institution.name)
            
            # Keep institutions with reasonable similarity
            if similarity >= 0.3:  # Threshold for fuzzy matching
                # Add similarity score as temporary attribute
                institution_dict = institution.model_dump()
                institution_dict['similarity_score'] = similarity
                institution_dict['match_type'] = "exact" if similarity >= 0.95 else "fuzzy"
                scored_institutions.append((similarity, institution))
        
        # Sort by similarity score (descending)
        scored_institutions.sort(key=lambda x: x[0], reverse=True)
        
        return [inst for score, inst in scored_institutions]
    
    def _format_results(self, institutions: List[FDICInstitution]) -> str:
        """
        Format FDIC institutions for tool response.
        
        Args:
            institutions: List of FDIC institutions
            
        Returns:
            Formatted string response
        """
        if not institutions:
            return "No banks found matching the search criteria."
        
        response_parts = [f"Found {len(institutions)} bank(s):\n"]
        
        for i, institution in enumerate(institutions, 1):
            response_parts.append(f"{i}. {institution.name}")
            
            if institution.rssd:
                response_parts.append(f"   RSSD ID: {institution.rssd}")
            
            if institution.cert:
                response_parts.append(f"   FDIC Certificate: {institution.cert}")
            
            # Build location string
            location_parts = []
            if institution.city:
                location_parts.append(institution.city)
            if institution.county and institution.county != institution.city:
                location_parts.append(f"{institution.county} County")
            if institution.stname:
                location_parts.append(institution.stname)
            elif institution.stalp:
                location_parts.append(institution.stalp)
            
            if location_parts:
                response_parts.append(f"   Location: {', '.join(location_parts)}")
            
            if institution.charter_type:
                response_parts.append(f"   Charter Type: {institution.charter_type}")
            
            if institution.asset:
                # Convert from thousands to readable format
                if institution.asset >= 1000000:
                    assets_str = f"${institution.asset/1000000:.1f}B"
                elif institution.asset >= 1000:
                    assets_str = f"${institution.asset/1000:.1f}M"
                else:
                    assets_str = f"${institution.asset}K"
                response_parts.append(f"   Total Assets: {assets_str}")
            
            if institution.offices:
                response_parts.append(f"   Offices: {institution.offices}")
            
            # Show status
            status = "Active" if institution.active else "Inactive"
            response_parts.append(f"   Status: {status}")
            
            response_parts.append("")  # Empty line between institutions
        
        response_parts.append("Use the RSSD ID or FDIC Certificate number with other banking tools for detailed financial analysis.")
        
        return "\n".join(response_parts)
    
    def _run(
        self,
        search_term: Optional[str] = None,
        city: Optional[str] = None,
        county: Optional[str] = None,
        state: Optional[str] = None,
        active_only: bool = True,
        fuzzy_match: bool = True,
        max_results: int = 5,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Synchronous execution with backward compatibility."""
        try:
            # Try to get the current event loop
            loop = asyncio.get_running_loop()
            # If we're in an event loop, we need to handle this differently
            import concurrent.futures
            
            # Create a new event loop in a thread pool
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    lambda: asyncio.run(self._arun(
                        search_term, city, county, state, active_only, 
                        fuzzy_match, max_results, run_manager
                    ))
                )
                return future.result()
                
        except RuntimeError:
            # No event loop running, safe to use asyncio.run
            return asyncio.run(self._arun(
                search_term, city, county, state, active_only, 
                fuzzy_match, max_results, run_manager
            ))
    
    async def _arun(
        self,
        search_term: Optional[str] = None,
        city: Optional[str] = None,
        county: Optional[str] = None,
        state: Optional[str] = None,
        active_only: bool = True,
        fuzzy_match: bool = True,
        max_results: int = 5,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ) -> str:
        """
        Execute enhanced bank lookup with FDIC API integration.
        
        Args:
            search_term: Bank name or identifier to search for
            city: City to filter results
            county: County to filter results
            state: State abbreviation to filter results  
            active_only: Only return active institutions
            fuzzy_match: Enable fuzzy matching (default: True)
            max_results: Maximum number of results (default: 5)
            run_manager: Optional callback manager
            
        Returns:
            Formatted string with search results
        """
        start_time = datetime.now(timezone.utc)
        
        try:
            logger.info(
                "Executing enhanced bank lookup with FDIC API",
                search_term=search_term,
                city=city,
                county=county,
                state=state,
                active_only=active_only,
                fuzzy_match=fuzzy_match,
                max_results=max_results
            )
            
            # Validate inputs - at least one search criterion required
            if not any([search_term, city, county, state]):
                return "Error: At least one search parameter (search_term, city, county, or state) must be provided"
            
            # Validate search term if provided
            if search_term and len(search_term.strip()) < 2:
                return "Error: Search term must be at least 2 characters"
            
            # Validate and constrain max_results
            max_results = max(1, min(50, max_results))
            
            # Validate state format if provided
            if state and len(state) != 2:
                return "Error: State must be 2-character abbreviation (e.g., 'CA', 'TX', 'NY')"
            
            try:
                # Call FDIC API
                fdic_response = await self.fdic_client.search_institutions(
                    name=search_term,
                    city=city,
                    county=county,
                    state=state,
                    active_only=active_only,
                    limit=max_results * 2  # Get extra for fuzzy filtering
                )
                
                if not fdic_response.success:
                    error_msg = fdic_response.error_message or "Unknown error"
                    if "server error" in error_msg.lower() or "not available" in error_msg.lower():
                        return "Error: Bank data not available from FDIC - service temporarily unavailable. Please try again later."
                    return f"Error: Bank search failed - {error_msg}"
                
                institutions = fdic_response.institutions
                
                if not institutions:
                    # Build helpful error message based on search criteria
                    criteria_parts = []
                    if search_term:
                        criteria_parts.append(f"name '{search_term}'")
                    if city:
                        criteria_parts.append(f"city '{city}'")
                    if county:
                        criteria_parts.append(f"county '{county}'") 
                    if state:
                        criteria_parts.append(f"state '{state}'")
                    
                    criteria_str = ", ".join(criteria_parts)
                    return f"No banks found matching {criteria_str}. Try broader search terms or different locations."
                
                # Apply fuzzy matching if enabled and we have a search term
                if fuzzy_match and search_term:
                    institutions = self._apply_fuzzy_matching(institutions, search_term)
                
                # Limit results
                institutions = institutions[:max_results]
                
                # Format response
                response = self._format_results(institutions)
                
                execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
                
                logger.info(
                    "Enhanced bank lookup completed successfully",
                    results_found=len(institutions),
                    execution_time=execution_time
                )
                
                return response
                
            except Exception as api_error:
                # Handle FDIC API specific errors
                error_str = str(api_error)
                logger.error(
                    "FDIC API call failed",
                    error=error_str,
                    error_type=type(api_error).__name__
                )
                
                if "authentication failed" in error_str.lower():
                    return "Error: FDIC API authentication failed - check API key configuration"
                elif "rate limit" in error_str.lower():
                    return "Error: FDIC API rate limit exceeded - please try again in a few minutes"
                elif "server error" in error_str.lower() or "not available" in error_str.lower():
                    return "Error: Bank data not available from FDIC - service temporarily unavailable"
                else:
                    return f"Error: Bank search failed - {error_str}"
                
        except Exception as e:
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            logger.error(
                "Bank lookup tool execution failed",
                error=str(e),
                error_type=type(e).__name__,
                execution_time=execution_time
            )
            
            return f"Error: Bank lookup failed due to unexpected error - {str(e)}"
    
    def get_bank_by_cert(self, cert_id: str) -> Optional[str]:
        """
        Get bank information by FDIC certificate number.
        
        Args:
            cert_id: FDIC certificate number
            
        Returns:
            Formatted bank information or None
        """
        async def _get_by_cert():
            try:
                fdic_response = await self.fdic_client.get_institution_by_cert(cert_id)
                if fdic_response.success and fdic_response.institutions:
                    return self._format_results(fdic_response.institutions[:1])
                return None
            except Exception as e:
                logger.error("Failed to get bank by cert", cert_id=cert_id, error=str(e))
                return None
        
        try:
            return asyncio.run(_get_by_cert())
        except Exception:
            return None
    
    async def health_check(self) -> bool:
        """Check if FDIC API is available."""
        try:
            return await self.fdic_client.health_check()
        except Exception:
            return False
    
    def is_available(self) -> bool:
        """Check if the bank lookup service is available."""
        return self.fdic_client.is_available()