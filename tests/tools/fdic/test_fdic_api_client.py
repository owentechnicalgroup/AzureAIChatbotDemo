"""
Unit tests for FDIC BankFind Suite API client.

Tests the HTTP client implementation with proper mocking
using aioresponses for comprehensive coverage.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import patch, MagicMock

# Add src directory to path for imports
import sys
from pathlib import Path
test_dir = Path(__file__).parent
src_dir = test_dir.parent.parent.parent / "src"
sys.path.insert(0, str(src_dir))

from aioresponses import aioresponses
import aiohttp

from tools.infrastructure.banking.fdic_api_client import FDICAPIClient, FDICAPICache
from tools.infrastructure.banking.fdic_models import FDICInstitution, FDICAPIResponse
from tools.infrastructure.banking.fdic_constants import FDIC_API_BASE_URL


class TestFDICAPICache:
    """Test cases for FDIC API cache functionality."""
    
    def test_cache_initialization(self):
        """Test cache initialization with proper parameters."""
        cache = FDICAPICache(default_ttl_seconds=1800, max_entries=500)
        
        assert cache.default_ttl == 1800
        assert cache.max_entries == 500
        assert len(cache._cache) == 0
    
    def test_cache_put_and_get(self):
        """Test basic cache put and get operations."""
        cache = FDICAPICache(default_ttl_seconds=3600)
        
        # Create mock response
        mock_institutions = [
            FDICInstitution(
                name="Test Bank",
                cert="12345",
                city="Test City",
                stname="California",
                active=True
            )
        ]
        
        response = FDICAPIResponse(
            success=True,
            data=mock_institutions,
            timestamp=datetime.now().isoformat()
        )
        
        # Cache the response
        cache.put("test_key", response)
        
        # Retrieve from cache
        cached_response = cache.get("test_key")
        
        assert cached_response is not None
        assert cached_response.success == True
        assert len(cached_response.institutions) == 1
        assert cached_response.institutions[0].name == "Test Bank"
    
    def test_cache_expiry(self):
        """Test that cache entries expire correctly."""
        cache = FDICAPICache(default_ttl_seconds=1)  # 1 second TTL
        
        response = FDICAPIResponse(
            success=True,
            data=[],
            timestamp=datetime.now().isoformat()
        )
        
        # Cache the response
        cache.put("test_key", response, ttl_seconds=1)
        
        # Should be available immediately
        cached_response = cache.get("test_key")
        assert cached_response is not None
        
        # Wait for expiry and check again
        import time
        time.sleep(1.1)  # Wait longer than TTL
        
        expired_response = cache.get("test_key")
        assert expired_response is None
    
    def test_cache_max_entries_eviction(self):
        """Test that cache evicts entries when max capacity is reached."""
        cache = FDICAPICache(default_ttl_seconds=3600, max_entries=2)
        
        response1 = FDICAPIResponse(success=True, data=[], timestamp=datetime.now().isoformat())
        response2 = FDICAPIResponse(success=True, data=[], timestamp=datetime.now().isoformat())
        response3 = FDICAPIResponse(success=True, data=[], timestamp=datetime.now().isoformat())
        
        # Add entries up to capacity
        cache.put("key1", response1)
        cache.put("key2", response2)
        
        # Both should be available
        assert cache.get("key1") is not None
        assert cache.get("key2") is not None
        
        # Add third entry, should evict oldest
        cache.put("key3", response3)
        
        # key3 should be available, one of the others should be evicted
        assert cache.get("key3") is not None
        assert len(cache._cache) <= 2


class TestFDICAPIClient:
    """Test cases for FDIC API client functionality."""
    
    @pytest.fixture
    def client(self):
        """Fixture providing FDIC API client instance."""
        return FDICAPIClient(api_key="test_api_key", timeout=10.0)
    
    @pytest.fixture
    def client_no_key(self):
        """Fixture providing FDIC API client without API key."""
        return FDICAPIClient(api_key=None, timeout=10.0)
    
    def test_client_initialization(self, client):
        """Test proper client initialization."""
        assert client.api_key == "test_api_key"
        assert client.base_url == FDIC_API_BASE_URL
        assert client.timeout.total == 10.0
        assert client.is_available() == True
    
    def test_client_initialization_no_key(self, client_no_key):
        """Test client initialization without API key."""
        assert client_no_key.api_key is None
        assert client_no_key.is_available() == True  # Should still be available
    
    @pytest.mark.asyncio
    async def test_search_institutions_success(self, client):
        """Test successful institution search."""
        mock_response_data = {
            "data": [
                {
                    "CERT": "12345",
                    "NAME": "Test Bank, National Association",
                    "CITY": "Test City",
                    "STNAME": "California",
                    "STALP": "CA",
                    "ACTIVE": 1,
                    "ASSET": 50000,
                    "RSSD": "987654"
                },
                {
                    "CERT": "67890",
                    "NAME": "Another Test Bank",
                    "CITY": "Another City",
                    "STNAME": "Texas", 
                    "STALP": "TX",
                    "ACTIVE": 1,
                    "ASSET": 25000,
                    "RSSD": "123456"
                }
            ],
            "meta": {
                "total": 2
            }
        }
        
        with aioresponses() as mock_http:
            mock_http.get(
                f'{FDIC_API_BASE_URL}/institutions',
                payload=mock_response_data,
                status=200
            )
            
            result = await client.search_institutions(
                name="Test Bank",
                state="CA",
                active_only=True,
                limit=10
            )
            
            assert result.success == True
            assert len(result.institutions) == 2
            
            # Check first institution
            first_institution = result.institutions[0]
            assert first_institution.name == "Test Bank, National Association"
            assert first_institution.cert == "12345"
            assert first_institution.city == "Test City"
            assert first_institution.stalp == "CA"
            assert first_institution.active == True
            assert first_institution.asset == Decimal("50000")
            assert first_institution.rssd == "987654"
            
            # Check second institution
            second_institution = result.institutions[1]
            assert second_institution.name == "Another Test Bank"
            assert second_institution.cert == "67890"
    
    @pytest.mark.asyncio
    async def test_search_institutions_with_api_key(self, client):
        """Test that API key is included in requests when provided."""
        mock_response_data = {"data": []}
        
        with aioresponses() as mock_http:
            mock_http.get(
                f'{FDIC_API_BASE_URL}/institutions',
                payload=mock_response_data,
                status=200
            )
            
            await client.search_institutions(name="Test Bank")
            
            # Verify the request was made with API key parameter
            requests = mock_http.requests
            assert len(requests) == 1
            
            request = requests[('GET', f'{FDIC_API_BASE_URL}/institutions')]
            assert 'api_key=test_api_key' in str(request[0].url)
    
    @pytest.mark.asyncio
    async def test_search_institutions_without_api_key(self, client_no_key):
        """Test requests work without API key."""
        mock_response_data = {"data": []}
        
        with aioresponses() as mock_http:
            mock_http.get(
                f'{FDIC_API_BASE_URL}/institutions',
                payload=mock_response_data,
                status=200
            )
            
            result = await client_no_key.search_institutions(name="Test Bank")
            
            assert result.success == True
            
            # Verify no API key was sent
            requests = mock_http.requests
            assert len(requests) == 1
            
            request = requests[('GET', f'{FDIC_API_BASE_URL}/institutions')]
            assert 'api_key' not in str(request[0].url)
    
    @pytest.mark.asyncio
    async def test_fdic_error_handling_400(self, client):
        """Test handling of 400 Bad Request errors."""
        with aioresponses() as mock_http:
            mock_http.get(
                f'{FDIC_API_BASE_URL}/institutions',
                status=400,
                payload={"error": "Invalid parameters"}
            )
            
            result = await client.search_institutions(name="Test")
            
            assert result.success == False
            assert "Invalid FDIC API request parameters" in result.error_message
    
    @pytest.mark.asyncio
    async def test_fdic_error_handling_401(self, client):
        """Test handling of 401 Unauthorized errors."""
        with aioresponses() as mock_http:
            mock_http.get(
                f'{FDIC_API_BASE_URL}/institutions',
                status=401
            )
            
            result = await client.search_institutions(name="Test")
            
            assert result.success == False
            assert "FDIC API authentication failed" in result.error_message
    
    @pytest.mark.asyncio
    async def test_fdic_error_handling_429(self, client):
        """Test handling of 429 Rate Limit errors."""
        with aioresponses() as mock_http:
            mock_http.get(
                f'{FDIC_API_BASE_URL}/institutions',
                status=429
            )
            
            result = await client.search_institutions(name="Test")
            
            assert result.success == False
            assert "rate limit exceeded" in result.error_message
    
    @pytest.mark.asyncio
    async def test_fdic_error_handling_500(self, client):
        """Test handling of 500 Server Error."""
        with aioresponses() as mock_http:
            mock_http.get(
                f'{FDIC_API_BASE_URL}/institutions',
                status=500
            )
            
            result = await client.search_institutions(name="Test")
            
            assert result.success == False
            assert "server error" in result.error_message.lower()
    
    @pytest.mark.asyncio
    async def test_search_with_multiple_filters(self, client):
        """Test search with multiple filter parameters."""
        mock_response_data = {"data": []}
        
        with aioresponses() as mock_http:
            mock_http.get(
                f'{FDIC_API_BASE_URL}/institutions',
                payload=mock_response_data,
                status=200
            )
            
            result = await client.search_institutions(
                name="Community Bank",
                city="Chicago",
                county="Cook County", 
                state="IL",
                active_only=True,
                limit=5
            )
            
            assert result.success == True
            
            # Verify query parameters were built correctly
            requests = mock_http.requests
            request = requests[('GET', f'{FDIC_API_BASE_URL}/institutions')]
            query_string = str(request[0].url.query_string)
            
            # Check that filters were properly formatted
            assert 'search=NAME%3A%22Community+Bank%22' in query_string or 'NAME:"Community Bank"' in str(request[0].url)
            assert 'filters=' in query_string
            assert 'ACTIVE:1' in str(request[0].url)
    
    @pytest.mark.asyncio
    async def test_get_institution_by_cert(self, client):
        """Test getting specific institution by certificate number."""
        mock_response_data = {
            "data": [{
                "CERT": "12345",
                "NAME": "Test Bank",
                "CITY": "Test City",
                "ACTIVE": 1
            }]
        }
        
        with aioresponses() as mock_http:
            mock_http.get(
                f'{FDIC_API_BASE_URL}/institutions',
                payload=mock_response_data,
                status=200
            )
            
            result = await client.get_institution_by_cert("12345")
            
            assert result.success == True
            assert len(result.institutions) == 1
            assert result.institutions[0].cert == "12345"
            assert result.institutions[0].name == "Test Bank"
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, client):
        """Test successful health check."""
        mock_response_data = {"data": []}
        
        with aioresponses() as mock_http:
            mock_http.get(
                f'{FDIC_API_BASE_URL}/institutions',
                payload=mock_response_data,
                status=200
            )
            
            result = await client.health_check()
            
            assert result == True
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self, client):
        """Test health check failure."""
        with aioresponses() as mock_http:
            mock_http.get(
                f'{FDIC_API_BASE_URL}/institutions',
                status=500
            )
            
            result = await client.health_check()
            
            assert result == False
    
    @pytest.mark.asyncio
    async def test_caching_functionality(self, client):
        """Test that responses are properly cached."""
        mock_response_data = {
            "data": [{
                "CERT": "12345",
                "NAME": "Cached Test Bank",
                "ACTIVE": 1
            }]
        }
        
        with aioresponses() as mock_http:
            # Set up mock to return response only once
            mock_http.get(
                f'{FDIC_API_BASE_URL}/institutions',
                payload=mock_response_data,
                status=200
            )
            
            # First request - should hit API
            result1 = await client.search_institutions(name="Test Bank")
            assert result1.success == True
            assert result1.institutions[0].name == "Cached Test Bank"
            
            # Second identical request - should hit cache (no additional HTTP call)
            result2 = await client.search_institutions(name="Test Bank")
            assert result2.success == True
            assert result2.institutions[0].name == "Cached Test Bank"
            
            # Verify only one HTTP request was made
            assert len(mock_http.requests) == 1
    
    @pytest.mark.asyncio
    async def test_invalid_json_response(self, client):
        """Test handling of invalid JSON responses."""
        with aioresponses() as mock_http:
            mock_http.get(
                f'{FDIC_API_BASE_URL}/institutions',
                body="Invalid JSON response",
                status=200,
                content_type='text/plain'
            )
            
            result = await client.search_institutions(name="Test")
            
            assert result.success == False
            assert "invalid JSON" in result.error_message
    
    @pytest.mark.asyncio
    async def test_network_timeout(self):
        """Test handling of network timeouts."""
        client = FDICAPIClient(api_key="test", timeout=0.001)  # Very short timeout
        
        with aioresponses() as mock_http:
            # Simulate slow response that will timeout
            async def slow_callback(url, **kwargs):
                await asyncio.sleep(0.1)  # Longer than timeout
                return aioresponses.CallbackResult(
                    status=200,
                    payload={"data": []}
                )
            
            mock_http.get(
                f'{FDIC_API_BASE_URL}/institutions',
                callback=slow_callback
            )
            
            result = await client.search_institutions(name="Test")
            
            # Should handle timeout gracefully
            assert result.success == False
            assert "timeout" in result.error_message.lower() or "failed" in result.error_message.lower()
    
    def test_cache_stats(self, client):
        """Test cache statistics reporting."""
        stats = client.get_cache_stats()
        
        assert "total_entries" in stats
        assert "expired_entries" in stats
        assert "active_entries" in stats
        assert "max_entries" in stats
        
        assert stats["total_entries"] >= 0
        assert stats["max_entries"] > 0
    
    def test_clear_cache(self, client):
        """Test cache clearing functionality."""
        # Cache should be empty initially
        stats_before = client.get_cache_stats()
        assert stats_before["total_entries"] == 0
        
        # Clear cache (should not error even when empty)
        client.clear_cache()
        
        stats_after = client.get_cache_stats()
        assert stats_after["total_entries"] == 0


if __name__ == "__main__":
    pytest.main([__file__])