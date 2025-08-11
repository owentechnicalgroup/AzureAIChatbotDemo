"""
Chatbot module for Azure OpenAI chatbot - LangChain-native architecture.
"""

# Export simplified components
from .agent import ChatbotAgent
from .prompts import SystemPrompts

__all__ = [
    "ChatbotAgent", 
    "SystemPrompts"
]