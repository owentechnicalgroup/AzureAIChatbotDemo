"""
Integration test for real FDIC API with fixed data structure mapping.

Tests the FDIC API client with actual API calls to verify
the fixed data structure mapping works correctly.
"""

import asyncio
import pytest
import sys
from pathlib import Path

# Add src directory to path for imports
test_dir = Path(__file__).parent
src_dir = test_dir.parent.parent.parent / "src"
sys.path.insert(0, str(src_dir))

from tools.infrastructure.banking.fdic_api_client import FDICAPIClient


class TestRealFDICAPI:
    """Integration tests with real FDIC API calls."""
    
    @pytest.mark.asyncio
    async def test_fdic_api_health_check(self):
        """Test FDIC API health check."""
        client = FDICAPIClient()
        
        # Test health check
        is_healthy = await client.health_check()
        assert isinstance(is_healthy, bool)
        print(f"FDIC API Health: {'Healthy' if is_healthy else 'Not Available'}")
    
    @pytest.mark.asyncio 
    async def test_fdic_api_search_wells_fargo(self):
        """Test FDIC API search for Wells Fargo with fixed data mapping."""
        client = FDICAPIClient()
        
        # Search for Wells Fargo banks
        response = await client.search_institutions(
            name="Wells Fargo",
            limit=3
        )
        
        print(f"Response success: {response.success}")
        if response.error_message:
            print(f"Error message: {response.error_message}")
        
        if response.success:
            print(f"Found {len(response.institutions)} institutions")
            
            for i, institution in enumerate(response.institutions):
                print(f"\nInstitution {i+1}:")
                print(f"  Name: {institution.name}")
                print(f"  CERT: {institution.cert}")
                print(f"  City: {institution.city}")
                print(f"  State: {institution.stalp}")
                print(f"  Active: {institution.active}")
                
                # Verify the institution model is properly constructed
                assert institution.name is not None
                assert len(institution.name) > 0
                
                # If cert is provided, should be numeric string
                if institution.cert:
                    assert institution.cert.isdigit()
                
                # State should be 2-character code if provided
                if institution.stalp:
                    assert len(institution.stalp) == 2
                    assert institution.stalp.isupper()
        
        # Verify response structure
        assert hasattr(response, 'success')
        assert hasattr(response, 'institutions')
        assert hasattr(response, 'timestamp')
    
    @pytest.mark.asyncio
    async def test_fdic_api_search_by_location(self):
        """Test FDIC API search by city and state."""
        client = FDICAPIClient()
        
        # Search for banks in San Francisco, CA
        response = await client.search_institutions(
            city="San Francisco",
            state="CA",
            limit=2
        )
        
        print(f"Location search success: {response.success}")
        
        if response.success and response.institutions:
            print(f"Found {len(response.institutions)} institutions in San Francisco, CA")
            
            for institution in response.institutions:
                print(f"  {institution.name} - {institution.city}, {institution.stalp}")
                
                # Verify location matches
                if institution.city:
                    assert "san francisco" in institution.city.lower()
                if institution.stalp:
                    assert institution.stalp == "CA"


if __name__ == "__main__":
    # Run tests directly
    asyncio.run(TestRealFDICAPI().test_fdic_api_health_check())
    asyncio.run(TestRealFDICAPI().test_fdic_api_search_wells_fargo())
    asyncio.run(TestRealFDICAPI().test_fdic_api_search_by_location())
    print("All integration tests completed!")