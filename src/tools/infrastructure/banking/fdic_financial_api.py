"""
FDIC Financial Data API client with caching and error handling.

Provides async HTTP client for FDIC Financial Data API (BankFind Suite)
with proper caching, validation, and error handling following existing patterns.
"""

import asyncio
import hashlib
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Union
import aiohttp
import structlog

from .fdic_financial_models import (
    FDICFinancialData,
    FDICFinancialAPIResponse,
    FDICFinancialCacheEntry
)
from .fdic_financial_constants import (
    FDIC_FINANCIAL_API_BASE_URL,
    FDIC_FINANCIAL_ENDPOINT,
    FDIC_FINANCIAL_API_CONFIG,
    FDIC_FINANCIAL_CACHE_CONFIG,
    FDIC_FINANCIAL_ERROR_CODES,
    build_financial_query_params,
    build_financial_cache_key,
    get_financial_error_message,
    get_fields_for_analysis_type
)

logger = structlog.get_logger(__name__).bind(log_type="SYSTEM")


class FDICFinancialAPICache:
    """
    Thread-safe cache for FDIC Financial API responses.
    
    Implements caching similar to the existing FDIC institution cache pattern
    for performance optimization with financial data.
    """
    
    def __init__(self, default_ttl_seconds: int = 1800, max_entries: int = 1000):
        """
        Initialize FDIC Financial API cache.
        
        Args:
            default_ttl_seconds: Default time-to-live for cache entries
            max_entries: Maximum number of cache entries to maintain
        """
        self._cache: Dict[str, FDICFinancialCacheEntry] = {}
        self._cache_lock = threading.Lock()
        self.default_ttl = default_ttl_seconds
        self.max_entries = max_entries
        self.logger = logger.bind(component="fdic_financial_cache")
        
        self.logger.info(
            "FDIC Financial API cache initialized",
            default_ttl_seconds=default_ttl_seconds,
            max_entries=max_entries
        )
    
    def get(self, cache_key: str) -> Optional[FDICFinancialAPIResponse]:
        """
        Get cached response if available and not expired.
        
        Args:
            cache_key: Cache key to lookup
            
        Returns:
            Cached FDICFinancialAPIResponse if available and fresh, None otherwise
        """
        with self._cache_lock:
            entry = self._cache.get(cache_key)
            if not entry:
                return None
                
            if entry.is_expired():
                self.logger.debug("Financial cache entry expired", cache_key=cache_key)
                del self._cache[cache_key]
                return None
                
            self.logger.debug(
                "Financial cache hit",
                cache_key=cache_key,
                ttl_remaining=entry.time_to_expiry()
            )
            return entry.response
    
    def put(self, cache_key: str, response: FDICFinancialAPIResponse, ttl_seconds: Optional[int] = None, query_params: Optional[Dict] = None) -> None:
        """
        Cache a response with specified TTL.
        
        Args:
            cache_key: Cache key to store under
            response: FDIC Financial API response to cache
            ttl_seconds: Time-to-live override, uses default if None
            query_params: Original query parameters for debugging
        """
        # Don't cache error responses for long
        if not response.success:
            ttl_seconds = FDIC_FINANCIAL_CACHE_CONFIG.get("error_response_ttl", 300)
        
        ttl = ttl_seconds or self.default_ttl
        now = datetime.now()
        
        entry = FDICFinancialCacheEntry(
            response=response,
            query_hash=cache_key,
            cached_at=now,
            expires_at=now + timedelta(seconds=ttl),
            query_params=query_params
        )
        
        with self._cache_lock:
            # Evict expired entries if at capacity
            if len(self._cache) >= self.max_entries:
                self._evict_expired_entries()
                
                # If still at capacity after eviction, remove oldest
                if len(self._cache) >= self.max_entries:
                    oldest_key = min(self._cache.keys(), 
                                   key=lambda k: self._cache[k].cached_at)
                    del self._cache[oldest_key]
                    self.logger.debug("Evicted oldest financial cache entry", evicted_key=oldest_key)
            
            self._cache[cache_key] = entry
            self.logger.debug(
                "Cached financial response",
                cache_key=cache_key,
                ttl_seconds=ttl,
                cache_size=len(self._cache),
                success=response.success
            )
    
    def _evict_expired_entries(self) -> int:
        """
        Remove expired entries from cache.
        
        Returns:
            Number of entries evicted
        """
        expired_keys = [
            key for key, entry in self._cache.items()
            if entry.is_expired()
        ]
        
        for key in expired_keys:
            del self._cache[key]
            
        if expired_keys:
            self.logger.debug(
                "Evicted expired financial cache entries",
                evicted_count=len(expired_keys)
            )
            
        return len(expired_keys)
    
    def clear(self) -> None:
        """Clear all cache entries."""
        with self._cache_lock:
            self._cache.clear()
            self.logger.info("Financial cache cleared")
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._cache_lock:
            expired_count = sum(1 for entry in self._cache.values() if entry.is_expired())
            return {
                "total_entries": len(self._cache),
                "expired_entries": expired_count,
                "active_entries": len(self._cache) - expired_count,
                "max_entries": self.max_entries
            }


