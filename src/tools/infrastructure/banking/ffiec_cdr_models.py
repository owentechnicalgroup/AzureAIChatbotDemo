"""
Pydantic data models for FFIEC CDR API structures.

Provides type-safe models for FFIEC Call Report data processing,
validation, and serialization following FFIEC CDR API standards.
"""

import base64
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Union, Any
from pydantic import BaseModel, Field, field_validator, ConfigDict
import structlog

from .ffiec_cdr_constants import (
    FFIEC_FACSIMILE_FORMATS,
    FFIEC_FI_ID_TYPES,
    validate_rssd_id,
    validate_reporting_period,
    validate_facsimile_format,
    assess_call_report_quality
)

logger = structlog.get_logger(__name__).bind(log_type="SYSTEM")


class FFIECCallReportRequest(BaseModel):
    """Input schema for FFIEC Call Report and UBPR data requests."""
    
    rssd_id: str = Field(
        description="Bank RSSD identifier (required)",
        example="451965"
    )
    reporting_period: Optional[str] = Field(
        default=None,
        description="Specific reporting period in YYYY-MM-DD format (optional)",
        example="2024-06-30"
    )
    facsimile_format: str = Field(
        default="SDF",
        description="Report format: SDF, XBRL, or PDF (for call reports)"
    )
    data_type: str = Field(
        default="call_report", 
        description="Data type: 'call_report' for raw regulatory data or 'ubpr' for processed performance ratios"
    )


class FFIECCallReportData(BaseModel):
    """
    Input model for FFIEC Call Report data requests.
    
    Represents a request to retrieve call report data from FFIEC CDR
    with proper validation and field descriptions.
    """
    
    rssd_id: str = Field(
        ...,
        description="Bank RSSD ID for call report retrieval",
        min_length=1,
        max_length=10
    )
    reporting_period: Optional[str] = Field(
        None,
        description="Specific reporting period (YYYY-MM-DD) or None for latest"
    )
    facsimile_format: str = Field(
        "PDF",
        description="Output format: PDF, XBRL, or SDF"
    )
    
    @field_validator("rssd_id")
    @classmethod
    def validate_rssd_format(cls, v: str) -> str:
        """Validate RSSD ID format."""
        if not validate_rssd_id(v):
            raise ValueError("RSSD ID must be 1-10 digits")
        return v
    
    @field_validator("reporting_period")
    @classmethod
    def validate_period_format(cls, v: Optional[str]) -> Optional[str]:
        """Validate reporting period format."""
        if v is not None and not validate_reporting_period(v):
            raise ValueError("Reporting period must be in YYYY-MM-DD format")
        return v
    
    @field_validator("facsimile_format")
    @classmethod
    def validate_format_type(cls, v: str) -> str:
        """Validate facsimile format."""
        if not validate_facsimile_format(v):
            valid_formats = list(FFIEC_FACSIMILE_FORMATS.values())
            raise ValueError(f"Format must be one of: {valid_formats}")
        return v.upper()


class FFIECCallReportData(BaseModel):
    """
    Model for retrieved FFIEC Call Report data.
    
    Represents call report data retrieved from FFIEC CDR
    with metadata and quality assessment.
    """
    
    rssd_id: str = Field(
        ...,
        description="Bank RSSD identifier"
    )
    reporting_period: date = Field(
        ...,
        description="Reporting period (quarter end date)"
    )
    report_format: str = Field(
        ...,
        description="Format of retrieved data (PDF, XBRL, SDF)"
    )
    data: bytes = Field(
        ...,
        description="Base64 decoded call report facsimile data"
    )
    data_size: int = Field(
        ...,
        description="Size of call report data in bytes"
    )
    retrieval_timestamp: datetime = Field(
        default_factory=datetime.now,
        description="When this data was retrieved"
    )
    data_source: str = Field(
        default="FFIEC CDR Public Data Distribution",
        description="Source of the data"
    )
    quality_indicator: str = Field(
        default="unknown",
        description="Data quality assessment"
    )
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    def __init__(self, **data):
        """Initialize with quality assessment."""
        super().__init__(**data)
        if self.data:
            self.quality_indicator = assess_call_report_quality(len(self.data))
    
    def get_data_size_formatted(self) -> str:
        """Get human-readable data size."""
        size = self.data_size
        if size < 1024:
            return f"{size} bytes"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        else:
            return f"{size / (1024 * 1024):.1f} MB"
    
    def is_high_quality(self) -> bool:
        """Check if data quality is good or excellent."""
        return self.quality_indicator in ["excellent", "good"]
    
    def get_metadata_summary(self) -> Dict[str, Any]:
        """Get summary metadata about this call report."""
        return {
            "rssd_id": self.rssd_id,
            "reporting_period": str(self.reporting_period),
            "format": self.report_format,
            "size": self.get_data_size_formatted(),
            "quality": self.quality_indicator,
            "retrieved": self.retrieval_timestamp.isoformat(),
            "source": self.data_source
        }


