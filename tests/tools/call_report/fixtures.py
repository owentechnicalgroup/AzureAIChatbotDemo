"""
Test fixtures for Call Report tools tests.

Provides common test data, fixtures, and utilities for testing
Call Report functionality across all test modules.
"""

import pytest
from datetime import date
from decimal import Decimal
from typing import Dict, Any, List
from unittest.mock import Mock, AsyncMock

# Add src directory to path for imports
import sys
from pathlib import Path
test_dir = Path(__file__).parent
src_dir = test_dir.parent.parent.parent / "src"
sys.path.insert(0, str(src_dir))

from tools.call_report.data_models import (
    CallReportField,
    BankIdentification,
    CallReportData,
    FinancialRatio,
    CallReportAPIResponse,
    BankSearchRequest
)
from tools.base import ToolExecutionResult, ToolStatus


@pytest.fixture
def sample_bank_identification():
    """Fixture providing sample bank identification data."""
    return BankIdentification(
        legal_name="Test Community Bank",
        rssd_id="123456",
        fdic_cert_id="12345",
        location="Test City, TS"
    )


@pytest.fixture
def sample_call_report_field():
    """Fixture providing sample Call Report field data."""
    return CallReportField(
        field_id="RCON2170",
        field_name="Total assets",
        value=Decimal("1000000.00"),
        schedule="RC",
        report_date=date(2024, 12, 31)
    )


@pytest.fixture
def sample_call_report_data(sample_bank_identification, sample_call_report_field):
    """Fixture providing sample Call Report data."""
    return CallReportData(
        bank_id="123456",
        report_date=date(2024, 12, 31),
        fields=[sample_call_report_field],
        bank_info=sample_bank_identification
    )


@pytest.fixture
def sample_financial_ratio():
    """Fixture providing sample financial ratio data."""
    return FinancialRatio(
        ratio_name="ROA",
        value=Decimal("1.25"),
        components={
            "net_income": Decimal("12500.00"),
            "total_assets": Decimal("1000000.00")
        },
        calculation_method="(Net Income / Total Assets) * 100",
        bank_id="123456",
        report_date=date(2024, 12, 31)
    )


@pytest.fixture
def sample_api_response_success():
    """Fixture providing successful API response."""
    return CallReportAPIResponse(
        success=True,
        data={
            "field_id": "RCON2170",
            "field_name": "Total assets",
            "value": 1000000.00,
            "schedule": "RC",
            "report_date": "2024-12-31"
        },
        timestamp="2024-01-01T10:00:00Z"
    )


@pytest.fixture
def sample_api_response_error():
    """Fixture providing error API response."""
    return CallReportAPIResponse(
        success=False,
        error="Bank not found",
        timestamp="2024-01-01T10:00:00Z"
    )


@pytest.fixture
def sample_bank_search_request():
    """Fixture providing sample bank search request."""
    return BankSearchRequest(
        search_term="Wells Fargo",
        fuzzy_match=True,
        max_results=10
    )


@pytest.fixture
def mock_call_report_api():
    """Fixture providing mock Call Report API client."""
    mock_api = Mock()
    mock_api.execute = AsyncMock()
    mock_api.get_schema = Mock(return_value={
        "type": "function",
        "function": {
            "name": "call_report_data",
            "description": "Mock Call Report API",
            "parameters": {
                "type": "object",
                "properties": {
                    "rssd_id": {"type": "string"},
                    "schedule": {"type": "string"},
                    "field_id": {"type": "string"}
                },
                "required": ["rssd_id", "schedule", "field_id"]
            }
        }
    })
    mock_api.is_available = Mock(return_value=True)
    mock_api.get_available_banks = Mock(return_value={
        "123456": {
            "rssd_id": "123456",
            "name": "Test Bank",
            "data_fields": 10
        }
    })
    return mock_api


@pytest.fixture
def mock_bank_lookup_service():
    """Fixture providing mock bank lookup service."""
    mock_service = Mock()
    mock_service.execute = AsyncMock()
    mock_service.get_schema = Mock(return_value={
        "type": "function",
        "function": {
            "name": "bank_lookup",
            "description": "Mock bank lookup service",
            "parameters": {
                "type": "object",
                "properties": {
                    "search_term": {"type": "string"},
                    "fuzzy_match": {"type": "boolean"},
                    "max_results": {"type": "integer"}
                },
                "required": ["search_term"]
            }
        }
    })
    mock_service.is_available = Mock(return_value=True)
    return mock_service


