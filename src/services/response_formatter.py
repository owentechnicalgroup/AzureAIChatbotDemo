"""
Response formatting service for improving AI agent output display.

Provides post-processing of agent responses to ensure consistent markdown formatting
and optimal display in Streamlit applications.
"""

import re
from typing import Dict, Any
import structlog

logger = structlog.get_logger(__name__).bind(log_type="SYSTEM")


class ResponseFormattingService:
    """
    Service for post-processing AI agent responses to improve formatting.
    
    Handles:
    - Markdown structure cleanup
    - Mathematical expression formatting
    - Source citation standardization
    - Currency and percentage formatting
    """
    
    def __init__(self):
        """Initialize the response formatting service."""
        self.logger = logger.bind(component="response_formatter")
        
    def format_response(self, agent_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format an agent response for optimal display.
        
        Args:
            agent_response: Raw response from agent with 'content' field
            
        Returns:
            Formatted response with improved markdown content
        """
        try:
            if not agent_response or 'content' not in agent_response:
                return agent_response
            
            original_content = agent_response['content']
            formatted_content = self._format_content(original_content)
            
            # Create new response with formatted content
            formatted_response = agent_response.copy()
            formatted_response['content'] = formatted_content
            formatted_response['formatting_applied'] = True
            
            self.logger.debug(
                "Response formatting applied",
                original_length=len(original_content),
                formatted_length=len(formatted_content)
            )
            
            return formatted_response
            
        except Exception as e:
            self.logger.warning(
                "Failed to format response, returning original",
                error=str(e)
            )
            return agent_response
    
    def _format_content(self, content: str) -> str:
        """
        Apply formatting transformations to content.
        
        Args:
            content: Raw content string
            
        Returns:
            Formatted markdown content
        """
        # Start with the original content
        formatted = content
        
        # Apply formatting transformations
        formatted = self._fix_line_breaks(formatted)
        formatted = self._format_currency_and_percentages(formatted)
        formatted = self._format_mathematical_expressions(formatted)
        formatted = self._standardize_source_citations(formatted)
        formatted = self._improve_structure(formatted)
        
        return formatted
    
    def _fix_line_breaks(self, content: str) -> str:
        """Fix line break issues for proper markdown display."""
        # Convert multiple newlines to proper spacing
        content = re.sub(r'\n\n+', '\n\n', content)
        
        # Ensure proper spacing around headers
        content = re.sub(r'\n(#{1,6}\s)', r'\n\n\1', content)
        
        # Ensure proper spacing before lists
        content = re.sub(r'\n(-\s)', r'\n\n\1', content)
        
        return content
    
    def _format_currency_and_percentages(self, content: str) -> str:
        """Improve currency and percentage formatting."""
        # Only add $ to numbers that don't already have currency symbols
        currency_patterns = [
            # Only add $ if not already present
            (r'(\b(?:Capital|Assets|Income|Revenue|Deposits|Loans):\s*)(\d+(?:,\d{3})*(?:\.\d{2})?)\b(?!\s*\$)', r'\1$\2'),
        ]
        
        for pattern, replacement in currency_patterns:
            content = re.sub(pattern, replacement, content, flags=re.IGNORECASE)
        
        # Remove double $ symbols that might have been created
        content = re.sub(r'\$\$+', '$', content)
        
        # Ensure percentages have % symbol
        content = re.sub(r'(\d+\.?\d*)\s*percent\b', r'\1%', content, flags=re.IGNORECASE)
        
        return content
    
    def _format_mathematical_expressions(self, content: str) -> str:
        """Improve mathematical expression formatting - skip if already well formatted."""
        # If content already has proper code blocks around math, don't modify
        if '```' in content and '=' in content:
            # Content appears to be already well formatted, just ensure proper spacing
            content = re.sub(r'```\n\n```', '```\n```', content)  # Remove empty code blocks
            return content
        
        # Only apply transformations if content lacks proper formatting
        # Look for calculation patterns and ensure they're in code blocks
        calc_pattern = r'(=\s*\([^)]+\)[^=]*=\s*[\d.]+%?)'
        
        def wrap_calculation(match):
            calc = match.group(1).strip()
            return f'\n```\n{calc}\n```\n'
        
        content = re.sub(calc_pattern, wrap_calculation, content)
        
        return content
    
    def _standardize_source_citations(self, content: str) -> str:
        """Standardize source citation formatting."""
        # Look for "Sources used:" section and standardize it
        sources_pattern = r'Sources\s+used:\s*\n((?:[-*]\s*[^\n]+\n?)*)'
        
        def format_sources(match):
            sources_text = match.group(1)
            # Ensure each source is a proper bullet point
            lines = [line.strip() for line in sources_text.split('\n') if line.strip()]
            formatted_sources = []
            
            for line in lines:
                if not line.startswith('- ') and not line.startswith('* '):
                    line = f'- {line}'
                formatted_sources.append(line)
            
            return f'\n## Sources\n\n' + '\n'.join(formatted_sources) + '\n'
        
        content = re.sub(sources_pattern, format_sources, content, flags=re.IGNORECASE | re.MULTILINE)
        
        return content
    
    def _improve_structure(self, content: str) -> str:
        """Improve overall content structure."""
        # Ensure proper heading hierarchy
        lines = content.split('\n')
        improved_lines = []
        
        for line in lines:
            # Convert "So, [Result]" patterns to proper result sections
            if re.match(r'^So,\s+', line, re.IGNORECASE):
                line = re.sub(r'^So,\s+', '**Result:** ', line, flags=re.IGNORECASE)
            
            # Ensure calculation results are emphasized
            if 'ratio would be' in line.lower() or 'ratio is' in line.lower():
                # Bold the percentage value
                line = re.sub(r'(\d+\.?\d*%)', r'**\1**', line)
            
            improved_lines.append(line)
        
        return '\n'.join(improved_lines)
    
    def get_formatting_stats(self, original: str, formatted: str) -> Dict[str, Any]:
        """
        Get statistics about formatting changes applied.
        
        Args:
            original: Original content
            formatted: Formatted content
            
        Returns:
            Dictionary with formatting statistics
        """
        return {
            "original_length": len(original),
            "formatted_length": len(formatted),
            "line_count_change": formatted.count('\n') - original.count('\n'),
            "has_headers": '##' in formatted,
            "has_code_blocks": '```' in formatted,
            "has_sources_section": '## Sources' in formatted,
            "currency_symbols": formatted.count('$'),
            "percentage_symbols": formatted.count('%')
        }