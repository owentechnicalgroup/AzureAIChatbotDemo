"""
System prompt templates for the Azure OpenAI chatbot.
Task 15: System prompt templates with configurable parameters and validation.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import structlog

logger = structlog.get_logger(__name__)


class SystemPrompts:
    """
    System prompt templates with configurable parameters.
    
    Provides various prompt templates for different conversation modes
    and use cases, with parameter injection and validation.
    """
    
    # Default system prompt
    DEFAULT_SYSTEM_PROMPT = """You are a helpful AI assistant powered by Azure OpenAI. You provide accurate, concise, and thoughtful responses to user questions and requests.

Key guidelines:
- Be helpful, harmless, and honest in all responses
- Provide clear and well-structured answers
- If you're unsure about something, acknowledge the uncertainty
- Use appropriate formatting for code, lists, and other structured content
- Be conversational but professional in tone
- Respect user privacy and don't store personal information"""

    # Assistant persona prompts
    PROFESSIONAL_ASSISTANT = """You are a professional AI assistant designed to help with business and work-related tasks. You excel at:

- Analyzing complex problems and providing structured solutions
- Drafting professional communications and documents  
- Explaining technical concepts clearly
- Providing research assistance and fact-checking
- Offering strategic advice and recommendations

Maintain a professional, competent, and courteous tone. Focus on delivering practical, actionable insights."""

    CREATIVE_ASSISTANT = """You are a creative AI assistant that specializes in:

- Creative writing and storytelling
- Brainstorming and ideation
- Content creation and marketing
- Design thinking and innovation
- Artistic expression and interpretation

Be imaginative, inspiring, and supportive of creative endeavors. Encourage exploration and experimentation while providing constructive feedback."""

    TECHNICAL_ASSISTANT = """You are a technical AI assistant with expertise in:

- Software development and programming
- System architecture and design
- DevOps and infrastructure
- Data analysis and machine learning
- Technical troubleshooting and debugging

Provide accurate technical information, code examples, and best practices. Be precise and thorough in technical explanations."""

    # Specialized domain prompts
    EDUCATIONAL_TUTOR = """You are an educational AI tutor designed to help students learn effectively. Your approach:

- Break down complex topics into digestible parts
- Use examples and analogies to explain concepts
- Encourage critical thinking and problem-solving
- Provide practice questions and exercises
- Adapt explanations to different learning styles
- Be patient and supportive

Focus on helping users understand concepts rather than just providing answers."""

    CODE_REVIEWER = """You are an AI code reviewer with expertise in software engineering best practices. When reviewing code:

- Check for bugs, security issues, and performance problems
- Suggest improvements for readability and maintainability
- Verify adherence to coding standards and conventions
- Recommend appropriate design patterns and architectures
- Consider scalability and extensibility
- Provide specific, actionable feedback

Be constructive and educational in your reviews."""

    CONVERSATION_SUMMARIZER = """You are an AI assistant specialized in conversation analysis and summarization. Your tasks:

- Identify key topics and themes discussed
- Extract important decisions and action items
- Summarize main points and conclusions
- Note any unresolved questions or issues
- Highlight significant insights or breakthroughs
- Maintain context and relationships between topics

Provide clear, organized summaries that capture the essence of conversations."""

    @classmethod
    def get_system_prompt(
        cls,
        prompt_type: str = "default",
        custom_instructions: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        user_name: Optional[str] = None,
        conversation_context: Optional[str] = None
    ) -> str:
        """
        Get a system prompt with optional customizations.
        
        Args:
            prompt_type: Type of prompt to use
            custom_instructions: Additional custom instructions
            context: Additional context to inject
            user_name: User's name for personalization
            conversation_context: Previous conversation context
            
        Returns:
            Formatted system prompt
        """
        # Get base prompt
        prompt_map = {
            "default": cls.DEFAULT_SYSTEM_PROMPT,
            "professional": cls.PROFESSIONAL_ASSISTANT,
            "creative": cls.CREATIVE_ASSISTANT,
            "technical": cls.TECHNICAL_ASSISTANT,
            "tutor": cls.EDUCATIONAL_TUTOR,
            "code_reviewer": cls.CODE_REVIEWER,
            "summarizer": cls.CONVERSATION_SUMMARIZER
        }
        
        base_prompt = prompt_map.get(prompt_type, cls.DEFAULT_SYSTEM_PROMPT)
        
        # Build the final prompt
        prompt_parts = [base_prompt]
        
        # Add user personalization
        if user_name:
            personalization = f"\nNote: The user's name is {user_name}. You may address them by name when appropriate."
            prompt_parts.append(personalization)
        
        # Add conversation context
        if conversation_context:
            context_section = f"\nPrevious conversation context:\n{conversation_context}"
            prompt_parts.append(context_section)
        
        # Add custom instructions
        if custom_instructions:
            custom_section = f"\nAdditional instructions:\n{custom_instructions}"
            prompt_parts.append(custom_section)
        
        # Add context information
        if context:
            context_parts = []
            for key, value in context.items():
                if value:
                    context_parts.append(f"- {key}: {value}")
            
            if context_parts:
                context_section = f"\nContext information:\n" + "\n".join(context_parts)
                prompt_parts.append(context_section)
        
        # Add timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
        timestamp_section = f"\nCurrent time: {timestamp}"
        prompt_parts.append(timestamp_section)
        
        # Add response guidelines
        guidelines = """
Response guidelines:
- Be concise but comprehensive
- Use appropriate formatting (markdown, code blocks, lists)
- If providing code, include explanations
- Ask clarifying questions when needed
- Acknowledge limitations or uncertainties"""
        prompt_parts.append(guidelines)
        
        final_prompt = "\n".join(prompt_parts)
        
        logger.debug(
            "System prompt generated",
            prompt_type=prompt_type,
            length=len(final_prompt),
            has_custom_instructions=bool(custom_instructions),
            has_context=bool(context),
            has_user_name=bool(user_name)
        )
        
        return final_prompt
    
    @classmethod
    def get_conversation_starter_prompt(
        cls,
        topic: Optional[str] = None,
        style: str = "friendly"
    ) -> str:
        """
        Get a prompt for starting conversations.
        
        Args:
            topic: Specific topic to discuss
            style: Conversation style (friendly, professional, educational)
            
        Returns:
            Conversation starter prompt
        """
        style_templates = {
            "friendly": "Start a friendly conversation{}. Be welcoming and engaging.",
            "professional": "Begin a professional discussion{}. Maintain a business-appropriate tone.",
            "educational": "Initiate an educational dialogue{}. Focus on learning and exploration."
        }
        
        topic_text = f" about {topic}" if topic else ""
        
        template = style_templates.get(style, style_templates["friendly"])
        prompt = template.format(topic_text)
        
        return prompt
    
    @classmethod
    def get_task_specific_prompt(
        cls,
        task: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Get a task-specific prompt.
        
        Args:
            task: Task type (summarize, analyze, translate, etc.)
            parameters: Task-specific parameters
            
        Returns:
            Task-specific prompt
        """
        task_templates = {
            "summarize": "Summarize the following content concisely, highlighting key points:",
            "analyze": "Analyze the following content and provide insights:",
            "translate": "Translate the following content to {target_language}:",
            "explain": "Explain the following concept in {detail_level} detail:",
            "debug": "Help debug the following code issue:",
            "improve": "Suggest improvements for the following:",
            "review": "Review the following and provide constructive feedback:"
        }
        
        template = task_templates.get(task, "Help with the following:")
        
        if parameters:
            try:
                prompt = template.format(**parameters)
            except KeyError as e:
                logger.warning(f"Missing parameter for task prompt: {e}")
                prompt = template
        else:
            prompt = template
        
        return prompt
    
    @classmethod
    def get_error_recovery_prompt(
        cls,
        error_type: str,
        context: Optional[str] = None
    ) -> str:
        """
        Get a prompt for error recovery scenarios.
        
        Args:
            error_type: Type of error that occurred
            context: Additional context about the error
            
        Returns:
            Error recovery prompt
        """
        base_prompt = """I apologize for the error that occurred. Let me help resolve this issue.

Error type: {error_type}
{context_section}

How would you like to proceed? I can:
1. Try a different approach
2. Break down the request into smaller parts
3. Clarify any requirements
4. Start over with a simpler version

Please let me know how you'd like to continue."""
        
        context_section = f"Context: {context}" if context else ""
        
        return base_prompt.format(
            error_type=error_type,
            context_section=context_section
        )
    
    @classmethod
    def validate_prompt(cls, prompt: str) -> Dict[str, Any]:
        """
        Validate a system prompt.
        
        Args:
            prompt: Prompt to validate
            
        Returns:
            Validation results
        """
        results = {
            'is_valid': True,
            'warnings': [],
            'suggestions': [],
            'stats': {
                'length': len(prompt),
                'word_count': len(prompt.split()),
                'line_count': prompt.count('\n') + 1
            }
        }
        
        # Check length
        if len(prompt) > 4000:
            results['warnings'].append("Prompt is very long and may impact performance")
        elif len(prompt) < 50:
            results['warnings'].append("Prompt is very short and may lack necessary context")
        
        # Check for essential elements
        essential_elements = [
            ('helpful', 'Consider mentioning being helpful'),
            ('honest', 'Consider mentioning honesty and accuracy'),
            ('format', 'Consider mentioning response formatting preferences')
        ]
        
        prompt_lower = prompt.lower()
        for element, suggestion in essential_elements:
            if element not in prompt_lower:
                results['suggestions'].append(suggestion)
        
        # Check for potential issues
        problematic_phrases = [
            ('ignore', 'Contains "ignore" - may cause instruction conflicts'),
            ('disregard', 'Contains "disregard" - may cause instruction conflicts'),
            ('always', 'Contains "always" - may be too restrictive'),
            ('never', 'Contains "never" - may be too restrictive')
        ]
        
        for phrase, warning in problematic_phrases:
            if phrase in prompt_lower:
                results['warnings'].append(warning)
        
        # Set overall validity
        if len(results['warnings']) > 3:
            results['is_valid'] = False
        
        return results
    
    @classmethod
    def get_available_prompt_types(cls) -> List[str]:
        """Get list of available prompt types."""
        return [
            "default",
            "professional", 
            "creative",
            "technical",
            "tutor",
            "code_reviewer",
            "summarizer"
        ]
    
    @classmethod
    def get_prompt_description(cls, prompt_type: str) -> str:
        """Get description of a prompt type."""
        descriptions = {
            "default": "General-purpose helpful assistant",
            "professional": "Professional business assistant for work-related tasks", 
            "creative": "Creative assistant for writing and artistic endeavors",
            "technical": "Technical assistant for programming and development",
            "tutor": "Educational tutor for learning and teaching",
            "code_reviewer": "Code reviewer for software development",
            "summarizer": "Conversation and content summarization specialist"
        }
        
        return descriptions.get(prompt_type, "Unknown prompt type")
    
    @classmethod
    def create_custom_prompt(
        cls,
        role: str,
        expertise: List[str],
        tone: str = "professional",
        guidelines: Optional[List[str]] = None
    ) -> str:
        """
        Create a custom system prompt.
        
        Args:
            role: Assistant's role (e.g., "expert consultant", "creative writer")
            expertise: List of expertise areas
            tone: Desired tone
            guidelines: Additional guidelines
            
        Returns:
            Custom system prompt
        """
        expertise_text = ", ".join(expertise)
        
        base_template = f"""You are a {role} with expertise in {expertise_text}. 

Your primary goal is to provide valuable assistance while maintaining a {tone} tone."""
        
        if guidelines:
            guidelines_text = "\n".join(f"- {guideline}" for guideline in guidelines)
            base_template += f"\n\nKey guidelines:\n{guidelines_text}"
        
        # Add standard closing
        base_template += "\n\nProvide helpful, accurate, and well-structured responses while respecting user privacy and maintaining ethical standards."
        
        logger.info(
            "Custom prompt created",
            role=role,
            expertise_count=len(expertise),
            tone=tone,
            has_guidelines=bool(guidelines)
        )
        
        return base_template