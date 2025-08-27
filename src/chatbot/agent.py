"""
Simplified Azure OpenAI chatbot agent following Azure development best practices.
Uses LangChain's native features with optional RAG tool integration for multi-step conversations.
"""

import os
import time
import uuid
from typing import Dict, List, Any, Optional, cast
from datetime import datetime, timezone
import structlog

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_community.chat_message_histories import FileChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.runnables import RunnableConfig
from langchain_core.output_parsers import StrOutputParser
from langchain.agents import create_openai_tools_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.memory import ConversationBufferWindowMemory

from src.config.settings import Settings
from src.utils.azure_langchain import create_azure_chat_openai
from src.utils.error_handlers import handle_error, ChatbotBaseError
from src.chatbot.tool_routing_instructions import get_tool_routing_instructions

logger = structlog.get_logger(__name__)


def create_session_history(session_id: str, persistence_file: Optional[str] = None):
    """Create chat history for a session - Azure best practice for session management."""
    if persistence_file:
        from pathlib import Path
        file_path = Path(f"{persistence_file}_{session_id}.json")
        file_path.parent.mkdir(parents=True, exist_ok=True)
        return FileChatMessageHistory(file_path=str(file_path))
    return InMemoryChatMessageHistory()


class ChatbotAgent:
    """
    Simplified Azure OpenAI chatbot agent using LangChain native features.
    
    Supports both simple conversation and multi-step RAG-enabled conversations.
    
    Follows Azure development best practices:
    - Single responsibility principle
    - Native LangChain integration
    - Optional RAG tool integration
    - Proper error handling
    - Azure-optimized configuration
    """
    
    def __init__(
        self,
        settings: Settings,
        conversation_id: Optional[str] = None,
        system_prompt: Optional[str] = None,
        prompt_type: Optional[str] = None,
        persistence_file: Optional[str] = None,
        tools: Optional[List[Any]] = None,
        enable_multi_step: bool = False,
        use_general_knowledge: bool = False
    ):
        """Initialize Azure OpenAI agent with LangChain native features and optional RAG tools."""
        self.settings = settings
        self.conversation_id = conversation_id or str(uuid.uuid4())
        self.persistence_file = persistence_file
        self.tools = tools or []
        self.enable_multi_step = enable_multi_step and len(self.tools) > 0
        self.use_general_knowledge = use_general_knowledge  # Store user preference
        
        # Azure observability setup
        self.logger = logger.bind(
            log_type="CONVERSATION",
            conversation_id=self.conversation_id,
            component="chatbot_agent",
            multi_step_enabled=self.enable_multi_step,
            tool_count=len(self.tools),
            use_general_knowledge=use_general_knowledge
        )
        
        # Initialize Azure OpenAI via LangChain
        try:
            self.llm = create_azure_chat_openai(settings)
            self.logger.info("Azure OpenAI agent initialized")
        except Exception as e:
            self.logger.error("Failed to initialize Azure OpenAI", error=str(e))
            raise
        
        # Setup system prompt (enhanced for multi-step if enabled)
        self.system_prompt = self._build_system_prompt(system_prompt, prompt_type)
        
        # Create conversation chain (simple or multi-step based on configuration)
        if self.enable_multi_step:
            self._setup_agent_executor()
        else:
            self._setup_conversation_chain()
        
        # Simple performance tracking
        self._start_time = time.time()
        self._message_count = 0
        
        self.logger.info("Azure OpenAI chatbot agent ready")
    
    def _build_system_prompt(self, custom_prompt: Optional[str], prompt_type: Optional[str]) -> str:
        """Build system prompt - Azure best practice for prompt management with optional multi-step support."""
        if custom_prompt:
            return custom_prompt
        
        # Base Azure-optimized prompt templates
        base_prompts = {
            "default": "You are a helpful AI assistant powered by Azure OpenAI. Provide accurate, concise responses.",
            "professional": "You are a professional AI assistant. Provide clear, structured, business-appropriate responses.",
            "creative": "You are a creative AI assistant. Think creatively and provide engaging, imaginative responses.",
            "technical": "You are a technical AI assistant. Provide detailed, accurate technical information with examples.",
            "tutor": "You are an AI tutor. Break down complex topics and guide users through learning step by step.",
            "code_reviewer": "You are a code review AI. Analyze code for best practices, security, and improvements.",
            "summarizer": "You are an AI summarizer. Provide concise, accurate summaries highlighting key points."
        }
        
        base_prompt = base_prompts.get(prompt_type or "default", base_prompts["default"])
        
        # Add optimized tool routing for multi-step conversations
        if self.enable_multi_step and self.tools:
            tool_routing = get_tool_routing_instructions(self.use_general_knowledge, self.tools)
            return base_prompt + "\n\n" + tool_routing
        
        return base_prompt
    
    def _setup_conversation_chain(self):
        """Setup simple LangChain conversation chain - Azure optimized."""
        # Simple chain: add system prompt -> LLM -> string output
        def add_system_prompt(messages: List[BaseMessage]) -> List[BaseMessage]:
            """Add system prompt and manage context window."""
            result: List[BaseMessage] = [SystemMessage(content=self.system_prompt)]
            
            # Simple context window management - reduced for performance
            max_messages = (self.settings.max_conversation_turns * 2) if self.settings.max_conversation_turns else 6
            recent_messages = messages[-max_messages:] if len(messages) > max_messages else messages
            
            result.extend([msg for msg in recent_messages if not isinstance(msg, SystemMessage)])
            return result
        
        # Create simple chain
        chain = add_system_prompt | self.llm | StrOutputParser()
        
        # Wrap with message history - LangChain handles everything else
        self.conversation_chain = RunnableWithMessageHistory(
            cast(Any, chain),  # Type assertion to work around LangChain typing
            lambda session_id: create_session_history(session_id, self.persistence_file),
            input_messages_key=None,
            history_messages_key=None,
        )

    def _setup_agent_executor(self):
        """Setup LangChain agent executor for multi-step conversations with RAG tools."""
        self.logger.info("Setting up multi-step agent executor", tool_count=len(self.tools))
        
        # Create prompt template for agent with tools
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            MessagesPlaceholder("chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder("agent_scratchpad")
        ])
        
        # Create OpenAI tools agent (works with Azure OpenAI)
        agent = create_openai_tools_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=prompt_template
        )
        
        # Create conversation memory for multi-step context - reduced for performance
        memory = ConversationBufferWindowMemory(
            memory_key="chat_history",
            output_key="output",
            return_messages=True,
            k=3  # Remember last 3 exchanges
        )
        
        # Create agent executor with Azure-optimized settings
        self.agent_executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            memory=memory,
            verbose=False,  # Disable verbose to avoid callback issues
            max_iterations=5,  # Restored original value
            early_stopping_method="force",  # Updated to supported value (was "generate")
            handle_parsing_errors=True
        )
        
        self.logger.info("Multi-step agent executor ready")
    
    def process_message(self, user_message: str, **kwargs) -> Dict[str, Any]:
        """
        Process user message using either simple chain or multi-step agent executor.
        
        Routes between conversation chain and agent executor based on enable_multi_step flag.
        Also handles agent-controlled RAG behavior based on use_general_knowledge setting.
        """
        if not user_message.strip():
            return self._error_response("Please provide a message.")

        start_time = time.time()
        
        try:
            # Use multi-step agent executor if available (let it choose the right tool)
            if self.enable_multi_step and self.agent_executor:
                # Multi-step mode: Use agent executor with RAG tools
                self.logger.info("Processing with multi-step agent executor")
                result = self.agent_executor.invoke({
                    "input": user_message
                })
                response_content = result.get("output", "")
                processing_mode = "multi-step"
                
            else:
                # Simple mode: Use conversation chain directly
                self.logger.info("Processing with simple conversation chain")
                config: RunnableConfig = {"configurable": {"session_id": self.conversation_id}}
                response_content = self.conversation_chain.invoke(
                    [HumanMessage(content=user_message)],
                    config=config
                )
                processing_mode = "simple"
            
            # Simple performance tracking
            response_time = time.time() - start_time
            self._message_count += 1
            
            # Azure observability logging
            self.logger.info(
                f"Response generated via {processing_mode} mode",
                message_length=len(user_message),
                response_length=len(response_content),
                response_time=response_time,
                message_count=self._message_count,
                processing_mode=processing_mode
            )
            
            return {
                'content': response_content,
                'conversation_id': self.conversation_id,
                'message_count': self._message_count,
                'response_time': response_time,
                'processing_mode': processing_mode,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'used_documents': False,  # Not RAG-based
                'sources': []
            }
            
        except Exception as e:
            return self._handle_error(e, user_message, time.time() - start_time)
    
    def stream_response(self, user_message: str, **kwargs):
        """Stream response using appropriate mode - supports both simple and multi-step."""
        if not user_message.strip():
            yield self._error_response("Please provide a message.")
            return
        
        try:
            if self.enable_multi_step and self.agent_executor:
                # Multi-step mode: Stream from agent executor
                self.logger.info("Streaming with multi-step agent executor")
                for chunk in self.agent_executor.stream({
                    "input": user_message
                }):
                    # Agent executor streams structured output
                    if 'output' in chunk:
                        yield {
                            'content': chunk['output'],
                            'conversation_id': self.conversation_id,
                            'is_streaming': True,
                            'processing_mode': 'multi-step',
                            'timestamp': time.time()
                        }
                    elif 'intermediate_steps' in chunk:
                        # Optional: expose tool usage for debugging
                        yield {
                            'content': f"[Using tool: {chunk['intermediate_steps'][-1][0].tool if chunk['intermediate_steps'] else 'unknown'}]",
                            'conversation_id': self.conversation_id,
                            'is_streaming': True,
                            'is_intermediate': True,
                            'processing_mode': 'multi-step',
                            'timestamp': time.time()
                        }
            
            else:
                # Simple mode: Stream from conversation chain
                self.logger.info("Streaming with simple conversation chain")
                config: RunnableConfig = {"configurable": {"session_id": self.conversation_id}}
                
                for chunk in self.conversation_chain.stream(
                    [HumanMessage(content=user_message)],
                    config=config
                ):
                    yield {
                        'content': chunk,
                        'conversation_id': self.conversation_id,
                        'is_streaming': True,
                        'processing_mode': 'simple',
                        'timestamp': time.time()
                    }
            
            # Final marker
            yield {
                'content': '',
                'conversation_id': self.conversation_id,
                'is_streaming': False,
                'is_final': True,
                'timestamp': time.time()
            }
            
        except Exception as e:
            yield self._error_response(f"Streaming error: {str(e)}")
    
    
    
    def update_general_knowledge_preference(self, use_general_knowledge: bool):
        """
        Update the agent's general knowledge preference.
        
        Args:
            use_general_knowledge: New preference setting
        """
        self.use_general_knowledge = use_general_knowledge
        self.logger.info("Updated general knowledge preference", use_general_knowledge=use_general_knowledge)

    def _handle_error(self, error: Exception, user_message: str, response_time: float) -> Dict[str, Any]:
        """Simplified error handling - Azure pattern."""
        chatbot_error = handle_error(error)
        
        self.logger.error(
            "Processing error",
            error=str(chatbot_error),
            error_type=type(error).__name__,
            response_time=response_time,
            message_length=len(user_message)
        )
        
        return self._error_response(
            "I encountered an issue processing your message. Please try again.",
            str(chatbot_error)
        )
    
    def _error_response(self, message: str, error: Optional[str] = None) -> Dict[str, Any]:
        """Create standardized error response."""
        return {
            'content': message,
            'conversation_id': self.conversation_id,
            'is_error': True,
            'error': error,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    
    def get_conversation_history(self) -> List[BaseMessage]:
        """Get conversation history from LangChain."""
        history = create_session_history(self.conversation_id, self.persistence_file)
        return history.messages
    
    def clear_conversation(self):
        """Clear conversation using LangChain native method."""
        history = create_session_history(self.conversation_id, self.persistence_file)
        history.clear()
        self._message_count = 0
        self.logger.info("Conversation cleared")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Simple statistics - Azure monitoring pattern."""
        history = self.get_conversation_history()
        return {
            'conversation_id': self.conversation_id,
            'message_count': self._message_count,
            'total_messages': len(history),
            'uptime': time.time() - self._start_time,
            'azure_model': getattr(self.llm, 'model_name', 'unknown'),
            'persistence': 'file' if self.persistence_file else 'memory'
        }
    
    def health_check(self) -> Dict[str, Any]:
        """Azure health check pattern."""
        try:
            # Simple test with Azure OpenAI
            test_response = self.llm.invoke([
                SystemMessage(content="You are a test assistant."),
                HumanMessage(content="Health check")
            ])
            
            return {
                'status': 'healthy',
                'azure_openai': 'connected',
                'model': getattr(self.llm, 'model_name', 'unknown'),
                'test_response_length': len(test_response.content),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    def save_conversation(self, filename: str):
        """Save conversation to file - simplified."""
        try:
            from pathlib import Path
            import json
            
            history = self.get_conversation_history()
            
            data = {
                'conversation_id': self.conversation_id,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'messages': [
                    {
                        'type': type(msg).__name__,
                        'content': msg.content
                    }
                    for msg in history
                ]
            }
            
            file_path = Path(filename)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
            self.logger.info("Conversation saved", filename=filename)
            
        except Exception as e:
            self.logger.error("Failed to save conversation", error=str(e))
            raise
    
    def run_interactive_session(self, max_turns: int = 50, welcome_message: bool = True):
        """
        Run an interactive chat session with the user.
        
        Args:
            max_turns: Maximum number of conversation turns
            welcome_message: Whether to show a welcome message
        """
        try:
            from src.utils.console import Console
            console = Console()
        except ImportError:
            # Fallback if console utils not available
            class SimpleConsole:
                def print_status(self, msg, status): print(f"[{status.upper()}] {msg}")
                def confirm(self, msg, default): return input(f"{msg} [y/N]: ").lower().startswith('y')
            console = SimpleConsole()
        
        if welcome_message:
            console.print_status("🤖 Azure OpenAI Chatbot started!", "success")
            console.print_status("Type 'quit', 'exit', or press Ctrl+C to end the conversation", "info")
            print()
        
        turn_count = 0
        
        try:
            while turn_count < max_turns:
                try:
                    # Get user input
                    user_input = input("🧑 You: ").strip()
                    
                    # Check for exit commands
                    if user_input.lower() in ['quit', 'exit', 'bye']:
                        console.print_status("Goodbye! 👋", "success")
                        break
                    
                    if not user_input:
                        continue
                    
                    # Process the message
                    print("🤖 Assistant: ", end="", flush=True)
                    
                    # Use streaming response for better UX
                    try:
                        for chunk in self.stream_response(user_input):
                            if chunk.get('type') == 'content':
                                content = chunk.get('content', '')
                                print(content, end="", flush=True)
                            elif chunk.get('type') == 'error':
                                console.print_status(f"Error: {chunk.get('content')}", "error")
                                break
                    except Exception as stream_error:
                        # Fallback to regular process_message if streaming fails
                        self.logger.warning("Streaming failed, using regular response", error=str(stream_error))
                        response = self.process_message(user_input)
                        print(response.get('response', 'Sorry, I encountered an error.'))
                    
                    print()  # New line after response
                    print()  # Extra line for readability
                    
                    turn_count += 1
                    
                except KeyboardInterrupt:
                    print()  # New line after Ctrl+C
                    console.print_status("Chat interrupted by user", "warning")
                    break
                except EOFError:
                    print()  # New line after EOF
                    console.print_status("Input stream ended", "info")
                    break
                except Exception as e:
                    console.print_status(f"Error processing message: {str(e)}", "error")
                    self.logger.error("Error in interactive session", error=str(e))
        
        except Exception as e:
            try:
                console.print_status(f"Session error: {str(e)}", "error")
            except:
                print(f"Session error: {str(e)}")
            self.logger.error("Interactive session failed", error=str(e))
        
        finally:
            if turn_count > 0:
                try:
                    console.print_status(f"Session ended after {turn_count} turns", "info")
                except:
                    print(f"Session ended after {turn_count} turns")
    
    def __repr__(self) -> str:
        """String representation."""
        return (
            f"ChatbotAgent("
            f"id={self.conversation_id[:8]}, "
            f"messages={self._message_count}, "
            f"model={getattr(self.llm, 'model_name', 'unknown')}"
            f")"
        )