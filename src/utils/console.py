"""
Rich console utilities for enhanced CLI output.
Task 18: Rich console utilities with progress indicators, status messages, and conversation formatting.
"""

import sys
import time
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.progress import Progress, TaskID, SpinnerColumn, TextColumn, BarColumn, MofNCompleteColumn
from rich.status import Status
from rich.prompt import Prompt, Confirm
from rich.layout import Layout
from rich.live import Live
from rich.align import Align
from rich.rule import Rule
from rich import box
import structlog

from src.utils.error_handlers import ChatbotBaseError

logger = structlog.get_logger(__name__)


class ChatbotConsole:
    """Enhanced console for chatbot application with Rich formatting."""
    
    def __init__(
        self,
        width: Optional[int] = None,
        file: Any = None,
        theme: str = "dark"
    ):
        """
        Initialize chatbot console.
        
        Args:
            width: Console width (auto-detected if None)
            file: Output file (default: stdout)
            theme: Console theme (dark/light)
        """
        # Handle Windows encoding issues
        import platform
        console_kwargs = {
            'width': width,
            'file': file or sys.stdout,
            'force_terminal': True,
            'color_system': "auto"
        }
        
        # On Windows, disable unicode emojis if encoding doesn't support them
        if platform.system() == "Windows":
            try:
                # Test if we can encode common unicode characters
                test_chars = "ℹ️✅⚠️❌🔄"
                (file or sys.stdout).encoding or "utf-8"
                test_chars.encode((file or sys.stdout).encoding or "utf-8")
            except (UnicodeEncodeError, AttributeError):
                # If encoding fails, we'll disable unicode emojis later
                pass
        
        self.console = Console(**console_kwargs)
        
        self.theme = theme
        self.conversation_count = 0
        
        # Test unicode support for emojis
        self.unicode_supported = True
        if platform.system() == "Windows":
            try:
                test_chars = "ℹ️✅⚠️❌🔄"
                encoding = (file or sys.stdout).encoding or "utf-8"
                test_chars.encode(encoding)
            except (UnicodeEncodeError, AttributeError):
                self.unicode_supported = False
        
        # Color scheme based on theme
        if theme == "light":
            self.colors = {
                'primary': 'blue',
                'secondary': 'cyan',
                'success': 'green',
                'warning': 'orange1',
                'error': 'red',
                'info': 'blue',
                'user': 'bright_blue',
                'assistant': 'bright_green',
                'system': 'bright_yellow'
            }
        else:  # dark theme
            self.colors = {
                'primary': 'bright_blue',
                'secondary': 'bright_cyan',
                'success': 'bright_green',
                'warning': 'bright_yellow',
                'error': 'bright_red',
                'info': 'bright_blue',
                'user': 'bright_blue',
                'assistant': 'bright_green',
                'system': 'bright_yellow'
            }
    
    def print_banner(self, app_name: str = "Azure OpenAI Chatbot", version: str = "1.0.0"):
        """Print application banner."""
        robot_emoji = "🤖" if self.unicode_supported else "[AI]"
        banner_text = f"""
{robot_emoji} {app_name} v{version}
Powered by Azure OpenAI and LangChain
        """.strip()
        
        banner_panel = Panel(
            Align.center(Text(banner_text, style=f"bold {self.colors['primary']}")),
            box=box.DOUBLE,
            style=self.colors['primary'],
            padding=(1, 2)
        )
        
        self.console.print()
        self.console.print(banner_panel)
        self.console.print()
    
    def print_status(
        self,
        message: str,
        status: str = "info",
        emoji: bool = True
    ):
        """Print status message with appropriate styling."""
        if self.unicode_supported:
            emoji_map = {
                'info': 'ℹ️',
                'success': '✅',
                'warning': '⚠️',
                'error': '❌',
                'loading': '🔄'
            }
        else:
            # ASCII fallbacks for Windows systems with encoding issues
            emoji_map = {
                'info': '[i]',
                'success': '[+]',
                'warning': '[!]',
                'error': '[x]',
                'loading': '[~]'
            }
        
        color = self.colors.get(status, self.colors['info'])
        prefix = f"{emoji_map.get(status, '')} " if emoji else ""
        
        self.console.print(f"{prefix}{message}", style=color)
    
    def print_error(self, error: Union[str, Exception, ChatbotBaseError]):
        """Print error with recovery suggestions."""
        if isinstance(error, ChatbotBaseError):
            # Rich error formatting for chatbot errors
            error_panel = Panel(
                self._format_chatbot_error(error),
                title="❌ Error",
                title_align="left",
                border_style=self.colors['error'],
                padding=(0, 1)
            )
            self.console.print(error_panel)
        else:
            # Simple error message
            self.console.print(f"❌ {str(error)}", style=self.colors['error'])
    
    def _format_chatbot_error(self, error: ChatbotBaseError) -> Text:
        """Format chatbot error with suggestions."""
        text = Text()
        
        # Error message
        text.append(f"{error.get_user_friendly_message()}\n", style=f"bold {self.colors['error']}")
        
        # Recovery suggestions
        if error.recovery_suggestions:
            text.append("\n💡 Suggestions:\n", style=f"bold {self.colors['warning']}")
            for i, suggestion in enumerate(error.recovery_suggestions, 1):
                text.append(f"  {i}. {suggestion}\n", style=self.colors['info'])
        
        # Error code
        if error.error_code:
            text.append(f"\n🔍 Error Code: {error.error_code}", style="dim")
        
        return text
    
    def print_info(self, message: str):
        """Print informational message."""
        if self.unicode_supported:
            icon = "ℹ️"
        else:
            icon = "[i]"
        
        self.console.print(f"{icon} {message}", style=self.colors['info'])
    
    def print_success(self, message: str):
        """Print success message."""
        if self.unicode_supported:
            icon = "✅"
        else:
            icon = "[+]"
        
        self.console.print(f"{icon} {message}", style=self.colors['success'])
    
    def print_warning(self, message: str):
        """Print warning message."""
        if self.unicode_supported:
            icon = "⚠️"
        else:
            icon = "[!]"
        
        self.console.print(f"{icon} {message}", style=self.colors['warning'])
    
    def print_conversation_message(
        self,
        role: str,
        content: str,
        timestamp: Optional[datetime] = None,
        token_count: Optional[int] = None
    ):
        """Print a conversation message with proper formatting."""
        # Determine role styling
        role_colors = {
            'user': self.colors['user'],
            'assistant': self.colors['assistant'],
            'system': self.colors['system']
        }
        
        if self.unicode_supported:
            role_icons = {
                'user': '👤',
                'assistant': '🤖',
                'system': '⚙️'
            }
            default_icon = '💬'
        else:
            role_icons = {
                'user': '[U]',
                'assistant': '[AI]',
                'system': '[SYS]'
            }
            default_icon = '[MSG]'
        
        role_color = role_colors.get(role.lower(), self.colors['info'])
        role_icon = role_icons.get(role.lower(), default_icon)
        
        # Format timestamp
        time_str = ""
        if timestamp:
            time_str = f" • {timestamp.strftime('%H:%M:%S')}"
        
        # Format token count
        token_str = ""
        if token_count:
            token_str = f" • {token_count} tokens"
        
        # Create header
        header = f"{role_icon} {role.title()}{time_str}{token_str}"
        
        # Format content
        if role.lower() == 'system':
            # System messages in smaller text
            content_text = Text(content, style="dim italic")
        else:
            # Try to detect and format code blocks
            if "```" in content:
                content_text = self._format_code_content(content)
            else:
                content_text = Text(content)
        
        # Create panel
        message_panel = Panel(
            content_text,
            title=header,
            title_align="left",
            border_style=role_color,
            padding=(0, 1),
            expand=False
        )
        
        self.console.print(message_panel)
        self.console.print()  # Add spacing
    
    def _format_code_content(self, content: str) -> Text:
        """Format content with code blocks."""
        text = Text()
        lines = content.split('\n')
        in_code_block = False
        code_language = None
        code_lines = []
        
        for line in lines:
            if line.strip().startswith('```'):
                if not in_code_block:
                    # Starting code block
                    in_code_block = True
                    code_language = line.strip()[3:].strip() or 'text'
                    code_lines = []
                else:
                    # Ending code block
                    in_code_block = False
                    if code_lines:
                        try:
                            syntax = Syntax(
                                '\n'.join(code_lines),
                                code_language,
                                theme="monokai" if self.theme == "dark" else "default",
                                line_numbers=len(code_lines) > 5
                            )
                            text.append('\n')
                            # Note: Rich Text doesn't directly support Syntax objects
                            # In a real implementation, you'd render this separately
                            text.append(f"[Code: {code_language}]\n", style="dim")
                            text.append('\n'.join(code_lines), style="cyan")
                            text.append('\n')
                        except Exception:
                            # Fallback to plain text
                            text.append('\n'.join(code_lines), style="cyan")
                    code_lines = []
            elif in_code_block:
                code_lines.append(line)
            else:
                text.append(line + '\n' if line != lines[-1] else line)
        
        return text
    
    def print_conversation_stats(self, stats: Dict[str, Any]):
        """Print conversation statistics in a table."""
        stats_emoji = "📊" if self.unicode_supported else "[STATS]"
        table = Table(title=f"{stats_emoji} Conversation Statistics", show_header=False, box=box.ROUNDED)
        table.add_column("Metric", style=self.colors['secondary'])
        table.add_column("Value", style=self.colors['primary'])
        
        # Format statistics
        formatted_stats = [
            ("Messages", str(stats.get('total_messages', 0))),
            ("User Messages", str(stats.get('user_messages', 0))),
            ("Assistant Responses", str(stats.get('assistant_messages', 0))),
            ("Total Tokens", f"{stats.get('total_tokens', 0):,}"),
            ("Duration", self._format_duration(stats.get('duration_seconds', 0))),
            ("Average Message Length", f"{stats.get('average_message_length', 0):.1f} chars")
        ]
        
        for metric, value in formatted_stats:
            table.add_row(metric, value)
        
        self.console.print(table)
        self.console.print()
    
    def _format_duration(self, seconds: float) -> str:
        """Format duration in human-readable format."""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f}m"
        else:
            hours = seconds / 3600
            return f"{hours:.1f}h"
    
    def create_progress_bar(
        self,
        description: str = "Processing...",
        total: Optional[int] = None
    ) -> Progress:
        """Create a progress bar with spinner."""
        progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn() if total else TextColumn(""),
            MofNCompleteColumn() if total else TextColumn(""),
            console=self.console
        )
        
        return progress
    
    def show_status(self, message: str) -> Status:
        """Show status with spinner."""
        return Status(message, console=self.console, spinner="dots")
    
    def prompt_user(
        self,
        message: str,
        default: Optional[str] = None,
        password: bool = False
    ) -> str:
        """Prompt user for input."""
        return Prompt.ask(
            f"[{self.colors['primary']}]{message}[/{self.colors['primary']}]",
            default=default,
            password=password,
            console=self.console
        )
    
    def confirm(
        self,
        message: str,
        default: bool = False
    ) -> bool:
        """Ask for user confirmation."""
        return Confirm.ask(
            f"[{self.colors['warning']}]{message}[/{self.colors['warning']}]",
            default=default,
            console=self.console
        )
    
    def print_table(
        self,
        data: List[Dict[str, Any]],
        title: Optional[str] = None,
        columns: Optional[List[str]] = None
    ):
        """Print data in table format."""
        if not data:
            self.print_status("No data to display", "info")
            return
        
        # Determine columns
        if columns is None:
            columns = list(data[0].keys())
        
        # Create table
        table = Table(title=title, show_header=True, header_style=f"bold {self.colors['primary']}")
        
        for column in columns:
            table.add_column(column.title().replace('_', ' '))
        
        # Add rows
        for row in data:
            values = [str(row.get(col, '')) for col in columns]
            table.add_row(*values)
        
        self.console.print(table)
    
    def print_separator(self, title: Optional[str] = None):
        """Print a separator line."""
        if title:
            self.console.print(Rule(title, style=self.colors['secondary']))
        else:
            self.console.print(Rule(style="dim"))
    
    def clear(self):
        """Clear the console."""
        self.console.clear()
    
    def print_help(self, commands: Dict[str, str]):
        """Print help information."""
        books_emoji = "📚" if self.unicode_supported else "[HELP]"
        help_table = Table(title=f"{books_emoji} Available Commands", show_header=True, box=box.ROUNDED)
        help_table.add_column("Command", style=f"bold {self.colors['primary']}")
        help_table.add_column("Description", style=self.colors['info'])
        
        for command, description in commands.items():
            help_table.add_row(command, description)
        
        self.console.print(help_table)
    
    def print_welcome_message(self):
        """Print welcome message for interactive mode."""
        robot_emoji = "🤖" if self.unicode_supported else "[AI]"
        chat_emoji = "💬" if self.unicode_supported else "[CHAT]"
        rocket_emoji = "🚀" if self.unicode_supported else "[START]"
        
        welcome_text = f"""
Welcome to the Azure OpenAI Chatbot! {robot_emoji}

Type your messages and press Enter to chat with the AI.
Use these commands at any time:

• `/help` - Show available commands
• `/stats` - Show conversation statistics  
• `/clear` - Clear conversation history
• `/save` - Save conversation to file
• `/load` - Load conversation from file
• `/exit` or `/quit` - Exit the application

Let's start chatting! {chat_emoji}
        """.strip()
        
        welcome_panel = Panel(
            welcome_text,
            title=f"{rocket_emoji} Getting Started",
            title_align="left",
            border_style=self.colors['success'],
            padding=(1, 2)
        )
        
        self.console.print(welcome_panel)
        self.console.print()
    
    def print_goodbye_message(self):
        """Print goodbye message."""
        goodbye_text = Text("Thank you for using Azure OpenAI Chatbot! 👋", style=f"bold {self.colors['success']}")
        goodbye_panel = Panel(
            Align.center(goodbye_text),
            border_style=self.colors['success'],
            padding=(1, 2)
        )
        
        self.console.print()
        self.console.print(goodbye_panel)
        self.console.print()


