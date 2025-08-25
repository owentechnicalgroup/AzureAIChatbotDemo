"""
Composite tools - multi-step workflow orchestration tools.

These tools coordinate multiple atomic tools to complete complex
workflows in a single tool call.

DEPRECATION NOTICE:
BankAnalysisTool has been deprecated in favor of atomic tool composition
via agent executor with 24 specialized FDIC analysis types for better
performance and flexibility.
"""

# Deprecated: Use atomic fdic_institution_search_tool + fdic_financial_data_tool with agent executor
# from .bank_analysis_tool import BankAnalysisTool

__all__ = [
    # "BankAnalysisTool"  # Deprecated
]