class FFIECDiscoveryResult(BaseModel):
    """
    Model for FFIEC filing discovery results.
    
    Represents the results of discovering available call report
    filings for a specific bank.
    """
    
    rssd_id: str = Field(
        ...,
        description="Bank RSSD identifier"
    )
    available_periods: List[str] = Field(
        default_factory=list,
        description="List of available reporting periods"
    )
    latest_period: Optional[str] = Field(
        None,
        description="Most recent reporting period available"
    )
    discovery_timestamp: datetime = Field(
        default_factory=datetime.now,
        description="When discovery was performed"
    )
    total_filings_found: int = Field(
        default=0,
        description="Total number of filings found"
    )
    
    def __init__(self, **data):
        """Initialize with computed fields."""
        super().__init__(**data)
        if self.available_periods:
            # Sort periods and find latest
            sorted_periods = sorted(self.available_periods, reverse=True)
            if sorted_periods:
                self.latest_period = sorted_periods[0]
            self.total_filings_found = len(self.available_periods)
    
    def has_recent_filings(self, months_back: int = 12) -> bool:
        """Check if bank has filings within specified months."""
        if not self.latest_period:
            return False
        
        try:
            from datetime import datetime
            latest_date = datetime.strptime(self.latest_period, "%Y-%m-%d").date()
            cutoff_date = datetime.now().date() - timedelta(days=months_back * 30)
            return latest_date >= cutoff_date
        except ValueError:
            return False
    
    def get_recent_periods(self, count: int = 4) -> List[str]:
        """Get the most recent N reporting periods."""
        sorted_periods = sorted(self.available_periods, reverse=True)
        return sorted_periods[:count]


class FFIECCDRAPIResponse(BaseModel):
    """
    Model for FFIEC CDR API responses.
    
    Standardized response model for all FFIEC CDR API operations
    with success/error handling and metadata.
    """
    
    success: bool = Field(
        ...,
        description="Whether the API call was successful"
    )
    call_report_data: Optional[FFIECCallReportData] = Field(
        None,
        description="Retrieved call report data if successful"
    )
    discovery_result: Optional[FFIECDiscoveryResult] = Field(
        None,
        description="Discovery results if applicable"
    )
    error_message: Optional[str] = Field(
        None,
        description="Error message if unsuccessful"
    )
    error_code: Optional[int] = Field(
        None,
        description="Error code if applicable"
    )
    request_timestamp: datetime = Field(
        default_factory=datetime.now,
        description="When the request was made"
    )
    response_timestamp: datetime = Field(
        default_factory=datetime.now,
        description="When the response was received"
    )
    execution_time: Optional[float] = Field(
        None,
        description="Execution time in seconds"
    )
    
    def __init__(self, **data):
        """Initialize with computed execution time."""
        super().__init__(**data)
        if self.request_timestamp and self.response_timestamp:
            delta = self.response_timestamp - self.request_timestamp
            self.execution_time = delta.total_seconds()
    
    def is_cached_response(self) -> bool:
        """Check if this appears to be a cached response (very fast)."""
        return self.execution_time is not None and self.execution_time < 0.1
    
    def get_response_summary(self) -> Dict[str, Any]:
        """Get summary of the API response."""
        summary = {
            "success": self.success,
            "execution_time": f"{self.execution_time:.3f}s" if self.execution_time else "unknown",
            "cached": self.is_cached_response()
        }
        
        if self.success:
            if self.call_report_data:
                summary["data_type"] = "call_report"
                summary["data_quality"] = self.call_report_data.quality_indicator
                summary["data_size"] = self.call_report_data.get_data_size_formatted()
            elif self.discovery_result:
                summary["data_type"] = "discovery"
                summary["filings_found"] = self.discovery_result.total_filings_found
                summary["latest_period"] = self.discovery_result.latest_period
        else:
            summary["error"] = self.error_message
            summary["error_code"] = self.error_code
        
        return summary


class FFIECCDRCacheEntry(BaseModel):
    """
    Model for FFIEC CDR cache entries.
    
    Represents a cached response from the FFIEC CDR API
    with expiration and metadata tracking.
    """
    
    response: FFIECCDRAPIResponse = Field(
        ...,
        description="Cached API response"
    )
    cache_timestamp: datetime = Field(
        default_factory=datetime.now,
        description="When this entry was cached"
    )
    ttl_seconds: int = Field(
        default=3600,
        description="Time-to-live in seconds"
    )
    access_count: int = Field(
        default=0,
        description="Number of times this entry was accessed"
    )
    
    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        expiry_time = self.cache_timestamp + timedelta(seconds=self.ttl_seconds)
        return datetime.now() > expiry_time
    
    def time_to_expiry(self) -> int:
        """Get time until expiry in seconds."""
        if self.is_expired():
            return 0
        
        expiry_time = self.cache_timestamp + timedelta(seconds=self.ttl_seconds)
        delta = expiry_time - datetime.now()
        return max(0, int(delta.total_seconds()))
    
    def mark_accessed(self):
        """Mark this entry as accessed (increment counter)."""
        self.access_count += 1