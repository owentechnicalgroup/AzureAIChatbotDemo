"""
Composite Bank Analysis Tool for Call Report queries.

This tool combines bank lookup and Call Report data retrieval into
intelligent workflows that complete multi-step banking queries.
"""

import json
from typing import Dict, Any, Optional, List
from decimal import Decimal

from src.tools.base import BaseTool, ToolExecutionResult, ToolStatus
from .bank_lookup import BankLookupTool as BaseBankLookupTool
from .mock_api_client import CallReportMockAPI
# Field mappings imported from constants if needed later


class BankAnalysisTool(BaseTool):
    """
    Intelligent bank analysis tool that handles complete workflows.
    
    Combines bank lookup with Call Report data retrieval to answer
    common banking queries in a single tool call.
    """
    
    def __init__(self):
        """Initialize the composite bank analysis tool."""
        super().__init__(
            name="bank_analysis",
            description="Complete banking analysis tool - look up banks and get financial data (total assets, ROA, ROE) in one call. Use this for any banking query that needs specific financial information."
        )
        
        # Initialize component tools
        self.bank_lookup = BaseBankLookupTool()
        self.api_client = CallReportMockAPI()
        
        self.logger.info(
            "BankAnalysisTool initialized",
            component="tool",
            tool_name=self.name
        )
    
    async def execute(
        self,
        bank_name: Optional[str] = None,
        rssd_id: Optional[str] = None,
        query_type: str = "basic_info",
        **kwargs
    ) -> ToolExecutionResult:
        """
        Execute comprehensive bank analysis.
        
        Args:
            bank_name: Bank name to search for (if rssd_id not provided)
            rssd_id: Bank RSSD ID (if known)
            query_type: Type of analysis ("basic_info", "total_assets", "roa", "roe", "capital_ratio")
            **kwargs: Additional parameters
            
        Returns:
            ToolExecutionResult with comprehensive bank data
        """
        try:
            self.logger.info(
                "Executing bank analysis",
                bank_name=bank_name,
                rssd_id=rssd_id,
                query_type=query_type,
                component="tool",
                tool_name=self.name
            )
            
            # Step 1: Get bank identification
            if not rssd_id and bank_name:
                lookup_result = await self.bank_lookup.execute(
                    search_term=bank_name,
                    max_results=1
                )
                
                if not lookup_result.success or not lookup_result.data.get('best_match'):
                    return ToolExecutionResult(
                        status=ToolStatus.ERROR,
                        error=f"Could not find bank: {bank_name}",
                        tool_name=self.name
                    )
                
                bank_info = lookup_result.data['best_match']['bank_info']
                rssd_id = bank_info['rssd_id']
            elif not rssd_id:
                return ToolExecutionResult(
                    status=ToolStatus.ERROR,
                    error="Must provide either bank_name or rssd_id",
                    tool_name=self.name
                )
            else:
                # If RSSD ID provided, still get bank info for context
                lookup_result = await self.bank_lookup.execute(
                    search_term=rssd_id,
                    max_results=1
                )
                bank_info = lookup_result.data.get('best_match', {}).get('bank_info', {})
            
            # Step 2: Execute specific query type
            result_data = {
                "bank_info": bank_info,
                "rssd_id": rssd_id
            }
            
            if query_type == "basic_info":
                # Just return bank information
                result_data["message"] = "Bank information retrieved successfully"
                
            elif query_type == "total_assets":
                # Get total assets
                assets_result = await self.api_client.execute(
                    rssd_id=rssd_id,
                    schedule="RC",
                    field_id="RCON2170"
                )
                
                if assets_result.success:
                    result_data["total_assets"] = assets_result.data
                    result_data["message"] = f"Total assets for {bank_info.get('legal_name', 'bank')}: ${assets_result.data.get('value', 'N/A'):,}"
                else:
                    result_data["error"] = f"Could not retrieve total assets: {assets_result.error}"
                    
            elif query_type in ["roa", "roe", "capital_ratio"]:
                # Calculate financial ratios
                ratio_data = await self._calculate_ratio(rssd_id, query_type, bank_info)
                result_data.update(ratio_data)
                
            else:
                return ToolExecutionResult(
                    status=ToolStatus.ERROR,
                    error=f"Unknown query type: {query_type}",
                    tool_name=self.name
                )
            
            return ToolExecutionResult(
                status=ToolStatus.SUCCESS,
                data=result_data,
                tool_name=self.name
            )
            
        except Exception as e:
            self.logger.error(
                "Bank analysis failed",
                error=str(e),
                component="tool",
                tool_name=self.name
            )
            return ToolExecutionResult(
                status=ToolStatus.ERROR,
                error=f"Bank analysis failed: {str(e)}",
                tool_name=self.name
            )
    
    async def _calculate_ratio(self, rssd_id: str, ratio_type: str, bank_info: Dict) -> Dict[str, Any]:
        """Calculate specific financial ratio."""
        try:
            if ratio_type == "roa":
                # ROA = Net Income / Total Assets
                net_income_result = await self.api_client.execute(
                    rssd_id=rssd_id, schedule="RI", field_id="RIAD4340"
                )
                total_assets_result = await self.api_client.execute(
                    rssd_id=rssd_id, schedule="RC", field_id="RCON2170"
                )
                
                if net_income_result.success and total_assets_result.success:
                    net_income = Decimal(str(net_income_result.data.get('value', 0)))
                    total_assets = Decimal(str(total_assets_result.data.get('value', 1)))
                    
                    if total_assets > 0:
                        roa = (net_income / total_assets) * 100
                        return {
                            "ratio_type": "ROA",
                            "ratio_value": float(roa.quantize(Decimal('0.01'))),
                            "net_income": net_income_result.data,
                            "total_assets": total_assets_result.data,
                            "calculation": f"ROA = ({net_income:,} / {total_assets:,}) * 100 = {roa:.2f}%",
                            "message": f"Return on Assets (ROA) for {bank_info.get('legal_name', 'bank')}: {roa:.2f}%"
                        }
                
            elif ratio_type == "roe":
                # ROE = Net Income / Total Equity
                net_income_result = await self.api_client.execute(
                    rssd_id=rssd_id, schedule="RI", field_id="RIAD4340"
                )
                total_equity_result = await self.api_client.execute(
                    rssd_id=rssd_id, schedule="RC", field_id="RCON3210"
                )
                
                if net_income_result.success and total_equity_result.success:
                    net_income = Decimal(str(net_income_result.data.get('value', 0)))
                    total_equity = Decimal(str(total_equity_result.data.get('value', 1)))
                    
                    if total_equity > 0:
                        roe = (net_income / total_equity) * 100
                        return {
                            "ratio_type": "ROE",
                            "ratio_value": float(roe.quantize(Decimal('0.01'))),
                            "net_income": net_income_result.data,
                            "total_equity": total_equity_result.data,
                            "calculation": f"ROE = ({net_income:,} / {total_equity:,}) * 100 = {roe:.2f}%",
                            "message": f"Return on Equity (ROE) for {bank_info.get('legal_name', 'bank')}: {roe:.2f}%"
                        }
            
            return {"error": f"Could not calculate {ratio_type.upper()} - insufficient data"}
            
        except Exception as e:
            return {"error": f"Ratio calculation failed: {str(e)}"}
    
    def get_schema(self) -> Dict[str, Any]:
        """Get OpenAI function schema for this tool."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": "Use this tool for banking queries that need financial data. It can find banks and retrieve Call Report data like total assets, calculate ratios like ROA/ROE, all in one call.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "bank_name": {
                            "type": "string",
                            "description": "Name of the bank to analyze (e.g., 'Wells Fargo', 'Bank of America')"
                        },
                        "rssd_id": {
                            "type": "string", 
                            "description": "Bank RSSD ID if known (optional if bank_name provided)"
                        },
                        "query_type": {
                            "type": "string",
                            "enum": ["basic_info", "total_assets", "roa", "roe", "capital_ratio"],
                            "description": "Type of analysis: basic_info (bank details), total_assets (get assets), roa (return on assets), roe (return on equity), capital_ratio (Tier 1 ratio)"
                        }
                    },
                    "required": ["query_type"]
                }
            }
        }