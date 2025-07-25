"""
Conversation memory management using LangChain.
Task 16: Conversation memory with LangChain memory classes, state management, and persistence.
"""

import json
import uuid
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from pathlib import Path
import structlog

from langchain.memory import (
    ConversationBufferMemory,
    ConversationBufferWindowMemory,
    ConversationSummaryBufferMemory
)
from langchain.memory.chat_memory import BaseChatMemory
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain.schema import BaseMemory

from config.settings import Settings
from utils.error_handlers import ConversationError

logger = structlog.get_logger(__name__)


@dataclass
class ConversationMetadata:
    """Metadata for a conversation."""
    conversation_id: str
    created_at: datetime
    updated_at: datetime
    message_count: int
    total_tokens: int
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    title: Optional[str] = None
    summary: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        # Convert datetime objects to ISO strings
        data['created_at'] = self.created_at.isoformat()
        data['updated_at'] = self.updated_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationMetadata':
        """Create from dictionary."""
        # Convert ISO strings back to datetime objects
        if isinstance(data.get('created_at'), str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if isinstance(data.get('updated_at'), str):
            data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        
        return cls(**data)


@dataclass
class ConversationMessage:
    """A single message in a conversation."""
    message_id: str
    role: str  # 'user', 'assistant', 'system'
    content: str
    timestamp: datetime
    token_count: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationMessage':
        """Create from dictionary."""
        if isinstance(data.get('timestamp'), str):
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)
    
    def to_langchain_message(self) -> BaseMessage:
        """Convert to LangChain message format."""
        if self.role.lower() == 'user':
            return HumanMessage(content=self.content)
        elif self.role.lower() == 'assistant':
            return AIMessage(content=self.content)
        elif self.role.lower() == 'system':
            return SystemMessage(content=self.content)
        else:
            # Default to human message for unknown roles
            return HumanMessage(content=self.content)


