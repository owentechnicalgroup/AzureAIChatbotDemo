"""
Unit tests for Call Report LangChain tool wrappers.

Tests the integration of Call Report functionality with the LangChain
tool framework and tool registry system.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch

# Add src directory to path for imports
import sys
from pathlib import Path
test_dir = Path(__file__).parent
src_dir = test_dir.parent.parent.parent / "src"
sys.path.insert(0, str(src_dir))

from tools.call_report.langchain_tools import (
    CallReportDataTool,
    BankLookupTool,
    CallReportToolset,
    create_call_report_toolset
)
from tools.base import ToolStatus, ToolExecutionResult


class TestCallReportDataTool:
    """Test cases for CallReportDataTool wrapper."""
    
    @pytest.fixture
    def mock_api_client(self):
        """Fixture providing mock API client."""
        mock_client = Mock()
        mock_client.execute = AsyncMock()
        mock_client.get_schema = Mock(return_value={
            "type": "function",
            "function": {
                "name": "call_report_data",
                "description": "Test API",
                "parameters": {"type": "object"}
            }
        })
        return mock_client
    
    @pytest.fixture
    def data_tool(self, mock_api_client):
        """Fixture providing CallReportDataTool instance."""
        return CallReportDataTool(mock_api_client)
    
    def test_initialization(self, data_tool, mock_api_client):
        """Test CallReportDataTool initialization."""
        assert data_tool.name == "call_report_data"
        assert "FFIEC Call Report field data" in data_tool.description
        assert data_tool.api_client == mock_api_client
    
    def test_initialization_without_client(self):
        """Test initialization without providing API client."""
        with patch('tools.call_report.langchain_tools.CallReportMockAPI') as mock_api_class:
            mock_api_instance = Mock()
            mock_api_class.return_value = mock_api_instance
            
            tool = CallReportDataTool()
            
            assert tool.api_client == mock_api_instance
            mock_api_class.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_success(self, data_tool, mock_api_client):
        """Test successful execution."""
        # Setup mock response
        expected_result = ToolExecutionResult(
            status=ToolStatus.SUCCESS,
            data={"field_id": "RCON2170", "value": 1000000},
            tool_name="call_report_data"
        )
        mock_api_client.execute.return_value = expected_result
        
        # Execute tool
        result = await data_tool.execute(
            rssd_id="123456",
            schedule="RC",
            field_id="RCON2170"
        )
        
        # Verify
        assert result == expected_result
        mock_api_client.execute.assert_called_once_with(
            rssd_id="123456",
            schedule="RC",
            field_id="RCON2170"
        )
    
    @pytest.mark.asyncio
    async def test_execute_error(self, data_tool, mock_api_client):
        """Test execution with error."""
        # Setup mock error response
        error_result = ToolExecutionResult(
            status=ToolStatus.ERROR,
            error="Bank not found",
            tool_name="call_report_data"
        )
        mock_api_client.execute.return_value = error_result
        
        # Execute tool
        result = await data_tool.execute(
            rssd_id="999999",
            schedule="RC",
            field_id="RCON2170"
        )
        
        # Verify
        assert result == error_result
        assert not result.success
        assert "not found" in result.error
    
    def test_get_schema(self, data_tool, mock_api_client):
        """Test schema retrieval."""
        expected_schema = {
            "type": "function",
            "function": {
                "name": "call_report_data",
                "description": "Test API",
                "parameters": {"type": "object"}
            }
        }
        mock_api_client.get_schema.return_value = expected_schema
        
        schema = data_tool.get_schema()
        
        assert schema == expected_schema
        mock_api_client.get_schema.assert_called_once()


class TestBankLookupTool:
    """Test cases for BankLookupTool wrapper."""
    
    @pytest.fixture
    def mock_lookup_service(self):
        """Fixture providing mock lookup service."""
        mock_service = Mock()
        mock_service.execute = AsyncMock()
        mock_service.get_schema = Mock(return_value={
            "type": "function",
            "function": {
                "name": "bank_lookup",
                "description": "Test lookup",
                "parameters": {"type": "object"}
            }
        })
        return mock_service
    
    @pytest.fixture
    def lookup_tool(self, mock_lookup_service):
        """Fixture providing BankLookupTool instance."""
        return BankLookupTool(mock_lookup_service)
    
    def test_initialization(self, lookup_tool, mock_lookup_service):
        """Test BankLookupTool initialization."""
        assert lookup_tool.name == "bank_lookup"
        assert "RSSD ID and information" in lookup_tool.description
        assert lookup_tool.lookup_service == mock_lookup_service
    
    def test_initialization_without_service(self):
        """Test initialization without providing lookup service."""
        with patch('tools.call_report.langchain_tools.BaseBankLookupTool') as mock_service_class:
            mock_service_instance = Mock()
            mock_service_class.return_value = mock_service_instance
            
            tool = BankLookupTool()
            
            assert tool.lookup_service == mock_service_instance
            mock_service_class.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_success(self, lookup_tool, mock_lookup_service):
        """Test successful bank lookup."""
        # Setup mock response
        expected_result = ToolExecutionResult(
            status=ToolStatus.SUCCESS,
            data={
                "banks": [{"rssd_id": "451965", "name": "Wells Fargo"}],
                "total_found": 1
            },
            tool_name="bank_lookup"
        )
        mock_lookup_service.execute.return_value = expected_result
        
        # Execute tool
        result = await lookup_tool.execute(
            search_term="Wells Fargo",
            fuzzy_match=True,
            max_results=10
        )
        
        # Verify
        assert result == expected_result
        mock_lookup_service.execute.assert_called_once_with(
            search_term="Wells Fargo",
            fuzzy_match=True,
            max_results=10
        )
    
    @pytest.mark.asyncio
    async def test_execute_no_results(self, lookup_tool, mock_lookup_service):
        """Test bank lookup with no results."""
        # Setup mock response
        no_results = ToolExecutionResult(
            status=ToolStatus.SUCCESS,
            data={
                "banks": [],
                "total_found": 0,
                "message": "No banks found"
            },
            tool_name="bank_lookup"
        )
        mock_lookup_service.execute.return_value = no_results
        
        # Execute tool
        result = await lookup_tool.execute(search_term="NonexistentBank")
        
        # Verify
        assert result == no_results
        assert result.success
        assert result.data["total_found"] == 0
    
    def test_get_schema(self, lookup_tool, mock_lookup_service):
        """Test schema retrieval."""
        expected_schema = {
            "type": "function",
            "function": {
                "name": "bank_lookup",
                "description": "Test lookup",
                "parameters": {"type": "object"}
            }
        }
        mock_lookup_service.get_schema.return_value = expected_schema
        
        schema = lookup_tool.get_schema()
        
        assert schema == expected_schema
        mock_lookup_service.get_schema.assert_called_once()


class TestCallReportToolset:
    """Test cases for CallReportToolset."""
    
    @pytest.fixture
    def mock_settings(self):
        """Fixture providing mock settings."""
        settings = Mock()
        settings.call_report_enabled = True
        settings.call_report_timeout_seconds = 30
        return settings
    
    @pytest.fixture
    def toolset(self, mock_settings):
        """Fixture providing CallReportToolset instance."""
        with patch('tools.call_report.langchain_tools.CallReportMockAPI') as mock_api, \
             patch('tools.call_report.langchain_tools.BaseBankLookupTool') as mock_lookup:
            
            mock_api_instance = Mock()
            mock_lookup_instance = Mock()
            mock_api.return_value = mock_api_instance
            mock_lookup.return_value = mock_lookup_instance
            
            return CallReportToolset(mock_settings)
    
    def test_initialization(self, toolset, mock_settings):
        """Test CallReportToolset initialization."""
        assert toolset.settings == mock_settings
        assert toolset.api_client is not None
        assert toolset.lookup_service is not None
        assert len(toolset.tools) == 2  # Bank lookup + Call Report data
        
        # Check tool types
        tool_names = [tool.name for tool in toolset.tools]
        assert "bank_lookup" in tool_names
        assert "call_report_data" in tool_names
    
    def test_get_tools(self, toolset):
        """Test getting tools list."""
        tools = toolset.get_tools()
        
        assert isinstance(tools, list)
        assert len(tools) == 2
        
        # Should return a copy, not the original
        assert tools is not toolset.tools
        assert tools == toolset.tools
    
    def test_register_with_registry_enabled(self, toolset):
        """Test registering tools with registry when enabled."""
        mock_registry = Mock()
        
        toolset.register_with_registry(mock_registry)
        
        # Should register all tools
        assert mock_registry.register_tool.call_count == 2
        
        # Check that each tool was registered
        registered_tools = [call.args[0] for call in mock_registry.register_tool.call_args_list]
        tool_names = [tool.name for tool in registered_tools]
        assert "bank_lookup" in tool_names
        assert "call_report_data" in tool_names
    
    def test_register_with_registry_disabled(self, mock_settings):
        """Test registering tools when disabled in settings."""
        mock_settings.call_report_enabled = False
        
        with patch('tools.call_report.langchain_tools.CallReportMockAPI'), \
             patch('tools.call_report.langchain_tools.BaseBankLookupTool'):
            
            toolset = CallReportToolset(mock_settings)
            mock_registry = Mock()
            
            toolset.register_with_registry(mock_registry)
            
            # Should not register any tools
            mock_registry.register_tool.assert_not_called()
    
    def test_register_with_registry_error_handling(self, toolset):
        """Test error handling during tool registration."""
        mock_registry = Mock()
        mock_registry.register_tool.side_effect = [None, Exception("Registration failed")]
        
        # Should not raise exception
        toolset.register_with_registry(mock_registry)
        
        # Should still attempt to register all tools
        assert mock_registry.register_tool.call_count == 2
    
    def test_is_available_enabled(self, toolset):
        """Test availability check when enabled."""
        toolset.api_client.is_available = Mock(return_value=True)
        toolset.lookup_service.is_available = Mock(return_value=True)
        
        assert toolset.is_available()
    
    def test_is_available_disabled(self, mock_settings):
        """Test availability check when disabled."""
        mock_settings.call_report_enabled = False
        
        with patch('tools.call_report.langchain_tools.CallReportMockAPI'), \
             patch('tools.call_report.langchain_tools.BaseBankLookupTool'):
            
            toolset = CallReportToolset(mock_settings)
            
            assert not toolset.is_available()
    
    def test_is_available_service_unavailable(self, toolset):
        """Test availability check when services are unavailable."""
        toolset.api_client.is_available = Mock(return_value=False)
        toolset.lookup_service.is_available = Mock(return_value=True)
        
        assert not toolset.is_available()
    
    def test_get_health_status(self, toolset):
        """Test health status reporting."""
        toolset.api_client.is_available = Mock(return_value=True)
        toolset.api_client.get_available_banks = Mock(return_value={"123": "test"})
        toolset.lookup_service.is_available = Mock(return_value=True)
        toolset.lookup_service.get_all_banks = Mock(return_value=[Mock(), Mock()])
        
        status = toolset.get_health_status()
        
        assert status["toolset_enabled"] is True
        assert status["tools_count"] == 2
        assert status["services"]["api_client"]["available"] is True
        assert status["services"]["api_client"]["banks_available"] == 1
        assert status["services"]["lookup_service"]["available"] is True
        assert status["services"]["lookup_service"]["banks_directory_size"] == 2
        assert status["overall_health"] == "healthy"
    
    def test_get_available_banks_summary(self, toolset):
        """Test getting available banks summary."""
        toolset.api_client.get_available_banks = Mock(return_value={"123": "test", "456": "test2"})
        
        mock_banks = [
            Mock(rssd_id="123", legal_name="Bank 1", location="City 1"),
            Mock(rssd_id="456", legal_name="Bank 2", location="City 2"),
            Mock(rssd_id="789", legal_name="Bank 3", location="City 3")
        ]
        toolset.lookup_service.get_all_banks = Mock(return_value=mock_banks)
        
        summary = toolset.get_available_banks_summary()
        
        assert summary["api_data_banks"] == 2
        assert summary["lookup_directory_banks"] == 3
        assert len(summary["sample_banks"]) == 3  # First 5 banks, but we only have 3
        
        # Check sample bank structure
        sample = summary["sample_banks"][0]
        assert "rssd_id" in sample
        assert "name" in sample
        assert "location" in sample


class TestCreateCallReportToolset:
    """Test cases for toolset factory function."""
    
    def test_create_call_report_toolset(self, mock_settings):
        """Test factory function creates toolset correctly."""
        with patch('tools.call_report.langchain_tools.CallReportMockAPI'), \
             patch('tools.call_report.langchain_tools.BaseBankLookupTool'):
            
            toolset = create_call_report_toolset(mock_settings)
            
            assert isinstance(toolset, CallReportToolset)
            assert toolset.settings == mock_settings


class TestToolIntegration:
    """Integration tests for tool interactions."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_workflow(self, mock_settings):
        """Test complete workflow from bank lookup to data retrieval."""
        with patch('tools.call_report.langchain_tools.CallReportMockAPI') as mock_api_class, \
             patch('tools.call_report.langchain_tools.BaseBankLookupTool') as mock_lookup_class:
            
            # Setup mock instances
            mock_api = Mock()
            mock_lookup = Mock()
            mock_api_class.return_value = mock_api
            mock_lookup_class.return_value = mock_lookup
            
            # Setup mock responses
            lookup_result = ToolExecutionResult(
                status=ToolStatus.SUCCESS,
                data={
                    "banks": [{"bank_info": {"rssd_id": "451965"}}],
                    "best_match": {"bank_info": {"rssd_id": "451965"}}
                }
            )
            
            data_result = ToolExecutionResult(
                status=ToolStatus.SUCCESS,
                data={"field_id": "RCON2170", "value": 1000000}
            )
            
            mock_lookup.execute = AsyncMock(return_value=lookup_result)
            mock_api.execute = AsyncMock(return_value=data_result)
            
            # Create toolset and get tools
            toolset = CallReportToolset(mock_settings)
            tools = toolset.get_tools()
            
            # Find tools
            bank_lookup_tool = next(t for t in tools if t.name == "bank_lookup")
            data_tool = next(t for t in tools if t.name == "call_report_data")
            
            # Execute workflow
            # 1. Look up bank
            lookup_response = await bank_lookup_tool.execute(search_term="Wells Fargo")
            assert lookup_response.success
            
            # 2. Extract RSSD ID
            rssd_id = lookup_response.data["best_match"]["bank_info"]["rssd_id"]
            
            # 3. Get Call Report data
            data_response = await data_tool.execute(
                rssd_id=rssd_id,
                schedule="RC",
                field_id="RCON2170"
            )
            assert data_response.success
            
            # Verify calls
            mock_lookup.execute.assert_called_once()
            mock_api.execute.assert_called_once_with(
                rssd_id="451965",
                schedule="RC",
                field_id="RCON2170"
            )
    
    @pytest.mark.asyncio
    async def test_concurrent_tool_execution(self, mock_settings):
        """Test concurrent execution of multiple tools."""
        with patch('tools.call_report.langchain_tools.CallReportMockAPI') as mock_api_class, \
             patch('tools.call_report.langchain_tools.BaseBankLookupTool') as mock_lookup_class:
            
            # Setup mocks
            mock_api = Mock()
            mock_lookup = Mock()
            mock_api_class.return_value = mock_api
            mock_lookup_class.return_value = mock_lookup
            
            # Setup async mock responses
            mock_lookup.execute = AsyncMock(return_value=ToolExecutionResult(ToolStatus.SUCCESS, {}))
            mock_api.execute = AsyncMock(return_value=ToolExecutionResult(ToolStatus.SUCCESS, {}))
            
            # Create toolset
            toolset = CallReportToolset(mock_settings)
            tools = toolset.get_tools()
            
            # Execute multiple operations concurrently
            tasks = []
            for tool in tools:
                if tool.name == "bank_lookup":
                    task = tool.execute(search_term="Test Bank")
                else:  # call_report_data
                    task = tool.execute(rssd_id="123", schedule="RC", field_id="RCON2170")
                tasks.append(task)
            
            results = await asyncio.gather(*tasks)
            
            # All should succeed
            for result in results:
                assert result.success