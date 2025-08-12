"""
Mock FFIEC Call Report API client for testing and development.

Provides realistic mock data for Call Report fields to enable
development and testing without accessing production FFIEC systems.
"""

import asyncio
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Dict, Any, Optional
import random

import structlog
from .constants import (
    ALL_FIELD_MAPPINGS, 
    VALID_FIELD_IDS, 
    VALID_SCHEDULES,
    get_field_info
)
from .data_models import CallReportField, CallReportAPIResponse

logger = structlog.get_logger(__name__).bind(log_type="SYSTEM")


class CallReportMockAPI:
    """
    Mock FFIEC Call Report API service implementation.
    
    Provides realistic Call Report data for development and testing
    without requiring access to actual FFIEC systems.
    """
    
    def __init__(self):
        """Initialize the mock Call Report API service."""
        self.logger = logger.bind(component="call_report_mock_api")
        
        # Load mock data
        self.mock_data = self._load_mock_data()
        
        self.logger.info(
            "CallReportMockAPI initialized",
            banks_count=len(self.mock_data),
            fields_per_bank=len(next(iter(self.mock_data.values())) if self.mock_data else {})
        )
    
    def _load_mock_data(self) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """
        Load realistic mock Call Report data for major banks.
        
        Returns:
            Dictionary structure: {rssd_id: {field_id: field_data}}
        """
        # Mock data for major US banks (using fake but realistic data)
        mock_banks = {
            "451965": {  # Wells Fargo (real RSSD ID but fake data)
                "name": "Wells Fargo Bank, National Association",
                "location": "Sioux Falls, SD",
                "assets_size": "large"
            },
            "480228": {  # JPMorgan Chase (real RSSD ID but fake data)
                "name": "JPMorgan Chase Bank, National Association", 
                "location": "Columbus, OH",
                "assets_size": "large"
            },
            "541101": {  # Bank of America (real RSSD ID but fake data)
                "name": "Bank of America, National Association",
                "location": "Charlotte, NC", 
                "assets_size": "large"
            },
            "628208": {  # Citibank (real RSSD ID but fake data)
                "name": "Citibank, National Association",
                "location": "Sioux Falls, SD",
                "assets_size": "large"
            },
            "123456": {  # Test bank for demos
                "name": "Test Community Bank",
                "location": "Test City, TS",
                "assets_size": "small"
            }
        }
        
        mock_data = {}
        
        for rssd_id, bank_info in mock_banks.items():
            mock_data[rssd_id] = self._generate_bank_data(bank_info)
            
        return mock_data
    
    def _generate_bank_data(self, bank_info: Dict[str, str]) -> Dict[str, Dict[str, Any]]:
        """
        Generate realistic Call Report data for a bank.
        
        Args:
            bank_info: Bank information including size category
            
        Returns:
            Dictionary of field_id to field data
        """
        size = bank_info["assets_size"]
        
        # Scale factors based on bank size
        scale_factors = {
            "large": {"assets": 2_000_000, "income": 25_000, "multiplier": 1.0},
            "medium": {"assets": 50_000, "income": 500, "multiplier": 0.5},
            "small": {"assets": 5_000, "income": 50, "multiplier": 0.1}
        }
        
        scale = scale_factors.get(size, scale_factors["small"])
        
        # Generate base values with some randomization
        base_assets = scale["assets"] * (0.8 + random.random() * 0.4)  # ±20% variation
        base_income = scale["income"] * (0.8 + random.random() * 0.4)
        
        # Generate realistic field data
        field_data = {}
        
        # Balance Sheet (RC) fields
        field_data["RCON2170"] = {  # Total Assets
            "value": Decimal(str(round(base_assets, 2))),
            "schedule": "RC",
            "field_name": "Total assets"
        }
        
        field_data["RCON3210"] = {  # Total Equity
            "value": Decimal(str(round(base_assets * 0.12, 2))),  # ~12% equity ratio
            "schedule": "RC", 
            "field_name": "Total bank equity capital"
        }
        
        field_data["RCON2200"] = {  # Total Deposits
            "value": Decimal(str(round(base_assets * 0.85, 2))),  # ~85% deposits
            "schedule": "RC",
            "field_name": "Total deposits"
        }
        
        field_data["RCON0071"] = {  # Securities
            "value": Decimal(str(round(base_assets * 0.25, 2))),  # ~25% securities
            "schedule": "RC",
            "field_name": "Securities"
        }
        
        field_data["RCON1400"] = {  # Total Loans
            "value": Decimal(str(round(base_assets * 0.65, 2))),  # ~65% loans
            "schedule": "RC",
            "field_name": "Total loans and leases"
        }
        
        # Income Statement (RI) fields
        field_data["RIAD4340"] = {  # Net Income
            "value": Decimal(str(round(base_income, 2))),
            "schedule": "RI",
            "field_name": "Net income"
        }
        
        field_data["RIAD4107"] = {  # Interest Income
            "value": Decimal(str(round(base_income * 2.5, 2))),  # Interest income ~2.5x net
            "schedule": "RI",
            "field_name": "Total interest income"
        }
        
        field_data["RIAD4073"] = {  # Interest Expense
            "value": Decimal(str(round(base_income * 0.8, 2))),  # Interest expense
            "schedule": "RI",
            "field_name": "Total interest expense"
        }
        
        field_data["RIAD4074"] = {  # Net Interest Income
            "value": Decimal(str(round(base_income * 1.7, 2))),  # Net interest income
            "schedule": "RI",
            "field_name": "Net interest income"
        }
        
        # Capital (RCR) fields
        field_data["RCON8274"] = {  # Tier 1 Capital
            "value": Decimal(str(round(base_assets * 0.14, 2))),  # ~14% Tier 1
            "schedule": "RCR",
            "field_name": "Tier 1 capital"
        }
        
        field_data["RCON0023"] = {  # Risk-Weighted Assets
            "value": Decimal(str(round(base_assets * 0.75, 2))),  # ~75% RWA
            "schedule": "RCR",
            "field_name": "Risk-weighted assets"
        }
        
        # Asset Quality (RCN) fields
        field_data["RCON5527"] = {  # Nonaccrual Loans
            "value": Decimal(str(round(base_assets * 0.005, 2))),  # ~0.5% nonaccrual
            "schedule": "RCN",
            "field_name": "Nonaccrual loans and leases"
        }
        
        return field_data
    
    def _validate_inputs(self, rssd_id: str, schedule: str, field_id: str) -> bool:
        """
        Validate input parameters.
        
        Args:
            rssd_id: Bank identifier
            schedule: FFIEC schedule 
            field_id: Field identifier
            
        Returns:
            True if inputs are valid
            
        Raises:
            ValueError: If inputs are invalid
        """
        if not rssd_id or not rssd_id.isdigit():
            raise ValueError("RSSD ID must be a numeric string")
            
        if not schedule or schedule.upper() not in VALID_SCHEDULES:
            raise ValueError(f"Invalid schedule: {schedule}")
            
        if not field_id or field_id.upper() not in VALID_FIELD_IDS:
            raise ValueError(f"Invalid field ID: {field_id}")
            
        return True
    
    def _get_field_data(self, rssd_id: str, schedule: str, field_id: str) -> Dict[str, Any]:
        """
        Get field data for specified bank and field.
        
        Args:
            rssd_id: Bank identifier
            schedule: FFIEC schedule
            field_id: Field identifier
            
        Returns:
            Field data dictionary
        """
        field_id = field_id.upper()
        schedule = schedule.upper()
        
        bank_data = self.mock_data.get(rssd_id, {})
        if not bank_data:
            raise ValueError(f"Bank with RSSD ID {rssd_id} not found")
            
        field_data = bank_data.get(field_id, {})
        if not field_data:
            # Return None value for valid but unavailable fields
            field_info = get_field_info(field_id)
            if field_info:
                return {
                    "field_id": field_id,
                    "field_name": field_info["field_name"],
                    "value": None,
                    "schedule": schedule,
                    "report_date": str(date.today().replace(day=1)),  # First of current month
                    "data_availability": "not_available"
                }
            else:
                raise ValueError(f"Unknown field ID: {field_id}")
        
        # Add metadata to field data
        return {
            "field_id": field_id,
            "field_name": field_data.get("field_name", ALL_FIELD_MAPPINGS.get(field_id, "Unknown")),
            "value": float(field_data["value"]) if field_data["value"] is not None else None,
            "schedule": field_data["schedule"],
            "report_date": str(date.today().replace(day=1)),  # First of current month
            "data_availability": "available"
        }
    
    async def execute(
        self, 
        rssd_id: str,
        schedule: str, 
        field_id: str
    ) -> Dict[str, Any]:
        """
        Execute Call Report data retrieval.
        
        Args:
            rssd_id: Bank identifier (RSSD ID)
            schedule: FFIEC schedule identifier (e.g., "RC", "RI")
            field_id: Field identifier (e.g., "RCON2170")
            
        Returns:
            Dictionary with field data or raises exception on error
        """
        start_time = datetime.now(timezone.utc)
        
        try:
            self.logger.info(
                "Retrieving Call Report data",
                rssd_id=rssd_id,
                schedule=schedule,
                field_id=field_id
            )
            
            # Validate inputs
            self._validate_inputs(rssd_id, schedule, field_id)
            
            # Simulate API latency
            await asyncio.sleep(0.1 + random.random() * 0.2)  # 100-300ms delay
            
            # Get field data
            field_data = self._get_field_data(rssd_id, schedule, field_id)
            
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            self.logger.info(
                "Call Report data retrieved successfully",
                rssd_id=rssd_id,
                field_id=field_id,
                execution_time=execution_time,
                data_available=field_data.get("data_availability") == "available"
            )
            
            return field_data
            
        except ValueError as e:
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            self.logger.warning(
                "Call Report data retrieval failed - validation error",
                rssd_id=rssd_id,
                field_id=field_id,
                error=str(e),
                execution_time=execution_time
            )
            
            raise e
            
        except Exception as e:
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            self.logger.error(
                "Call Report data retrieval failed - unexpected error",
                rssd_id=rssd_id,
                field_id=field_id,
                error=str(e),
                execution_time=execution_time
            )
            
            raise RuntimeError(f"Failed to retrieve Call Report data: {str(e)}")
    
    
    def get_available_banks(self) -> Dict[str, Dict[str, str]]:
        """
        Get list of available banks in mock data.
        
        Returns:
            Dictionary of RSSD ID to bank information
        """
        bank_info = {}
        for rssd_id, data in self.mock_data.items():
            # Extract bank name from first field or use default
            bank_info[rssd_id] = {
                "rssd_id": rssd_id,
                "name": f"Mock Bank {rssd_id}",  # Mock names for privacy
                "data_fields": len([f for f in data.keys() if isinstance(data[f], dict)])
            }
        return bank_info
    
    def is_available(self) -> bool:
        """Check if the mock API is available."""
        return bool(self.mock_data)