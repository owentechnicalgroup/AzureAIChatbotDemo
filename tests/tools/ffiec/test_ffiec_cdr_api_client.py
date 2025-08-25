"""
Unit tests for FFIEC CDR SOAP API client.

Tests the SOAP client implementation with proper mocking
using pytest-asyncio for comprehensive coverage.
"""

import pytest
import asyncio
import base64
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, AsyncMock
from zeep.exceptions import Fault as SOAPFault

# Add src directory to path for imports
import sys
from pathlib import Path
test_dir = Path(__file__).parent
src_dir = test_dir.parent.parent.parent / "src"
sys.path.insert(0, str(src_dir))

from tools.infrastructure.banking.ffiec_cdr_api_client import FFIECCDRAPIClient, FFIECCDRAPICache
from tools.infrastructure.banking.ffiec_cdr_models import FFIECCDRAPIResponse
from tools.infrastructure.banking.ffiec_cdr_constants import FFIEC_CDR_WSDL_URL
from .fixtures import *


class TestFFIECCDRAPICache:
    """Test cases for FFIEC CDR API cache functionality."""
    
    def test_cache_initialization(self):
        """Test cache initialization with proper parameters."""
        cache = FFIECCDRAPICache(default_ttl_seconds=1800, max_entries=500)
        
        assert cache.default_ttl == 1800
        assert cache.max_entries == 500
        assert len(cache._cache) == 0
    
    def test_cache_put_and_get(self, sample_api_response_success):
        """Test basic cache put and get operations."""
        cache = FFIECCDRAPICache(default_ttl_seconds=3600)
        cache_key = "test_key"
        
        # Store in cache
        cache.put(cache_key, sample_api_response_success)
        
        # Retrieve from cache
        cached_response = cache.get(cache_key)
        
        assert cached_response is not None
        assert cached_response.success == sample_api_response_success.success
        assert cached_response.call_report_data == sample_api_response_success.call_report_data
    
    def test_cache_expiry(self, sample_api_response_success):
        """Test cache entry expiry."""
        cache = FFIECCDRAPICache(default_ttl_seconds=1)  # 1 second TTL
        cache_key = "test_key"
        
        # Store in cache
        cache.put(cache_key, sample_api_response_success)
        
        # Should be available immediately
        assert cache.get(cache_key) is not None
        
        # Wait for expiry and check
        import time
        time.sleep(1.1)
        assert cache.get(cache_key) is None
    
    def test_cache_max_entries(self, sample_api_response_success):
        """Test cache max entries limit."""
        cache = FFIECCDRAPICache(default_ttl_seconds=3600, max_entries=2)
        
        # Add entries up to limit
        cache.put("key1", sample_api_response_success)
        cache.put("key2", sample_api_response_success)
        
        # Both should be present
        assert cache.get("key1") is not None
        assert cache.get("key2") is not None
        
        # Add third entry (should evict oldest)
        cache.put("key3", sample_api_response_success)
        
        # First entry should be gone, others should remain
        assert cache.get("key1") is None
        assert cache.get("key2") is not None
        assert cache.get("key3") is not None


