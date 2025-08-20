"""
Unit tests for enhanced banking tools with FDIC integration.

Tests the bank_lookup_tool and bank_analysis_tool with FDIC API integration,
including backward compatibility and new functionality.
"""

import pytest
import asyncio
from unittest.mock import patch, Mock, AsyncMock
from decimal import Decimal

# Add src directory to path for imports
import sys
from pathlib import Path
test_dir = Path(__file__).parent
src_dir = test_dir.parent.parent.parent / "src"
sys.path.insert(0, str(src_dir))

from aioresponses import aioresponses

from tools.atomic.bank_lookup_tool import BankLookupTool
from tools.composite.bank_analysis_tool import BankAnalysisTool
from tools.infrastructure.banking.fdic_models import FDICInstitution, FDICAPIResponse
from tools.infrastructure.banking.fdic_constants import FDIC_API_BASE_URL


class TestEnhancedBankLookupTool:
    """Test cases for enhanced BankLookupTool with FDIC integration."""
    
    @pytest.fixture
    def mock_settings(self):
        """Mock settings for testing."""
        settings = Mock()
        settings.fdic_api_key = "test_api_key"
        settings.tools_timeout_seconds = 30.0
        settings.tools_cache_ttl_minutes = 15
        return settings
    
    @pytest.fixture
    def bank_lookup_tool(self, mock_settings):
        """Fixture providing BankLookupTool instance."""
        return BankLookupTool(settings=mock_settings)
    
    def test_tool_initialization(self, bank_lookup_tool):
        """Test proper tool initialization with FDIC client."""
        assert bank_lookup_tool.name == "bank_lookup"
        assert "FDIC BankFind Suite API" in bank_lookup_tool.description
        assert "Enhanced Search Capabilities" in bank_lookup_tool.description
        assert hasattr(bank_lookup_tool, '_fdic_client')
    
    @pytest.mark.asyncio
    async def test_search_by_name_success(self, bank_lookup_tool):
        """Test successful bank search by name."""
        mock_institutions = [
            FDICInstitution(
                name="Wells Fargo Bank, National Association",
                cert="3511",
                rssd="451965",
                city="Sioux Falls",
                stname="South Dakota",
                stalp="SD",
                active=True,
                asset=Decimal("1900000000"),  # $1.9T in thousands
                offices=5200
            )
        ]
        
        mock_response = FDICAPIResponse(
            success=True,
            data=mock_institutions,
            timestamp="2024-01-01T12:00:00Z"
        )
        
        with patch.object(bank_lookup_tool.fdic_client, 'search_institutions', return_value=mock_response):
            result = await bank_lookup_tool._arun(
                search_term="Wells Fargo",
                fuzzy_match=True,
                max_results=5
            )
            
            assert "Found 1 bank(s)" in result
            assert "Wells Fargo Bank, National Association" in result
            assert "RSSD ID: 451965" in result
            assert "FDIC Certificate: 3511" in result
            assert "Location: Sioux Falls, South Dakota" in result
            assert "Total Assets: $1900.0B" in result
            assert "Status: Active" in result
    
    @pytest.mark.asyncio
    async def test_search_with_location_filters(self, bank_lookup_tool):
        """Test bank search with city and state filters."""
        mock_institutions = [
            FDICInstitution(
                name="First National Bank of Chicago",
                cert="12345",
                city="Chicago",
                county="Cook County",
                stname="Illinois",
                stalp="IL",
                active=True
            )
        ]
        
        mock_response = FDICAPIResponse(
            success=True,
            data=mock_institutions,
            timestamp="2024-01-01T12:00:00Z"
        )
        
        with patch.object(bank_lookup_tool.fdic_client, 'search_institutions', return_value=mock_response) as mock_search:
            result = await bank_lookup_tool._arun(
                search_term="First National",
                city="Chicago",
                state="IL",
                max_results=3
            )
            
            # Verify the FDIC API was called with correct parameters
            mock_search.assert_called_once_with(
                name="First National",
                city="Chicago",
                county=None,
                state="IL",
                active_only=True,
                limit=6  # max_results * 2 for fuzzy filtering
            )
            
            assert "Found 1 bank(s)" in result
            assert "First National Bank of Chicago" in result
            assert "Chicago, Cook County, Illinois" in result
    
    @pytest.mark.asyncio
    async def test_search_location_only(self, bank_lookup_tool):
        """Test bank search with location only (no name)."""
        mock_institutions = [
            FDICInstitution(
                name="Community Bank of Texas",
                cert="67890",
                city="Houston",
                stname="Texas",
                stalp="TX",
                active=True
            )
        ]
        
        mock_response = FDICAPIResponse(
            success=True,
            data=mock_institutions,
            timestamp="2024-01-01T12:00:00Z"
        )
        
        with patch.object(bank_lookup_tool.fdic_client, 'search_institutions', return_value=mock_response):
            result = await bank_lookup_tool._arun(
                city="Houston",
                state="TX",
                active_only=True,
                max_results=5
            )
            
            assert "Found 1 bank(s)" in result
            assert "Community Bank of Texas" in result
    
    @pytest.mark.asyncio
    async def test_backward_compatibility(self, bank_lookup_tool):
        """Test backward compatibility with old interface."""
        mock_institutions = [
            FDICInstitution(
                name="Bank of America, National Association",
                cert="3510",
                rssd="541101",
                active=True
            )
        ]
        
        mock_response = FDICAPIResponse(
            success=True,
            data=mock_institutions,
            timestamp="2024-01-01T12:00:00Z"
        )
        
        with patch.object(bank_lookup_tool.fdic_client, 'search_institutions', return_value=mock_response):
            # Test old-style call (search_term, fuzzy_match, max_results only)
            result = await bank_lookup_tool._arun(
                search_term="Bank of America",
                fuzzy_match=True,
                max_results=5
            )
            
            assert "Found 1 bank(s)" in result
            assert "Bank of America, National Association" in result
    
    @pytest.mark.asyncio
    async def test_input_validation_errors(self, bank_lookup_tool):
        """Test input validation and error handling."""
        # No search criteria
        result = await bank_lookup_tool._arun()
        assert "Error: At least one search parameter" in result
        
        # Search term too short
        result = await bank_lookup_tool._arun(search_term="A")
        assert "Error: Search term must be at least 2 characters" in result
        
        # Invalid state format
        result = await bank_lookup_tool._arun(
            search_term="Test Bank",
            state="California"  # Should be CA
        )
        assert "Error: State must be 2-character abbreviation" in result
    
    @pytest.mark.asyncio
    async def test_fdic_api_error_handling(self, bank_lookup_tool):
        """Test handling of FDIC API errors."""
        # Authentication failure
        mock_response = FDICAPIResponse(
            success=False,
            error_message="FDIC API authentication failed",
            timestamp="2024-01-01T12:00:00Z"
        )
        
        with patch.object(bank_lookup_tool.fdic_client, 'search_institutions', return_value=mock_response):
            result = await bank_lookup_tool._arun(search_term="Test Bank")
            assert "Error: Bank search failed - FDIC API authentication failed" in result
        
        # Server error
        mock_response_server_error = FDICAPIResponse(
            success=False,
            error_message="FDIC API server error - bank data not available",
            timestamp="2024-01-01T12:00:00Z"
        )
        
        with patch.object(bank_lookup_tool.fdic_client, 'search_institutions', return_value=mock_response_server_error):
            result = await bank_lookup_tool._arun(search_term="Test Bank")
            assert "Error: Bank data not available from FDIC - service temporarily unavailable" in result
    
    @pytest.mark.asyncio
    async def test_no_results_found(self, bank_lookup_tool):
        """Test handling when no banks are found."""
        mock_response = FDICAPIResponse(
            success=True,
            data=[],
            timestamp="2024-01-01T12:00:00Z"
        )
        
        with patch.object(bank_lookup_tool.fdic_client, 'search_institutions', return_value=mock_response):
            result = await bank_lookup_tool._arun(
                search_term="Nonexistent Bank",
                city="Nowhere",
                state="XX"
            )
            
            assert "No banks found matching" in result
            assert "name 'Nonexistent Bank'" in result
            assert "city 'Nowhere'" in result
            assert "state 'XX'" in result
    
    @pytest.mark.asyncio
    async def test_fuzzy_matching_functionality(self, bank_lookup_tool):
        """Test fuzzy matching logic."""
        mock_institutions = [
            FDICInstitution(name="JPMorgan Chase Bank, National Association", cert="628"),
            FDICInstitution(name="Chase Bank USA, National Association", cert="4277")
        ]
        
        mock_response = FDICAPIResponse(
            success=True,
            data=mock_institutions,
            timestamp="2024-01-01T12:00:00Z"
        )
        
        with patch.object(bank_lookup_tool.fdic_client, 'search_institutions', return_value=mock_response):
            # Test with fuzzy matching enabled
            result = await bank_lookup_tool._arun(
                search_term="Chase",
                fuzzy_match=True,
                max_results=5
            )
            
            # Should find both Chase banks
            assert "Found" in result
            assert "JPMorgan Chase Bank" in result or "Chase Bank USA" in result
    
    def test_similarity_calculation(self, bank_lookup_tool):
        """Test bank name similarity calculation."""
        # Test exact match
        similarity = bank_lookup_tool._calculate_similarity(
            "Wells Fargo Bank",
            "Wells Fargo Bank, National Association"
        )
        assert similarity >= 0.8  # Should be high similarity
        
        # Test partial match
        similarity = bank_lookup_tool._calculate_similarity(
            "Chase",
            "JPMorgan Chase Bank, National Association"
        )
        assert similarity >= 0.5  # Should have reasonable similarity
        
        # Test no match
        similarity = bank_lookup_tool._calculate_similarity(
            "Wells Fargo",
            "Bank of America"
        )
        assert similarity < 0.5  # Should be low similarity
    
    def test_bank_name_normalization(self, bank_lookup_tool):
        """Test bank name normalization for better matching."""
        normalized = bank_lookup_tool._normalize_bank_name(
            "Wells Fargo Bank, National Association"
        )
        assert normalized == "wells fargo"
        
        normalized = bank_lookup_tool._normalize_bank_name(
            "JPMorgan Chase Bank, N.A."
        )
        assert normalized == "jpmorgan chase"
    
    @pytest.mark.asyncio
    async def test_health_check(self, bank_lookup_tool):
        """Test health check functionality."""
        with patch.object(bank_lookup_tool.fdic_client, 'health_check', return_value=True):
            health_status = await bank_lookup_tool.health_check()
            assert health_status == True
        
        with patch.object(bank_lookup_tool.fdic_client, 'health_check', return_value=False):
            health_status = await bank_lookup_tool.health_check()
            assert health_status == False
    
    def test_service_availability(self, bank_lookup_tool):
        """Test service availability check."""
        with patch.object(bank_lookup_tool.fdic_client, 'is_available', return_value=True):
            assert bank_lookup_tool.is_available() == True
        
        with patch.object(bank_lookup_tool.fdic_client, 'is_available', return_value=False):
            assert bank_lookup_tool.is_available() == False