class NullConsole:
    """A console that doesn't output anything when console logging is disabled."""
    
    def print_status(self, *args, **kwargs):
        """No-op print status."""
        pass
    
    def show_status(self, *args, **kwargs):
        """No-op show status."""
        from contextlib import nullcontext
        return nullcontext()
    
    def print_banner(self, *args, **kwargs):
        """No-op print banner."""
        pass
    
    def print_welcome_message(self, *args, **kwargs):
        """No-op print welcome message."""
        pass
    
    def print_goodbye_message(self, *args, **kwargs):
        """No-op print goodbye message."""
        pass
    
    def print_conversation_separator(self, *args, **kwargs):
        """No-op print conversation separator."""
        pass
    
    def print_error(self, *args, **kwargs):
        """No-op print error."""
        pass
    
    def print_warning(self, *args, **kwargs):
        """No-op print warning."""
        pass
    
    def print_info(self, *args, **kwargs):
        """No-op print info."""
        pass
    
    def print_success(self, *args, **kwargs):
        """No-op print success."""
        pass
    
    def print_conversation_message(self, *args, **kwargs):
        """No-op print conversation message."""
        pass
    
    def print_conversation_stats(self, *args, **kwargs):
        """No-op print conversation stats."""
        pass
    
    def print_table(self, *args, **kwargs):
        """No-op print table."""
        pass
    
    def print_separator(self, *args, **kwargs):
        """No-op print separator."""
        pass
    
    def print_help(self, *args, **kwargs):
        """No-op print help."""
        pass
    
    def create_progress(self, *args, **kwargs):
        """Return a no-op progress context."""
        from contextlib import nullcontext
        return nullcontext()
    
    def __getattr__(self, name):
        """Return no-op for any other method calls."""
        def no_op(*args, **kwargs):
            pass
        return no_op


