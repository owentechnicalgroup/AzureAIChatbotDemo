"""
FDIC BankFind Suite API client with caching and error handling.

Provides async HTTP client for FDIC institution data retrieval with
proper caching, validation, and error handling following existing patterns.
"""

import asyncio
import hashlib
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
import aiohttp
import structlog

from .fdic_models import (
    FDICInstitution,
    FDICAPIResponse,
    FDICSearchFilters, 
    FDICCacheEntry
)
from .fdic_constants import (
    FDIC_API_BASE_URL,
    FDIC_INSTITUTIONS_ENDPOINT,
    FDIC_ERROR_CODES,
    FDIC_CACHE_CONFIG,
    build_fdic_query,
    get_error_message,
    build_cache_key,
    map_fdic_response_field
)

logger = structlog.get_logger(__name__).bind(log_type="SYSTEM")


class FDICAPICache:
    """
    Thread-safe cache for FDIC API responses.
    
    Implements caching similar to the credential cache pattern
    in the existing codebase for performance optimization.
    """
    
    def __init__(self, default_ttl_seconds: int = 3600, max_entries: int = 1000):
        """
        Initialize FDIC API cache.
        
        Args:
            default_ttl_seconds: Default time-to-live for cache entries
            max_entries: Maximum number of cache entries to maintain
        """
        self._cache: Dict[str, FDICCacheEntry] = {}
        self._cache_lock = threading.Lock()
        self.default_ttl = default_ttl_seconds
        self.max_entries = max_entries
        self.logger = logger.bind(component="fdic_api_cache")
        
        self.logger.info(
            "FDIC API cache initialized",
            default_ttl_seconds=default_ttl_seconds,
            max_entries=max_entries
        )
    
    def get(self, cache_key: str) -> Optional[FDICAPIResponse]:
        """
        Get cached response if available and not expired.
        
        Args:
            cache_key: Cache key to lookup
            
        Returns:
            Cached FDICAPIResponse if available and fresh, None otherwise
        """
        with self._cache_lock:
            entry = self._cache.get(cache_key)
            if not entry:
                return None
                
            if entry.is_expired():
                self.logger.debug("Cache entry expired", cache_key=cache_key)
                del self._cache[cache_key]
                return None
                
            self.logger.debug(
                "Cache hit",
                cache_key=cache_key,
                ttl_remaining=entry.time_to_expiry()
            )
            return entry.response
    
    def put(self, cache_key: str, response: FDICAPIResponse, ttl_seconds: Optional[int] = None) -> None:
        """
        Cache a response with specified TTL.
        
        Args:
            cache_key: Cache key to store under
            response: FDIC API response to cache
            ttl_seconds: Time-to-live override, uses default if None
        """
        ttl = ttl_seconds or self.default_ttl
        now = datetime.now()
        
        entry = FDICCacheEntry(
            response=response,
            query_hash=cache_key,
            cached_at=now,
            expires_at=now + timedelta(seconds=ttl)
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
                    self.logger.debug("Evicted oldest cache entry", evicted_key=oldest_key)
            
            self._cache[cache_key] = entry
            self.logger.debug(
                "Cached response",
                cache_key=cache_key,
                ttl_seconds=ttl,
                cache_size=len(self._cache)
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
                "Evicted expired cache entries",
                evicted_count=len(expired_keys)
            )
            
        return len(expired_keys)
    
    def clear(self) -> None:
        """Clear all cache entries."""
        with self._cache_lock:
            self._cache.clear()
            self.logger.info("Cache cleared")
    
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


class FDICAPIClient:
    """
    Async HTTP client for FDIC BankFind Suite API.
    
    Provides institution search with caching, error handling,
    and response validation following existing codebase patterns.
    """
    
    def __init__(
        self, 
        api_key: Optional[str] = None, 
        timeout: float = 30.0,
        cache_ttl: int = FDIC_CACHE_CONFIG["institution_data_ttl"]
    ):
        """
        Initialize FDIC API client.
        
        Args:
            api_key: FDIC API key (optional - API works without key but with limits)
            timeout: HTTP request timeout in seconds
            cache_ttl: Default cache TTL in seconds
        """
        self.api_key = api_key
        self.base_url = FDIC_API_BASE_URL
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.cache = FDICAPICache(default_ttl_seconds=cache_ttl)
        
        self.logger = logger.bind(component="fdic_api_client")
        
        self.logger.info(
            "FDIC API client initialized",
            has_api_key=bool(api_key),
            timeout_seconds=timeout,
            cache_ttl_seconds=cache_ttl,
            base_url=self.base_url
        )
    
    async def search_institutions(
        self,
        name: Optional[str] = None,
        city: Optional[str] = None,
        county: Optional[str] = None,
        state: Optional[str] = None,
        active_only: bool = True,
        limit: int = 100
    ) -> FDICAPIResponse:
        """
        Search for banking institutions using FDIC API.
        
        Args:
            name: Institution name to search for
            city: City to filter by
            county: County to filter by  
            state: State abbreviation to filter by
            active_only: Only return active institutions
            limit: Maximum number of results
            
        Returns:
            FDICAPIResponse with search results
        """
        start_time = datetime.now(timezone.utc)
        
        try:
            # Build search filters
            filters = FDICSearchFilters(
                name=name,
                city=city,
                county=county,
                state=state,
                active_only=active_only,
                limit=limit
            )
            
            # Convert to FDIC query parameters
            query_params = filters.to_fdic_query()
            
            # Add API key if available
            if self.api_key:
                query_params["api_key"] = self.api_key
            
            # Check cache first
            cache_key = build_cache_key(query_params)
            cached_response = self.cache.get(cache_key)
            if cached_response:
                self.logger.info(
                    "Returning cached FDIC search results",
                    cache_key=cache_key[:20] + "...",
                    results_count=len(cached_response.institutions)
                )
                return cached_response
            
            self.logger.info(
                "Executing FDIC API search",
                name=name,
                city=city,
                county=county,
                state=state,
                active_only=active_only,
                limit=limit
            )
            
            # Make HTTP request
            response_data = await self._make_request(
                endpoint=FDIC_INSTITUTIONS_ENDPOINT,
                params=query_params
            )
            
            # Process and validate response
            fdic_response = await self._process_response(response_data)
            
            # Cache successful responses
            if fdic_response.success:
                self.cache.put(cache_key, fdic_response)
            
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            self.logger.info(
                "FDIC API search completed",
                success=fdic_response.success,
                results_count=len(fdic_response.institutions),
                execution_time=execution_time
            )
            
            return fdic_response
            
        except Exception as e:
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            self.logger.error(
                "FDIC API search failed",
                error=str(e),
                error_type=type(e).__name__,
                execution_time=execution_time
            )
            
            return FDICAPIResponse(
                success=False,
                data=None,
                error_message=f"FDIC API search failed: {str(e)}",
                timestamp=datetime.now(timezone.utc).isoformat()
            )
    
    async def _make_request(
        self, 
        endpoint: str, 
        params: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Make HTTP request to FDIC API with proper error handling.
        
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
                if response.status == 400:
                    error_text = await response.text()
                    raise ValueError(f"Invalid FDIC API request parameters: {error_text}")
                elif response.status == 401:
                    raise ValueError("FDIC API authentication failed - check API key")
                elif response.status == 429:
                    raise ValueError("FDIC API rate limit exceeded - try again later")
                elif response.status >= 500:
                    error_msg = get_error_message(response.status)
                    raise ValueError(f"FDIC API server error - {error_msg}")
                
                # Raise for other HTTP errors
                response.raise_for_status()
                
                # Parse JSON response
                try:
                    data = await response.json()
                except aiohttp.ContentTypeError as e:
                    response_text = await response.text()
                    raise ValueError(f"FDIC API returned invalid JSON: {response_text[:200]}") from e
                
                self.logger.debug(
                    "FDIC API request successful",
                    status=response.status,
                    url=url,
                    params_count=len(params)
                )
                
                return data
    
    async def _process_response(self, raw_data: Dict[str, Any]) -> FDICAPIResponse:
        """
        Process and validate FDIC API response data.
        
        Args:
            raw_data: Raw response data from FDIC API
            
        Returns:
            Validated FDICAPIResponse
        """
        try:
            # FDIC API returns data in "data" field or directly as list
            institutions_data = raw_data.get("data", raw_data)
            
            # Handle case where response is not a list
            if not isinstance(institutions_data, list):
                if isinstance(institutions_data, dict) and "data" in institutions_data:
                    institutions_data = institutions_data["data"]
                else:
                    raise ValueError(f"Unexpected FDIC response format: {type(institutions_data)}")
            
            # Convert raw institution data to FDICInstitution models
            institutions = []
            for inst_data in institutions_data:
                try:
                    # Handle nested data structure - FDIC returns {"data": {...}, "score": ...}
                    if isinstance(inst_data, dict) and "data" in inst_data:
                        # Extract actual institution data from nested structure
                        institution_fields = inst_data["data"]
                    else:
                        # Data is already at top level
                        institution_fields = inst_data
                    
                    # Map FDIC fields to internal model fields
                    mapped_data = {}
                    for fdic_field, fdic_value in institution_fields.items():
                        internal_field, processed_value = map_fdic_response_field(
                            fdic_field, fdic_value
                        )
                        mapped_data[internal_field] = processed_value
                    
                    # Create and validate institution model
                    institution = FDICInstitution.model_validate(mapped_data)
                    institutions.append(institution)
                    
                except Exception as e:
                    self.logger.warning(
                        "Failed to process institution data",
                        institution_data=inst_data,
                        error=str(e)
                    )
                    # Continue processing other institutions
                    continue
            
            # Extract metadata if available
            meta = {}
            if isinstance(raw_data, dict):
                meta = {
                    k: v for k, v in raw_data.items() 
                    if k not in ["data"] and not isinstance(v, list)
                }
            
            return FDICAPIResponse(
                success=True,
                data=institutions,
                meta=meta,
                timestamp=datetime.now(timezone.utc).isoformat()
            )
            
        except Exception as e:
            self.logger.error(
                "Failed to process FDIC response",
                error=str(e),
                raw_data_type=type(raw_data).__name__
            )
            
            return FDICAPIResponse(
                success=False,
                data=None,
                error_message=f"Failed to process FDIC response: {str(e)}",
                timestamp=datetime.now(timezone.utc).isoformat()
            )
    
    async def get_institution_by_cert(self, cert_id: str) -> FDICAPIResponse:
        """
        Get specific institution by FDIC certificate number.
        
        Args:
            cert_id: FDIC certificate number
            
        Returns:
            FDICAPIResponse with institution data
        """
        try:
            query_params = {
                "filters": f"CERT:{cert_id}",
                "format": "json"
            }
            
            if self.api_key:
                query_params["api_key"] = self.api_key
            
            # Check cache first
            cache_key = build_cache_key(query_params)
            cached_response = self.cache.get(cache_key)
            if cached_response:
                return cached_response
            
            # Make request
            response_data = await self._make_request(
                endpoint=FDIC_INSTITUTIONS_ENDPOINT,
                params=query_params
            )
            
            # Process response
            fdic_response = await self._process_response(response_data)
            
            # Cache successful responses
            if fdic_response.success:
                self.cache.put(cache_key, fdic_response)
            
            return fdic_response
            
        except Exception as e:
            self.logger.error(
                "Failed to get institution by cert",
                cert_id=cert_id,
                error=str(e)
            )
            
            return FDICAPIResponse(
                success=False,
                data=None,
                error_message=f"Failed to get institution by cert {cert_id}: {str(e)}",
                timestamp=datetime.now(timezone.utc).isoformat()
            )
    
    async def health_check(self) -> bool:
        """
        Check if FDIC API is available and responding.
        
        Returns:
            True if API is healthy, False otherwise
        """
        try:
            # Make a simple request with minimal parameters
            query_params = {
                "filters": "ACTIVE:1",
                "limit": "1",
                "format": "json"
            }
            
            if self.api_key:
                query_params["api_key"] = self.api_key
            
            response_data = await self._make_request(
                endpoint=FDIC_INSTITUTIONS_ENDPOINT,
                params=query_params
            )
            
            # Just check if we got a response
            return isinstance(response_data, (dict, list))
            
        except Exception as e:
            self.logger.warning(
                "FDIC API health check failed",
                error=str(e)
            )
            return False
    
    def is_available(self) -> bool:
        """
        Check if FDIC API client is properly configured.
        
        Returns:
            True if client can make requests
        """
        return bool(self.base_url and self.timeout)
    
    def clear_cache(self) -> None:
        """Clear the response cache."""
        self.cache.clear()
        self.logger.info("FDIC API cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics for monitoring."""
        return self.cache.stats()