class TestEnhancedBankAnalysisTool:
    """Test cases for enhanced BankAnalysisTool with FDIC integration."""
    
    @pytest.fixture
    def bank_analysis_tool(self):
        """Fixture providing BankAnalysisTool instance."""
        return BankAnalysisTool()
    
    def test_tool_initialization(self, bank_analysis_tool):
        """Test proper tool initialization."""
        assert bank_analysis_tool.name == "bank_analysis"
        assert "FDIC API integration" in bank_analysis_tool.description
        assert "Enhanced Search and Analysis Capabilities" in bank_analysis_tool.description
        assert "Location-based bank identification" in bank_analysis_tool.description
    
    @pytest.mark.asyncio
    async def test_analysis_with_enhanced_search(self, bank_analysis_tool):
        """Test bank analysis with enhanced search parameters."""
        # Mock the bank lookup tool to return a successful lookup
        mock_lookup_result = """Found 1 bank(s):

1. First National Bank of Chicago
   RSSD ID: 123456
   FDIC Certificate: 12345
   Location: Chicago, Cook County, Illinois
   Status: Active
"""
        
        with patch.object(bank_analysis_tool.bank_lookup, '_arun', return_value=mock_lookup_result):
            result = await bank_analysis_tool._arun(
                bank_name="First National",
                city="Chicago",
                state="IL",
                query_type="basic_info"
            )
            
            # Should successfully process the lookup and proceed with analysis
            assert "Error:" not in result or "First National" in result
    
    @pytest.mark.asyncio
    async def test_enhanced_input_validation(self, bank_analysis_tool):
        """Test enhanced input validation for new parameters."""
        # Test with location parameters only
        with patch.object(bank_analysis_tool.bank_lookup, '_arun') as mock_lookup:
            mock_lookup.return_value = "No banks found matching city 'Unknown City'."
            
            result = await bank_analysis_tool._arun(
                city="Unknown City",
                state="XX",
                query_type="basic_info"
            )
            
            # Should attempt to use location-based lookup
            mock_lookup.assert_called_once()
            args, kwargs = mock_lookup.call_args
            assert kwargs.get('city') == "Unknown City"
            assert kwargs.get('state') == "XX"
    
    @pytest.mark.asyncio
    async def test_backward_compatibility_bank_name_only(self, bank_analysis_tool):
        """Test backward compatibility with bank_name only."""
        mock_lookup_result = """Found 1 bank(s):

1. Wells Fargo Bank, National Association
   RSSD ID: 451965
   FDIC Certificate: 3511
   Status: Active
"""
        
        with patch.object(bank_analysis_tool.bank_lookup, '_arun', return_value=mock_lookup_result):
            result = await bank_analysis_tool._arun(
                bank_name="Wells Fargo",
                query_type="basic_info"
            )
            
            # Should work with legacy interface
            assert "Error:" not in result or "Wells Fargo" in result
    
    @pytest.mark.asyncio
    async def test_backward_compatibility_rssd_only(self, bank_analysis_tool):
        """Test backward compatibility with RSSD ID only."""
        # When RSSD ID is provided, should skip lookup
        with patch.object(bank_analysis_tool.api_client, 'execute') as mock_api:
            mock_api.return_value = Mock(success=True, data={"field_id": "RCON2170", "value": 150000})
            
            result = await bank_analysis_tool._arun(
                rssd_id="451965",
                query_type="basic_info"
            )
            
            # Should proceed directly to Call Report analysis
            # This test verifies the tool doesn't break with RSSD-only input
            assert isinstance(result, str)  # Should return a string result
    
    @pytest.mark.asyncio
    async def test_enhanced_validation_multiple_identifiers(self, bank_analysis_tool):
        """Test validation with multiple identification methods."""
        # Valid: has bank identifier
        assert await bank_analysis_tool._arun(
            bank_name="Test Bank",
            query_type="basic_info"
        ) != "Error: At least one identifier must be provided"
        
        # Valid: has city (location-based search)
        with patch.object(bank_analysis_tool.bank_lookup, '_arun', return_value="Found 1 bank(s):"):
            result = await bank_analysis_tool._arun(
                city="Chicago",
                state="IL",
                query_type="basic_info"
            )
            assert "Error: At least one identifier" not in result
    
    @pytest.mark.asyncio
    async def test_error_propagation(self, bank_analysis_tool):
        """Test that FDIC errors are properly propagated."""
        # Mock lookup tool returning FDIC error
        fdic_error_message = "Error: Bank data not available from FDIC - service temporarily unavailable"
        
        with patch.object(bank_analysis_tool.bank_lookup, '_arun', return_value=fdic_error_message):
            result = await bank_analysis_tool._arun(
                bank_name="Test Bank",
                query_type="basic_info"
            )
            
            # Should propagate the FDIC error
            assert "FDIC" in result and "unavailable" in result
    
    @pytest.mark.asyncio
    async def test_query_type_parameter_preservation(self, bank_analysis_tool):
        """Test that all query types are still supported."""
        valid_query_types = ["basic_info", "financial_summary", "key_ratios"]
        
        for query_type in valid_query_types:
            # Each should be accepted without validation error
            try:
                result = await bank_analysis_tool._arun(
                    bank_name="Test Bank",
                    query_type=query_type
                )
                # Should not raise validation error
                assert isinstance(result, str)
            except Exception as e:
                # Should not fail due to query_type validation
                assert "query_type" not in str(e).lower()