@pytest.fixture
def successful_tool_result():
    """Fixture providing successful tool execution result."""
    return ToolExecutionResult(
        status=ToolStatus.SUCCESS,
        data={
            "field_id": "RCON2170",
            "field_name": "Total assets",
            "value": 1000000.00,
            "schedule": "RC"
        },
        execution_time=0.5,
        tool_name="call_report_data"
    )


@pytest.fixture
def error_tool_result():
    """Fixture providing error tool execution result."""
    return ToolExecutionResult(
        status=ToolStatus.ERROR,
        error="Bank not found",
        execution_time=0.2,
        tool_name="call_report_data"
    )


@pytest.fixture
def bank_lookup_success_result():
    """Fixture providing successful bank lookup result."""
    return ToolExecutionResult(
        status=ToolStatus.SUCCESS,
        data={
            "banks": [
                {
                    "bank_info": {
                        "legal_name": "Wells Fargo Bank, National Association",
                        "rssd_id": "451965",
                        "fdic_cert_id": "3511",
                        "location": "Sioux Falls, SD"
                    },
                    "similarity_score": 0.95,
                    "match_type": "exact"
                }
            ],
            "total_found": 1,
            "search_term": "Wells Fargo",
            "best_match": {
                "bank_info": {
                    "legal_name": "Wells Fargo Bank, National Association",
                    "rssd_id": "451965",
                    "fdic_cert_id": "3511",
                    "location": "Sioux Falls, SD"
                },
                "similarity_score": 0.95,
                "match_type": "exact"
            }
        },
        execution_time=0.1,
        tool_name="bank_lookup"
    )


class MockSettings:
    """Mock settings class for testing."""
    
    def __init__(self):
        self.enable_tools = True
        self.call_report_enabled = True
        self.call_report_timeout_seconds = 30
        self.tools_timeout_seconds = 30


@pytest.fixture
def mock_settings():
    """Fixture providing mock settings."""
    return MockSettings()


class CallReportTestData:
    """Test data generator for Call Report tests."""
    
    @staticmethod
    def generate_bank_data(count: int = 5) -> List[BankIdentification]:
        """Generate list of test bank identifications."""
        banks = []
        for i in range(count):
            banks.append(BankIdentification(
                legal_name=f"Test Bank {i+1}",
                rssd_id=str(123456 + i),
                fdic_cert_id=str(12345 + i),
                location=f"Test City {i+1}, TS"
            ))
        return banks
    
    @staticmethod
    def generate_call_report_fields(count: int = 10) -> List[CallReportField]:
        """Generate list of test Call Report fields."""
        fields = []
        field_templates = [
            ("RCON2170", "Total assets", "RC"),
            ("RIAD4340", "Net income", "RI"),
            ("RCON3210", "Total equity", "RC"),
            ("RIAD4107", "Interest income", "RI"),
            ("RCON8274", "Tier 1 capital", "RCR")
        ]
        
        for i in range(min(count, len(field_templates))):
            field_id, field_name, schedule = field_templates[i]
            fields.append(CallReportField(
                field_id=field_id,
                field_name=field_name,
                value=Decimal(str(1000000 * (i + 1))),
                schedule=schedule,
                report_date=date(2024, 12, 31)
            ))
        
        return fields
    
    @staticmethod
    def generate_ratio_calculation_test_cases() -> List[Dict[str, Any]]:
        """Generate test cases for ratio calculations."""
        return [
            {
                "ratio_name": "ROA",
                "net_income": Decimal("50000"),
                "total_assets": Decimal("1000000"),
                "expected_ratio": Decimal("5.0")
            },
            {
                "ratio_name": "ROE", 
                "net_income": Decimal("50000"),
                "total_equity": Decimal("100000"),
                "expected_ratio": Decimal("50.0")
            },
            {
                "ratio_name": "Tier1_Capital_Ratio",
                "tier1_capital": Decimal("120000"),
                "risk_weighted_assets": Decimal("800000"),
                "expected_ratio": Decimal("15.0")
            }
        ]


@pytest.fixture
def test_data_generator():
    """Fixture providing test data generator."""
    return CallReportTestData()