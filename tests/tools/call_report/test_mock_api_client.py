"""
Unit tests for Call Report Mock API Client.

Tests the mock API client functionality including data retrieval,
error handling, and tool interface compliance.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch

# Add src directory to path for imports
import sys
from pathlib import Path
test_dir = Path(__file__).parent
src_dir = test_dir.parent.parent.parent / "src"
sys.path.insert(0, str(src_dir))

from tools.call_report.mock_api_client import CallReportMockAPI
from tools.base import ToolStatus


class TestCallReportMockAPI:
    """Test cases for CallReportMockAPI."""
    
    @pytest.fixture
    def api_client(self):
        """Fixture providing CallReportMockAPI instance."""
        return CallReportMockAPI()
    
    def test_initialization(self, api_client):
        """Test CallReportMockAPI initialization."""
        assert api_client.name == "call_report_data"
        assert "FFIEC Call Report data" in api_client.description
        assert api_client.mock_data is not None
        assert len(api_client.mock_data) > 0
        assert api_client.is_available()
    
    def test_get_schema(self, api_client):
        """Test OpenAI function schema generation."""
        schema = api_client.get_schema()
        
        assert schema["type"] == "function"
        assert "function" in schema
        
        function_def = schema["function"]
        assert function_def["name"] == "call_report_data"
        assert "parameters" in function_def
        
        parameters = function_def["parameters"]
        assert parameters["type"] == "object"
        assert "properties" in parameters
        assert "required" in parameters
        
        # Check required parameters
        required = parameters["required"]
        assert "rssd_id" in required
        assert "schedule" in required
        assert "field_id" in required
        
        # Check parameter definitions
        properties = parameters["properties"]
        assert "rssd_id" in properties
        assert "schedule" in properties
        assert "field_id" in properties
    
    def test_get_available_banks(self, api_client):
        """Test getting available banks."""
        banks = api_client.get_available_banks()
        
        assert isinstance(banks, dict)
        assert len(banks) > 0
        
        # Check bank structure
        for rssd_id, bank_info in banks.items():
            assert "rssd_id" in bank_info
            assert "name" in bank_info
            assert "data_fields" in bank_info
            assert bank_info["rssd_id"] == rssd_id
    
    @pytest.mark.asyncio
    async def test_execute_success(self, api_client):
        """Test successful API execution."""
        result = await api_client.execute(
            rssd_id="123456",
            schedule="RC",
            field_id="RCON2170"
        )
        
        assert result.success
        assert result.status == ToolStatus.SUCCESS
        assert result.error is None
        assert result.data is not None
        assert result.tool_name == "call_report_data"
        assert result.execution_time > 0
        
        # Check data structure
        data = result.data
        assert "field_id" in data
        assert "field_name" in data
        assert "value" in data
        assert "schedule" in data
        assert "report_date" in data
        assert data["field_id"] == "RCON2170"
        assert data["schedule"] == "RC"
    
    @pytest.mark.asyncio
    async def test_execute_bank_not_found(self, api_client):
        """Test API execution with non-existent bank."""
        result = await api_client.execute(
            rssd_id="999999",  # Non-existent bank
            schedule="RC",
            field_id="RCON2170"
        )
        
        assert not result.success
        assert result.status == ToolStatus.ERROR
        assert result.error is not None
        assert "not found" in result.error.lower()
        assert result.tool_name == "call_report_data"
    
    @pytest.mark.asyncio
    async def test_execute_invalid_inputs(self, api_client):
        """Test API execution with invalid inputs."""
        # Invalid RSSD ID
        result = await api_client.execute(
            rssd_id="invalid",
            schedule="RC",
            field_id="RCON2170"
        )
        assert not result.success
        assert "numeric string" in result.error
        
        # Invalid schedule
        result = await api_client.execute(
            rssd_id="123456",
            schedule="INVALID",
            field_id="RCON2170"
        )
        assert not result.success
        assert "Invalid schedule" in result.error
        
        # Invalid field ID
        result = await api_client.execute(
            rssd_id="123456",
            schedule="RC",
            field_id="INVALID123"
        )
        assert not result.success
        assert "Invalid field ID" in result.error
    
    @pytest.mark.asyncio
    async def test_execute_field_not_available(self, api_client):
        """Test API execution with valid but unavailable field."""
        # Use a valid field ID that might not have data
        result = await api_client.execute(
            rssd_id="123456",
            schedule="RCN",
            field_id="RCON5525"  # Valid field but might not have data
        )
        
        # Should succeed but might have null value
        assert result.success
        assert result.data is not None
        assert "data_availability" in result.data
    
    def test_validate_inputs(self, api_client):
        """Test input validation method."""
        # Valid inputs
        assert api_client._validate_inputs("123456", "RC", "RCON2170")
        
        # Invalid RSSD ID
        with pytest.raises(ValueError, match="numeric string"):
            api_client._validate_inputs("invalid", "RC", "RCON2170")
        
        # Invalid schedule
        with pytest.raises(ValueError, match="Invalid schedule"):
            api_client._validate_inputs("123456", "INVALID", "RCON2170")
        
        # Invalid field ID
        with pytest.raises(ValueError, match="Invalid field ID"):
            api_client._validate_inputs("123456", "RC", "INVALID")
    
    def test_get_field_data_success(self, api_client):
        """Test successful field data retrieval."""
        field_data = api_client._get_field_data("123456", "RC", "RCON2170")
        
        assert isinstance(field_data, dict)
        assert "field_id" in field_data
        assert "field_name" in field_data
        assert "value" in field_data
        assert "schedule" in field_data
        assert "report_date" in field_data
        assert field_data["field_id"] == "RCON2170"
    
    def test_get_field_data_bank_not_found(self, api_client):
        """Test field data retrieval with non-existent bank."""
        with pytest.raises(ValueError, match="not found"):
            api_client._get_field_data("999999", "RC", "RCON2170")
    
    @pytest.mark.asyncio
    async def test_execution_timeout_simulation(self, api_client):
        """Test that execution includes realistic timing."""
        import time
        start_time = time.time()
        
        result = await api_client.execute(
            rssd_id="123456",
            schedule="RC", 
            field_id="RCON2170"
        )
        
        end_time = time.time()
        actual_time = end_time - start_time
        
        assert result.success
        assert result.execution_time > 0
        # Should have some delay due to simulated latency
        assert actual_time >= 0.1  # At least 100ms
    
    @pytest.mark.asyncio
    async def test_case_insensitive_inputs(self, api_client):
        """Test that inputs are handled case-insensitively."""
        # Test with lowercase inputs
        result = await api_client.execute(
            rssd_id="123456",
            schedule="rc",  # lowercase
            field_id="rcon2170"  # lowercase
        )
        
        assert result.success
        assert result.data["schedule"] == "RC"  # Should be normalized
        assert result.data["field_id"] == "RCON2170"  # Should be normalized
    
    def test_mock_data_structure(self, api_client):
        """Test that mock data has expected structure."""
        mock_data = api_client.mock_data
        
        assert isinstance(mock_data, dict)
        assert len(mock_data) > 0
        
        # Check structure of mock data
        for rssd_id, bank_data in mock_data.items():
            assert isinstance(rssd_id, str)
            assert rssd_id.isdigit()
            assert isinstance(bank_data, dict)
            
            # Check that bank has some field data
            field_count = sum(1 for v in bank_data.values() if isinstance(v, dict))
            assert field_count > 0
    
    def test_realistic_data_generation(self, api_client):
        """Test that generated data is realistic."""
        # Get data for a test bank
        result_data = api_client._get_field_data("123456", "RC", "RCON2170")
        
        # Check that value is reasonable for total assets
        assert result_data["value"] is not None
        assert result_data["value"] > 0
        assert result_data["value"] < 10000000  # Less than $10T (reasonable for test data)
        
        # Check field name mapping
        assert "assets" in result_data["field_name"].lower()
    
    @pytest.mark.asyncio
    async def test_concurrent_execution(self, api_client):
        """Test concurrent API executions."""
        # Execute multiple requests concurrently
        tasks = []
        for i in range(5):
            task = api_client.execute(
                rssd_id="123456",
                schedule="RC",
                field_id="RCON2170"
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        # All should succeed
        for result in results:
            assert result.success
            assert result.data is not None
    
    def test_is_available(self, api_client):
        """Test availability checking."""
        assert api_client.is_available()
        
        # Test when disabled
        api_client.disable()
        assert not api_client.is_available()
        
        # Test when re-enabled
        api_client.enable()
        assert api_client.is_available()
        
        # Test with empty mock data
        original_data = api_client.mock_data
        api_client.mock_data = {}
        assert not api_client.is_available()
        
        # Restore data
        api_client.mock_data = original_data
        assert api_client.is_available()
    
    @pytest.mark.asyncio
    async def test_error_handling_edge_cases(self, api_client):
        """Test error handling for edge cases."""
        # Empty strings
        result = await api_client.execute(
            rssd_id="",
            schedule="RC",
            field_id="RCON2170"
        )
        assert not result.success
        
        # None values (should be handled gracefully)
        result = await api_client.execute(
            rssd_id=None,
            schedule="RC", 
            field_id="RCON2170"
        )
        assert not result.success