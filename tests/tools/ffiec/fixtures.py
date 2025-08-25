"""
Test fixtures for FFIEC Call Report tools tests.

Provides common test data, fixtures, and utilities for testing
FFIEC Call Report functionality across all test modules.
"""

import pytest
import base64
from datetime import date, datetime
from decimal import Decimal
from typing import Dict, Any, List
from unittest.mock import Mock, AsyncMock

# Add src directory to path for imports
import sys
from pathlib import Path
test_dir = Path(__file__).parent
src_dir = test_dir.parent.parent.parent / "src"
sys.path.insert(0, str(src_dir))

from tools.infrastructure.banking.ffiec_cdr_models import (
    FFIECCallReportRequest,
    FFIECCallReportData,
    FFIECDiscoveryResult,
    FFIECCDRAPIResponse
)


@pytest.fixture
def sample_rssd_id():
    """Fixture providing sample RSSD ID."""
    return "451965"  # Wells Fargo RSSD ID


@pytest.fixture
def sample_reporting_period():
    """Fixture providing sample reporting period."""
    return "2024-06-30"


@pytest.fixture
def sample_call_report_request(sample_rssd_id, sample_reporting_period):
    """Fixture providing sample call report request."""
    return FFIECCallReportRequest(
        rssd_id=sample_rssd_id,
        reporting_period=sample_reporting_period,
        facsimile_format="PDF"
    )


@pytest.fixture
def sample_call_report_data(sample_rssd_id, sample_reporting_period):
    """Fixture providing sample call report data."""
    # Create mock PDF data
    mock_pdf_data = b"Mock PDF content for call report"
    
    return FFIECCallReportData(
        rssd_id=sample_rssd_id,
        reporting_period=date(2024, 6, 30),
        report_format="PDF",
        data=mock_pdf_data,
        data_size=len(mock_pdf_data)
    )


@pytest.fixture
def sample_discovery_result(sample_rssd_id):
    """Fixture providing sample discovery result."""
    return FFIECDiscoveryResult(
        rssd_id=sample_rssd_id,
        available_periods=["2024-06-30", "2024-03-31", "2023-12-31"],
        latest_period="2024-06-30"
    )


@pytest.fixture
def sample_api_response_success(sample_call_report_data):
    """Fixture providing successful API response."""
    return FFIECCDRAPIResponse(
        success=True,
        call_report_data=sample_call_report_data
    )


@pytest.fixture
def sample_api_response_error():
    """Fixture providing error API response."""
    return FFIECCDRAPIResponse(
        success=False,
        error_message="Call report not found",
        error_code=404
    )


@pytest.fixture
def mock_soap_client():
    """Fixture providing mock SOAP client."""
    mock_client = Mock()
    
    # Mock service methods
    mock_service = Mock()
    mock_client.service = mock_service
    
    # Mock RetrieveReportingPeriods
    mock_service.RetrieveReportingPeriods = AsyncMock(return_value=[
        "2024-06-30", "2024-03-31", "2023-12-31", "2023-09-30"
    ])
    
    # Mock RetrieveFilersSinceDate
    mock_service.RetrieveFilersSinceDate = AsyncMock(return_value=[
        451965, 123456, 789012  # Include Wells Fargo RSSD
    ])
    
    # Mock RetrieveFacsimile - return base64 encoded mock data
    mock_pdf_data = b"Mock PDF content for call report testing"
    encoded_data = base64.b64encode(mock_pdf_data).decode('utf-8')
    mock_service.RetrieveFacsimile = AsyncMock(return_value=encoded_data)
    
    return mock_client


@pytest.fixture
def mock_ffiec_api_client():
    """Fixture providing mock FFIEC CDR API client."""
    mock_client = Mock()
    
    # Mock discovery method
    mock_client.discover_latest_filing = AsyncMock(return_value="2024-06-30")
    
    # Mock retrieve facsimile method
    mock_pdf_data = b"Mock PDF content for call report testing"
    mock_client.retrieve_facsimile = AsyncMock(return_value=mock_pdf_data)
    
    # Mock test connection method
    mock_client.test_connection = AsyncMock(return_value=True)
    
    # Mock availability check
    mock_client.is_available = Mock(return_value=True)
    
    return mock_client


