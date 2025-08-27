"""
Optimized tool routing instructions for ChatbotAgent.
Extracted from main agent to reduce system prompt size and improve performance.
"""

def get_tool_routing_instructions(use_general_knowledge: bool, tools: list) -> str:
    """Generate concise tool routing instructions."""
    
    # Build tool list efficiently
    tool_list = []
    for tool in tools:
        name = getattr(tool, 'name', 'unknown')
        desc = getattr(tool, 'description', 'No description')[:50] + "..."
        tool_list.append(f"- {name}: {desc}")
    
    tools_text = "\n".join(tool_list) if tool_list else "No tools available"
    
    # Concise routing rules with FDIC priority and specific call report usage
    routing_rules = f"""
TOOL ROUTING (General Knowledge: {'ON' if use_general_knowledge else 'OFF'}):

🔍 Documents/Policies → rag_search
🏛️ Bank Search → fdic_institution_search (try exact name first, then variations)
📊 Financial Data → fdic_financial_data (FIRST CHOICE - comprehensive financial metrics)
📋 Call Reports → ffiec_call_report_data (ONLY for specific capital ratios when requested)

PRIORITIZATION RULES:
1. ALWAYS use fdic_financial_data FIRST for ALL financial questions
2. NEVER use ffiec_call_report_data unless user explicitly mentions these EXACT terms:
   • "CET1", "Common Equity Tier 1", "Tier 1 Capital", "Total Capital Ratio", "Leverage Ratio", "Capital Adequacy"
3. If user asks for "financial data", "performance", "ratios" (generic) → use fdic_financial_data
4. If user asks for "capital ratios" without specifying which ones → use fdic_financial_data

CRITICAL: RSSD ID HANDLING
When using ffiec_call_report_data, ALWAYS use the EXACT RSSD ID from fdic_institution_search results.
DO NOT use CERT numbers or other identifiers - only RSSD ID.

CAPITAL RATIO WORKFLOW:
1. First: Use fdic_institution_search to get bank's RSSD ID
2. Then: Use ffiec_call_report_data with that EXACT RSSD ID

CAPITAL RATIO ROUTING (when specifically requested):
• CET1 Ratio → schedules=["RCRI"], specific_fields=["RCOAP793", "RCOAP859", "RCOAA223"]  
• Tier 1 Capital Ratio → schedules=["RCRI"], specific_fields=["RCOA7206", "RCOA8274", "RCOAA223"]
• Total Capital Ratio → schedules=["RCRI"], specific_fields=["RCOA7205", "RCOA3792", "RCOAA223"] 
• Tier 1 Leverage Ratio → schedules=["RCRI"], specific_fields=["RCOA7204", "RCOA8274", "RCOAA224"]

DEFAULT: Use fdic_financial_data for ROA, ROE, efficiency, profitability, asset quality, etc.

Tools: {tools_text}"""
    
    if not use_general_knowledge:
        routing_rules += "\n\nDOCUMENT-ONLY MODE: Only use rag_search results + banking data. No general knowledge."
    
    return routing_rules