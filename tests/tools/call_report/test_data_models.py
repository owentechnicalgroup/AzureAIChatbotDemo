"""
Unit tests for Call Report data models.

Tests Pydantic model validation, serialization, and business logic
for Call Report data structures.
"""

import pytest
from datetime import date
from decimal import Decimal
from pydantic import ValidationError

# Add src directory to path for imports
import sys
from pathlib import Path
test_dir = Path(__file__).parent
src_dir = test_dir.parent.parent.parent / "src"
sys.path.insert(0, str(src_dir))

# Import fixtures
from .fixtures import (
    sample_bank_identification,
    sample_call_report_field,
    sample_call_report_data,
    sample_financial_ratio,
    sample_api_response_success,
    sample_api_response_error,
    sample_bank_search_request
)

from tools.call_report.data_models import (
    CallReportField,
    BankIdentification,
    CallReportData,
    FinancialRatio,
    CallReportAPIResponse,
    BankSearchRequest
)


class TestCallReportField:
    """Test cases for CallReportField model."""
    
    def test_valid_call_report_field(self, sample_call_report_field):
        """Test creating valid CallReportField."""
        field = sample_call_report_field
        
        assert field.field_id == "RCON2170"
        assert field.field_name == "Total assets"
        assert field.value == Decimal("1000000.00")
        assert field.schedule == "RC"
        assert field.report_date == date(2024, 12, 31)
    
    def test_field_id_validation(self):
        """Test field ID validation."""
        # Valid field ID
        field = CallReportField(
            field_id="RCON2170",
            field_name="Test field",
            schedule="RC"
        )
        assert field.field_id == "RCON2170"
        
        # Invalid field ID - too short
        with pytest.raises(ValidationError) as exc_info:
            CallReportField(
                field_id="RCON123",  # Only 7 characters
                field_name="Test field",
                schedule="RC"
            )
        assert "at least 8 characters" in str(exc_info.value)
        
        # Invalid field ID - wrong prefix
        with pytest.raises(ValidationError) as exc_info:
            CallReportField(
                field_id="XXXX2170",
                field_name="Test field", 
                schedule="RC"
            )
        assert "must start with one of" in str(exc_info.value)
    
    def test_value_validation(self):
        """Test financial value validation and conversion."""
        # Valid decimal value
        field = CallReportField(
            field_id="RCON2170",
            field_name="Test field",
            value="1000000.50",
            schedule="RC"
        )
        assert field.value == Decimal("1000000.50")
        
        # Valid integer value
        field = CallReportField(
            field_id="RCON2170",
            field_name="Test field",
            value=1000000,
            schedule="RC"
        )
        assert field.value == Decimal("1000000")
        
        # Valid float value  
        field = CallReportField(
            field_id="RCON2170",
            field_name="Test field",
            value=1000000.75,
            schedule="RC"
        )
        assert field.value == Decimal("1000000.75")
        
        # None value should be allowed
        field = CallReportField(
            field_id="RCON2170", 
            field_name="Test field",
            value=None,
            schedule="RC"
        )
        assert field.value is None
        
        # Invalid value
        with pytest.raises(ValidationError) as exc_info:
            CallReportField(
                field_id="RCON2170",
                field_name="Test field",
                value="invalid_decimal",
                schedule="RC"
            )
        assert "Input should be a valid decimal" in str(exc_info.value)
    
    def test_schedule_validation(self):
        """Test schedule validation."""
        # Valid schedule
        field = CallReportField(
            field_id="RCON2170",
            field_name="Test field",
            schedule="rc"  # Should be converted to uppercase
        )
        assert field.schedule == "RC"
        
        # Empty schedule should fail
        with pytest.raises(ValidationError) as exc_info:
            CallReportField(
                field_id="RCON2170",
                field_name="Test field",
                schedule=""
            )
        assert "Schedule cannot be empty" in str(exc_info.value)


class TestBankIdentification:
    """Test cases for BankIdentification model."""
    
    def test_valid_bank_identification(self, sample_bank_identification):
        """Test creating valid BankIdentification."""
        bank = sample_bank_identification
        
        assert bank.legal_name == "Test Community Bank"
        assert bank.rssd_id == "123456"
        assert bank.fdic_cert_id == "12345"
        assert bank.location == "Test City, TS"
    
    def test_rssd_id_validation(self):
        """Test RSSD ID validation."""
        # Valid RSSD ID
        bank = BankIdentification(
            legal_name="Test Bank",
            rssd_id="451965"
        )
        assert bank.rssd_id == "451965"
        
        # Invalid RSSD ID - contains letters
        with pytest.raises(ValidationError) as exc_info:
            BankIdentification(
                legal_name="Test Bank",
                rssd_id="45196A"
            )
        assert "must contain only digits" in str(exc_info.value)
        
        # Invalid RSSD ID - too short
        with pytest.raises(ValidationError) as exc_info:
            BankIdentification(
                legal_name="Test Bank",
                rssd_id="123"
            )
        assert "at least 4 characters" in str(exc_info.value)
    
    def test_fdic_cert_id_validation(self):
        """Test FDIC Certificate ID validation."""
        # Valid FDIC cert ID
        bank = BankIdentification(
            legal_name="Test Bank",
            rssd_id="123456",
            fdic_cert_id="3511"
        )
        assert bank.fdic_cert_id == "3511"
        
        # None should be allowed
        bank = BankIdentification(
            legal_name="Test Bank",
            rssd_id="123456",
            fdic_cert_id=None
        )
        assert bank.fdic_cert_id is None
        
        # Invalid FDIC cert ID
        with pytest.raises(ValidationError) as exc_info:
            BankIdentification(
                legal_name="Test Bank", 
                rssd_id="123456",
                fdic_cert_id="351A"
            )
        assert "must contain only digits" in str(exc_info.value)


