"""
Unit tests for FFIEC Call Report Data Tool.

Tests the atomic tool implementation with mocked API responses
and LangChain integration patterns.
"""

import pytest
import asyncio
import json
from unittest.mock import patch, MagicMock, AsyncMock

# Add src directory to path for imports
import sys
from pathlib import Path
test_dir = Path(__file__).parent
src_dir = test_dir.parent.parent.parent / "src"
sys.path.insert(0, str(src_dir))

from tools.atomic.ffiec_call_report_data_tool import FFIECCallReportDataTool
from tools.infrastructure.banking.ffiec_cdr_models import FFIECCallReportRequest
from .fixtures import *


class TestFFIECCallReportDataTool:
    """Test cases for FFIEC Call Report Data Tool."""
    
    def test_tool_initialization_with_credentials(self, mock_settings):
        """Test tool initialization with valid credentials."""
        with patch('tools.atomic.ffiec_call_report_data_tool.FFIECCDRAPIClient'):
            tool = FFIECCallReportDataTool(settings=mock_settings)
            
            assert tool.name == "ffiec_call_report_data"
            assert tool.is_available() is True
            assert tool.args_schema == FFIECCallReportRequest
    
    def test_tool_initialization_without_credentials(self, mock_empty_settings):
        """Test tool initialization without credentials."""
        tool = FFIECCallReportDataTool(settings=mock_empty_settings)
        
        assert tool.name == "ffiec_call_report_data"
        assert tool.is_available() is False
    
    @pytest.mark.asyncio
    async def test_successful_call_report_retrieval(self, mock_settings, mock_ffiec_api_client):
        """Test successful call report data retrieval."""
        with patch('tools.atomic.ffiec_call_report_data_tool.FFIECCDRAPIClient', return_value=mock_ffiec_api_client):
            tool = FFIECCallReportDataTool(settings=mock_settings)
            
            # Test with specific period
            result = await tool._arun(
                rssd_id="451965",
                reporting_period="2024-06-30",
                facsimile_format="PDF"
            )
            
            # Parse JSON result
            result_data = json.loads(result)
            
            assert result_data["success"] is True
            assert result_data["rssd_id"] == "451965"
            assert result_data["reporting_period"] == "2024-06-30"
            assert result_data["format"] == "PDF"
            assert result_data["data_retrieved"] is True
            
            # Verify API client was called correctly
            mock_ffiec_api_client.retrieve_facsimile.assert_called_once_with(
                rssd_id="451965",
                reporting_period="2024-06-30",
                format_type="PDF"
            )
    
    @pytest.mark.asyncio
    async def test_automatic_period_discovery(self, mock_settings, mock_ffiec_api_client):
        """Test automatic discovery of latest reporting period."""
        with patch('tools.atomic.ffiec_call_report_data_tool.FFIECCDRAPIClient', return_value=mock_ffiec_api_client):
            tool = FFIECCallReportDataTool(settings=mock_settings)
            
            # Test without specifying period (should trigger discovery)
            result = await tool._arun(
                rssd_id="451965",
                facsimile_format="PDF"
            )
            
            # Parse JSON result
            result_data = json.loads(result)
            
            assert result_data["success"] is True
            assert result_data["period_discovered"] is True
            assert "discovery_note" in result_data
            
            # Verify discovery was called
            mock_ffiec_api_client.discover_latest_filing.assert_called_once_with("451965")
    
    @pytest.mark.asyncio
    async def test_no_filings_found(self, mock_settings):
        """Test handling when no filings are found for a bank."""
        mock_client = AsyncMock()
        mock_client.discover_latest_filing.return_value = None  # No filings found
        
        with patch('tools.atomic.ffiec_call_report_data_tool.FFIECCDRAPIClient', return_value=mock_client):
            tool = FFIECCallReportDataTool(settings=mock_settings)
            
            result = await tool._arun(rssd_id="999999")
            
            # Parse JSON result
            result_data = json.loads(result)
            
            assert result_data["success"] is False
            assert result_data["error_code"] == "NO_FILINGS_FOUND"
            assert "999999" in result_data["error"]
    
    @pytest.mark.asyncio
    async def test_data_not_available(self, mock_settings):
        """Test handling when call report data is not available."""
        mock_client = AsyncMock()
        mock_client.discover_latest_filing.return_value = "2024-06-30"
        mock_client.retrieve_facsimile.return_value = None  # Data not available
        
        with patch('tools.atomic.ffiec_call_report_data_tool.FFIECCDRAPIClient', return_value=mock_client):
            tool = FFIECCallReportDataTool(settings=mock_settings)
            
            result = await tool._arun(rssd_id="451965")
            
            # Parse JSON result
            result_data = json.loads(result)
            
            assert result_data["success"] is False
            assert result_data["error_code"] == "DATA_NOT_AVAILABLE"
            assert "451965" in result_data["error"]
    
    @pytest.mark.asyncio
    async def test_invalid_rssd_id(self, mock_settings, mock_ffiec_api_client):
        """Test validation of invalid RSSD ID."""
        with patch('tools.atomic.ffiec_call_report_data_tool.FFIECCDRAPIClient', return_value=mock_ffiec_api_client):
            tool = FFIECCallReportDataTool(settings=mock_settings)
            
            # Test with invalid RSSD ID
            result = await tool._arun(rssd_id="invalid_rssd")
            
            # Parse JSON result
            result_data = json.loads(result)
            
            assert result_data["success"] is False
            assert result_data["error_code"] == "VALIDATION_ERROR"
            assert "Invalid input" in result_data["error"]
    
    @pytest.mark.asyncio
    async def test_invalid_reporting_period(self, mock_settings, mock_ffiec_api_client):
        """Test validation of invalid reporting period format."""
        with patch('tools.atomic.ffiec_call_report_data_tool.FFIECCDRAPIClient', return_value=mock_ffiec_api_client):
            tool = FFIECCallReportDataTool(settings=mock_settings)
            
            # Test with invalid period format
            result = await tool._arun(
                rssd_id="451965",
                reporting_period="invalid_date"
            )
            
            # Parse JSON result
            result_data = json.loads(result)
            
            assert result_data["success"] is False
            assert result_data["error_code"] == "VALIDATION_ERROR"
    
    @pytest.mark.asyncio
    async def test_invalid_facsimile_format(self, mock_settings, mock_ffiec_api_client):
        """Test validation of invalid facsimile format."""
        with patch('tools.atomic.ffiec_call_report_data_tool.FFIECCDRAPIClient', return_value=mock_ffiec_api_client):
            tool = FFIECCallReportDataTool(settings=mock_settings)
            
            # Test with invalid format
            result = await tool._arun(
                rssd_id="451965",
                facsimile_format="INVALID"
            )
            
            # Parse JSON result
            result_data = json.loads(result)
            
            assert result_data["success"] is False
            assert result_data["error_code"] == "VALIDATION_ERROR"
    
    @pytest.mark.asyncio
    async def test_service_unavailable(self, mock_empty_settings):
        """Test behavior when service is unavailable."""
        tool = FFIECCallReportDataTool(settings=mock_empty_settings)
        
        result = await tool._arun(rssd_id="451965")
        
        # Parse JSON result
        result_data = json.loads(result)
        
        assert result_data["success"] is False
        assert result_data["error_code"] == "SERVICE_UNAVAILABLE"
        assert "not available" in result_data["error"]
    
    @pytest.mark.asyncio
    async def test_api_exception_handling(self, mock_settings):
        """Test handling of API exceptions."""
        mock_client = AsyncMock()
        mock_client.discover_latest_filing.side_effect = Exception("API connection failed")
        
        with patch('tools.atomic.ffiec_call_report_data_tool.FFIECCDRAPIClient', return_value=mock_client):
            tool = FFIECCallReportDataTool(settings=mock_settings)
            
            result = await tool._arun(rssd_id="451965")
            
            # Parse JSON result
            result_data = json.loads(result)
            
            assert result_data["success"] is False
            assert result_data["error_code"] == "RETRIEVAL_ERROR"
            assert "API connection failed" in result_data["error"]
    
    def test_synchronous_run_method(self, mock_settings, mock_ffiec_api_client):
        """Test synchronous _run method (LangChain compatibility)."""
        with patch('tools.atomic.ffiec_call_report_data_tool.FFIECCDRAPIClient', return_value=mock_ffiec_api_client):
            tool = FFIECCallReportDataTool(settings=mock_settings)
            
            # Test synchronous call
            result = tool._run(rssd_id="451965", reporting_period="2024-06-30")
            
            # Parse JSON result
            result_data = json.loads(result)
            
            assert result_data["success"] is True
            assert result_data["rssd_id"] == "451965"
    
    @pytest.mark.asyncio
    async def test_connection_test(self, mock_settings, mock_ffiec_api_client):
        """Test connection testing functionality."""
        with patch('tools.atomic.ffiec_call_report_data_tool.FFIECCDRAPIClient', return_value=mock_ffiec_api_client):
            tool = FFIECCallReportDataTool(settings=mock_settings)
            
            # Test connection
            result = await tool.test_connection()
            
            assert result is True
            mock_ffiec_api_client.test_connection.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_data_quality_assessment(self, mock_settings):
        """Test data quality assessment in response."""
        # Mock different data sizes to test quality assessment
        test_cases = [
            (200 * 1024, "excellent"),  # 200KB
            (75 * 1024, "good"),        # 75KB
            (25 * 1024, "fair"),        # 25KB
            (5 * 1024, "poor")          # 5KB
        ]
        
        for data_size, expected_quality in test_cases:
            mock_client = AsyncMock()
            mock_client.discover_latest_filing.return_value = "2024-06-30"
            mock_client.retrieve_facsimile.return_value = b"x" * data_size
            
            with patch('tools.atomic.ffiec_call_report_data_tool.FFIECCDRAPIClient', return_value=mock_client):
                tool = FFIECCallReportDataTool(settings=mock_settings)
                
                result = await tool._arun(rssd_id="451965")
                result_data = json.loads(result)
                
                assert result_data["success"] is True
                assert result_data["data_quality"] == expected_quality
    
    def test_langchain_tool_schema(self, mock_settings):
        """Test LangChain tool schema generation."""
        with patch('tools.atomic.ffiec_call_report_data_tool.FFIECCDRAPIClient'):
            tool = FFIECCallReportDataTool(settings=mock_settings)
            
            # Test that tool has proper LangChain attributes
            assert hasattr(tool, 'name')
            assert hasattr(tool, 'description')
            assert hasattr(tool, 'args_schema')
            
            # Test schema structure
            assert tool.name == "ffiec_call_report_data"
            assert "FFIEC Call Report" in tool.description
            assert tool.args_schema == FFIECCallReportRequest
    
    def test_format_success_response(self, mock_settings, mock_ffiec_api_client):
        """Test success response formatting."""
        with patch('tools.atomic.ffiec_call_report_data_tool.FFIECCDRAPIClient', return_value=mock_ffiec_api_client):
            tool = FFIECCallReportDataTool(settings=mock_settings)
            
            # Test formatting
            response = tool._format_success(
                rssd_id="451965",
                reporting_period="2024-06-30",
                format_type="PDF",
                data_size=50000,
                execution_time=1.234,
                discovered_period=True
            )
            
            result_data = json.loads(response)
            
            assert result_data["success"] is True
            assert result_data["rssd_id"] == "451965"
            assert result_data["data_size"] == "48.8 KB"
            assert result_data["execution_time"] == "1.234s"
            assert result_data["period_discovered"] is True
            assert "discovery_note" in result_data
    
    def test_format_error_response(self, mock_settings):
        """Test error response formatting."""
        with patch('tools.atomic.ffiec_call_report_data_tool.FFIECCDRAPIClient'):
            tool = FFIECCallReportDataTool(settings=mock_settings)
            
            # Test formatting
            response = tool._format_error(
                error_message="Test error message",
                error_code="TEST_ERROR",
                rssd_id="451965",
                reporting_period="2024-06-30"
            )
            
            result_data = json.loads(response)
            
            assert result_data["success"] is False
            assert result_data["error"] == "Test error message"
            assert result_data["error_code"] == "TEST_ERROR"
            assert result_data["rssd_id"] == "451965"
            assert result_data["reporting_period"] == "2024-06-30"