class FDICFinancialAPI:
    """
    Async HTTP client for FDIC BankFind Suite Financial Data API.
    
    Provides financial data retrieval with caching, error handling,
    and response validation following existing codebase patterns.
    """
    
    def __init__(
        self, 
        api_key: Optional[str] = None, 
        timeout: float = 30.0,
        cache_ttl: int = FDIC_FINANCIAL_CACHE_CONFIG["financial_data_ttl"]
    ):
        """
        Initialize FDIC Financial API client.
        
        Args:
            api_key: FDIC API key (optional - API works without key but with limits)
            timeout: HTTP request timeout in seconds
            cache_ttl: Default cache TTL in seconds
        """
        self.api_key = api_key
        self.base_url = FDIC_FINANCIAL_API_BASE_URL
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.cache = FDICFinancialAPICache(default_ttl_seconds=cache_ttl)
        
        self.logger = logger.bind(component="fdic_financial_api")
        
        self.logger.info(
            "FDIC Financial API client initialized",
            has_api_key=bool(api_key),
            timeout_seconds=timeout,
            cache_ttl_seconds=cache_ttl,
            base_url=self.base_url
        )
    
    async def get_financial_data(
        self,
        cert_id: Optional[str] = None,
        filters: Optional[str] = None,
        fields: Optional[List[str]] = None,
        quarters: int = 1,
        report_date: Optional[str] = None,
        analysis_type: Optional[str] = None
    ) -> FDICFinancialAPIResponse:
        """
        Get financial data from FDIC BankFind Suite Financial API.
        
        Args:
            cert_id: FDIC certificate number for specific bank
            filters: Additional Elasticsearch query filters
            fields: Specific fields to retrieve (performance optimization)
            quarters: Number of recent quarters (default 1)
            report_date: Specific report date filter (YYYY-MM-DD)
            analysis_type: Predefined field selection (basic_info, financial_summary, key_ratios)
            
        Returns:
            FDICFinancialAPIResponse with financial data
        """
        start_time = datetime.now(timezone.utc)
        
        try:
            self.logger.info(
                "Retrieving FDIC financial data",
                cert_id=cert_id,
                filters=filters,
                quarters=quarters,
                report_date=report_date,
                analysis_type=analysis_type,
                field_count=len(fields) if fields else 0
            )
            
            # Build query parameters using existing pattern
            query_params = self._build_query_parameters(
                cert_id=cert_id,
                filters=filters,
                fields=fields,
                quarters=quarters,
                report_date=report_date,
                analysis_type=analysis_type
            )
            
            # Check cache first
            cache_key = build_financial_cache_key(query_params)
            cached_response = self.cache.get(cache_key)
            if cached_response:
                self.logger.info(
                    "Returning cached FDIC financial data",
                    cache_key=cache_key[:20] + "...",
                    results_count=len(cached_response.financial_records)
                )
                return cached_response
            
            # Make HTTP request
            response_data = await self._make_request(
                endpoint=FDIC_FINANCIAL_ENDPOINT,
                params=query_params
            )
            
            # Process and validate response
            fdic_response = await self._process_response(response_data, query_params)
            
            # Cache successful responses and some errors
            self.cache.put(cache_key, fdic_response, query_params=query_params)
            
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            self.logger.info(
                "FDIC Financial API request completed",
                success=fdic_response.success,
                results_count=len(fdic_response.financial_records),
                execution_time=execution_time,
                cert_id=cert_id
            )
            
            return fdic_response
            
        except Exception as e:
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            self.logger.error(
                "FDIC Financial API request failed",
                error=str(e),
                error_type=type(e).__name__,
                execution_time=execution_time,
                cert_id=cert_id
            )
            
            return FDICFinancialAPIResponse(
                success=False,
                data=None,
                metadata=None,
                error_message=f"FDIC Financial API request failed: {str(e)}",
                timestamp=datetime.now(timezone.utc).isoformat(),
                query_info={
                    "cert_id": cert_id,
                    "analysis_type": analysis_type,
                    "quarters": quarters,
                    "report_date": report_date
                }
            )
    
    def _build_query_parameters(
        self,
        cert_id: Optional[str] = None,
        filters: Optional[str] = None,
        fields: Optional[List[str]] = None,
        quarters: int = 1,
        report_date: Optional[str] = None,
        analysis_type: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Build query parameters for FDIC Financial API request.
        
        Args:
            cert_id: FDIC certificate number for specific bank
            filters: Additional Elasticsearch query filters
            fields: Specific fields to retrieve
            quarters: Number of recent quarters
            report_date: Specific report date filter
            analysis_type: Predefined field selection
            
        Returns:
            Dictionary of query parameters
        """
        # Use predefined field selection if analysis_type provided
        if analysis_type and not fields:
            fields = get_fields_for_analysis_type(analysis_type)
        
        # Build date filters if needed
        date_filters = []
        if report_date:
            date_filters.append(f"REPDTE:{report_date}")
        
        # Combine all filters
        all_filters = []
        if cert_id:
            all_filters.append(f"CERT:{cert_id}")
        if date_filters:
            all_filters.extend(date_filters)
        if filters:
            all_filters.append(filters)
        
        # Build final query parameters
        params = build_financial_query_params(
            cert_id=cert_id if not all_filters else None,  # Don't double-add cert filter
            filters=" AND ".join(all_filters) if all_filters else None,
            fields=fields,
            limit=min(quarters * 10, FDIC_FINANCIAL_API_CONFIG["max_results_per_query"])  # Buffer for multiple banks
        )
        
        # Add API key if available
        if self.api_key:
            params["api_key"] = self.api_key
        
        return params
    
    async def _make_request(
        self, 
        endpoint: str, 
        params: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Make HTTP request to FDIC Financial API with proper error handling.
        
        Args:
            endpoint: API endpoint path
            params: Query parameters
            
        Returns:
            Raw response data
            
        Raises:
            ValueError: For FDIC-specific errors
            aiohttp.ClientError: For HTTP-related errors
        """
        url = f"{self.base_url}{endpoint}"
        
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.get(url, params=params) as response:
                
                # Handle FDIC-specific error status codes
                if response.status in FDIC_FINANCIAL_ERROR_CODES:
                    error_msg = get_financial_error_message(response.status)
                    if response.status == 400:
                        error_text = await response.text()
                        raise ValueError(f"Invalid FDIC Financial API request parameters: {error_text}")
                    elif response.status == 401:
                        raise ValueError("FDIC Financial API authentication failed - check API key")
                    elif response.status == 429:
                        raise ValueError("FDIC Financial API rate limit exceeded - try again later")
                    else:
                        raise ValueError(f"FDIC Financial API error - {error_msg}")
                
                # Raise for other HTTP errors
                response.raise_for_status()
                
                # Parse JSON response
                try:
                    data = await response.json()
                except aiohttp.ContentTypeError as e:
                    response_text = await response.text()
                    raise ValueError(f"FDIC Financial API returned invalid JSON: {response_text[:200]}") from e
                
                # CRITICAL: Check for API-level errors in response body
                # FDIC API can return 200 with error in body
                if isinstance(data, dict) and "error" in data:
                    raise ValueError(f"FDIC Financial API error: {data['error']}")
                
                self.logger.debug(
                    "FDIC Financial API request successful",
                    status=response.status,
                    url=url,
                    params_count=len(params)
                )
                
                return data
    
    async def _process_response(self, raw_data: Dict[str, Any], query_params: Dict[str, str]) -> FDICFinancialAPIResponse:
        """
        Process and validate FDIC Financial API response data.
        
        Args:
            raw_data: Raw response data from FDIC Financial API
            query_params: Original query parameters
            
        Returns:
            Validated FDICFinancialAPIResponse
        """
        try:
            # CRITICAL: Financial API response format differs from institution API
            # Returns: {metadata: {...}, data: [{CERT: "123", ASSET: 1000, ...}]}
            
            # Extract financial records data
            financial_records = []
            
            if isinstance(raw_data, dict):
                # Standard FDIC Financial API format
                records_data = raw_data.get("data", [])
                metadata = raw_data.get("metadata", {})
            elif isinstance(raw_data, list):
                # Direct array format
                records_data = raw_data
                metadata = {}
            else:
                raise ValueError(f"Unexpected FDIC Financial API response format: {type(raw_data)}")
            
            # Process each financial record
            for record_data in records_data:
                try:
                    # CRITICAL: Handle case where data might be nested
                    if isinstance(record_data, dict) and "data" in record_data:
                        # Extract actual financial data from nested structure
                        financial_fields = record_data["data"]
                    else:
                        # Data is already at top level
                        financial_fields = record_data
                    
                    # Convert field names to lowercase for Pydantic model
                    normalized_data = {}
                    for field_name, field_value in financial_fields.items():
                        # Convert FDIC field names to model field names
                        model_field_name = field_name.lower()
                        
                        # Handle CERT field - ensure it's a string
                        if field_name == "CERT":
                            field_value = str(field_value)
                        
                        # Handle field conversions for misnamed "ratio" fields that are actually dollar amounts
                        # FDIC API issue: Some fields marked as ratios are actually raw amounts
                        if field_name in ["NIM", "EFFRATIO"] and field_value is not None:
                            # These are actually dollar amounts (in thousands), not ratios
                            # We should skip them and let calculate_derived_ratios() handle the calculations
                            self.logger.warning(
                                f"Skipping FDIC field {field_name} - contains raw amount, not ratio",
                                field_name=field_name,
                                raw_value=field_value
                            )
                            continue
                        
                        # Handle special field conversions
                        if field_name == "REPDTE" and isinstance(field_value, str):
                            # Convert FDIC date format to date object
                            try:
                                from datetime import datetime as dt
                                # Try FDIC API format first: YYYYMMDD (e.g., 20250331)
                                if len(field_value) == 8 and field_value.isdigit():
                                    date_obj = dt.strptime(field_value, "%Y%m%d").date()
                                else:
                                    # Try standard formats
                                    date_obj = dt.strptime(field_value, "%Y-%m-%d").date()
                                normalized_data[model_field_name] = date_obj
                            except ValueError:
                                # Try alternative date formats
                                try:
                                    date_obj = dt.strptime(field_value, "%m/%d/%Y").date()
                                    normalized_data[model_field_name] = date_obj
                                except ValueError:
                                    self.logger.warning("Could not parse date", date_value=field_value, attempted_formats=["YYYYMMDD", "YYYY-MM-DD", "MM/DD/YYYY"])
                                    continue
                        else:
                            normalized_data[model_field_name] = field_value
                    
                    # Ensure minimum required fields are present
                    # Only require cert (certificate number) - date might fail to parse but record could still be useful
                    if "cert" not in normalized_data:
                        self.logger.warning(
                            "Skipping financial record missing cert field",
                            available_fields=list(normalized_data.keys())
                        )
                        continue
                    
                    # If date parsing failed, try to add a fallback date
                    if "repdte" not in normalized_data and "REPDTE" in financial_fields:
                        # Try one more time with the YYYYMMDD format directly
                        raw_date = financial_fields["REPDTE"]
                        try:
                            from datetime import datetime as dt
                            if isinstance(raw_date, str) and len(raw_date) == 8 and raw_date.isdigit():
                                date_obj = dt.strptime(raw_date, "%Y%m%d").date()
                                normalized_data["repdte"] = date_obj
                                self.logger.info(
                                    "Successfully parsed date on second attempt", 
                                    raw_date=raw_date,
                                    parsed_date=date_obj,
                                    cert_id=normalized_data.get("cert")
                                )
                        except Exception as e:
                            self.logger.warning(
                                "Final date parsing attempt failed, skipping record",
                                raw_date=raw_date,
                                error=str(e),
                                cert_id=normalized_data.get("cert")
                            )
                            continue
                    
                    # Create and validate financial data model
                    financial_record = FDICFinancialData.model_validate(normalized_data)
                    financial_records.append(financial_record)
                    
                except Exception as e:
                    self.logger.warning(
                        "Failed to process financial record",
                        record_data=record_data,
                        error=str(e)
                    )
                    # Continue processing other records
                    continue
            
            # Create successful response
            return FDICFinancialAPIResponse(
                success=True,
                data=financial_records,
                metadata=metadata,
                error_message=None,
                timestamp=datetime.now(timezone.utc).isoformat(),
                query_info={
                    "query_params": query_params,
                    "records_processed": len(records_data),
                    "records_validated": len(financial_records)
                }
            )
            
        except Exception as e:
            self.logger.error(
                "Failed to process FDIC Financial API response",
                error=str(e),
                raw_data_type=type(raw_data).__name__
            )
            
            return FDICFinancialAPIResponse(
                success=False,
                data=None,
                metadata=None,
                error_message=f"Failed to process FDIC Financial API response: {str(e)}",
                timestamp=datetime.now(timezone.utc).isoformat(),
                query_info={"query_params": query_params}
            )
    
    async def get_financial_data_by_cert(
        self, 
        cert_id: str, 
        analysis_type: str = "financial_summary",
        quarters: int = 1
    ) -> FDICFinancialAPIResponse:
        """
        Get financial data for a specific bank by FDIC certificate number.
        
        Args:
            cert_id: FDIC certificate number
            analysis_type: Type of analysis (determines field selection)
            quarters: Number of recent quarters to retrieve
            
        Returns:
            FDICFinancialAPIResponse with financial data
        """
        return await self.get_financial_data(
            cert_id=cert_id,
            analysis_type=analysis_type,
            quarters=quarters
        )
    
    async def health_check(self) -> bool:
        """
        Check if FDIC Financial API is available and responding.
        
        Returns:
            True if API is healthy, False otherwise
        """
        try:
            # Make a simple request with minimal parameters
            test_response = await self.get_financial_data(
                filters="ASSET:[1000000 TO 9999999]",  # Large banks
                fields=["CERT", "REPDTE", "ASSET"],
                quarters=1
            )
            
            # Check if we got a reasonable response
            return test_response.success and test_response.total_count >= 0
            
        except Exception as e:
            self.logger.warning(
                "FDIC Financial API health check failed",
                error=str(e)
            )
            return False
    
    def is_available(self) -> bool:
        """
        Check if FDIC Financial API client is properly configured.
        
        Returns:
            True if client can make requests
        """
        return bool(self.base_url and self.timeout)
    
    def clear_cache(self) -> None:
        """Clear the response cache."""
        self.cache.clear()
        self.logger.info("FDIC Financial API cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics for monitoring."""
        return self.cache.stats()
    
    async def get_peer_comparison_data(
        self,
        asset_range: tuple,
        report_date: Optional[str] = None,
        peer_count: int = 10
    ) -> FDICFinancialAPIResponse:
        """
        Get financial data for peer comparison based on asset size.
        
        Args:
            asset_range: Tuple of (min_assets, max_assets) in thousands
            report_date: Specific report date or None for latest
            peer_count: Number of peer banks to retrieve
            
        Returns:
            FDICFinancialAPIResponse with peer financial data
        """
        min_assets, max_assets = asset_range
        filters = f"ASSET:[{min_assets} TO {max_assets}]"
        
        return await self.get_financial_data(
            filters=filters,
            analysis_type="key_ratios",
            quarters=1,
            report_date=report_date
        )