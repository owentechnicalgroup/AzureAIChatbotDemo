"""
Unit tests for FDIC data models and validation.

Tests Pydantic model validation, field mappings, and data processing
for FDIC BankFind Suite API data structures.
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Any

# Add src directory to path for imports
import sys
from pathlib import Path
test_dir = Path(__file__).parent
src_dir = test_dir.parent.parent.parent / "src"
sys.path.insert(0, str(src_dir))

from pydantic import ValidationError

from tools.infrastructure.banking.fdic_models import (
    FDICInstitution,
    FDICSearchFilters,
    FDICAPIResponse,
    FDICCacheEntry,
    BankLookupInput,
    BankAnalysisInput
)


class TestFDICInstitution:
    """Test cases for FDICInstitution model validation and processing."""
    
    def test_fdic_institution_valid_data(self):
        """Test FDICInstitution creation with valid data."""
        institution = FDICInstitution(
            cert="12345",
            name="Test Bank, National Association",
            rssd="987654",
            city="Test City",
            county="Test County",
            stname="California", 
            stalp="CA",
            zip="90210",
            active=True,
            charter_type="National Bank",
            asset=Decimal("150000"),
            dep=Decimal("125000"),
            offices=25,
            open_date="2020-01-15",
            cert_date="2020-01-01"
        )
        
        assert institution.cert == "12345"
        assert institution.name == "Test Bank, National Association"
        assert institution.rssd == "987654"
        assert institution.city == "Test City"
        assert institution.stalp == "CA"
        assert institution.active == True
        assert institution.asset == Decimal("150000")
        assert institution.dep == Decimal("125000")
        assert institution.offices == 25
    
    def test_fdic_institution_minimal_data(self):
        """Test FDICInstitution with minimal required data."""
        institution = FDICInstitution(
            name="Minimal Test Bank"
        )
        
        assert institution.name == "Minimal Test Bank"
        assert institution.cert is None
        assert institution.rssd is None
        assert institution.active is None
    
    def test_fdic_institution_cert_validation(self):
        """Test FDIC certificate number validation."""
        # Valid cert number
        institution = FDICInstitution(name="Test Bank", cert="12345")
        assert institution.cert == "12345"
        
        # Invalid cert number (non-numeric)
        with pytest.raises(ValidationError) as exc_info:
            FDICInstitution(name="Test Bank", cert="ABC123")
        assert "must contain only digits" in str(exc_info.value)
        
        # Cert number too long
        with pytest.raises(ValidationError) as exc_info:
            FDICInstitution(name="Test Bank", cert="12345678901")
        assert ("too long" in str(exc_info.value) or "at most 10 characters" in str(exc_info.value))
    
    def test_fdic_institution_rssd_validation(self):
        """Test RSSD ID validation."""
        # Valid RSSD
        institution = FDICInstitution(name="Test Bank", rssd="451965")
        assert institution.rssd == "451965"
        
        # Invalid RSSD (non-numeric)
        with pytest.raises(ValidationError) as exc_info:
            FDICInstitution(name="Test Bank", rssd="ABC123")
        assert "must contain only digits" in str(exc_info.value)
    
    def test_fdic_institution_state_validation(self):
        """Test state abbreviation validation."""
        # Valid state
        institution = FDICInstitution(name="Test Bank", stalp="CA")
        assert institution.stalp == "CA"
        
        # Invalid state length
        with pytest.raises(ValidationError) as exc_info:
            FDICInstitution(name="Test Bank", stalp="CAL")
        assert "exactly 2 characters" in str(exc_info.value)
        
        # State should be uppercase
        institution = FDICInstitution(name="Test Bank", stalp="ca")
        assert institution.stalp == "CA"
    
    def test_fdic_institution_financial_validation(self):
        """Test financial amount validation and conversion."""
        # Valid amounts
        institution = FDICInstitution(
            name="Test Bank",
            asset="150000.50",
            dep=125000
        )
        assert institution.asset == Decimal("150000.50")
        assert institution.dep == Decimal("125000")
        
        # Test string conversion with formatting
        institution = FDICInstitution(
            name="Test Bank",
            asset="$150,000.50",
            dep="125,000"
        )
        assert institution.asset == Decimal("150000.50")
        assert institution.dep == Decimal("125000")
        
        # Invalid financial amount
        with pytest.raises(ValidationError) as exc_info:
            FDICInstitution(name="Test Bank", asset="not_a_number")
        assert "Invalid financial amount" in str(exc_info.value)
    
    def test_fdic_institution_offices_validation(self):
        """Test number of offices validation."""
        # Valid number of offices
        institution = FDICInstitution(name="Test Bank", offices=150)
        assert institution.offices == 150
        
        # Negative offices should fail
        with pytest.raises(ValidationError) as exc_info:
            FDICInstitution(name="Test Bank", offices=-5)
        assert "cannot be negative" in str(exc_info.value)


class TestFDICSearchFilters:
    """Test cases for FDICSearchFilters model and query generation."""
    
    def test_search_filters_creation(self):
        """Test FDICSearchFilters creation with various parameters."""
        filters = FDICSearchFilters(
            name="Wells Fargo",
            city="San Francisco",
            county="San Francisco County",
            state="CA",
            active_only=True,
            limit=10
        )
        
        assert filters.name == "Wells Fargo"
        assert filters.city == "San Francisco"
        assert filters.county == "San Francisco County"
        assert filters.state == "CA"
        assert filters.active_only == True
        assert filters.limit == 10
    
    def test_search_filters_state_validation(self):
        """Test state abbreviation validation in filters."""
        # Valid state
        filters = FDICSearchFilters(state="TX")
        assert filters.state == "TX"
        
        # Invalid state length
        with pytest.raises(ValidationError) as exc_info:
            FDICSearchFilters(state="Texas")
        assert "2-character abbreviation" in str(exc_info.value)
        
        # Lowercase should be converted to uppercase
        filters = FDICSearchFilters(state="ny")
        assert filters.state == "NY"
    
    def test_search_filters_limit_validation(self):
        """Test limit parameter validation."""
        # Valid limits
        filters = FDICSearchFilters(limit=50)
        assert filters.limit == 50
        
        # Limit too low
        with pytest.raises(ValidationError) as exc_info:
            FDICSearchFilters(limit=0)
        
        # Limit too high
        with pytest.raises(ValidationError) as exc_info:
            FDICSearchFilters(limit=15000)
    
    def test_to_fdic_query_conversion(self):
        """Test conversion of filters to FDIC API query parameters."""
        filters = FDICSearchFilters(
            name="Test Bank",
            city="Chicago",
            state="IL",
            active_only=True,
            limit=5
        )
        
        query_params = filters.to_fdic_query()
        
        assert "search" in query_params
        assert 'NAME:"Test Bank"' in query_params["search"]
        assert "filters" in query_params
        assert 'CITY:"Chicago"' in query_params["filters"]
        assert 'STALP:IL' in query_params["filters"]
        assert 'ACTIVE:1' in query_params["filters"]
        assert query_params["limit"] == "5"
        assert query_params["format"] == "json"
    
    def test_to_fdic_query_minimal(self):
        """Test query conversion with minimal parameters."""
        filters = FDICSearchFilters(active_only=False)
        
        query_params = filters.to_fdic_query()
        
        # Should not include search or filters for minimal parameters
        assert "search" not in query_params or not query_params["search"]
        assert "filters" not in query_params or not query_params["filters"]
        assert query_params["limit"] == "50"  # default
        assert query_params["format"] == "json"


class TestFDICAPIResponse:
    """Test cases for FDICAPIResponse model and properties."""
    
    def test_api_response_success(self):
        """Test successful API response creation."""
        institutions = [
            FDICInstitution(name="Test Bank 1", cert="12345"),
            FDICInstitution(name="Test Bank 2", cert="67890")
        ]
        
        response = FDICAPIResponse(
            success=True,
            data=institutions,
            meta={"total": 2},
            timestamp=datetime.now().isoformat()
        )
        
        assert response.success == True
        assert len(response.data) == 2
        assert len(response.institutions) == 2
        assert response.total_count == 2
        assert response.is_success() == True
    
    def test_api_response_failure(self):
        """Test failed API response creation."""
        response = FDICAPIResponse(
            success=False,
            data=None,
            error_message="API request failed",
            timestamp=datetime.now().isoformat()
        )
        
        assert response.success == False
        assert response.data is None
        assert len(response.institutions) == 0
        assert response.error_message == "API request failed"
        assert response.is_success() == False
    
    def test_api_response_validation(self):
        """Test validation of API response fields."""
        # Should require error message when success=False
        with pytest.raises(ValidationError) as exc_info:
            FDICAPIResponse(
                success=False,
                data=None,
                timestamp=datetime.now().isoformat()
            )
        assert "Error message required" in str(exc_info.value)
    
    def test_total_count_property(self):
        """Test total_count property calculation."""
        # With meta total
        response = FDICAPIResponse(
            success=True,
            data=[FDICInstitution(name="Test")],
            meta={"total": 100},
            timestamp=datetime.now().isoformat()
        )
        assert response.total_count == 100
        
        # Without meta, should use data length
        response = FDICAPIResponse(
            success=True,
            data=[FDICInstitution(name="Test")],
            timestamp=datetime.now().isoformat()
        )
        assert response.total_count == 1


class TestFDICCacheEntry:
    """Test cases for FDIC cache entry functionality."""
    
    def test_cache_entry_creation(self):
        """Test FDICCacheEntry creation and properties."""
        response = FDICAPIResponse(
            success=True,
            data=[],
            timestamp=datetime.now().isoformat()
        )
        
        now = datetime.now()
        expires_in_hour = now + timedelta(hours=1)
        
        entry = FDICCacheEntry(
            response=response,
            query_hash="test_hash_123",
            cached_at=now,
            expires_at=expires_in_hour
        )
        
        assert entry.response == response
        assert entry.query_hash == "test_hash_123"
        assert entry.cached_at == now
        assert entry.expires_at == expires_in_hour
        assert entry.is_expired() == False
        assert entry.time_to_expiry() > 3500  # Should be close to 1 hour
    
    def test_cache_entry_expiry(self):
        """Test cache entry expiry detection."""
        response = FDICAPIResponse(
            success=True,
            data=[],
            timestamp=datetime.now().isoformat()
        )
        
        # Create expired entry
        past_time = datetime.now() - timedelta(hours=1)
        entry = FDICCacheEntry(
            response=response,
            query_hash="expired_hash",
            cached_at=past_time,
            expires_at=past_time
        )
        
        assert entry.is_expired() == True
        assert entry.time_to_expiry() < 0


class TestBankLookupInput:
    """Test cases for enhanced BankLookupInput model."""
    
    def test_bank_lookup_input_creation(self):
        """Test BankLookupInput creation with all parameters."""
        input_data = BankLookupInput(
            search_term="Wells Fargo",
            city="San Francisco",
            county="San Francisco County",
            state="CA",
            active_only=True,
            fuzzy_match=True,
            max_results=10
        )
        
        assert input_data.search_term == "Wells Fargo"
        assert input_data.city == "San Francisco"
        assert input_data.county == "San Francisco County"
        assert input_data.state == "CA"
        assert input_data.active_only == True
        assert input_data.fuzzy_match == True
        assert input_data.max_results == 10
    
    def test_bank_lookup_input_validation(self):
        """Test input validation for BankLookupInput."""
        # Valid state
        input_data = BankLookupInput(state="TX")
        assert input_data.state == "TX"
        
        # Invalid state
        with pytest.raises(ValidationError) as exc_info:
            BankLookupInput(state="Texas")
        assert "2-character abbreviation" in str(exc_info.value)
        
        # Max results bounds
        with pytest.raises(ValidationError):
            BankLookupInput(max_results=0)
        
        with pytest.raises(ValidationError):
            BankLookupInput(max_results=100)
    
    def test_bank_lookup_input_search_term_validation(self):
        """Test search term validation and cleaning."""
        # Clean search term
        input_data = BankLookupInput(search_term="  Wells Fargo Bank  ")
        assert input_data.search_term == "Wells Fargo Bank"
        
        # Invalid characters should fail
        with pytest.raises(ValidationError) as exc_info:
            BankLookupInput(search_term="Bank <script>alert('test')</script>")
        assert "invalid characters" in str(exc_info.value)
    
    def test_to_fdic_filters_conversion(self):
        """Test conversion to FDICSearchFilters."""
        input_data = BankLookupInput(
            search_term="Community Bank",
            city="Chicago",
            state="IL",
            max_results=5
        )
        
        filters = input_data.to_fdic_filters()
        
        assert filters.name == "Community Bank"
        assert filters.city == "Chicago"
        assert filters.state == "IL"
        assert filters.limit == 10  # max_results * 2 for fuzzy filtering
    
    def test_has_search_criteria(self):
        """Test search criteria validation."""
        # Has criteria
        input_with_criteria = BankLookupInput(search_term="Test Bank")
        assert input_with_criteria.has_search_criteria() == True
        
        input_with_city = BankLookupInput(city="Chicago")
        assert input_with_city.has_search_criteria() == True
        
        # No criteria
        empty_input = BankLookupInput()
        assert empty_input.has_search_criteria() == False


class TestBankAnalysisInput:
    """Test cases for enhanced BankAnalysisInput model."""
    
    def test_bank_analysis_input_creation(self):
        """Test BankAnalysisInput creation with all parameters."""
        input_data = BankAnalysisInput(
            bank_name="JPMorgan Chase",
            rssd_id="480228",
            query_type="financial_summary",
            city="New York",
            state="NY"
        )
        
        assert input_data.bank_name == "JPMorgan Chase"
        assert input_data.rssd_id == "480228"
        assert input_data.query_type == "financial_summary"
        assert input_data.city == "New York"
        assert input_data.state == "NY"
    
    def test_bank_analysis_input_state_validation(self):
        """Test state abbreviation validation."""
        # Valid state
        input_data = BankAnalysisInput(state="FL")
        assert input_data.state == "FL"
        
        # Invalid state length
        with pytest.raises(ValidationError) as exc_info:
            BankAnalysisInput(state="Florida")
        assert "2-character abbreviation" in str(exc_info.value)
        
        # Lowercase should be converted
        input_data = BankAnalysisInput(state="fl")
        assert input_data.state == "FL"
    
    def test_has_bank_identifier(self):
        """Test bank identifier validation."""
        # Has bank name
        input_with_name = BankAnalysisInput(bank_name="Wells Fargo")
        assert input_with_name.has_bank_identifier() == True
        
        # Has RSSD ID
        input_with_rssd = BankAnalysisInput(rssd_id="451965")
        assert input_with_rssd.has_bank_identifier() == True
        
        # No identifier
        empty_input = BankAnalysisInput()
        assert empty_input.has_bank_identifier() == False


if __name__ == "__main__":
    pytest.main([__file__])