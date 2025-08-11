"""
Simplified system prompt for the Azure OpenAI chatbot.
Provides basic prompt functionality using LangChain SystemMessage directly.
"""

import structlog

logger = structlog.get_logger(__name__)


class SystemPrompts:
    """
    Simple system prompt provider.
    
    Provides a basic system prompt that can be used directly with 
    LangChain's SystemMessage and HumanMessage.
    """
    
    DEFAULT_SYSTEM_PROMPT = """You are a helpful AI assistant powered by Azure OpenAI. You provide accurate, concise, and thoughtful responses to user questions and requests.

Key guidelines:
- Be helpful, harmless, and honest in all responses
- Provide clear and well-structured answers
- If you're unsure about something, acknowledge the uncertainty
- Use appropriate formatting for code, lists, and other structured content
- Be conversational but professional in tone
- Respect user privacy and don't store personal information"""

    @classmethod
    def get_system_prompt(
        cls,
        prompt_type: str = "default",
        custom_instructions: str = None,
        context: dict = None,
        **kwargs
    ) -> str:
        """
        Get the system prompt.
        
        Args:
            prompt_type: Ignored, kept for compatibility
            custom_instructions: Optional custom instructions to append
            context: Ignored, kept for compatibility
            **kwargs: Additional parameters, ignored for compatibility
            
        Returns:
            System prompt string
        """
        prompt = cls.DEFAULT_SYSTEM_PROMPT
        
        if custom_instructions:
            prompt += f"\n\nAdditional instructions:\n{custom_instructions}"
        
        logger.debug(
            "System prompt generated",
            length=len(prompt),
            has_custom_instructions=bool(custom_instructions)
        )
        
        return prompt
    
    @classmethod
    def validate_prompt(cls, prompt: str) -> dict:
        """
        Basic prompt validation.
        
        Args:
            prompt: Prompt to validate
            
        Returns:
            Validation results
        """
        return {
            'is_valid': bool(prompt and len(prompt.strip()) > 10),
            'warnings': [],
            'suggestions': [],
            'stats': {
                'length': len(prompt),
                'word_count': len(prompt.split()),
                'line_count': prompt.count('\n') + 1
            }
        }