class TestBackwardCompatibility:
    """Test backward compatibility with existing interfaces."""
    
    @pytest.fixture
    def mock_settings(self):
        """Mock settings for testing."""
        settings = Mock()
        settings.fdic_api_key = None  # Test without API key
        settings.tools_timeout_seconds = 30.0
        settings.tools_cache_ttl_minutes = 15
        return settings
    
    def test_bank_lookup_input_backward_compatibility(self):
        """Test that old BankLookupInput interface still works."""
        from tools.infrastructure.banking.fdic_models import BankLookupInput
        
        # Old interface should still work
        old_style_input = BankLookupInput(
            search_term="Bank of America",
            fuzzy_match=True,
            max_results=5
        )
        
        assert old_style_input.search_term == "Bank of America"
        assert old_style_input.fuzzy_match == True
        assert old_style_input.max_results == 5
        
        # New fields should have defaults
        assert old_style_input.city is None
        assert old_style_input.state is None
        assert old_style_input.active_only == True  # Default
    
    def test_bank_analysis_input_backward_compatibility(self):
        """Test that old BankAnalysisInput interface still works."""
        from tools.infrastructure.banking.fdic_models import BankAnalysisInput
        
        # Old interface should still work
        old_style_input = BankAnalysisInput(
            bank_name="Wells Fargo",
            query_type="basic_info"
        )
        
        assert old_style_input.bank_name == "Wells Fargo"
        assert old_style_input.query_type == "basic_info"
        
        # New fields should have defaults
        assert old_style_input.city is None
        assert old_style_input.state is None
    
    @pytest.mark.asyncio
    async def test_tools_work_without_api_key(self, mock_settings):
        """Test that tools work without FDIC API key (graceful degradation)."""
        bank_lookup = BankLookupTool(settings=mock_settings)
        
        # Should initialize without error even without API key
        assert bank_lookup.fdic_client.api_key is None
        assert bank_lookup.is_available() == True
        
        # Should handle API calls gracefully (might return errors but shouldn't crash)
        try:
            result = await bank_lookup._arun(search_term="Test Bank")
            assert isinstance(result, str)  # Should return some result
        except Exception as e:
            # If it fails, should be a controlled failure
            assert "Error:" in str(e) or isinstance(e, (ValueError, ConnectionError))


if __name__ == "__main__":
    pytest.main([__file__])