class TestCallReportData:
    """Test cases for CallReportData model."""
    
    def test_valid_call_report_data(self, sample_call_report_data):
        """Test creating valid CallReportData."""
        data = sample_call_report_data
        
        assert data.bank_id == "123456"
        assert data.report_date == date(2024, 12, 31)
        assert len(data.fields) == 1
        assert data.bank_info is not None
    
    def test_report_date_validation(self):
        """Test report date validation."""
        # Valid date
        data = CallReportData(
            bank_id="123456",
            report_date=date(2024, 12, 31),
            fields=[]
        )
        assert data.report_date == date(2024, 12, 31)
        
        # Date too early
        with pytest.raises(ValidationError) as exc_info:
            CallReportData(
                bank_id="123456",
                report_date=date(1975, 1, 1),
                fields=[]
            )
        assert "must be between" in str(exc_info.value)
    
    def test_get_field_by_id(self, sample_call_report_data):
        """Test getting field by ID."""
        data = sample_call_report_data
        
        # Existing field
        field = data.get_field_by_id("RCON2170")
        assert field is not None
        assert field.field_id == "RCON2170"
        
        # Non-existing field
        field = data.get_field_by_id("RCON9999")
        assert field is None
    
    def test_get_fields_by_schedule(self, sample_call_report_data):
        """Test getting fields by schedule."""
        data = sample_call_report_data
        
        # Existing schedule
        fields = data.get_fields_by_schedule("RC")
        assert len(fields) == 1
        assert fields[0].schedule == "RC"
        
        # Case insensitive
        fields = data.get_fields_by_schedule("rc")
        assert len(fields) == 1
        
        # Non-existing schedule
        fields = data.get_fields_by_schedule("XX")
        assert len(fields) == 0
    
    def test_get_field_value(self, sample_call_report_data):
        """Test getting field value."""
        data = sample_call_report_data
        
        # Existing field
        value = data.get_field_value("RCON2170")
        assert value == Decimal("1000000.00")
        
        # Non-existing field
        value = data.get_field_value("RCON9999")
        assert value is None


class TestFinancialRatio:
    """Test cases for FinancialRatio model."""
    
    def test_valid_financial_ratio(self, sample_financial_ratio):
        """Test creating valid FinancialRatio."""
        ratio = sample_financial_ratio
        
        assert ratio.ratio_name == "ROA"
        assert ratio.value == Decimal("1.25")
        assert "net_income" in ratio.components
        assert ratio.calculation_method == "(Net Income / Total Assets) * 100"
    
    def test_ratio_value_validation(self):
        """Test ratio value validation with warnings."""
        # Normal ratio value
        ratio = FinancialRatio(
            ratio_name="ROA",
            value=Decimal("1.5"),
            components={},
            calculation_method="test",
            bank_id="123456",
            report_date=date(2024, 12, 31)
        )
        assert ratio.value == Decimal("1.5")
        
        # Extreme value should still be accepted but logged
        ratio = FinancialRatio(
            ratio_name="ROA",
            value=Decimal("150.0"),  # Very high ratio
            components={},
            calculation_method="test",
            bank_id="123456",
            report_date=date(2024, 12, 31)
        )
        assert ratio.value == Decimal("150.0")


class TestCallReportAPIResponse:
    """Test cases for CallReportAPIResponse model."""
    
    def test_successful_response(self, sample_api_response_success):
        """Test successful API response."""
        response = sample_api_response_success
        
        assert response.success is True
        assert response.data is not None
        assert response.error is None
    
    def test_error_response(self, sample_api_response_error):
        """Test error API response."""
        response = sample_api_response_error
        
        assert response.success is False
        assert response.error == "Bank not found"
        assert response.data is None
    
    def test_error_validation(self):
        """Test that error message is required when success=False."""
        # This should work - success=False with error message
        response = CallReportAPIResponse(
            success=False,
            error="Test error"
        )
        assert response.success is False
        assert response.error == "Test error"


class TestBankSearchRequest:
    """Test cases for BankSearchRequest model."""
    
    def test_valid_search_request(self, sample_bank_search_request):
        """Test valid bank search request."""
        request = sample_bank_search_request
        
        assert request.search_term == "Wells Fargo"
        assert request.fuzzy_match is True
        assert request.max_results == 10
    
    def test_search_term_validation(self):
        """Test search term validation."""
        # Valid search term
        request = BankSearchRequest(search_term="Wells Fargo")
        assert request.search_term == "Wells Fargo"
        
        # Too short
        with pytest.raises(ValidationError) as exc_info:
            BankSearchRequest(search_term="W")
        assert "at least 2 characters" in str(exc_info.value)
        
        # Invalid characters
        with pytest.raises(ValidationError) as exc_info:
            BankSearchRequest(search_term="Wells <script>")
        assert "invalid characters" in str(exc_info.value)
    
    def test_max_results_validation(self):
        """Test max results validation."""
        # Valid range
        request = BankSearchRequest(
            search_term="Test Bank",
            max_results=25
        )
        assert request.max_results == 25
        
        # Too low
        with pytest.raises(ValidationError) as exc_info:
            BankSearchRequest(
                search_term="Test Bank",
                max_results=0
            )
        assert "Input should be greater than or equal to 1" in str(exc_info.value)
        
        # Too high
        with pytest.raises(ValidationError) as exc_info:
            BankSearchRequest(
                search_term="Test Bank",
                max_results=100
            )
        assert "Input should be less than or equal to 50" in str(exc_info.value)