@pytest.fixture
def mock_settings():
    """Fixture providing mock settings."""
    settings = Mock()
    settings.ffiec_cdr_enabled = True
    settings.ffiec_cdr_api_key = "test_api_key"
    settings.ffiec_cdr_username = "test_username"
    settings.ffiec_cdr_timeout_seconds = 30
    settings.ffiec_cdr_cache_ttl = 3600
    return settings


@pytest.fixture
def mock_empty_settings():
    """Fixture providing mock settings without FFIEC credentials."""
    settings = Mock()
    settings.ffiec_cdr_enabled = False
    settings.ffiec_cdr_api_key = None
    settings.ffiec_cdr_username = None
    settings.ffiec_cdr_timeout_seconds = 30
    settings.ffiec_cdr_cache_ttl = 3600
    return settings


class FFIECTestData:
    """Test data generator for FFIEC Call Report tests."""
    
    @staticmethod
    def generate_rssd_ids(count: int = 5) -> List[str]:
        """Generate list of test RSSD IDs."""
        # Start with real RSSD IDs for major banks
        real_rssd_ids = [
            "451965",  # Wells Fargo
            "852218",  # JPMorgan Chase  
            "480228",  # Bank of America
            "451965",  # Citibank
            "497404"   # Goldman Sachs
        ]
        
        result = real_rssd_ids[:count]
        
        # Add generated IDs if needed
        for i in range(len(result), count):
            result.append(str(100000 + i))
        
        return result
    
    @staticmethod
    def generate_reporting_periods(count: int = 8) -> List[str]:
        """Generate list of test reporting periods (quarters)."""
        from datetime import datetime, timedelta
        import calendar
        
        periods = []
        current_date = datetime.now()
        
        for i in range(count):
            # Go back quarters (approximately 3 months each)
            months_back = i * 3
            period_date = current_date - timedelta(days=months_back * 30)
            
            # Get quarter end date
            if period_date.month <= 3:
                quarter_end = datetime(period_date.year, 3, 31)
            elif period_date.month <= 6:
                quarter_end = datetime(period_date.year, 6, 30)
            elif period_date.month <= 9:
                quarter_end = datetime(period_date.year, 9, 30)
            else:
                quarter_end = datetime(period_date.year, 12, 31)
            
            periods.append(quarter_end.strftime("%Y-%m-%d"))
        
        return sorted(list(set(periods)), reverse=True)  # Remove duplicates and sort
    
    @staticmethod
    def generate_mock_pdf_content(rssd_id: str, period: str) -> bytes:
        """Generate mock PDF content for testing."""
        content = f"""
        Mock FFIEC Call Report PDF
        Bank RSSD ID: {rssd_id}
        Reporting Period: {period}
        
        This is mock content for testing purposes.
        In a real implementation, this would be actual PDF data
        from the FFIEC CDR system.
        
        Generated at: {datetime.now().isoformat()}
        """
        return content.encode('utf-8')
    
    @staticmethod
    def generate_soap_fault_scenarios() -> List[Dict[str, Any]]:
        """Generate test scenarios for SOAP faults."""
        return [
            {
                "fault_code": "soap:Client",
                "fault_string": "Invalid RSSD ID format",
                "expected_message": "Client error - invalid request format or parameters"
            },
            {
                "fault_code": "soap:Server",
                "fault_string": "Internal server error",
                "expected_message": "Server error - FFIEC CDR internal processing error"
            },
            {
                "fault_code": "soap:VersionMismatch",
                "fault_string": "SOAP version not supported",
                "expected_message": "SOAP version mismatch"
            }
        ]


@pytest.fixture
def test_data_generator():
    """Fixture providing test data generator."""
    return FFIECTestData()


@pytest.fixture
def successful_tool_result():
    """Fixture providing successful tool execution result."""
    return {
        "success": True,
        "rssd_id": "451965",
        "reporting_period": "2024-06-30",
        "format": "PDF",
        "data_retrieved": True,
        "data_size": "25.6 KB",
        "data_quality": "excellent",
        "execution_time": "1.234s",
        "message": "Successfully retrieved PDF call report for RSSD 451965 from period 2024-06-30"
    }


@pytest.fixture
def error_tool_result():
    """Fixture providing error tool execution result."""
    return {
        "success": False,
        "error": "No recent FFIEC call report filings found for RSSD ID 999999",
        "error_code": "NO_FILINGS_FOUND",
        "rssd_id": "999999"
    }