class TestFFIECCDRAPIClient:
    """Test cases for FFIEC CDR API client."""
    
    @patch('tools.infrastructure.banking.ffiec_cdr_api_client.AsyncClient')
    @patch('tools.infrastructure.banking.ffiec_cdr_api_client.httpx')
    def test_client_initialization(self, mock_httpx, mock_async_client):
        """Test SOAP client initialization with authentication."""
        # Setup mocks
        mock_wsdl_client = MagicMock()
        mock_async_http_client = MagicMock()
        mock_httpx.Client.return_value = mock_wsdl_client
        mock_httpx.AsyncClient.return_value = mock_async_http_client
        
        # Initialize client
        client = FFIECCDRAPIClient(
            api_key="test_key",
            username="test_user",
            timeout=30,
            cache_ttl=3600
        )
        
        # Verify initialization
        assert client.api_key == "test_key"
        assert client.username == "test_user"
        assert client.timeout == 30
        
        # Verify SOAP client setup was called
        mock_httpx.Client.assert_called_once()
        mock_httpx.AsyncClient.assert_called_once()
        mock_async_client.assert_called_once_with(FFIEC_CDR_WSDL_URL, transport=mock_async_client.call_args[1]['transport'])
    
    @pytest.mark.asyncio
    @patch('tools.infrastructure.banking.ffiec_cdr_api_client.AsyncClient')
    async def test_discover_latest_filing_success(self, mock_async_client_class, mock_soap_client):
        """Test successful discovery of latest filing."""
        # Setup mock
        mock_client_instance = mock_soap_client
        mock_async_client_class.return_value = mock_client_instance
        
        with patch('tools.infrastructure.banking.ffiec_cdr_api_client.httpx'):
            client = FFIECCDRAPIClient("test_key", "test_user")
            client._soap_client = mock_client_instance
            
            # Test discovery
            result = await client.discover_latest_filing("451965")
            
            assert result == "2024-06-30"
            
            # Verify API calls were made
            mock_client_instance.service.RetrieveReportingPeriods.assert_called_once_with(dataSeries="Call")
            mock_client_instance.service.RetrieveFilersSinceDate.assert_called()
    
    @pytest.mark.asyncio
    @patch('tools.infrastructure.banking.ffiec_cdr_api_client.AsyncClient')
    async def test_discover_latest_filing_not_found(self, mock_async_client_class):
        """Test discovery when bank has no recent filings."""
        # Setup mock with empty filers list
        mock_client = MagicMock()
        mock_service = MagicMock()
        mock_client.service = mock_service
        
        mock_service.RetrieveReportingPeriods = AsyncMock(return_value=[
            "2024-06-30", "2024-03-31"
        ])
        mock_service.RetrieveFilersSinceDate = AsyncMock(return_value=[])  # No filers
        
        mock_async_client_class.return_value = mock_client
        
        with patch('tools.infrastructure.banking.ffiec_cdr_api_client.httpx'):
            client = FFIECCDRAPIClient("test_key", "test_user")
            client._soap_client = mock_client
            
            # Test discovery
            result = await client.discover_latest_filing("999999")
            
            assert result is None
    
    @pytest.mark.asyncio
    @patch('tools.infrastructure.banking.ffiec_cdr_api_client.AsyncClient')
    async def test_retrieve_facsimile_success(self, mock_async_client_class, mock_soap_client):
        """Test successful facsimile retrieval."""
        # Setup mock
        mock_client_instance = mock_soap_client
        mock_async_client_class.return_value = mock_client_instance
        
        with patch('tools.infrastructure.banking.ffiec_cdr_api_client.httpx'):
            client = FFIECCDRAPIClient("test_key", "test_user")
            client._soap_client = mock_client_instance
            
            # Test facsimile retrieval
            result = await client.retrieve_facsimile("451965", "2024-06-30", "PDF")
            
            assert result is not None
            assert isinstance(result, bytes)
            assert b"Mock PDF content" in result
            
            # Verify API call was made
            mock_client_instance.service.RetrieveFacsimile.assert_called_once_with(
                dataSeries="Call",
                reportingPeriodEndDate="2024-06-30",
                fiIDType="ID_RSSD",
                fiID=451965,
                facsimileFormat="PDF"
            )
    
    @pytest.mark.asyncio
    @patch('tools.infrastructure.banking.ffiec_cdr_api_client.AsyncClient')
    async def test_retrieve_facsimile_not_found(self, mock_async_client_class):
        """Test facsimile retrieval when data not available."""
        # Setup mock with empty response
        mock_client = MagicMock()
        mock_service = MagicMock()
        mock_client.service = mock_service
        mock_service.RetrieveFacsimile = AsyncMock(return_value=None)
        
        mock_async_client_class.return_value = mock_client
        
        with patch('tools.infrastructure.banking.ffiec_cdr_api_client.httpx'):
            client = FFIECCDRAPIClient("test_key", "test_user")
            client._soap_client = mock_client
            
            # Test facsimile retrieval
            result = await client.retrieve_facsimile("999999", "2024-06-30", "PDF")
            
            assert result is None
    
    @pytest.mark.asyncio
    @patch('tools.infrastructure.banking.ffiec_cdr_api_client.AsyncClient')
    async def test_soap_fault_handling(self, mock_async_client_class, test_data_generator):
        """Test SOAP fault handling."""
        fault_scenarios = test_data_generator.generate_soap_fault_scenarios()
        
        for scenario in fault_scenarios:
            # Setup mock to raise SOAP fault
            mock_client = MagicMock()
            mock_service = MagicMock()
            mock_client.service = mock_service
            
            soap_fault = SOAPFault(scenario["fault_string"])
            soap_fault.code = scenario["fault_code"]
            mock_service.RetrieveFacsimile = AsyncMock(side_effect=soap_fault)
            
            mock_async_client_class.return_value = mock_client
            
            with patch('tools.infrastructure.banking.ffiec_cdr_api_client.httpx'):
                client = FFIECCDRAPIClient("test_key", "test_user")
                client._soap_client = mock_client
                
                # Test that SOAP fault is handled gracefully
                result = await client.retrieve_facsimile("451965", "2024-06-30", "PDF")
                
                assert result is None  # Should return None on fault
    
    @pytest.mark.asyncio
    @patch('tools.infrastructure.banking.ffiec_cdr_api_client.AsyncClient')
    async def test_caching_behavior(self, mock_async_client_class, mock_soap_client):
        """Test that responses are properly cached."""
        # Setup mock
        mock_client_instance = mock_soap_client
        mock_async_client_class.return_value = mock_client_instance
        
        with patch('tools.infrastructure.banking.ffiec_cdr_api_client.httpx'):
            client = FFIECCDRAPIClient("test_key", "test_user")
            client._soap_client = mock_client_instance
            
            # First call should hit the API
            result1 = await client.retrieve_facsimile("451965", "2024-06-30", "PDF")
            
            # Second call should use cache (API should only be called once)
            result2 = await client.retrieve_facsimile("451965", "2024-06-30", "PDF")
            
            assert result1 == result2
            
            # Verify API was only called once
            assert mock_client_instance.service.RetrieveFacsimile.call_count == 1
    
    @pytest.mark.asyncio
    @patch('tools.infrastructure.banking.ffiec_cdr_api_client.AsyncClient')
    async def test_connection_test_success(self, mock_async_client_class, mock_soap_client):
        """Test successful connection test."""
        # Setup mock
        mock_client_instance = mock_soap_client
        mock_async_client_class.return_value = mock_client_instance
        
        with patch('tools.infrastructure.banking.ffiec_cdr_api_client.httpx'):
            client = FFIECCDRAPIClient("test_key", "test_user")
            client._soap_client = mock_client_instance
            
            # Test connection
            result = await client.test_connection()
            
            assert result is True
            mock_client_instance.service.RetrieveReportingPeriods.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('tools.infrastructure.banking.ffiec_cdr_api_client.AsyncClient')
    async def test_connection_test_failure(self, mock_async_client_class):
        """Test connection test failure."""
        # Setup mock to raise exception
        mock_client = MagicMock()
        mock_service = MagicMock()
        mock_client.service = mock_service
        mock_service.RetrieveReportingPeriods = AsyncMock(side_effect=Exception("Connection failed"))
        
        mock_async_client_class.return_value = mock_client
        
        with patch('tools.infrastructure.banking.ffiec_cdr_api_client.httpx'):
            client = FFIECCDRAPIClient("test_key", "test_user")
            client._soap_client = mock_client
            
            # Test connection
            result = await client.test_connection()
            
            assert result is False
    
    @patch('tools.infrastructure.banking.ffiec_cdr_api_client.AsyncClient')
    def test_availability_check(self, mock_async_client_class):
        """Test service availability check."""
        # Setup mock to avoid WSDL loading
        mock_client = MagicMock()
        mock_async_client_class.return_value = mock_client
        
        with patch('tools.infrastructure.banking.ffiec_cdr_api_client.httpx'):
            # Client with credentials should be available
            client = FFIECCDRAPIClient("test_key", "test_user")
            assert client.is_available() is True
            
            # Client without credentials should not be available
            client_no_creds = FFIECCDRAPIClient("", "")
            assert client_no_creds.is_available() is False