class ConversationManager:
    """
    Manages conversation memory and persistence using LangChain memory classes.
    
    Features:
    - Multiple memory types (buffer, buffer_window, summary_buffer)
    - Conversation state serialization/deserialization
    - Message history persistence
    - Conversation summarization
    - Token usage tracking
    - Conversation cleanup and archival
    """
    
    def __init__(
        self,
        settings: Settings,
        conversation_id: Optional[str] = None,
        memory_type: Optional[str] = None,
        max_turns: Optional[int] = None
    ):
        """
        Initialize conversation manager.
        
        Args:
            settings: Application settings
            conversation_id: Unique conversation identifier
            memory_type: Type of memory to use (buffer, buffer_window, summary)
            max_turns: Maximum number of turns to keep in memory
        """
        self.settings = settings
        self.conversation_id = conversation_id or str(uuid.uuid4())
        self.memory_type = memory_type or settings.conversation_memory_type
        self.max_turns = max_turns or settings.max_conversation_turns
        
        self.logger = logger.bind(
            conversation_id=self.conversation_id,
            memory_type=self.memory_type
        )
        
        # Initialize conversation metadata
        self.metadata = ConversationMetadata(
            conversation_id=self.conversation_id,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            message_count=0,
            total_tokens=0
        )
        
        # Initialize LangChain memory
        self.memory = self._create_memory()
        
        # Message storage for persistence
        self.messages: List[ConversationMessage] = []
        
        self.logger.info(
            "Conversation manager initialized",
            memory_type=self.memory_type,
            max_turns=self.max_turns
        )
    
    def _create_memory(self) -> BaseMemory:
        """Create appropriate LangChain memory instance."""
        try:
            if self.memory_type == "buffer":
                return ConversationBufferMemory(
                    return_messages=True,
                    memory_key="chat_history"
                )
            elif self.memory_type == "buffer_window":
                return ConversationBufferWindowMemory(
                    k=self.max_turns,
                    return_messages=True,
                    memory_key="chat_history"
                )
            elif self.memory_type == "summary":
                # Note: This requires an LLM for summarization
                # We'll implement a basic version here
                return ConversationSummaryBufferMemory(
                    max_token_limit=2000,
                    return_messages=True,
                    memory_key="chat_history"
                )
            else:
                self.logger.warning(
                    f"Unknown memory type: {self.memory_type}, defaulting to buffer_window"
                )
                return ConversationBufferWindowMemory(
                    k=self.max_turns,
                    return_messages=True,
                    memory_key="chat_history"
                )
        except Exception as e:
            self.logger.error(
                "Failed to create memory instance",
                error=str(e),
                memory_type=self.memory_type
            )
            # Fallback to basic buffer memory
            return ConversationBufferMemory(
                return_messages=True,
                memory_key="chat_history"
            )
    
    def add_message(
        self,
        role: str,
        content: str,
        token_count: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Add a message to the conversation.
        
        Args:
            role: Message role ('user', 'assistant', 'system')
            content: Message content
            token_count: Number of tokens in the message
            metadata: Additional metadata for the message
            
        Returns:
            Message ID
            
        Raises:
            ConversationError: If message validation fails
        """
        # Validate input
        if not content.strip():
            raise ConversationError("Message content cannot be empty")
        
        if role.lower() not in ['user', 'assistant', 'system']:
            raise ConversationError(f"Invalid message role: {role}")
        
        # Create message
        message = ConversationMessage(
            message_id=str(uuid.uuid4()),
            role=role.lower(),
            content=content.strip(),
            timestamp=datetime.now(timezone.utc),
            token_count=token_count,
            metadata=metadata or {}
        )
        
        try:
            # Add to LangChain memory
            if role.lower() == 'user':
                self.memory.chat_memory.add_user_message(content)
            elif role.lower() == 'assistant':
                self.memory.chat_memory.add_ai_message(content)
            # System messages are typically not added to chat memory
            
            # Store message locally
            self.messages.append(message)
            
            # Update metadata
            self.metadata.message_count += 1
            self.metadata.updated_at = datetime.now(timezone.utc)
            if token_count:
                self.metadata.total_tokens += token_count
            
            # Generate conversation title if this is the first user message
            if role.lower() == 'user' and self.metadata.message_count == 1:
                self.metadata.title = self._generate_title(content)
            
            self.logger.debug(
                "Message added to conversation",
                message_id=message.message_id,
                role=role,
                content_length=len(content),
                token_count=token_count
            )
            
            return message.message_id
            
        except Exception as e:
            self.logger.error(
                "Failed to add message to conversation",
                error=str(e),
                role=role,
                content_length=len(content)
            )
            raise ConversationError(f"Failed to add message: {str(e)}")
    
    def get_messages(
        self,
        limit: Optional[int] = None,
        include_system: bool = False
    ) -> List[ConversationMessage]:
        """
        Get conversation messages.
        
        Args:
            limit: Maximum number of messages to return (most recent first)
            include_system: Whether to include system messages
            
        Returns:
            List of conversation messages
        """
        messages = self.messages.copy()
        
        if not include_system:
            messages = [msg for msg in messages if msg.role != 'system']
        
        if limit:
            messages = messages[-limit:]
        
        return messages
    
    def get_langchain_messages(
        self,
        include_system: bool = True
    ) -> List[BaseMessage]:
        """
        Get messages in LangChain format.
        
        Args:
            include_system: Whether to include system messages
            
        Returns:
            List of LangChain BaseMessage objects
        """
        messages = []
        
        for msg in self.messages:
            if not include_system and msg.role == 'system':
                continue
            messages.append(msg.to_langchain_message())
        
        return messages
    
    def get_memory_variables(self) -> Dict[str, Any]:
        """Get memory variables for LangChain integration."""
        return self.memory.load_memory_variables({})
    
    def clear_memory(self) -> None:
        """Clear conversation memory."""
        try:
            self.memory.clear()
            self.messages.clear()
            
            # Reset metadata
            self.metadata.message_count = 0
            self.metadata.total_tokens = 0
            self.metadata.updated_at = datetime.now(timezone.utc)
            self.metadata.title = None
            self.metadata.summary = None
            
            self.logger.info("Conversation memory cleared")
            
        except Exception as e:
            self.logger.error("Failed to clear memory", error=str(e))
            raise ConversationError(f"Failed to clear memory: {str(e)}")
    
    def get_conversation_summary(self, max_length: int = 500) -> str:
        """
        Generate a summary of the conversation.
        
        Args:
            max_length: Maximum length of the summary
            
        Returns:
            Conversation summary
        """
        if not self.messages:
            return "Empty conversation"
        
        # Simple summarization - in production, this could use an LLM
        user_messages = [msg for msg in self.messages if msg.role == 'user']
        assistant_messages = [msg for msg in self.messages if msg.role == 'assistant']
        
        summary_parts = []
        
        if self.metadata.title:
            summary_parts.append(f"Topic: {self.metadata.title}")
        
        summary_parts.extend([
            f"Messages: {self.metadata.message_count}",
            f"User messages: {len(user_messages)}",
            f"Assistant responses: {len(assistant_messages)}",
            f"Duration: {datetime.now(timezone.utc) - self.metadata.created_at}"
        ])
        
        if self.metadata.total_tokens > 0:
            summary_parts.append(f"Total tokens: {self.metadata.total_tokens}")
        
        # Add snippet of first user message
        if user_messages:
            first_msg = user_messages[0].content
            snippet = first_msg[:100] + "..." if len(first_msg) > 100 else first_msg
            summary_parts.append(f"Started with: \"{snippet}\"")
        
        summary = ". ".join(summary_parts)
        
        # Truncate if too long
        if len(summary) > max_length:
            summary = summary[:max_length-3] + "..."
        
        return summary
    
    def _generate_title(self, first_user_message: str) -> str:
        """Generate a conversation title from the first user message."""
        # Simple title generation - in production, this could use an LLM
        title = first_user_message.strip()
        
        # Truncate to reasonable length
        if len(title) > 50:
            title = title[:47] + "..."
        
        # Remove newlines and extra spaces
        title = " ".join(title.split())
        
        return title
    
    def export_conversation(self, include_metadata: bool = True) -> Dict[str, Any]:
        """
        Export conversation to dictionary format.
        
        Args:
            include_metadata: Whether to include conversation metadata
            
        Returns:
            Dictionary containing conversation data
        """
        data = {
            'conversation_id': self.conversation_id,
            'messages': [msg.to_dict() for msg in self.messages],
            'message_count': len(self.messages),
            'exported_at': datetime.now(timezone.utc).isoformat()
        }
        
        if include_metadata:
            data['metadata'] = self.metadata.to_dict()
        
        return data
    
    def import_conversation(self, data: Dict[str, Any]) -> None:
        """
        Import conversation from dictionary format.
        
        Args:
            data: Dictionary containing conversation data
        """
        try:
            # Clear existing conversation
            self.clear_memory()
            
            # Import messages
            if 'messages' in data:
                for msg_data in data['messages']:
                    msg = ConversationMessage.from_dict(msg_data)
                    self.messages.append(msg)
                    
                    # Add to LangChain memory
                    if msg.role == 'user':
                        self.memory.chat_memory.add_user_message(msg.content)
                    elif msg.role == 'assistant':
                        self.memory.chat_memory.add_ai_message(msg.content)
            
            # Import metadata if available
            if 'metadata' in data:
                self.metadata = ConversationMetadata.from_dict(data['metadata'])
            else:
                # Reconstruct metadata from messages
                self.metadata.message_count = len(self.messages)
                self.metadata.updated_at = datetime.now(timezone.utc)
                if self.messages:
                    self.metadata.total_tokens = sum(
                        msg.token_count or 0 for msg in self.messages
                    )
            
            self.logger.info(
                "Conversation imported successfully",
                message_count=len(self.messages),
                total_tokens=self.metadata.total_tokens
            )
            
        except Exception as e:
            self.logger.error("Failed to import conversation", error=str(e))
            raise ConversationError(f"Failed to import conversation: {str(e)}")
    
    def save_to_file(self, file_path: Union[str, Path]) -> None:
        """
        Save conversation to JSON file.
        
        Args:
            file_path: Path to save the conversation
        """
        try:
            file_path = Path(file_path)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            data = self.export_conversation(include_metadata=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(
                "Conversation saved to file",
                file_path=str(file_path),
                message_count=len(self.messages)
            )
            
        except Exception as e:
            self.logger.error(
                "Failed to save conversation to file",
                error=str(e),
                file_path=str(file_path)
            )
            raise ConversationError(f"Failed to save conversation: {str(e)}")
    
    def load_from_file(self, file_path: Union[str, Path]) -> None:
        """
        Load conversation from JSON file.
        
        Args:
            file_path: Path to load the conversation from
        """
        try:
            file_path = Path(file_path)
            
            if not file_path.exists():
                raise ConversationError(f"Conversation file not found: {file_path}")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.import_conversation(data)
            
            self.logger.info(
                "Conversation loaded from file",
                file_path=str(file_path),
                message_count=len(self.messages)
            )
            
        except json.JSONDecodeError as e:
            self.logger.error(
                "Invalid JSON in conversation file",
                error=str(e),
                file_path=str(file_path)
            )
            raise ConversationError(f"Invalid conversation file format: {str(e)}")
        except Exception as e:
            self.logger.error(
                "Failed to load conversation from file",
                error=str(e),
                file_path=str(file_path)
            )
            raise ConversationError(f"Failed to load conversation: {str(e)}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get conversation statistics."""
        user_messages = [msg for msg in self.messages if msg.role == 'user']
        assistant_messages = [msg for msg in self.messages if msg.role == 'assistant']
        system_messages = [msg for msg in self.messages if msg.role == 'system']
        
        total_chars = sum(len(msg.content) for msg in self.messages)
        avg_message_length = total_chars / len(self.messages) if self.messages else 0
        
        return {
            'conversation_id': self.conversation_id,
            'total_messages': self.metadata.message_count,
            'user_messages': len(user_messages),
            'assistant_messages': len(assistant_messages),
            'system_messages': len(system_messages),
            'total_tokens': self.metadata.total_tokens,
            'total_characters': total_chars,
            'average_message_length': avg_message_length,
            'duration_seconds': (
                self.metadata.updated_at - self.metadata.created_at
            ).total_seconds(),
            'created_at': self.metadata.created_at.isoformat(),
            'updated_at': self.metadata.updated_at.isoformat(),
            'title': self.metadata.title,
            'memory_type': self.memory_type
        }
    
    def __repr__(self) -> str:
        """String representation of the conversation manager."""
        return (
            f"ConversationManager("
            f"id={self.conversation_id[:8]}, "
            f"messages={self.metadata.message_count}, "
            f"tokens={self.metadata.total_tokens}, "
            f"memory={self.memory_type}"
            f")"
        )