# Global console instance
_console: Optional[ChatbotConsole] = None


def create_console(
    theme: str = "dark",
    width: Optional[int] = None,
    settings = None
) -> Union[ChatbotConsole, NullConsole]:
    """
    Create or get the global console instance.
    
    Args:
        theme: Console theme (dark/light)
        width: Console width
        settings: Application settings instance
        
    Returns:
        ChatbotConsole instance or NullConsole if console logging is disabled
    """
    global _console
    
    # Check if console logging is disabled
    if settings and hasattr(settings, 'enable_console_logging') and not settings.enable_console_logging:
        return NullConsole()
    
    if _console is None:
        _console = ChatbotConsole(theme=theme, width=width)
    
    return _console


def get_console() -> ChatbotConsole:
    """Get the global console instance."""
    if _console is None:
        return create_console()
    return _console


def format_conversation(
    messages: List[Dict[str, Any]],
    include_timestamps: bool = True,
    include_tokens: bool = True
) -> str:
    """
    Format conversation messages for display or export.
    
    Args:
        messages: List of conversation messages
        include_timestamps: Whether to include timestamps
        include_tokens: Whether to include token counts
        
    Returns:
        Formatted conversation string
    """
    if not messages:
        return "No messages in conversation."
    
    formatted_lines = []
    
    for msg in messages:
        role = msg.get('role', 'unknown')
        content = msg.get('content', '')
        timestamp = msg.get('timestamp')
        token_count = msg.get('token_count')
        
        # Format header
        header_parts = [f"{role.upper()}"]
        
        if include_timestamps and timestamp:
            if isinstance(timestamp, str):
                timestamp_str = timestamp
            else:
                timestamp_str = timestamp.strftime('%H:%M:%S')
            header_parts.append(timestamp_str)
        
        if include_tokens and token_count:
            header_parts.append(f"{token_count} tokens")
        
        header = " • ".join(header_parts)
        
        # Add to output
        formatted_lines.append(f"[{header}]")
        formatted_lines.append(content)
        formatted_lines.append("")  # Empty line for spacing
    
    return "\n".join(formatted_lines)


def format_error_message(error: Exception) -> str:
    """
    Format error message for console display.
    
    Args:
        error: Exception to format
        
    Returns:
        Formatted error message
    """
    if isinstance(error, ChatbotBaseError):
        lines = [f"❌ Error: {error.get_user_friendly_message()}"]
        
        if error.recovery_suggestions:
            lines.append("\n💡 Suggestions:")
            for i, suggestion in enumerate(error.recovery_suggestions, 1):
                lines.append(f"  {i}. {suggestion}")
        
        if error.error_code:
            lines.append(f"\n🔍 Error Code: {error.error_code}")
        
        return "\n".join(lines)
    else:
        return f"❌ Error: {str(error)}"