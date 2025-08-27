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
🏛️ Bank Search → fdic_institution_search  
📊 Financial Data → fdic_financial_data (DEFAULT for most ratios)
📋 Call Reports → ffiec_call_report_data (SPECIFIC capital ratios ONLY)

CAPITAL RATIO ROUTING:
Use ffiec_call_report_data for these SPECIFIC ratios with field filtering:

• CET1 Ratio → schedules=["RCRI"], specific_fields=["RCON8274", "RCON3792", "RCON7273"]
• Tier 1 Capital Ratio → schedules=["RCRI"], specific_fields=["RCON8275", "RCON3792", "RCON7274"] 
• Total Capital Ratio → schedules=["RCRI"], specific_fields=["RCON8276", "RCON3792", "RCON7275"]
• Tier 1 Leverage Ratio → schedules=["RCRI", "RCK"], specific_fields=["RCON8275", "RCOA3368", "RCON7204"]

ALWAYS use specific_fields parameter for capital ratios to get only the 3-4 fields needed instead of 50+ fields.

ALL OTHER FINANCIAL QUERIES → fdic_financial_data (ROA, ROE, efficiency, etc.)

Tools: {tools_text}"""
    
    if not use_general_knowledge:
        routing_rules += "\n\nDOCUMENT-ONLY MODE: Only use rag_search results + banking data. No general knowledge."
    
    return routing_rules