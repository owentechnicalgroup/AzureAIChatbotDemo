"""
DEPRECATED: bank_lookup_tool.py

This tool has been replaced by clean atomic FDIC tools:
- fdic_institution_search_tool.py (for institution discovery)
- fdic_financial_data_tool.py (for financial data retrieval)

The original bank_lookup_tool was misnamed and had several issues:
1. Name implied lookup of known banks, but actually did search/discovery
2. Used regex without proper import
3. Returned formatted text instead of structured data
4. Complex fuzzy matching logic that wasn't needed
5. Mixed concerns (search + formatting)

New architecture provides:
- Clear separation of concerns
- Structured JSON output (no string parsing)
- Simplified CERT-based flow
- Tool graph ready
- Proper naming that reflects functionality

Migration Guide:
- Replace bank_lookup_tool calls with fdic_institution_search_tool
- Use extract_cert_from_search() to get CERT numbers from results
- Use fdic_financial_data_tool with CERT for financial analysis

For backwards compatibility, this file will remain but is deprecated.
"""

# Re-export the old tool for compatibility if needed
import warnings
from .bank_lookup_tool import BankLookupTool

warnings.warn(
    "bank_lookup_tool is deprecated. Use fdic_institution_search_tool and fdic_financial_data_tool instead.",
    DeprecationWarning,
    stacklevel=2
)

# Keep class available for backwards compatibility
__all__ = ['BankLookupTool']