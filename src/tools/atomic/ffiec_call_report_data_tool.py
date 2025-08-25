"""
Atomic FFIEC Call Report Data Tool.

Clean, focused tool for retrieving call report data using FFIEC CDR Public Data Distribution API.
Requires RSSD ID from institution search tool.
"""

import asyncio
import json
import xml.etree.ElementTree as ET
from typing import Optional, Type, Dict, Any
from datetime import datetime, timezone

import structlog
from pydantic import BaseModel, Field
from langchain.tools import BaseTool
from langchain.callbacks.manager import (
    AsyncCallbackManagerForToolRun,
    CallbackManagerForToolRun,
)

from ..infrastructure.banking.ffiec_cdr_api_client import FFIECCDRAPIClient
from ..infrastructure.banking.ffiec_cdr_models import FFIECCallReportRequest

logger = structlog.get_logger(__name__).bind(log_type="SYSTEM")


class FFIECCallReportDataTool(BaseTool):
    """
    Atomic tool for retrieving FFIEC Call Report data.
    
    Provides clean, focused call report data retrieval using FFIEC CDR Public Data
    Distribution SOAP API. Requires RSSD ID from institution search - no complex
    coordination logic.
    
    Key Features:
    - Direct RSSD-based call report retrieval
    - FFIEC Discovery API for latest filing detection with quarter-based fallback
    - Multiple format support (SDF, XBRL, PDF)
    - Real FFIEC regulatory data
    - Session-based caching for performance
    - Comprehensive error handling and automatic fallbacks
    
    Format Options:
    - SDF: Structured Data Format (default - reliable structured data)
    - XBRL: eXtensible Business Reporting Language format (XML-based structured data)
    - PDF: Standard portable document format (not suitable for data extraction)
    
    Input Requirements:
    - rssd_id: Bank RSSD identifier (from fdic_institution_search_tool)
    
    Example Usage:
    - rssd_id="451965" → Wells Fargo latest call report
    - rssd_id="451965", format="XBRL" → Wells Fargo in XBRL format
    - rssd_id="451965", reporting_period="2024-06-30" → Specific quarter
    
    Output: Call report metadata and retrieval confirmation
    """
    
    name: str = "ffiec_call_report_data"
    description: str = """Retrieve and parse FFIEC Call Report and UBPR data for banking institutions with comprehensive analysis.

This enhanced tool retrieves official FFIEC data from the FFIEC CDR Public Data Distribution 
service and automatically extracts financial information from structured formats.

Required Input:
- rssd_id: Bank RSSD identifier (obtained from fdic_institution_search_tool)

Optional Parameters:
- reporting_period: Specific reporting period (YYYY-MM-DD format) or None for latest available  
- data_type: 'call_report' for raw regulatory data or 'ubpr' for processed performance ratios (default: call_report)
- facsimile_format: Output format - SDF, XBRL, or PDF (default: SDF for call reports, XBRL for UBPR)

Data Types Available:
1. Call Report Data (raw regulatory filings):
   - Balance sheet items: Total Assets, Cash, Loans, Securities
   - Format: SDF (structured), XBRL (XML), or PDF
   
2. UBPR Data (Uniform Bank Performance Report):
   - Performance ratios: ROE, ROA, Net Interest Margin
   - Capital ratios: Tier 1, Total Capital, Leverage
   - Asset quality: NPL ratios, Loan loss provisions
   - Format: XBRL only (processed financial metrics)

Use Cases:
1. Performance Analysis: Get key financial ratios and peer comparisons (UBPR)
2. Balance Sheet Analysis: Get raw asset and liability data (Call Reports)
3. Regulatory Compliance: Access official FFIEC filing data
4. Historical Trending: Compare performance across reporting periods
5. Risk Assessment: Analyze capital adequacy and asset quality metrics

Discovery Method:
- Primary: FFIEC Discovery API for real-time filing availability
- Fallback: Quarter-based search for reliability when API is unavailable  
- UBPR: Extended 8-quarter search (2 years) due to quarterly publication schedule

Returns: Structured response with parsed financial data, formatted ratios/amounts, and metadata"""

    args_schema: Type[BaseModel] = FFIECCallReportRequest
    
    def __init__(self, **kwargs):
        """Initialize the FFIEC Call Report data tool with CDR API integration."""
        super().__init__(**kwargs)
        
        # Get settings from kwargs or use defaults
        from src.config.settings import get_settings
        settings = kwargs.get('settings') or get_settings()
        
        # Initialize FFIEC CDR API client - use private attributes to avoid Pydantic conflicts
        if settings.ffiec_cdr_api_key and settings.ffiec_cdr_username:
            object.__setattr__(self, '_ffiec_client', FFIECCDRAPIClient(
                api_key=settings.ffiec_cdr_api_key,
                username=settings.ffiec_cdr_username,
                timeout=getattr(settings, 'ffiec_cdr_timeout_seconds', 30),
                cache_ttl=getattr(settings, 'ffiec_cdr_cache_ttl', 3600)
            ))
            object.__setattr__(self, '_is_available', True)
        else:
            object.__setattr__(self, '_ffiec_client', None)
            object.__setattr__(self, '_is_available', False)
            logger.warning("FFIEC CDR API credentials not configured - tool will not be available")
        
        logger.info("FFIEC Call Report data tool initialized", 
                   available=self._is_available)
    
    @property
    def ffiec_client(self) -> Optional[FFIECCDRAPIClient]:
        """Get FFIEC CDR API client."""
        return getattr(self, '_ffiec_client', None)
    
    def is_available(self) -> bool:
        """Check if FFIEC CDR service is available."""
        return getattr(self, '_is_available', False) and self.ffiec_client is not None
    
    async def _get_most_recent_filing(self, rssd_id: str, max_periods_back: int = 4) -> tuple[Optional[str], Optional[bytes]]:
        """
        Get the most recent filing by checking recent quarters sequentially.
        
        More reliable than FFIEC discovery API which can have server errors.
        Checks the last 4 quarters starting from the most recent completed quarter.
        
        Args:
            rssd_id: Bank RSSD identifier
            max_periods_back: Number of quarters to check backwards
            
        Returns:
            Tuple of (reporting_period, call_report_data) or (None, None) if not found
        """
        from datetime import date
        
        logger.info(f"Finding most recent filing using quarter-based search", rssd_id=rssd_id)
        
        # Calculate most recent completed quarter end
        # Call reports are filed quarterly: Q1 (Mar 31), Q2 (Jun 30), Q3 (Sep 30), Q4 (Dec 31)
        today = date.today()
        
        # Determine the most recent COMPLETED quarter
        # Banks typically have 30-70 days after quarter end to file, so be conservative
        if today.month >= 6 and today.day >= 15:  # Mid-June or later - Q1 definitely filed
            if today.month >= 9 and today.day >= 15:  # Mid-September or later - Q2 definitely filed  
                if today.month >= 12 and today.day >= 15:  # Mid-December or later - Q3 definitely filed
                    latest_quarter = date(today.year, 9, 30)  # Q3 of current year
                else:
                    latest_quarter = date(today.year, 6, 30)  # Q2 of current year
            else:
                latest_quarter = date(today.year, 3, 31)  # Q1 of current year
        else:
            # Before mid-June, assume Q4 of previous year is the latest completed
            latest_quarter = date(today.year - 1, 12, 31)  # Q4 of previous year
        
        logger.debug(f"Starting search from quarter {latest_quarter}", rssd_id=rssd_id)
        
        # Check recent quarters sequentially
        quarters_to_check = []
        current_quarter = latest_quarter
        
        for i in range(max_periods_back):
            quarters_to_check.append(current_quarter)
            
            # Calculate previous quarter end date properly
            if current_quarter.month == 12:  # Q4 -> Q3
                current_quarter = date(current_quarter.year, 9, 30)
            elif current_quarter.month == 9:  # Q3 -> Q2  
                current_quarter = date(current_quarter.year, 6, 30)
            elif current_quarter.month == 6:  # Q2 -> Q1
                current_quarter = date(current_quarter.year, 3, 31)
            elif current_quarter.month == 3:  # Q1 -> Q4 of previous year
                current_quarter = date(current_quarter.year - 1, 12, 31)
        
        for period_date in quarters_to_check:
            period_str = period_date.strftime("%Y-%m-%d")
            
            try:
                logger.debug(f"Checking period {period_str}", rssd_id=rssd_id)
                
                filing_data = await self.ffiec_client.retrieve_facsimile(
                    rssd_id=rssd_id,
                    reporting_period=period_str,
                    format_type="SDF"
                )
                
                if filing_data:
                    logger.info(
                        f"Found filing for period {period_str}",
                        rssd_id=rssd_id,
                        period=period_str,
                        data_size=len(filing_data)
                    )
                    return period_str, filing_data
                    
            except Exception as e:
                logger.debug(
                    f"No filing found for period {period_str}",
                    rssd_id=rssd_id,
                    period=period_str,
                    error=str(e)
                )
                continue
        
        logger.warning(f"No recent filings found in last {max_periods_back} quarters", rssd_id=rssd_id)
        return None, None
    
    def _parse_xbrl_data(self, xbrl_data: bytes) -> Dict[str, Any]:
        """
        Parse XBRL data to extract balance sheet information.
        
        Args:
            xbrl_data: Raw XBRL data as bytes
            
        Returns:
            Dictionary containing parsed balance sheet data
        """
        try:
            # First, analyze the data structure and detect compression
            import gzip
            import zipfile
            import zlib
            from io import BytesIO
            
            logger.debug(
                "Analyzing XBRL data structure",
                data_size=len(xbrl_data),
                first_16_bytes=xbrl_data[:16].hex() if len(xbrl_data) >= 16 else xbrl_data.hex(),
                starts_with_xml=xbrl_data.startswith(b'<?xml') or xbrl_data.startswith(b'<xbrl'),
                starts_with_gzip=xbrl_data.startswith(b'\x1f\x8b'),
                starts_with_zip=xbrl_data.startswith(b'PK')
            )
            
            original_data_size = len(xbrl_data)
            decompression_method = "none"
            
            # Try multiple decompression methods
            
            # Method 1: Check for gzip compression
            if xbrl_data.startswith(b'\x1f\x8b'):
                try:
                    xbrl_data = gzip.decompress(xbrl_data)
                    decompression_method = "gzip"
                    logger.debug("Successfully decompressed gzip XBRL data", 
                               original_size=original_data_size, 
                               decompressed_size=len(xbrl_data))
                except Exception as gz_error:
                    logger.warning("Failed to decompress gzip data", error=str(gz_error))
            
            # Method 2: Check for ZIP file
            elif xbrl_data.startswith(b'PK'):
                try:
                    with zipfile.ZipFile(BytesIO(xbrl_data)) as zip_file:
                        # Look for XML files in the ZIP
                        xml_files = [f for f in zip_file.namelist() if f.endswith('.xml') or f.endswith('.xbrl')]
                        if xml_files:
                            # Use the first XML file found
                            xbrl_data = zip_file.read(xml_files[0])
                            decompression_method = f"zip:{xml_files[0]}"
                            logger.debug(f"Successfully extracted {xml_files[0]} from ZIP archive",
                                       original_size=original_data_size,
                                       decompressed_size=len(xbrl_data))
                        else:
                            logger.warning("No XML files found in ZIP archive")
                            return {
                                'parsing_successful': False,
                                'error': "ZIP archive contains no XML/XBRL files"
                            }
                except Exception as zip_error:
                    logger.warning("Failed to extract ZIP data", error=str(zip_error))
            
            # Method 3: Try raw deflate decompression (sometimes ZIP data is just deflated)
            elif not (xbrl_data.startswith(b'<?xml') or xbrl_data.startswith(b'<xbrl')):
                try:
                    # Try zlib decompression (raw deflate)
                    xbrl_data = zlib.decompress(xbrl_data)
                    decompression_method = "deflate"
                    logger.debug("Successfully decompressed deflate XBRL data",
                               original_size=original_data_size,
                               decompressed_size=len(xbrl_data))
                except Exception as deflate_error:
                    logger.debug("Deflate decompression failed", error=str(deflate_error))
                    
                    # Method 4: Try zlib decompression with window bits (for gzip without header)
                    try:
                        xbrl_data = zlib.decompress(xbrl_data, -zlib.MAX_WBITS)
                        decompression_method = "deflate_raw"
                        logger.debug("Successfully decompressed raw deflate XBRL data",
                                   original_size=original_data_size,
                                   decompressed_size=len(xbrl_data))
                    except Exception as raw_deflate_error:
                        logger.debug("Raw deflate decompression failed", error=str(raw_deflate_error))
                        
                        # If the data doesn't look like XML at all, it might be corrupted
                        if not any(marker in xbrl_data[:100] for marker in [b'<', b'xml', b'xbrl']):
                            logger.error(
                                "XBRL data appears to be corrupted or in unknown format",
                                data_size=len(xbrl_data),
                                first_50_bytes_hex=xbrl_data[:50].hex(),
                                first_20_chars_escaped=repr(xbrl_data[:20].decode('latin-1', errors='replace'))
                            )
                            return {
                                'parsing_successful': False,
                                'error': "XBRL data appears to be corrupted, encrypted, or in an unsupported format",
                                'debug_info': {
                                    'original_size': original_data_size,
                                    'first_50_bytes_hex': xbrl_data[:50].hex(),
                                    'compression_attempts': ['gzip', 'zip', 'deflate', 'raw_deflate']
                                }
                            }
            
            # Now try to decode the text with multiple encoding strategies
            xbrl_str = None
            encoding_tried = []
            
            # List of encodings to try in order of likelihood for financial data
            encodings_to_try = [
                'utf-8', 
                'utf-8-sig',  # UTF-8 with BOM
                'latin-1',    # Common for older financial systems
                'cp1252',     # Windows Western European
                'iso-8859-1', # Latin-1
                'ascii'       # Last resort
            ]
            
            for encoding in encodings_to_try:
                try:
                    xbrl_str = xbrl_data.decode(encoding)
                    logger.debug(f"Successfully decoded XBRL data using {encoding} encoding")
                    break
                except UnicodeDecodeError as decode_error:
                    encoding_tried.append(f"{encoding}: {str(decode_error)}")
                    continue
                except Exception as e:
                    encoding_tried.append(f"{encoding}: {str(e)}")
                    continue
            
            # If all encodings failed, try to decode with error handling
            if xbrl_str is None:
                try:
                    xbrl_str = xbrl_data.decode('utf-8', errors='replace')
                    logger.warning("Decoded with error replacement - some characters may be corrupted")
                except Exception as final_error:
                    logger.error(
                        "All encoding attempts failed", 
                        encodings_tried=encoding_tried,
                        final_error=str(final_error),
                        data_start=xbrl_data[:50].hex() if len(xbrl_data) >= 50 else xbrl_data.hex()
                    )
                    return {
                        'parsing_successful': False,
                        'error': f"Failed to decode XBRL data. Tried encodings: {', '.join([e.split(':')[0] for e in encoding_tried])}. Data appears to be binary or unsupported encoding.",
                        'debug_info': {
                            'data_size': len(xbrl_data),
                            'data_start_hex': xbrl_data[:20].hex() if len(xbrl_data) >= 20 else xbrl_data.hex(),
                            'encoding_attempts': encoding_tried
                        }
                    }
            
            # Parse the XML
            root = ET.fromstring(xbrl_str)
            
            # Define correct namespace mappings for Call Report XBRL
            namespaces = {
                'xbrli': 'http://www.xbrl.org/2003/instance',
                'xbrl': 'http://www.xbrl.org/2003/instance',
                'ffiec_call': 'http://www.ffiec.gov/xbrl/call/concepts',
                'link': 'http://www.xbrl.org/2003/linkbase'
            }
            
            logger.debug("Starting comprehensive Call Report XBRL parsing")
            
            # Extract ALL available Call Report elements dynamically
            balance_sheet_data = {}
            
            # Discover all Call Report elements in the XML
            all_call_elements = {}
            
            # Find all elements in the FFIEC call namespace
            for elem in root.iter():
                if 'ffiec.gov/xbrl/call/concepts' in elem.tag:
                    tag_name = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                    if elem.text and elem.text.strip():
                        context_ref = elem.get('contextRef', '')
                        unit_ref = elem.get('unitRef', '')
                        
                        # Group by element code and select most recent context
                        if tag_name not in all_call_elements:
                            all_call_elements[tag_name] = {
                                'element': elem,
                                'context': context_ref,
                                'unit': unit_ref,
                                'value': elem.text.strip()
                            }
                        else:
                            # Keep the one with the most recent context
                            if context_ref > all_call_elements[tag_name]['context']:
                                all_call_elements[tag_name] = {
                                    'element': elem,
                                    'context': context_ref,
                                    'unit': unit_ref,
                                    'value': elem.text.strip()
                                }
            
            logger.debug("Found total Call Report elements", total_found=len(all_call_elements))
            
            # Process all discovered Call Report elements
            elements_found = 0
            logger.debug("Processing all Call Report elements")
            
            for element_code, element_info in all_call_elements.items():
                try:
                    # Use the already discovered element info
                    element = element_info['element']
                    value = element_info['value']
                    unit_ref = element_info['unit']
                    context_ref = element_info['context']
                    
                    # Process the element value
                    if value and value.strip() and value.strip() not in ['', '0000', 'N/A', 'null']:
                        try:
                            # Clean the value
                            clean_value = value.strip()
                            
                            # Remove common formatting characters
                            clean_value = clean_value.replace(',', '').replace('$', '').replace('%', '')
                            
                            # Handle leading zeros but preserve decimals
                            if '.' in clean_value:
                                clean_value = clean_value.lstrip('0') or '0'
                            else:
                                clean_value = clean_value.lstrip('0') or '0'
                            
                            # Handle negative values in parentheses
                            if clean_value.startswith('(') and clean_value.endswith(')'):
                                clean_value = '-' + clean_value[1:-1]
                            
                            numeric_value = float(clean_value)
                            
                            # Use element code as field name (lowercase for consistency)
                            field_name = element_code.lower()
                            
                            # Store the raw value and metadata
                            balance_sheet_data[field_name] = numeric_value
                            balance_sheet_data[f"{field_name}_unit"] = unit_ref
                            balance_sheet_data[f"{field_name}_context"] = context_ref
                            elements_found += 1
                            
                            # Format based on unit type
                            if unit_ref == 'PURE':
                                # These are ratios/percentages
                                if abs(numeric_value) < 1:
                                    # Decimal format (0.15 = 15%)
                                    display_value = numeric_value * 100
                                else:
                                    # Already in percentage format
                                    display_value = numeric_value
                                balance_sheet_data[f"{field_name}_formatted"] = f"{display_value:.2f}%"
                                
                            elif unit_ref == 'USD':
                                # Dollar amounts in thousands (Call Report standard)
                                dollar_amount = numeric_value * 1000
                                balance_sheet_data[f"{field_name}_formatted"] = self._format_currency(dollar_amount)
                                
                            elif unit_ref == 'NON-MONETARY':
                                # Count or other non-monetary values
                                balance_sheet_data[f"{field_name}_formatted"] = f"{numeric_value:,.0f}"
                                
                            else:
                                # Default formatting
                                if abs(numeric_value) >= 1000:
                                    balance_sheet_data[f"{field_name}_formatted"] = f"{numeric_value:,.0f}"
                                else:
                                    balance_sheet_data[f"{field_name}_formatted"] = f"{numeric_value:.2f}"
                            
                            # Log successful extraction (only for first few to avoid spam)
                            if elements_found <= 10:
                                logger.debug(f"Extracted Call Report {element_code}: {value} ({unit_ref})",
                                           context=context_ref,
                                           formatted_value=balance_sheet_data.get(f"{field_name}_formatted", "N/A"))
                            
                        except (ValueError, TypeError) as parse_error:
                            logger.debug(f"Could not parse Call Report {element_code} value '{value}': {parse_error}")
                            continue
                            
                except Exception as element_error:
                    logger.debug(f"Error processing Call Report element {element_code}: {element_error}")
                    continue
            
            # Add metadata
            balance_sheet_data['parsing_successful'] = True
            balance_sheet_data['elements_found'] = elements_found
            balance_sheet_data['total_elements_available'] = len(all_call_elements)
            balance_sheet_data['format_used'] = 'COMPREHENSIVE_CALL_REPORT_XBRL'
            
            success_rate = f"{elements_found/len(all_call_elements)*100:.1f}%" if all_call_elements else "0%"
            logger.info("Comprehensive Call Report XBRL parsing completed", 
                       elements_found=elements_found,
                       total_available=len(all_call_elements),
                       success_rate=success_rate)
            
            return balance_sheet_data
            
        except ET.ParseError as parse_error:
            logger.error(
                "XBRL parsing failed - invalid XML structure", 
                error=str(parse_error),
                xml_snippet=xbrl_str[:200] if xbrl_str else "Could not decode data"
            )
            return {
                'parsing_successful': False,
                'error': f"Invalid XBRL XML format: {str(parse_error)}",
                'debug_info': {
                    'xml_decode_successful': xbrl_str is not None,
                    'xml_snippet': xbrl_str[:200] if xbrl_str else None
                }
            }
        except UnicodeDecodeError as unicode_error:
            logger.error(
                "XBRL parsing failed - encoding issue", 
                error=str(unicode_error),
                error_position=getattr(unicode_error, 'start', None),
                problematic_byte=f"0x{xbrl_data[unicode_error.start]:02x}" if hasattr(unicode_error, 'start') and unicode_error.start < len(xbrl_data) else None
            )
            return {
                'parsing_successful': False,
                'error': f"Encoding error: {str(unicode_error)}",
                'debug_info': {
                    'error_position': getattr(unicode_error, 'start', None),
                    'data_size': len(xbrl_data),
                    'data_start_hex': xbrl_data[:20].hex() if len(xbrl_data) >= 20 else xbrl_data.hex()
                }
            }
        except Exception as e:
            logger.error("XBRL parsing failed", error=str(e), error_type=type(e).__name__)
            return {
                'parsing_successful': False,
                'error': f"XBRL parsing error: {str(e)}",
                'debug_info': {
                    'error_type': type(e).__name__,
                    'data_size': len(xbrl_data)
                }
            }
    
    def _parse_sdf_data(self, sdf_data: bytes, rssd_id: str = None) -> Dict[str, Any]:
        """
        Parse SDF (Structured Data Format) to extract balance sheet information.
        
        SDF is typically a tab-delimited or pipe-delimited format used by FFIEC
        for structured call report data.
        
        Args:
            sdf_data: Raw SDF data as bytes
            
        Returns:
            Dictionary containing parsed balance sheet data
        """
        try:
            # Decode the SDF data
            sdf_str = None
            encodings_to_try = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']
            
            for encoding in encodings_to_try:
                try:
                    sdf_str = sdf_data.decode(encoding)
                    logger.debug(f"Successfully decoded SDF data using {encoding} encoding")
                    break
                except UnicodeDecodeError:
                    continue
            
            if sdf_str is None:
                sdf_str = sdf_data.decode('utf-8', errors='replace')
                logger.warning("SDF decoded with error replacement - some characters may be corrupted")
            
            balance_sheet_data = {}
            lines = sdf_str.split('\n')
            
            # Based on test data, SDF format is semicolon-delimited with headers:
            # Call Date;Bank RSSD Identifier;MDRM #;Value;Last Update;Short Definition;Call Schedule;Line Number
            
            # Look for common call report MDRM codes for balance sheet items
            balance_sheet_mdrm_codes = {
                # Total Assets 
                'RCFD2170': 'total_assets',  # Total Assets
                'RCON2170': 'total_assets',  # Total Assets (consolidated)
                'RCFA2170': 'total_assets',  # Total Assets (alternative)
                
                # Cash and Cash Equivalents
                'RCFD0010': 'cash_and_equivalents',  # Cash and balances due from depository institutions
                'RCON0010': 'cash_and_equivalents',
                'RCFA0010': 'cash_and_equivalents',
                
                # Loans
                'RCFD1400': 'total_loans',  # Total loans and lease financing receivables
                'RCON1400': 'total_loans',
                'RCFA1400': 'total_loans',
                'RCFD2122': 'total_loans_net',  # Total loans net of unearned income and allowances
                'RCON2122': 'total_loans_net',
                
                # Securities
                'RCFD1773': 'securities',  # Total securities
                'RCON1773': 'securities',
                'RCFA1773': 'securities',
                'RCFD1754': 'securities_afs',  # Available-for-sale securities
                'RCFD1771': 'securities_htm',  # Held-to-maturity securities
            }
            
            # Parse semicolon-delimited SDF data
            header_found = False
            data_rows = 0
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Check if this is the header line
                if 'Call Date;Bank RSSD Identifier;MDRM' in line or 'MDRM #;Value' in line:
                    header_found = True
                    logger.debug("Found SDF header line", line_preview=line[:100])
                    continue
                
                if not header_found:
                    continue
                
                # Split by semicolon
                if ';' in line:
                    parts = [p.strip() for p in line.split(';')]
                    if len(parts) >= 4:  # Need at least: Date, RSSD, MDRM, Value
                        data_rows += 1
                        
                        try:
                            # SDF format: Call Date;Bank RSSD Identifier;MDRM #;Value;...
                            call_date = parts[0] if len(parts) > 0 else ''
                            rssd_id_check = parts[1] if len(parts) > 1 else ''
                            mdrm_code = parts[2].upper() if len(parts) > 2 else ''
                            value_str = parts[3] if len(parts) > 3 else ''
                            
                            # Verify this is the right bank
                            if rssd_id_check and rssd_id_check != rssd_id:
                                continue
                            
                            # Check if this MDRM code is one we want
                            if mdrm_code in balance_sheet_mdrm_codes:
                                field_name = balance_sheet_mdrm_codes[mdrm_code]
                                
                                try:
                                    # Parse the value (already in actual dollars, not thousands)
                                    clean_value = value_str.replace(',', '').replace('$', '').strip()
                                    if clean_value and clean_value != '0' and clean_value != '':
                                        value = float(clean_value)
                                        
                                        # Only update if we haven't found this field yet (prefer first occurrence)
                                        if field_name not in balance_sheet_data:
                                            balance_sheet_data[field_name] = value
                                            balance_sheet_data[f"{field_name}_formatted"] = self._format_currency(value)
                                            logger.debug(f"Found {field_name}: {clean_value} -> {value}", 
                                                       mdrm_code=mdrm_code, call_date=call_date)
                                
                                except (ValueError, TypeError) as parse_error:
                                    logger.debug(f"Could not parse value for {mdrm_code}: {value_str}", error=str(parse_error))
                                    continue
                        
                        except Exception as row_error:
                            logger.debug(f"Error parsing SDF row", error=str(row_error), line_preview=line[:100])
                            continue
            
            # Add metadata
            balance_sheet_data['parsing_successful'] = True
            balance_sheet_data['elements_found'] = len([k for k in balance_sheet_data.keys() 
                                                      if not k.endswith('_formatted') and k not in ['parsing_successful', 'elements_found', 'format_used', 'data_rows_processed']])
            balance_sheet_data['format_used'] = 'SDF'
            balance_sheet_data['data_rows_processed'] = data_rows
            
            logger.info("SDF parsing completed", 
                       elements_found=balance_sheet_data.get('elements_found', 0),
                       data_rows_processed=balance_sheet_data.get('data_rows_processed', 0))
            
            return balance_sheet_data
            
        except Exception as e:
            logger.error("SDF parsing failed", error=str(e))
            return {
                'parsing_successful': False,
                'error': f"SDF parsing error: {str(e)}",
                'format_used': 'SDF'
            }
    
    def _parse_ubpr_xbrl_data(self, ubpr_data: bytes) -> Dict[str, Any]:
        """
        Parse UBPR XBRL data to extract ALL available performance ratios and metrics.
        
        Args:
            ubpr_data: Raw UBPR XBRL data as bytes
            
        Returns:
            Dictionary containing parsed UBPR performance data
        """
        try:
            logger.debug("Starting comprehensive UBPR XBRL parsing", data_size=len(ubpr_data))
            # Parse UBPR XBRL XML
            ubpr_str = ubpr_data.decode('utf-8')
            
            # Remove BOM if present
            if ubpr_str.startswith('\ufeff'):
                ubpr_str = ubpr_str[1:]
            
            logger.debug("Parsing XML", xml_length=len(ubpr_str))
            root = ET.fromstring(ubpr_str)
            logger.debug("XML parsed successfully")
            
            # Define correct namespace mappings for UBPR XBRL (based on actual Wells Fargo data analysis)
            namespaces = {
                'xbrli': 'http://www.xbrl.org/2003/instance',
                'xbrl': 'http://www.xbrl.org/2003/instance',  
                'ubpr': 'http://www.cdr.ffiec.gov/xbrl/ubpr/v174/Concepts',
                'ubpr_src': 'http://www.cdr.ffiec.gov/xbrl/ubpr/v174/SourceConcepts',
                'ubpr_core': 'http://www.cdr.ffiec.gov/xbrl/ubpr/v174/Core',
                'link': 'http://www.xbrl.org/2003/linkbase'
            }
            
            # Extract ALL available UBPR elements dynamically
            ubpr_parsed_data = {}
            
            # Discover all UBPR elements in the XML
            logger.debug("Discovering all UBPR elements in XML")
            all_ubpr_elements = {}
            
            # Find all elements that start with 'UBPR'
            for elem in root.iter():
                tag_name = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                if tag_name.startswith('UBPR') and elem.text:
                    context_ref = elem.get('contextRef', '')
                    unit_ref = elem.get('unitRef', '')
                    
                    # Group by element code and select most recent context
                    if tag_name not in all_ubpr_elements:
                        all_ubpr_elements[tag_name] = {
                            'element': elem,
                            'context': context_ref,
                            'unit': unit_ref,
                            'value': elem.text
                        }
                    else:
                        # Keep the one with the most recent context (sorted alphabetically, latest wins)
                        if context_ref > all_ubpr_elements[tag_name]['context']:
                            all_ubpr_elements[tag_name] = {
                                'element': elem,
                                'context': context_ref,
                                'unit': unit_ref,
                                'value': elem.text
                            }
            
            logger.debug("Found total UBPR elements", total_found=len(all_ubpr_elements))
            
            # Process all discovered UBPR elements
            elements_found = 0
            logger.debug("Processing all UBPR elements")
            
            for element_code, element_info in all_ubpr_elements.items():
                try:
                    # Use the already discovered element info
                    element = element_info['element']
                    value = element_info['value']
                    unit_ref = element_info['unit']
                    context_ref = element_info['context']
                    
                    # Process the element value
                    if value is not None and isinstance(value, str) and value.strip() and value.strip() not in ['', '0000', 'N/A', 'null']:
                        try:
                            # Clean the value - handle various formats
                            clean_value = value.strip()
                            
                            # Ensure clean_value is still a string after stripping
                            if not isinstance(clean_value, str) or not clean_value:
                                continue
                            
                            # Remove common formatting characters
                            clean_value = clean_value.replace(',', '').replace('$', '').replace('%', '')
                            
                            # Ensure clean_value is still valid after replacements
                            if not clean_value or not isinstance(clean_value, str):
                                continue
                            
                            # Handle leading zeros but preserve decimals
                            if '.' in clean_value:
                                clean_value = clean_value.lstrip('0') or '0'
                            else:
                                clean_value = clean_value.lstrip('0') or '0'
                            
                            # Handle negative values in parentheses
                            if clean_value.startswith('(') and clean_value.endswith(')'):
                                clean_value = '-' + clean_value[1:-1]
                            
                            numeric_value = float(clean_value)
                            
                            # Use element code as field name for comprehensive extraction
                            field_name = element_code.lower()
                            
                            # Store the raw value and metadata
                            ubpr_parsed_data[field_name] = numeric_value
                            ubpr_parsed_data[f"{field_name}_unit"] = unit_ref
                            ubpr_parsed_data[f"{field_name}_context"] = context_ref
                            elements_found += 1
                            
                            # Format based on unit type
                            if unit_ref == 'PURE':
                                # These are ratios/percentages 
                                if abs(numeric_value) < 1:
                                    # Decimal format (0.15 = 15%)
                                    display_value = numeric_value * 100
                                else:
                                    # Already in percentage format
                                    display_value = numeric_value
                                ubpr_parsed_data[f"{field_name}_formatted"] = f"{display_value:.2f}%"
                                
                            elif unit_ref == 'USD':
                                # Dollar amounts - check if they're in thousands based on magnitude
                                if abs(numeric_value) > 1000000:  # Values over 1M likely in actual dollars
                                    ubpr_parsed_data[f"{field_name}_formatted"] = self._format_currency(numeric_value)
                                else:
                                    # Smaller values might be in thousands
                                    dollar_amount = numeric_value * 1000
                                    ubpr_parsed_data[f"{field_name}_formatted"] = self._format_currency(dollar_amount)
                                
                            elif unit_ref == 'NON-MONETARY':
                                # Count or other non-monetary values
                                ubpr_parsed_data[f"{field_name}_formatted"] = f"{numeric_value:,.0f}"
                                
                            else:
                                # Default formatting for other metrics
                                if abs(numeric_value) >= 1000:
                                    ubpr_parsed_data[f"{field_name}_formatted"] = f"{numeric_value:,.0f}"
                                else:
                                    ubpr_parsed_data[f"{field_name}_formatted"] = f"{numeric_value:.2f}"
                            
                            # Log successful extraction (only for first few to avoid spam)
                            if elements_found <= 10:
                                logger.debug(f"Extracted UBPR {element_code}: {value} ({unit_ref})", 
                                           context=context_ref,
                                           formatted_value=ubpr_parsed_data.get(f"{field_name}_formatted", "N/A"))
                            
                        except (ValueError, TypeError) as parse_error:
                            logger.debug(f"Could not parse UBPR {element_code} value '{value}': {parse_error}")
                            continue
            
                except Exception as element_error:
                    logger.debug(f"Error processing element {element_code}: {element_error}")
                    continue
            
            # Add metadata
            ubpr_parsed_data['parsing_successful'] = True
            ubpr_parsed_data['elements_found'] = elements_found
            ubpr_parsed_data['total_elements_available'] = len(all_ubpr_elements)
            ubpr_parsed_data['format_used'] = 'COMPREHENSIVE_UBPR_XBRL'
            
            success_rate = f"{elements_found/len(all_ubpr_elements)*100:.1f}%" if all_ubpr_elements else "0%"
            logger.info("Comprehensive UBPR XBRL parsing completed", 
                       elements_found=elements_found,
                       total_available=len(all_ubpr_elements),
                       success_rate=success_rate)
            
            return ubpr_parsed_data
            
        except ET.ParseError as parse_error:
            logger.error("UBPR XBRL parsing failed - invalid XML", error=str(parse_error))
            return {
                'parsing_successful': False,
                'error': f"Invalid UBPR XBRL XML format: {str(parse_error)}",
                'format_used': 'UBPR_XBRL'
            }
        except UnicodeDecodeError as decode_error:
            logger.error("UBPR XBRL decoding failed", error=str(decode_error))
            return {
                'parsing_successful': False,
                'error': f"UBPR XBRL encoding error: {str(decode_error)}",
                'format_used': 'UBPR_XBRL'
            }
        except Exception as e:
            logger.error("UBPR XBRL parsing failed", error=str(e))
            return {
                'parsing_successful': False,
                'error': f"UBPR XBRL parsing error: {str(e)}",
                'format_used': 'UBPR_XBRL'
            }
    
    def _format_currency(self, amount: float) -> str:
        """Format currency amount in billions/millions/thousands."""
        if amount >= 1_000_000_000:
            return f"${amount / 1_000_000_000:.1f}B"
        elif amount >= 1_000_000:
            return f"${amount / 1_000_000:.1f}M"
        elif amount >= 1_000:
            return f"${amount / 1_000:.1f}K"
        else:
            return f"${amount:,.0f}"
    
    def _run(self, 
             rssd_id: str,
             reporting_period: Optional[str] = None,
             facsimile_format: str = "SDF",
             data_type: str = "call_report",
             run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Synchronous wrapper for async call report retrieval."""
        try:
            # Try to get the current event loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is running, we need to create a task
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        self._arun(rssd_id, reporting_period, facsimile_format, data_type, None)
                    )
                    return future.result()
            else:
                # Loop exists but not running, we can use asyncio.run
                return asyncio.run(self._arun(rssd_id, reporting_period, facsimile_format, data_type, None))
        except RuntimeError:
            # No event loop, safe to use asyncio.run
            return asyncio.run(self._arun(rssd_id, reporting_period, facsimile_format, data_type, None))
    
    async def _arun(self,
                   rssd_id: str,
                   reporting_period: Optional[str] = None,
                   facsimile_format: str = "SDF",
                   data_type: str = "call_report",
                   run_manager: Optional[AsyncCallbackManagerForToolRun] = None) -> str:
        """
        Retrieve FFIEC Call Report data for a bank.
        
        Args:
            rssd_id: Bank RSSD identifier
            reporting_period: Specific reporting period or None for latest
            facsimile_format: Format type (PDF, XBRL, SDF)
            run_manager: LangChain callback manager
            
        Returns:
            Structured JSON response with call report data and metadata
        """
        start_time = datetime.now(timezone.utc)
        
        # Check if service is available
        if not self.is_available():
            return self._format_error(
                "FFIEC CDR service not available - API credentials not configured",
                error_code="SERVICE_UNAVAILABLE"
            )
        
        try:
            # Check if RSSD ID is N/A or unknown
            if rssd_id in ["N/A", "n/a", "NA", "na", "Not available", "Unknown", "None", ""]:
                logger.info(
                    "RSSD ID is not available, cannot retrieve FFIEC call report data",
                    provided_rssd=rssd_id,
                    suggestion="FFIEC data requires a valid RSSD ID - use bank_analysis tool for FDIC data instead"
                )
                return self._format_error(
                    "RSSD ID not available. FFIEC Call Report data requires a valid RSSD ID. Use bank_analysis tool for comprehensive bank data from FDIC instead.",
                    error_code="RSSD_NOT_AVAILABLE"
                )
            
            # Validate input
            request = FFIECCallReportRequest(
                rssd_id=rssd_id,
                reporting_period=reporting_period,
                facsimile_format=facsimile_format,
                data_type=data_type
            )
            
            logger.info(
                "Retrieving FFIEC data",
                rssd_id=rssd_id,
                reporting_period=reporting_period,
                format=facsimile_format,
                data_type=data_type
            )
            
            # Discover latest filing if no period specified
            actual_period = reporting_period
            call_report_data = None
            period_discovered = False
            
            if not actual_period:
                logger.debug(f"Finding most recent {data_type} filing using FFIEC Discovery API", rssd_id=rssd_id)
                
                # Choose discovery method based on data type
                if data_type == "ubpr":
                    discovered_period = await self.ffiec_client.discover_latest_ubpr_filing(rssd_id)
                else:
                    discovered_period = await self.ffiec_client.discover_latest_filing(rssd_id)
                
                if not discovered_period:
                    logger.warning("FFIEC Discovery API failed, falling back to quarter-based search", rssd_id=rssd_id)
                    
                    # Fallback to quarter-based search if discovery fails
                    discovered_period, discovered_data = await self._get_most_recent_filing(rssd_id)
                    
                    if not discovered_period:
                        return self._format_error(
                            f"No recent FFIEC call report filings found for RSSD ID {rssd_id} using either discovery method",
                            error_code="NO_FILINGS_FOUND",
                            rssd_id=rssd_id
                        )
                    
                    actual_period = discovered_period
                    call_report_data = discovered_data
                    period_discovered = True
                    
                    logger.info(
                        "Latest filing found using fallback quarter-based search",
                        rssd_id=rssd_id,
                        discovered_period=actual_period,
                        data_size=len(call_report_data) if call_report_data else 0
                    )
                else:
                    # Discovery API succeeded, now retrieve the actual data
                    actual_period = discovered_period
                    period_discovered = True
                    
                    logger.info(
                        "Latest filing period discovered via FFIEC Discovery API",
                        rssd_id=rssd_id,
                        discovered_period=actual_period
                    )
                    
                    # Retrieve data for discovered period based on data type
                    if data_type == "ubpr":
                        call_report_data = await self.ffiec_client.retrieve_ubpr_facsimile(
                            rssd_id=rssd_id,
                            reporting_period=actual_period
                        )
                    else:
                        call_report_data = await self.ffiec_client.retrieve_facsimile(
                            rssd_id=rssd_id,
                            reporting_period=actual_period,
                            format_type=facsimile_format.upper()
                        )
            else:
                # Retrieve data for specified period based on data type
                if data_type == "ubpr":
                    call_report_data = await self.ffiec_client.retrieve_ubpr_facsimile(
                        rssd_id=rssd_id,
                        reporting_period=actual_period
                    )
                else:
                    call_report_data = await self.ffiec_client.retrieve_facsimile(
                        rssd_id=rssd_id,
                        reporting_period=actual_period,
                        format_type=facsimile_format.upper()
                    )
            
            if not call_report_data:
                return self._format_error(
                    f"FFIEC call report data not available for RSSD ID {rssd_id} in period {actual_period}",
                    error_code="DATA_NOT_AVAILABLE",
                    rssd_id=rssd_id,
                    reporting_period=actual_period
                )
            
            # Parse structured data based on data type and format
            parsed_data = None
            if data_type == "ubpr":
                logger.info("Parsing UBPR XBRL data for performance metrics extraction", rssd_id=rssd_id)
                parsed_data = self._parse_ubpr_xbrl_data(call_report_data)
            elif facsimile_format.upper() == "SDF":
                logger.info("Parsing SDF data for balance sheet extraction", rssd_id=rssd_id)
                parsed_data = self._parse_sdf_data(call_report_data, rssd_id)
                
                # If SDF parsing failed completely, try XBRL format as fallback
                if parsed_data and not parsed_data.get("parsing_successful", False):
                    logger.warning("SDF parsing failed, attempting XBRL format as fallback", rssd_id=rssd_id)
                    try:
                        # Retrieve XBRL format
                        xbrl_data = await self.ffiec_client.retrieve_facsimile(
                            rssd_id=rssd_id,
                            reporting_period=actual_period,
                            format_type="XBRL"
                        )
                        if xbrl_data:
                            logger.info("Successfully retrieved XBRL format, parsing...", rssd_id=rssd_id)
                            xbrl_parsed_data = self._parse_xbrl_data(xbrl_data)
                            if xbrl_parsed_data and xbrl_parsed_data.get("parsing_successful", False):
                                parsed_data = xbrl_parsed_data
                                # Update format type to reflect what was actually used
                                facsimile_format = "XBRL"
                                call_report_data = xbrl_data
                                logger.info("XBRL fallback successful", rssd_id=rssd_id)
                    except Exception as xbrl_error:
                        logger.warning("XBRL fallback also failed", error=str(xbrl_error), rssd_id=rssd_id)
            elif facsimile_format.upper() == "XBRL":
                logger.info("Parsing XBRL data for balance sheet extraction", rssd_id=rssd_id)
                parsed_data = self._parse_xbrl_data(call_report_data)
                
                # If XBRL parsing failed completely, try SDF format as fallback
                if parsed_data and not parsed_data.get("parsing_successful", False):
                    logger.warning("XBRL parsing failed, attempting SDF format as fallback", rssd_id=rssd_id)
                    try:
                        # Retrieve SDF format
                        sdf_data = await self.ffiec_client.retrieve_facsimile(
                            rssd_id=rssd_id,
                            reporting_period=actual_period,
                            format_type="SDF"
                        )
                        if sdf_data:
                            logger.info("Successfully retrieved SDF format, parsing...", rssd_id=rssd_id)
                            sdf_parsed_data = self._parse_sdf_data(sdf_data, rssd_id)
                            if sdf_parsed_data and sdf_parsed_data.get("parsing_successful", False):
                                parsed_data = sdf_parsed_data
                                # Update format type to reflect what was actually used
                                facsimile_format = "SDF"
                                call_report_data = sdf_data
                                logger.info("SDF fallback successful", rssd_id=rssd_id)
                    except Exception as sdf_error:
                        logger.warning("SDF fallback also failed", error=str(sdf_error), rssd_id=rssd_id)
            
            # Calculate execution time
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            # Format successful response with parsed data
            return self._format_success(
                rssd_id=rssd_id,
                reporting_period=actual_period,
                format_type=facsimile_format.upper(),
                data_size=len(call_report_data),
                execution_time=execution_time,
                discovered_period=period_discovered,
                parsed_data=parsed_data
            )
            
        except ValueError as validation_error:
            logger.error(
                "Input validation failed",
                error=str(validation_error),
                rssd_id=rssd_id
            )
            return self._format_error(
                f"Invalid input: {str(validation_error)}",
                error_code="VALIDATION_ERROR",
                rssd_id=rssd_id
            )
            
        except Exception as e:
            error_context = "discovery and retrieval" if not reporting_period else "retrieval"
            logger.error(
                f"FFIEC call report {error_context} failed",
                error=str(e),
                rssd_id=rssd_id,
                reporting_period=reporting_period,
                used_discovery_api=not reporting_period
            )
            return self._format_error(
                f"FFIEC call report {error_context} failed: {str(e)}",
                error_code="RETRIEVAL_ERROR",
                rssd_id=rssd_id,
                reporting_period=reporting_period
            )
    
    def _format_success(self,
                       rssd_id: str,
                       reporting_period: str,
                       format_type: str,
                       data_size: int,
                       execution_time: float,
                       discovered_period: bool = False,
                       parsed_data: Optional[Dict[str, Any]] = None) -> str:
        """
        Format successful call report retrieval response.
        
        Args:
            rssd_id: Bank RSSD identifier
            reporting_period: Reporting period used
            format_type: Format type retrieved
            data_size: Size of data in bytes
            execution_time: Time taken for retrieval
            discovered_period: Whether period was discovered automatically
            parsed_data: Parsed balance sheet data if available
            
        Returns:
            JSON formatted success response
        """
        # Format data size
        if data_size < 1024:
            size_formatted = f"{data_size} bytes"
        elif data_size < 1024 * 1024:
            size_formatted = f"{data_size / 1024:.1f} KB"
        else:
            size_formatted = f"{data_size / (1024 * 1024):.1f} MB"
        
        # Assess quality based on size
        if data_size >= 100 * 1024:  # 100 KB+
            quality = "excellent"
        elif data_size >= 50 * 1024:  # 50 KB+
            quality = "good"
        elif data_size >= 10 * 1024:  # 10 KB+
            quality = "fair"
        else:
            quality = "poor"
        
        response = {
            "success": True,
            "rssd_id": rssd_id,
            "reporting_period": reporting_period,
            "format": format_type,
            "data_retrieved": True,
            "data_size": size_formatted,
            "data_quality": quality,
            "execution_time": f"{execution_time:.3f}s",
            "period_discovered": discovered_period,
            "retrieval_timestamp": datetime.now(timezone.utc).isoformat(),
            "data_source": "FFIEC CDR Public Data Distribution",
            "message": f"Successfully retrieved {format_type} call report for RSSD {rssd_id} from period {reporting_period}"
        }
        
        if discovered_period:
            response["discovery_note"] = f"Automatically discovered latest available filing period: {reporting_period}"
            # Add discovery method information based on context
            response["discovery_method"] = "FFIEC Discovery API with quarter-based fallback"
        
        # Add parsed balance sheet data if available
        if parsed_data:
            response["balance_sheet_data"] = parsed_data
            
            # Add summary if parsing was successful
            if parsed_data.get("parsing_successful", False):
                balance_sheet_summary = {}
                
                # Add each found balance sheet item to summary
                for key, value in parsed_data.items():
                    if key.endswith('_formatted') and not key.startswith('error'):
                        clean_key = key.replace('_formatted', '').replace('_', ' ').title()
                        balance_sheet_summary[clean_key] = value
                
                if balance_sheet_summary:
                    response["balance_sheet_summary"] = balance_sheet_summary
                    response["message"] += f" - Balance sheet data extracted with {parsed_data.get('elements_found', 0)} elements"
            else:
                response["balance_sheet_parsing_error"] = parsed_data.get("error", "Unknown parsing error")
        
        return json.dumps(response, indent=2)
    
    def _format_error(self,
                     error_message: str,
                     error_code: str,
                     rssd_id: Optional[str] = None,
                     reporting_period: Optional[str] = None) -> str:
        """
        Format error response.
        
        Args:
            error_message: Human-readable error message
            error_code: Machine-readable error code
            rssd_id: Bank RSSD identifier if available
            reporting_period: Reporting period if available
            
        Returns:
            JSON formatted error response
        """
        response = {
            "success": False,
            "error": error_message,
            "error_code": error_code,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": "FFIEC CDR Public Data Distribution"
        }
        
        if rssd_id:
            response["rssd_id"] = rssd_id
        
        if reporting_period:
            response["reporting_period"] = reporting_period
        
        return json.dumps(response, indent=2)
    
    async def test_connection(self) -> bool:
        """
        Test connection to FFIEC CDR service.
        
        Returns:
            True if connection successful, False otherwise
        """
        if not self.is_available():
            return False
        
        try:
            return await self.ffiec_client.test_connection()
        except Exception as e:
            logger.error("Connection test failed", error=str(e))
            return False