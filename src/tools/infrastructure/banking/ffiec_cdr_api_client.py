"""
FFIEC CDR SOAP API client with authentication, caching, and error handling.

Provides async SOAP client for FFIEC CDR Public Data Distribution API
with proper authentication, session-based caching, and comprehensive error handling.
"""

import asyncio
import base64
import hashlib
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Union
import structlog

# SOAP client imports
from zeep import AsyncClient
from zeep.transports import AsyncTransport
from zeep.exceptions import Fault as SOAPFault, TransportError
import httpx

from .ffiec_cdr_models import (
    FFIECCallReportData,
    FFIECDiscoveryResult,
    FFIECCDRAPIResponse,
    FFIECCDRCacheEntry
)
from .ffiec_cdr_constants import (
    FFIEC_CDR_WSDL_URL,
    FFIEC_CDR_API_CONFIG,
    FFIEC_CDR_CACHE_CONFIG,
    FFIEC_CDR_ERROR_CODES,
    FFIEC_SOAP_FAULT_CODES,
    FFIEC_DATA_SERIES,
    FFIEC_FI_ID_TYPES,
    FFIEC_UBPR_CONFIG,
    build_ffiec_cache_key,
    build_discovery_cache_key,
    get_ffiec_error_message
)

logger = structlog.get_logger(__name__).bind(log_type="SYSTEM")


class FFIECCDRAPICache:
    """
    Thread-safe cache for FFIEC CDR API responses.
    
    Implements session-based caching for call report data and discovery results
    to improve performance and reduce API load.
    """
    
    def __init__(self, default_ttl_seconds: int = 3600, max_entries: int = 500):
        """
        Initialize FFIEC CDR API cache.
        
        Args:
            default_ttl_seconds: Default time-to-live for cache entries
            max_entries: Maximum number of cache entries to maintain
        """
        self._cache: Dict[str, FFIECCDRCacheEntry] = {}
        self._cache_lock = threading.Lock()
        self.default_ttl = default_ttl_seconds
        self.max_entries = max_entries
        self.logger = logger.bind(component="ffiec_cdr_cache")
        
        self.logger.info(
            "FFIEC CDR API cache initialized",
            default_ttl_seconds=default_ttl_seconds,
            max_entries=max_entries
        )
    
    def get(self, cache_key: str) -> Optional[FFIECCDRAPIResponse]:
        """
        Get cached response if available and not expired.
        
        Args:
            cache_key: Cache key to lookup
            
        Returns:
            Cached FFIECCDRAPIResponse if available and fresh, None otherwise
        """
        with self._cache_lock:
            entry = self._cache.get(cache_key)
            if not entry:
                return None
                
            if entry.is_expired():
                self.logger.debug("Cache entry expired", cache_key=cache_key)
                del self._cache[cache_key]
                return None
                
            # Mark as accessed and return
            entry.mark_accessed()
            self.logger.debug(
                "Cache hit",
                cache_key=cache_key,
                ttl_remaining=entry.time_to_expiry(),
                access_count=entry.access_count
            )
            return entry.response
    
    def put(self, cache_key: str, response: FFIECCDRAPIResponse, ttl_seconds: Optional[int] = None) -> None:
        """
        Cache a response with specified TTL.
        
        Args:
            cache_key: Cache key to store under
            response: FFIEC CDR API response to cache
            ttl_seconds: Time-to-live override, uses default if None
        """
        with self._cache_lock:
            # Clean up expired entries if cache is getting full
            if len(self._cache) >= self.max_entries:
                self._cleanup_expired_entries()
            
            # Remove oldest entry if still at limit
            if len(self._cache) >= self.max_entries:
                oldest_key = min(self._cache.keys(), 
                               key=lambda k: self._cache[k].cache_timestamp)
                del self._cache[oldest_key]
                self.logger.debug("Removed oldest cache entry", cache_key=oldest_key)
            
            # Store new entry
            ttl = ttl_seconds or self.default_ttl
            entry = FFIECCDRCacheEntry(response=response, ttl_seconds=ttl)
            self._cache[cache_key] = entry
            
            self.logger.debug(
                "Cached response",
                cache_key=cache_key,
                ttl_seconds=ttl,
                cache_size=len(self._cache)
            )
    
    def _cleanup_expired_entries(self):
        """Remove all expired cache entries."""
        expired_keys = [
            key for key, entry in self._cache.items()
            if entry.is_expired()
        ]
        
        for key in expired_keys:
            del self._cache[key]
        
        if expired_keys:
            self.logger.debug(
                "Cleaned up expired cache entries",
                expired_count=len(expired_keys),
                remaining_count=len(self._cache)
            )
    
    def clear(self):
        """Clear all cache entries."""
        with self._cache_lock:
            cleared_count = len(self._cache)
            self._cache.clear()
            self.logger.info("Cache cleared", cleared_entries=cleared_count)


