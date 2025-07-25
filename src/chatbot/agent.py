"""
Main chatbot agent using LangChain's ConversationChain.
Task 17: Chatbot agent with Azure OpenAI integration, conversation management, and graceful degradation.
"""

import asyncio
import time
import uuid
from typing import Dict, List, Any, Optional, Union, AsyncGenerator
from datetime import datetime, timezone
import structlog

from langchain.chains import ConversationChain
from langchain.schema import BaseMemory
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

from config.settings import Settings
from services.azure_client import AzureOpenAIClient, ResponseMetadata
from services.logging_service import log_conversation_event, ConversationLogger
from chatbot.conversation import ConversationManager
from chatbot.prompts import SystemPrompts
from utils.error_handlers import (
    handle_error, 
    ChatbotBaseError, 
    AzureOpenAIError, 
    ConversationError,
    is_retryable_error,
    get_retry_delay
)
from utils.console import get_console

logger = structlog.get_logger(__name__)


class ChatbotAgent:
    """
    Main chatbot agent that orchestrates conversation flow.
    
    Features:
    - Azure OpenAI integration through LangChain
    - Conversation memory management
    - Message processing and response generation
    - Error handling with graceful degradation
    - Performance monitoring and logging
    - Interactive and batch conversation modes
    """
    
    def __init__(
        self,
        settings: Settings,
        conversation_id: Optional[str] = None,
        system_prompt: Optional[str] = None,
        prompt_type: str = "default"
    ):
        """
        Initialize chatbot agent.
        
        Args:
            settings: Application settings
            conversation_id: Unique conversation identifier
            system_prompt: Custom system prompt
            prompt_type: Type of system prompt to use
        """
        self.settings = settings
        self.conversation_id = conversation_id or str(uuid.uuid4())
        self.prompt_type = prompt_type
        
        self.logger = logger.bind(
            log_type="CONVERSATION",
            conversation_id=self.conversation_id,
            component="chatbot_agent"
        )
        
        # Initialize services
        try:
            self.azure_client = AzureOpenAIClient(settings)
            self.conversation_manager = ConversationManager(
                settings=settings,
                conversation_id=self.conversation_id
            )
            
            self.logger.info("Chatbot agent initialized successfully")
            
        except Exception as e:
            self.logger.error(
                "Failed to initialize chatbot agent",
                error=str(e),
                error_type=type(e).__name__
            )
            raise
        
        # Set system prompt
        self.system_prompt = self._initialize_system_prompt(system_prompt)
        
        # Performance tracking
        self._conversation_start_time = time.time()
        self._message_count = 0
        self._total_response_time = 0.0
        
        # State management
        self._is_active = True
        self._last_error = None
        
        self.logger.info(
            "Chatbot agent ready",
            prompt_type=prompt_type,
            system_prompt_length=len(self.system_prompt)
        )
    
    def _initialize_system_prompt(self, custom_prompt: Optional[str] = None) -> str:
        """Initialize system prompt with configuration."""
        if custom_prompt:
            prompt = custom_prompt
        else:
            # Use settings or default
            prompt = getattr(self.settings, 'system_message', None)
            if not prompt:
                prompt = SystemPrompts.get_system_prompt(
                    prompt_type=self.prompt_type,
                    context={
                        'environment': self.settings.environment,
                        'conversation_id': self.conversation_id
                    }
                )
        
        # Validate prompt
        validation = SystemPrompts.validate_prompt(prompt)
        if not validation['is_valid']:
            self.logger.warning(
                "System prompt validation failed",
                warnings=validation['warnings'],
                suggestions=validation['suggestions']
            )
        
        # Add system message to conversation
        self.conversation_manager.add_message(
            role="system",
            content=prompt,
            metadata={"type": "system_prompt", "prompt_type": self.prompt_type}
        )
        
        return prompt
    
    async def process_message_async(
        self,
        user_message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process user message and generate response asynchronously.
        
        Args:
            user_message: User's input message
            context: Additional context for processing
            
        Returns:
            Dictionary containing response and metadata
        """
        start_time = time.time()
        message_id = str(uuid.uuid4())
        
        # Use conversation logger for structured logging
        with ConversationLogger(
            conversation_id=self.conversation_id,
            user_id=context.get('user_id') if context else None
        ) as conv_logger:
            
            try:
                # Validate input
                if not user_message.strip():
                    raise ConversationError("Empty message received")
                
                conv_logger.info(
                    "Processing user message",
                    message_length=len(user_message),
                    message_id=message_id
                )
                
                # Add user message to conversation
                metadata = {
                    "message_id": message_id,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                if context:
                    metadata.update(context)
                
                user_msg_id = self.conversation_manager.add_message(
                    role="user",
                    content=user_message,
                    metadata=metadata
                )
                
                # Prepare messages for Azure OpenAI
                messages = self._prepare_messages_for_api()
                
                # Generate response with retry logic
                response_data = await self._generate_response_with_retry(
                    messages=messages,
                    context=context
                )
                
                # Extract response content and metadata
                response_content = response_data['content']
                response_metadata = response_data.get('metadata', {})
                
                # Add assistant response to conversation
                assistant_msg_id = self.conversation_manager.add_message(
                    role="assistant",
                    content=response_content,
                    token_count=response_metadata.get('token_usage', {}).get('completion_tokens'),
                    metadata={
                        "message_id": str(uuid.uuid4()),
                        "response_metadata": response_metadata,
                        "user_message_id": user_msg_id
                    }
                )
                
                # Calculate total response time
                total_response_time = time.time() - start_time
                
                # Update performance metrics
                self._update_performance_metrics(
                    response_time=total_response_time,
                    token_usage=response_metadata.get('token_usage', {})
                )
                
                # Log conversation event
                log_conversation_event(
                    event="response_generated",
                    conversation_id=self.conversation_id,
                    user_message=user_message,
                    assistant_response=response_content,
                    token_usage=response_metadata.get('token_usage'),
                    response_time=total_response_time
                )
                
                # Prepare final response
                final_response = {
                    'content': response_content,
                    'message_id': assistant_msg_id,
                    'user_message_id': user_msg_id,
                    'conversation_id': self.conversation_id,
                    'metadata': {
                        **response_metadata,
                        'total_response_time': total_response_time,
                        'message_count': self.conversation_manager.metadata.message_count,
                        'conversation_turns': self._message_count + 1
                    },
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
                
                conv_logger.info(
                    "Message processed successfully",
                    response_time=total_response_time,
                    response_length=len(response_content),
                    token_usage=response_metadata.get('token_usage')
                )
                
                return final_response
                
            except Exception as e:
                # Handle errors with graceful degradation
                error_response = await self._handle_processing_error(
                    error=e,
                    user_message=user_message,
                    start_time=start_time,
                    conv_logger=conv_logger
                )
                
                return error_response
    
    def process_message(
        self,
        user_message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process user message synchronously (wrapper around async method).
        
        Args:
            user_message: User's input message
            context: Additional context for processing
            
        Returns:
            Dictionary containing response and metadata
        """
        try:
            # Run async method with proper event loop handling
            try:
                # Check if we're already in a running event loop
                loop = asyncio.get_running_loop()
                # If we're already in an event loop, create a new task in a thread
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        self.process_message_async(user_message, context)
                    )
                    return future.result()
            except RuntimeError:
                # No event loop running, safe to create new one
                return asyncio.run(self.process_message_async(user_message, context))
                
        except Exception as e:
            self.logger.error(
                "Error in synchronous message processing",
                error=str(e),
                user_message_length=len(user_message) if user_message else 0
            )
            
            # Return error response
            return {
                'content': f"I apologize, but I encountered an error: {str(e)}",
                'error': str(e),
                'conversation_id': self.conversation_id,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'is_error': True
            }
    
    async def stream_response_async(
        self,
        user_message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream response generation for real-time output.
        
        Args:
            user_message: User's input message
            context: Additional context for processing
            
        Yields:
            Response chunks with metadata
        """
        start_time = time.time()
        
        try:
            # Add user message to conversation
            self.conversation_manager.add_message(
                role="user",
                content=user_message
            )
            
            # Prepare messages for API
            messages = self._prepare_messages_for_api()
            
            # Stream response from Azure OpenAI
            full_response = ""
            async for chunk in self.azure_client.generate_stream_async(
                messages=messages,
                conversation_id=self.conversation_id
            ):
                if chunk.get('is_final'):
                    # Final chunk - add complete response to conversation
                    if full_response.strip():
                        self.conversation_manager.add_message(
                            role="assistant",
                            content=full_response,
                            metadata={
                                "streaming": True,
                                "total_response_time": time.time() - start_time
                            }
                        )
                    
                    # Update performance metrics
                    self._update_performance_metrics(
                        response_time=time.time() - start_time
                    )
                
                else:
                    # Regular chunk - accumulate response
                    chunk_content = chunk.get('content', '')
                    full_response += chunk_content
                
                yield chunk
                
        except Exception as e:
            self.logger.error(
                "Error in streaming response",
                error=str(e),
                user_message_length=len(user_message)
            )
            
            yield {
                'content': '',
                'error': str(e),
                'conversation_id': self.conversation_id,
                'is_final': True,
                'timestamp': time.time()
            }
    
    def _prepare_messages_for_api(self) -> List[Dict[str, str]]:
        """Prepare conversation messages for Azure OpenAI API."""
        messages = []
        
        # Get messages from conversation manager
        conv_messages = self.conversation_manager.get_messages(
            limit=self.settings.max_conversation_turns,
            include_system=True
        )
        
        # Convert to API format
        for msg in conv_messages:
            messages.append({
                'role': msg.role,
                'content': msg.content
            })
        
        self.logger.debug(
            "Prepared messages for API",
            message_count=len(messages),
            total_length=sum(len(msg['content']) for msg in messages)
        )
        
        return messages
    
    async def _generate_response_with_retry(
        self,
        messages: List[Dict[str, str]],
        context: Optional[Dict[str, Any]] = None,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """Generate response with retry logic for resilience."""
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                self.logger.debug(
                    "Generating response",
                    attempt=attempt + 1,
                    max_retries=max_retries + 1
                )
                
                response = await self.azure_client.generate_response_async(
                    messages=messages,
                    conversation_id=self.conversation_id,
                    **(context or {})
                )
                
                return response
                
            except Exception as e:
                last_error = e
                chatbot_error = handle_error(e, context={'attempt': attempt + 1})
                
                # Check if error is retryable
                if attempt < max_retries and is_retryable_error(e):
                    retry_delay = get_retry_delay(e, attempt + 1)
                    
                    self.logger.warning(
                        "Retryable error occurred, will retry",
                        error=str(e),
                        attempt=attempt + 1,
                        retry_delay=retry_delay
                    )
                    
                    await asyncio.sleep(retry_delay)
                    continue
                else:
                    self.logger.error(
                        "Max retries exceeded or non-retryable error",
                        error=str(e),
                        attempt=attempt + 1,
                        is_retryable=is_retryable_error(e)
                    )
                    raise chatbot_error
        
        # This should never be reached, but just in case
        if last_error:
            raise handle_error(last_error)
        
        raise AzureOpenAIError("Unexpected error in response generation")
    
    async def _handle_processing_error(
        self,
        error: Exception,
        user_message: str,
        start_time: float,
        conv_logger
    ) -> Dict[str, Any]:
        """Handle processing errors with graceful degradation."""
        processing_time = time.time() - start_time
        
        # Convert to chatbot error
        chatbot_error = handle_error(error, context={
            'user_message_length': len(user_message),
            'processing_time': processing_time,
            'conversation_id': self.conversation_id
        })
        
        # Store last error for diagnostics
        self._last_error = chatbot_error
        
        # Log the error
        log_conversation_event(
            event="error_occurred",
            conversation_id=self.conversation_id,
            user_message=user_message,
            error=str(chatbot_error),
            processing_time=processing_time
        )
        
        # Generate graceful error response
        if isinstance(chatbot_error, AzureOpenAIError):
            error_content = "I'm having trouble connecting to my AI service right now. Please try again in a moment."
        elif isinstance(chatbot_error, ConversationError):
            error_content = "There was an issue with our conversation. Let me try to help you in a different way."
        else:
            error_content = "I encountered an unexpected issue. Please try rephrasing your message or ask something else."
        
        # Add recovery suggestions if available
        if chatbot_error.recovery_suggestions:
            error_content += "\n\nHere are some things you can try:\n"
            error_content += "\n".join(f"• {suggestion}" for suggestion in chatbot_error.recovery_suggestions[:3])
        
        # Add error response to conversation
        try:
            error_msg_id = self.conversation_manager.add_message(
                role="assistant",
                content=error_content,
                metadata={
                    "is_error_response": True,
                    "original_error": str(error),
                    "error_type": type(error).__name__,
                    "error_code": getattr(chatbot_error, 'error_code', None)
                }
            )
        except Exception as conv_error:
            conv_logger.error(
                "Failed to add error response to conversation",
                conv_error=str(conv_error)
            )
            error_msg_id = None
        
        return {
            'content': error_content,
            'message_id': error_msg_id,
            'conversation_id': self.conversation_id,
            'error': str(chatbot_error),
            'error_code': getattr(chatbot_error, 'error_code', None),
            'recovery_suggestions': chatbot_error.recovery_suggestions,
            'is_error': True,
            'metadata': {
                'processing_time': processing_time,
                'error_type': type(chatbot_error).__name__
            },
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    
    def _update_performance_metrics(
        self,
        response_time: float,
        token_usage: Optional[Dict[str, Any]] = None
    ):
        """Update performance tracking metrics."""
        self._message_count += 1
        self._total_response_time += response_time
        
        # Log performance metrics
        from services.logging_service import log_performance_metrics
        
        metrics = {
            'message_count': self._message_count,
            'average_response_time': self._total_response_time / self._message_count,
            'conversation_duration': time.time() - self._conversation_start_time
        }
        
        if token_usage:
            metrics.update(token_usage)
        
        log_performance_metrics(
            operation="message_processing",
            duration=response_time,
            success=True,
            **metrics
        )
    
    def run_interactive_session(
        self,
        max_turns: Optional[int] = None,
        welcome_message: bool = True
    ):
        """
        Run interactive chat session.
        
        Args:
            max_turns: Maximum number of conversation turns
            welcome_message: Whether to show welcome message
        """
        console = get_console()
        
        try:
            if welcome_message:
                console.print_banner("Azure OpenAI Chatbot", "1.0.0")
                console.print_welcome_message()
            
            turn_count = 0
            max_turns = max_turns or self.settings.max_conversation_turns
            
            while self._is_active and (max_turns is None or turn_count < max_turns):
                try:
                    # Get user input
                    user_input = console.prompt_user(
                        "You",
                        default=""
                    ).strip()
                    
                    if not user_input:
                        continue
                    
                    # Handle special commands
                    if user_input.startswith('/'):
                        if self._handle_command(user_input, console):
                            continue
                        else:
                            break  # Exit command
                    
                    # Show processing status
                    with console.show_status("🤔 Thinking..."):
                        response = self.process_message(user_input)
                    
                    # Display response
                    if response.get('is_error'):
                        console.print_error(response.get('error', 'Unknown error occurred'))
                        if response.get('recovery_suggestions'):
                            console.print_status(
                                "Suggestions: " + "; ".join(response['recovery_suggestions'][:2]),
                                "info"
                            )
                    else:
                        console.print_conversation_message(
                            role="assistant",
                            content=response['content'],
                            timestamp=datetime.fromisoformat(response['timestamp'].replace('Z', '+00:00')),
                            token_count=response.get('metadata', {}).get('token_usage', {}).get('total_tokens')
                        )
                    
                    turn_count += 1
                    
                except KeyboardInterrupt:
                    console.print_status("\nChat interrupted by user", "warning")
                    break
                except Exception as e:
                    console.print_error(f"Unexpected error: {str(e)}")
                    self.logger.error("Interactive session error", error=str(e))
                    
                    if not console.confirm("Continue chatting?", default=True):
                        break
            
            # Show final statistics
            if turn_count > 0:
                console.print_separator("Session Summary")
                stats = self.get_conversation_statistics()
                console.print_conversation_stats(stats)
            
            console.print_goodbye_message()
            
        except Exception as e:
            self.logger.error("Fatal error in interactive session", error=str(e))
            console.print_error(f"Fatal error: {str(e)}")
        finally:
            self._is_active = False
    
    def _handle_command(self, command: str, console) -> bool:
        """
        Handle special chat commands.
        
        Args:
            command: Command string
            console: Console instance
            
        Returns:
            True to continue chatting, False to exit
        """
        command = command.lower().strip()
        
        if command in ['/exit', '/quit', '/q']:
            return False
        
        elif command == '/help':
            commands = {
                '/help': 'Show available commands',
                '/stats': 'Show conversation statistics',
                '/clear': 'Clear conversation history',
                '/save [file]': 'Save conversation to file',
                '/load [file]': 'Load conversation from file',
                '/export': 'Export conversation as JSON',
                '/health': 'Check system health',
                '/exit, /quit': 'Exit the application'
            }
            console.print_help(commands)
        
        elif command == '/stats':
            stats = self.get_conversation_statistics()
            console.print_conversation_stats(stats)
        
        elif command == '/clear':
            if console.confirm("Clear conversation history?", default=False):
                self.clear_conversation()
                console.print_status("Conversation history cleared", "success")
        
        elif command.startswith('/save'):
            parts = command.split(' ', 1)
            filename = parts[1] if len(parts) > 1 else f"conversation_{self.conversation_id[:8]}.json"
            try:
                self.save_conversation(filename)
                console.print_status(f"Conversation saved to {filename}", "success")
            except Exception as e:
                console.print_error(f"Failed to save conversation: {str(e)}")
        
        elif command.startswith('/load'):
            parts = command.split(' ', 1)
            if len(parts) < 2:
                console.print_error("Please specify a filename: /load <filename>")
            else:
                filename = parts[1]
                try:
                    self.load_conversation(filename)
                    console.print_status(f"Conversation loaded from {filename}", "success")
                except Exception as e:
                    console.print_error(f"Failed to load conversation: {str(e)}")
        
        elif command == '/export':
            try:
                data = self.export_conversation()
                console.print_status(f"Conversation exported ({len(data['messages'])} messages)", "success")
                # Could implement clipboard copy or file save here
            except Exception as e:
                console.print_error(f"Failed to export conversation: {str(e)}")
        
        elif command == '/health':
            health_status = self.health_check()
            if health_status['status'] == 'healthy':
                console.print_status("System is healthy ✓", "success")
            else:
                console.print_status(f"System health issue: {health_status.get('error', 'Unknown')}", "warning")
        
        else:
            console.print_status(f"Unknown command: {command}. Type /help for available commands.", "warning")
        
        return True
    
    def get_conversation_statistics(self) -> Dict[str, Any]:
        """Get comprehensive conversation statistics."""
        base_stats = self.conversation_manager.get_statistics()
        
        # Add agent-specific metrics
        agent_stats = {
            'average_response_time': (
                self._total_response_time / self._message_count 
                if self._message_count > 0 else 0.0
            ),
            'total_response_time': self._total_response_time,
            'session_duration': time.time() - self._conversation_start_time,
            'azure_client_metrics': self.azure_client.get_metrics(),
            'last_error': str(self._last_error) if self._last_error else None,
            'system_prompt_type': self.prompt_type,
            'is_active': self._is_active
        }
        
        return {**base_stats, **agent_stats}
    
    def clear_conversation(self):
        """Clear conversation history."""
        self.conversation_manager.clear_memory()
        
        # Re-add system prompt
        self.conversation_manager.add_message(
            role="system",
            content=self.system_prompt,
            metadata={"type": "system_prompt", "prompt_type": self.prompt_type}
        )
        
        self.logger.info("Conversation cleared and system prompt reinitialized")
    
    def save_conversation(self, filename: str):
        """Save conversation to file."""
        self.conversation_manager.save_to_file(filename)
    
    def load_conversation(self, filename: str):
        """Load conversation from file."""
        self.conversation_manager.load_from_file(filename)
    
    def export_conversation(self) -> Dict[str, Any]:
        """Export conversation data."""
        return self.conversation_manager.export_conversation(include_metadata=True)
    
    def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check."""
        try:
            # Check Azure OpenAI client
            azure_health = self.azure_client.health_check()
            
            # Check conversation manager
            conv_stats = self.conversation_manager.get_statistics()
            
            # Overall health assessment
            is_healthy = (
                azure_health['status'] == 'healthy' and
                self._is_active and
                conv_stats['total_messages'] >= 0  # Basic sanity check
            )
            
            return {
                'status': 'healthy' if is_healthy else 'degraded',
                'azure_openai': azure_health,
                'conversation_manager': {
                    'status': 'healthy',
                    'message_count': conv_stats['total_messages'],
                    'memory_type': conv_stats['memory_type']
                },
                'agent': {
                    'is_active': self._is_active,
                    'message_count': self._message_count,
                    'last_error': str(self._last_error) if self._last_error else None,
                    'uptime': time.time() - self._conversation_start_time
                },
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    def shutdown(self):
        """Gracefully shutdown the agent."""
        self.logger.info("Shutting down chatbot agent")
        self._is_active = False
        
        # Could add cleanup logic here if needed
        
    def __repr__(self) -> str:
        """String representation of the chatbot agent."""
        return (
            f"ChatbotAgent("
            f"id={self.conversation_id[:8]}, "
            f"messages={self._message_count}, "
            f"active={self._is_active}, "
            f"prompt_type={self.prompt_type}"
            f")"
        )