class FFIECCDRAPIClient:
    """
    FFIEC CDR SOAP API client with authentication and caching.
    
    Provides async access to FFIEC Call Report data through the CDR Public Data
    Distribution SOAP web service with proper authentication and caching.
    """
    
    def __init__(self, 
                 api_key: str, 
                 username: str,
                 timeout: int = 30,
                 cache_ttl: int = 3600):
        """
        Initialize FFIEC CDR API client.
        
        Args:
            api_key: FFIEC CDR API key (PIN)
            username: FFIEC CDR username
            timeout: Request timeout in seconds
            cache_ttl: Cache TTL in seconds
        """
        self.api_key = api_key
        self.username = username
        self.timeout = timeout
        self.cache = FFIECCDRAPICache(default_ttl_seconds=cache_ttl)
        
        self.logger = logger.bind(component="ffiec_cdr_api_client")
        
        # Initialize SOAP client with async/sync pattern
        self._soap_client: Optional[AsyncClient] = None
        self._setup_soap_client()
        
        self.logger.info(
            "FFIEC CDR API client initialized",
            has_api_key=bool(api_key),
            has_username=bool(username),
            timeout_seconds=timeout,
            cache_ttl_seconds=cache_ttl
        )
    
    def _setup_soap_client(self):
        """Setup SOAP client with WS-Security authentication."""
        try:
            # Import WS-Security support for zeep
            from zeep.wsse.username import UsernameToken
            
            # CRITICAL: FFIEC CDR requires WS-Security authentication, not basic HTTP auth
            # Synchronous client for WSDL loading (no auth needed for WSDL)
            wsdl_client = httpx.Client(
                verify=FFIEC_CDR_API_CONFIG["verify_ssl"],
                timeout=FFIEC_CDR_API_CONFIG["connection_timeout"]
            )
            
            # Async client for execution (no auth needed at transport level)
            async_client = httpx.AsyncClient(
                verify=FFIEC_CDR_API_CONFIG["verify_ssl"],
                timeout=FFIEC_CDR_API_CONFIG["connection_timeout"]
            )
            
            # Create transport with both clients
            transport = AsyncTransport(
                client=async_client,
                wsdl_client=wsdl_client
            )
            
            # Initialize async SOAP client with WS-Security
            self._soap_client = AsyncClient(
                FFIEC_CDR_WSDL_URL,
                transport=transport,
                wsse=UsernameToken(self.username, self.api_key)
            )
            
            self.logger.info("SOAP client initialized successfully")
            
        except Exception as e:
            self.logger.error("Failed to initialize SOAP client", error=str(e))
            raise
    
    async def discover_latest_filing(self, rssd_id: str) -> Optional[str]:
        """
        Discover the latest call report filing for a bank.
        
        Args:
            rssd_id: Bank RSSD identifier
            
        Returns:
            Latest reporting period string or None if not found
        """
        cache_key = build_discovery_cache_key(rssd_id)
        
        # Check cache first
        cached_response = self.cache.get(cache_key)
        if cached_response and cached_response.discovery_result:
            self.logger.debug("Using cached discovery result", rssd_id=rssd_id)
            return cached_response.discovery_result.latest_period
        
        try:
            self.logger.info("Discovering latest filing", rssd_id=rssd_id)
            
            # Get available reporting periods
            periods = await self._soap_client.service.RetrieveReportingPeriods(
                dataSeries=FFIEC_DATA_SERIES["call_reports"]
            )
            
            if not periods:
                self.logger.warning("No reporting periods available")
                return None
            
            # Sort periods newest to oldest
            sorted_periods = sorted(periods, reverse=True)
            
            # Check recent periods for this bank
            for period in sorted_periods[:4]:  # Check last 4 periods
                try:
                    filers = await self._soap_client.service.RetrieveFilersSinceDate(
                        dataSeries=FFIEC_DATA_SERIES["call_reports"],
                        reportingPeriodEndDate=period,
                        lastUpdateDateTime=period
                    )
                    
                    if filers and int(rssd_id) in filers:
                        # Create and cache discovery result
                        discovery_result = FFIECDiscoveryResult(
                            rssd_id=rssd_id,
                            available_periods=[period],
                            latest_period=period
                        )
                        
                        response = FFIECCDRAPIResponse(
                            success=True,
                            discovery_result=discovery_result
                        )
                        
                        self.cache.put(cache_key, response, ttl_seconds=FFIEC_CDR_CACHE_CONFIG["discovery_data_ttl"])
                        
                        # Convert period to standard YYYY-MM-DD format if needed
                        standardized_period = self._standardize_date_format(period)
                        
                        self.logger.info(
                            "Latest filing discovered",
                            rssd_id=rssd_id,
                            latest_period=period,
                            standardized_period=standardized_period
                        )
                        return standardized_period
                        
                except Exception as period_error:
                    self.logger.warning(
                        "Error checking period",
                        period=period,
                        error=str(period_error)
                    )
                    continue
            
            self.logger.warning("No recent filings found", rssd_id=rssd_id)
            return None
            
        except SOAPFault as soap_error:
            error_msg = self._handle_soap_fault(soap_error)
            self.logger.error("SOAP fault during discovery", error=error_msg, rssd_id=rssd_id)
            return None
            
        except Exception as e:
            self.logger.error("Discovery failed", error=str(e), rssd_id=rssd_id)
            return None
    
    async def retrieve_facsimile(self, 
                                rssd_id: str, 
                                reporting_period: str, 
                                format_type: str = "PDF") -> Optional[bytes]:
        """
        Retrieve call report facsimile data.
        
        Args:
            rssd_id: Bank RSSD identifier
            reporting_period: Reporting period (YYYY-MM-DD)
            format_type: Format type (PDF, XBRL, SDF)
            
        Returns:
            Call report data as bytes or None if not available
        """
        cache_key = build_ffiec_cache_key(rssd_id, reporting_period, format_type)
        
        # Check cache first
        cached_response = self.cache.get(cache_key)
        if cached_response and cached_response.call_report_data:
            self.logger.debug(
                "Using cached call report data",
                rssd_id=rssd_id,
                reporting_period=reporting_period,
                format_type=format_type
            )
            return cached_response.call_report_data.data
        
        try:
            self.logger.info(
                "Retrieving call report facsimile",
                rssd_id=rssd_id,
                reporting_period=reporting_period,
                format_type=format_type
            )
            
            # Call FFIEC CDR API
            result = await self._soap_client.service.RetrieveFacsimile(
                dataSeries=FFIEC_DATA_SERIES["call_reports"],
                reportingPeriodEndDate=reporting_period,
                fiIDType=FFIEC_FI_ID_TYPES["rssd"],
                fiID=int(rssd_id),
                facsimileFormat=format_type.upper()
            )
            
            if not result:
                self.logger.warning(
                    "No facsimile data returned",
                    rssd_id=rssd_id,
                    reporting_period=reporting_period
                )
                return None
            
            # Handle different result types from FFIEC API
            decoded_data = None
            
            if isinstance(result, bytes):
                # Data is already in bytes format - no base64 decoding needed
                decoded_data = result
                self.logger.debug(
                    "FFIEC returned direct bytes data",
                    data_size=len(result),
                    rssd_id=rssd_id,
                    format_type=format_type
                )
            elif isinstance(result, str):
                # Data might be base64 encoded string
                try:
                    decoded_data = base64.b64decode(result)
                    self.logger.debug(
                        "Successfully decoded base64 string",
                        original_size=len(result),
                        decoded_size=len(decoded_data),
                        rssd_id=rssd_id
                    )
                except Exception as decode_error:
                    self.logger.error(
                        "Failed to decode base64 data",
                        error=str(decode_error),
                        rssd_id=rssd_id,
                        data_type=type(result),
                        data_length=len(result),
                        data_preview=result[:100] if len(result) > 100 else result
                    )
                    return None
            else:
                self.logger.error(
                    "Unexpected data type from FFIEC API",
                    data_type=type(result),
                    rssd_id=rssd_id
                )
                return None
            
            # Create call report data model
            # Standardize the date format before parsing
            standardized_period = self._standardize_date_format(reporting_period)
            call_report_data = FFIECCallReportData(
                rssd_id=rssd_id,
                reporting_period=datetime.strptime(standardized_period, "%Y-%m-%d").date(),
                report_format=format_type.upper(),
                data=decoded_data,
                data_size=len(decoded_data)
            )
            
            # Cache the response
            response = FFIECCDRAPIResponse(
                success=True,
                call_report_data=call_report_data
            )
            
            self.cache.put(cache_key, response, ttl_seconds=FFIEC_CDR_CACHE_CONFIG["call_report_data_ttl"])
            
            self.logger.info(
                "Call report facsimile retrieved successfully",
                rssd_id=rssd_id,
                reporting_period=reporting_period,
                data_size=call_report_data.get_data_size_formatted(),
                quality=call_report_data.quality_indicator
            )
            
            return decoded_data
            
        except SOAPFault as soap_error:
            error_msg = self._handle_soap_fault(soap_error)
            self.logger.error(
                "SOAP fault during facsimile retrieval",
                error=error_msg,
                rssd_id=rssd_id,
                reporting_period=reporting_period
            )
            return None
            
        except Exception as e:
            self.logger.error(
                "Facsimile retrieval failed",
                error=str(e),
                rssd_id=rssd_id,
                reporting_period=reporting_period
            )
            return None
    
    async def retrieve_ubpr_reporting_periods(self) -> Optional[List[str]]:
        """
        Retrieve available UBPR reporting periods.
        
        Returns:
            List of available UBPR reporting periods or None if failed
        """
        try:
            self.logger.info("Retrieving UBPR reporting periods")
            
            periods = await self._soap_client.service.RetrieveUBPRReportingPeriods()
            
            if periods:
                # Standardize date formats
                standardized_periods = [
                    self._standardize_date_format(period) for period in periods
                ]
                
                # Sort chronologically to find true latest period
                try:
                    def parse_for_sorting(date_str: str) -> datetime:
                        try:
                            return datetime.strptime(date_str, "%Y-%m-%d")
                        except Exception:
                            return datetime(1900, 1, 1)  # Fallback for malformed dates
                    
                    sorted_standardized = sorted(standardized_periods, key=parse_for_sorting, reverse=True)
                    actual_latest = sorted_standardized[0] if sorted_standardized else None
                except Exception as e:
                    self.logger.warning("Could not sort periods for latest detection", error=str(e))
                    actual_latest = standardized_periods[0] if standardized_periods else None
                    sorted_standardized = standardized_periods
                
                self.logger.info(
                    "UBPR reporting periods retrieved successfully",
                    periods_count=len(standardized_periods),
                    latest_period=actual_latest
                )
                
                return sorted_standardized
            else:
                self.logger.warning("No UBPR reporting periods available")
                return None
                
        except SOAPFault as soap_error:
            error_msg = self._handle_soap_fault(soap_error)
            self.logger.error("SOAP fault during UBPR periods retrieval", error=error_msg)
            return None
            
        except Exception as e:
            self.logger.error("UBPR periods retrieval failed", error=str(e))
            return None
    
    async def retrieve_ubpr_facsimile(self,
                                     rssd_id: str,
                                     reporting_period: str) -> Optional[bytes]:
        """
        Retrieve UBPR facsimile data in XBRL format.
        
        Args:
            rssd_id: Bank RSSD identifier
            reporting_period: Reporting period (YYYY-MM-DD)
            
        Returns:
            UBPR data as bytes or None if not available
        """
        cache_key = f"ubpr_{build_ffiec_cache_key(rssd_id, reporting_period, 'XBRL')}"
        
        # Check cache first
        cached_response = self.cache.get(cache_key)
        if cached_response and cached_response.call_report_data:
            self.logger.debug(
                "Using cached UBPR data",
                rssd_id=rssd_id,
                reporting_period=reporting_period
            )
            return cached_response.call_report_data.data
        
        try:
            self.logger.info(
                "Retrieving UBPR facsimile",
                rssd_id=rssd_id,
                reporting_period=reporting_period
            )
            
            # Call FFIEC UBPR API
            result = await self._soap_client.service.RetrieveUBPRXBRLFacsimile(
                reportingPeriodEndDate=reporting_period,
                fiIDType=FFIEC_FI_ID_TYPES["rssd"],
                fiID=int(rssd_id)
            )
            
            if not result:
                self.logger.warning(
                    "No UBPR data returned",
                    rssd_id=rssd_id,
                    reporting_period=reporting_period
                )
                return None
            
            # Handle different result types from FFIEC API
            decoded_data = None
            
            if isinstance(result, bytes):
                # Data is already in bytes format
                decoded_data = result
                self.logger.debug(
                    "FFIEC returned direct UBPR bytes data",
                    data_size=len(result),
                    rssd_id=rssd_id
                )
            elif isinstance(result, str):
                # Data might be base64 encoded string
                try:
                    decoded_data = base64.b64decode(result)
                    self.logger.debug(
                        "Successfully decoded base64 UBPR string",
                        original_size=len(result),
                        decoded_size=len(decoded_data),
                        rssd_id=rssd_id
                    )
                except Exception as decode_error:
                    self.logger.error(
                        "Failed to decode base64 UBPR data",
                        error=str(decode_error),
                        rssd_id=rssd_id,
                        data_type=type(result),
                        data_length=len(result),
                        data_preview=result[:100] if len(result) > 100 else result
                    )
                    return None
            else:
                self.logger.error(
                    "Unexpected UBPR data type from FFIEC API",
                    data_type=type(result),
                    rssd_id=rssd_id
                )
                return None
            
            # Create call report data model for UBPR
            # Standardize the date format before parsing
            standardized_period = self._standardize_date_format(reporting_period)
            call_report_data = FFIECCallReportData(
                rssd_id=rssd_id,
                reporting_period=datetime.strptime(standardized_period, "%Y-%m-%d").date(),
                report_format="UBPR_XBRL",
                data=decoded_data,
                data_size=len(decoded_data)
            )
            
            # Cache the response
            response = FFIECCDRAPIResponse(
                success=True,
                call_report_data=call_report_data
            )
            
            self.cache.put(cache_key, response, ttl_seconds=FFIEC_UBPR_CONFIG["cache_ttl"])
            
            self.logger.info(
                "UBPR facsimile retrieved successfully",
                rssd_id=rssd_id,
                reporting_period=reporting_period,
                data_size=call_report_data.get_data_size_formatted(),
                quality=call_report_data.quality_indicator
            )
            
            return decoded_data
            
        except SOAPFault as soap_error:
            error_msg = self._handle_soap_fault(soap_error)
            self.logger.error(
                "SOAP fault during UBPR facsimile retrieval",
                error=error_msg,
                rssd_id=rssd_id,
                reporting_period=reporting_period
            )
            return None
            
        except Exception as e:
            self.logger.error(
                "UBPR facsimile retrieval failed",
                error=str(e),
                rssd_id=rssd_id,
                reporting_period=reporting_period
            )
            return None
    
    async def discover_latest_ubpr_filing(self, rssd_id: str) -> Optional[str]:
        """
        Discover the latest UBPR filing for a bank.
        
        Args:
            rssd_id: Bank RSSD identifier
            
        Returns:
            Latest UBPR reporting period string or None if not found
        """
        cache_key = f"ubpr_discovery_{rssd_id}"
        
        # Check cache first
        cached_response = self.cache.get(cache_key)
        if cached_response and cached_response.discovery_result:
            self.logger.debug("Using cached UBPR discovery result", rssd_id=rssd_id)
            return cached_response.discovery_result.latest_period
        
        try:
            self.logger.info("Discovering latest UBPR filing", rssd_id=rssd_id)
            
            # Get available UBPR reporting periods
            periods = await self.retrieve_ubpr_reporting_periods()
            
            if not periods:
                self.logger.warning("No UBPR reporting periods available")
                return None
            
            # Sort periods newest to oldest using proper date parsing, not string sorting
            def parse_date_for_sorting(date_str: str) -> datetime:
                """Parse date string for proper chronological sorting."""
                try:
                    standardized = self._standardize_date_format(date_str)
                    return datetime.strptime(standardized, "%Y-%m-%d")
                except Exception as e:
                    self.logger.warning(
                        "Could not parse date for sorting, using fallback",
                        date_string=date_str,
                        error=str(e)
                    )
                    # Fallback: assume far past date so it sorts to end
                    return datetime(1900, 1, 1)
            
            sorted_periods = sorted(periods, key=parse_date_for_sorting, reverse=True)
            
            # Check recent periods for this bank (UBPR is published quarterly)
            for period in sorted_periods[:8]:  # Check last 8 quarters (2 years) for UBPR
                try:
                    # Try to retrieve UBPR data to see if it exists
                    ubpr_data = await self.retrieve_ubpr_facsimile(rssd_id, period)
                    
                    if ubpr_data:
                        # Create and cache discovery result
                        discovery_result = FFIECDiscoveryResult(
                            rssd_id=rssd_id,
                            available_periods=[period],
                            latest_period=period
                        )
                        
                        response = FFIECCDRAPIResponse(
                            success=True,
                            discovery_result=discovery_result
                        )
                        
                        self.cache.put(cache_key, response, ttl_seconds=FFIEC_CDR_CACHE_CONFIG["discovery_data_ttl"])
                        
                        # Convert period to standard YYYY-MM-DD format if needed
                        standardized_period = self._standardize_date_format(period)
                        
                        self.logger.info(
                            "Latest UBPR filing discovered",
                            rssd_id=rssd_id,
                            latest_period=period,
                            standardized_period=standardized_period
                        )
                        return standardized_period
                        
                except Exception as period_error:
                    self.logger.debug(
                        "No UBPR data for period",
                        period=period,
                        error=str(period_error),
                        rssd_id=rssd_id
                    )
                    continue
            
            self.logger.warning("No recent UBPR filings found", rssd_id=rssd_id)
            return None
            
        except Exception as e:
            self.logger.error("UBPR discovery failed", error=str(e), rssd_id=rssd_id)
            return None
    
    def _standardize_date_format(self, date_string: str) -> str:
        """
        Convert various date formats to YYYY-MM-DD format.
        
        Handles formats like:
        - M/D/YYYY (e.g., "9/30/2024")
        - MM/DD/YYYY (e.g., "09/30/2024") 
        - M/D/YY (e.g., "6/30/25") - 2-digit years
        - MM/DD/YY (e.g., "06/30/25") - 2-digit years
        - YYYY-MM-DD (already standard)
        
        Note: For 2-digit years, Python uses pivot system:
        - 00-68 -> 2000-2068 
        - 69-99 -> 1969-1999
        
        Args:
            date_string: Date in various formats
            
        Returns:
            Date in YYYY-MM-DD format
        """
        if not date_string:
            return date_string
            
        # Already in YYYY-MM-DD format
        if len(date_string) == 10 and date_string.count('-') == 2:
            return date_string
        
        try:
            from datetime import datetime
            
            # Try M/D/YYYY or MM/DD/YYYY format first (4-digit year)
            if '/' in date_string:
                try:
                    # Try 4-digit year format first
                    parsed_date = datetime.strptime(date_string, "%m/%d/%Y")
                    return parsed_date.strftime("%Y-%m-%d")
                except ValueError:
                    try:
                        # Try 2-digit year format as fallback
                        parsed_date = datetime.strptime(date_string, "%m/%d/%y")
                        # Apply business logic: for financial data, 2-digit years should be historical
                        # Banking data is typically quarterly reports, so anything beyond current quarter
                        # should be treated as historical (previous century)
                        from datetime import date
                        current_date = date.today()
                        current_year = current_date.year
                        
                        # If the parsed year is equal to or greater than current year,
                        # and it came from a 2-digit year format, treat it as historical
                        if parsed_date.year >= current_year:
                            # Subtract 100 years to make it historical
                            historical_year = parsed_date.year - 100
                            parsed_date = parsed_date.replace(year=historical_year)
                            self.logger.debug(
                                "Converted 2-digit year to historical date",
                                original_string=date_string,
                                parsed_year=parsed_date.year + 100,
                                adjusted_year=historical_year
                            )
                        return parsed_date.strftime("%Y-%m-%d")
                    except ValueError:
                        pass
            
            # If it's already in a different standard format, try to parse and reformat
            for fmt in ["%Y-%m-%d", "%m-%d-%Y", "%d-%m-%Y"]:
                try:
                    parsed_date = datetime.strptime(date_string, fmt)
                    return parsed_date.strftime("%Y-%m-%d")
                except ValueError:
                    continue
            
            # If all else fails, return original
            self.logger.warning("Could not parse date format", date_string=date_string)
            return date_string
            
        except Exception as e:
            self.logger.warning("Date format conversion failed", 
                              date_string=date_string, 
                              error=str(e))
            return date_string
    
    def _handle_soap_fault(self, fault: SOAPFault) -> str:
        """
        Handle SOAP fault and return user-friendly error message.
        
        Args:
            fault: SOAP fault exception
            
        Returns:
            User-friendly error message
        """
        fault_code = getattr(fault, 'code', 'Unknown')
        fault_string = getattr(fault, 'message', str(fault))
        
        # Map common SOAP fault codes to friendly messages
        friendly_message = FFIEC_SOAP_FAULT_CODES.get(fault_code, fault_string)
        
        self.logger.warning(
            "SOAP fault occurred",
            fault_code=fault_code,
            fault_string=fault_string,
            friendly_message=friendly_message
        )
        
        return friendly_message
    
    async def test_connection(self) -> bool:
        """
        Test connection to FFIEC CDR API.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.logger.info("Testing FFIEC CDR API connection")
            
            # Try to retrieve reporting periods as a simple test
            periods = await self._soap_client.service.RetrieveReportingPeriods(
                dataSeries=FFIEC_DATA_SERIES["call_reports"]
            )
            
            success = periods is not None and len(periods) > 0
            
            if success:
                self.logger.info(
                    "FFIEC CDR API connection test successful",
                    periods_available=len(periods)
                )
            else:
                self.logger.warning("FFIEC CDR API connection test failed - no periods returned")
            
            return success
            
        except SOAPFault as soap_error:
            error_msg = self._handle_soap_fault(soap_error)
            self.logger.error("Connection test failed with SOAP fault", error=error_msg)
            return False
            
        except Exception as e:
            self.logger.error("Connection test failed", error=str(e))
            return False
    
    def is_available(self) -> bool:
        """
        Check if FFIEC CDR service is available.
        
        Returns:
            True if service appears to be available
        """
        return self._soap_client is not None and bool(self.api_key) and bool(self.username)
    
    def clear_cache(self):
        """Clear all cached data."""
        self.cache.clear()
    
    async def close(self):
        """Close the SOAP client and clean up resources."""
        if self._soap_client and hasattr(self._soap_client.transport, 'client'):
            try:
                await self._soap_client.transport.client.aclose()
                self.logger.info("SOAP client closed successfully")
            except Exception as e:
                self.logger.warning("Error closing SOAP client", error=str(e))