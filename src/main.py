#!/usr/bin/env python3
"""
RAG-Enabled Chatbot - Main Entry Point
Updated to launch Streamlit web interface as primary UI, replacing CLI interface.
Legacy CLI interface preserved for backwards compatibility.
"""

import sys
import os
import asyncio
from typing import Optional, Any, Dict
from pathlib import Path
import click
from rich.console import Console

# Fix Windows encoding issues
if os.name == 'nt':  # Windows
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    # Try to set console output to UTF-8
    try:
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.detach())
    except (AttributeError, UnicodeError):
        pass

# Add src directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Configure logging before other imports
import structlog

# Import application components
from config.settings import get_settings, Settings, reload_settings
from services.logging_service import setup_logging, get_logger
from services.azure_client import AzureOpenAIClient
from chatbot.agent import ChatbotAgent
from chatbot.prompts import SystemPrompts
from utils.console import create_console, get_console
from utils.error_handlers import handle_error, format_error_for_user
from utils.logging_helpers import log_startup_event, StructuredLogger

# Import Streamlit app for new primary interface
try:
    from ui.streamlit_app import main as streamlit_main
    STREAMLIT_AVAILABLE = True
except ImportError:
    STREAMLIT_AVAILABLE = False

# Import dual observability system
try:
    from observability.telemetry_service import (
        initialize_dual_observability, 
        is_telemetry_initialized,
        shutdown_telemetry
    )
    DUAL_OBSERVABILITY_AVAILABLE = True
except ImportError:
    DUAL_OBSERVABILITY_AVAILABLE = False

# Initialize logger
logger = structlog.get_logger(__name__).bind(log_type="SYSTEM")


class GlobalContext:
    """Global context for CLI commands."""
    
    def __init__(self):
        self.settings: Optional[Settings] = None
        self.console: Optional[Console] = None
        self.debug: bool = False
        self.dual_observability_initialized: bool = False
        
    def init_settings(self, config_file: Optional[str] = None, debug: bool = False):
        """Initialize application settings."""
        if config_file:
            os.environ['CHATBOT_CONFIG_FILE'] = config_file
        
        self.debug = debug
        
        try:
            # Log initialization start
            log_startup_event(
                message="Initializing application settings",
                component="settings",
                success=True
            )
            
            self.settings = get_settings()
            
            # Initialize dual observability system BEFORE other logging setup
            if DUAL_OBSERVABILITY_AVAILABLE:
                try:
                    log_startup_event(
                        message="Initializing dual observability system",
                        component="telemetry",
                        success=True
                    )
                    
                    self.dual_observability_initialized = initialize_dual_observability(self.settings)
                    
                    if self.dual_observability_initialized:
                        log_startup_event(
                            message="Dual observability system initialized successfully",
                            component="telemetry",
                            success=True
                        )
                    else:
                        log_startup_event(
                            message="Dual observability system initialization failed",
                            component="telemetry",
                            success=False,
                            error_type="InitializationError"
                        )
                        logger.warning(
                            "Dual observability system failed to initialize - continuing with legacy logging",
                            fallback_mode=True
                        )
                        
                except Exception as e:
                    log_startup_event(
                        message=f"Error initializing dual observability: {str(e)}",
                        component="telemetry",
                        success=False,
                        error_type=type(e).__name__
                    )
                    logger.error(
                        "Failed to initialize dual observability system",
                        error=str(e),
                        error_type=type(e).__name__,
                        fallback_mode=True
                    )
                    self.dual_observability_initialized = False
            else:
                logger.warning(
                    "Dual observability system not available - using legacy logging",
                    reason="Import failed or dependencies missing"
                )
                self.dual_observability_initialized = False
            
            # Setup logging (now with dual observability if available)
            setup_logging(self.settings)
            
            # Initialize console
            self.console = create_console(
                theme="dark" if not debug else "light",
                width=None,
                settings=self.settings
            )
            
            # Log successful initialization
            log_startup_event(
                message="Application settings initialized successfully",
                component="application",
                success=True
            )
            
            if debug:
                config_validation = self.settings.validate_configuration()
                logger.info(
                    "Application initialized in debug mode",
                    config_validation=config_validation,
                    dual_observability_enabled=self.dual_observability_initialized,
                    telemetry_initialized=is_telemetry_initialized() if DUAL_OBSERVABILITY_AVAILABLE else False
                )
            
        except Exception as e:
            # Log initialization failure
            log_startup_event(
                message=f"Failed to initialize application: {str(e)}",
                component="application",
                success=False,
                error_type=type(e).__name__
            )
            click.echo(f"❌ Failed to initialize application: {str(e)}", err=True)
            if debug:
                import traceback
                traceback.print_exc()
            raise click.ClickException("Application initialization failed")


# Global context instance
ctx = GlobalContext()


@click.group(invoke_without_command=True)
@click.option(
    '--config-file', 
    envvar='CHATBOT_CONFIG_FILE', 
    type=click.Path(exists=True),
    help='Configuration file path'
)
@click.option(
    '--log-level', 
    envvar='CHATBOT_LOG_LEVEL',
    type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR'], case_sensitive=False),
    default='INFO',
    help='Log level'
)
@click.option('--debug', is_flag=True, help='Enable debug mode')
@click.option('--version', is_flag=True, help='Show version information')
@click.option('--cli', is_flag=True, help='Force CLI mode instead of Streamlit')
@click.pass_context
def cli(click_ctx, config_file: Optional[str], log_level: str, debug: bool, version: bool, cli: bool):
    """
    RAG-Enabled Chatbot
    
    A comprehensive chatbot with RAG capabilities powered by Azure OpenAI and ChromaDB.
    By default, launches Streamlit web interface. Use --cli to force CLI mode.
    """
    if version:
        click.echo("RAG-Enabled Chatbot v2.0.0")
        click.echo("Powered by Azure OpenAI, ChromaDB, and Streamlit")
        return
    
    # Initialize global context
    try:
        ctx.init_settings(config_file, debug)
        
        # Store in click context
        click_ctx.obj = {
            'settings': ctx.settings,
            'console': ctx.console,
            'debug': debug
        }
        
    except Exception as e:
        logger.error("Failed to initialize CLI", error=str(e))
        raise click.ClickException(f"Initialization failed: {str(e)}")
    
    # If no command is specified, launch Streamlit by default (unless --cli is specified)
    if click_ctx.invoked_subcommand is None:
        if cli:
            click_ctx.invoke(chat)
        else:
            click_ctx.invoke(streamlit)


@cli.command()
@click.option(
    '--system-prompt',
    help='Custom system prompt for the conversation'
)
@click.option(
    '--prompt-type',
    type=click.Choice([
        'default', 'professional', 'creative', 'technical', 
        'tutor', 'code_reviewer', 'summarizer'
    ]),
    default='default',
    help='Type of system prompt to use'
)
@click.option(
    '--max-turns',
    type=int,
    default=None,
    help='Maximum number of conversation turns'
)
@click.option(
    '--conversation-id',
    help='Existing conversation ID to continue'
)
@click.option(
    '--save-conversation',
    type=click.Path(),
    help='Save conversation to file after session'
)
@click.option(
    '--stream/--no-stream',
    default=False,
    help='Enable streaming responses'
)
@click.option(
    '--no-console',
    is_flag=True,
    help='Disable console logging'
)
@click.option(
    '--log-file',
    type=str,
    help='Enable file logging to specified path'
)
@click.option(
    '--log-level',
    type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR']),
    help='Set log level'
)
@click.pass_context
def chat(
    click_ctx,
    system_prompt: Optional[str],
    prompt_type: str,
    max_turns: Optional[int],
    conversation_id: Optional[str],
    save_conversation: Optional[str],
    stream: bool,
    no_console: bool,
    log_file: Optional[str],
    log_level: Optional[str]
):
    """Start an interactive chat session with the AI assistant."""
    # Initialize structured logger for chat session
    chat_logger = StructuredLogger(__name__)
    
    settings = click_ctx.obj['settings']
    
    # Override settings based on CLI options
    if no_console:
        settings.enable_console_logging = False
    if log_file:
        settings.enable_file_logging = True
        settings.log_file_path = log_file
    if log_level:
        settings.log_level = log_level
    
    # Reconfigure logging with new settings
    setup_logging(settings)
    
    # Recreate console with new settings
    console = create_console(
        theme="dark",
        width=None,
        settings=settings
    )
    click_ctx.obj['console'] = console
    debug = click_ctx.obj['debug']
    
    try:
        # Log chat session start
        import uuid
        session_id = str(uuid.uuid4())
        conv_id = conversation_id or str(uuid.uuid4())
        
        chat_logger.log_conversation_event(
            message="Starting interactive chat session",
            conversation_id=conv_id,
            user_id="cli_user",
            session_id=session_id
        )
        
        # Validate configuration including dual observability
        config_validation = settings.validate_configuration()
        if not config_validation['configuration_complete']:
            console.print_error("Configuration incomplete. Please check your settings.")
            
            missing_items = []
            if not config_validation['azure_openai_configured']:
                missing_items.append("Azure OpenAI configuration")
            if not config_validation['logging_configured']:
                missing_items.append("Logging configuration")
            if not config_validation.get('dual_observability_configured', True):
                missing_items.append("Dual observability configuration")
            
            # Show dual observability status
            if not ctx.dual_observability_initialized:
                console.print_status("⚠️  Dual observability not initialized (using legacy logging)", "warning")
            else:
                console.print_status("✅ Dual observability system active", "info")
            
            console.print_status(f"Missing: {', '.join(missing_items)}", "warning")
            
            if not console.confirm("Continue anyway?", default=False):
                raise click.ClickException("Configuration incomplete")
        
        # Create chatbot agent
        agent = ChatbotAgent(
            settings=settings,
            conversation_id=conversation_id,
            system_prompt=system_prompt,
            prompt_type=prompt_type
        )
        
        if debug:
            console.print_status("Debug mode enabled", "info")
            health = agent.health_check()
            console.print_status(f"System health: {health['status']}", "info")
        
        # Run interactive session
        try:
            agent.run_interactive_session(
                max_turns=max_turns or settings.max_conversation_turns,
                welcome_message=True
            )
            
        except KeyboardInterrupt:
            console.print_status("Chat session interrupted by user", "warning")
        
        # Save conversation if requested
        if save_conversation:
            try:
                agent.save_conversation(save_conversation)
                console.print_status(f"Conversation saved to {save_conversation}", "success")
            except Exception as e:
                console.print_error(f"Failed to save conversation: {str(e)}")
        
    except Exception as e:
        error = handle_error(e)
        console.print_error(error)
        
        if debug:
            import traceback
            traceback.print_exc()
        
        raise click.ClickException(f"Chat session failed: {str(e)}")


@cli.command()
@click.argument('message', required=True)
@click.option(
    '--system-prompt',
    help='Custom system prompt'
)
@click.option(
    '--prompt-type',
    type=click.Choice([
        'default', 'professional', 'creative', 'technical',
        'tutor', 'code_reviewer', 'summarizer'
    ]),
    default='default',
    help='Type of system prompt to use'
)
@click.option(
    '--output-format',
    type=click.Choice(['text', 'json', 'markdown']),
    default='text',
    help='Output format'
)
@click.option(
    '--save-to',
    type=click.Path(),
    help='Save response to file'
)
@click.pass_context
def ask(
    click_ctx,
    message: str,
    system_prompt: Optional[str],
    prompt_type: str,
    output_format: str,
    save_to: Optional[str]
):
    """Ask a single question and get a response (non-interactive mode)."""
    settings = click_ctx.obj['settings']
    console = click_ctx.obj['console']
    debug = click_ctx.obj['debug']
    
    try:
        # Create chatbot agent
        agent = ChatbotAgent(
            settings=settings,
            system_prompt=system_prompt,
            prompt_type=prompt_type
        )
        
        # Process message
        with console.show_status("Processing your question..."):
            response = agent.process_message(message)
        
        if response.get('is_error'):
            console.print_error(response.get('error', 'Unknown error'))
            return
        
        # Output response based on format
        if output_format == 'json':
            import json
            click.echo(json.dumps(response, indent=2, ensure_ascii=False))
        
        elif output_format == 'markdown':
            click.echo(f"# Response\n\n{response['content']}")
            if debug:
                metadata = response.get('metadata', {})
                click.echo(f"\n---\n**Tokens:** {metadata.get('token_usage', {}).get('total_tokens', 'N/A')}")
                click.echo(f"**Response Time:** {metadata.get('total_response_time', 'N/A'):.2f}s")
        
        else:  # text format
            click.echo(response['content'])
            
            if debug:
                metadata = response.get('metadata', {})
                click.echo(f"\n[Debug] Tokens: {metadata.get('token_usage', {}).get('total_tokens', 'N/A')}, "
                          f"Time: {metadata.get('total_response_time', 'N/A'):.2f}s", err=True)
        
        # Save to file if requested
        if save_to:
            try:
                with open(save_to, 'w', encoding='utf-8') as f:
                    if output_format == 'json':
                        import json
                        json.dump(response, f, indent=2, ensure_ascii=False)
                    else:
                        f.write(response['content'])
                
                console.print_status(f"Response saved to {save_to}", "success")
                
            except Exception as e:
                console.print_error(f"Failed to save response: {str(e)}")
    
    except Exception as e:
        error = handle_error(e)
        console.print_error(error)
        
        if debug:
            import traceback
            traceback.print_exc()
        
        raise click.ClickException(f"Failed to process question: {str(e)}")


@cli.command()
@click.option(
    '--output-format',
    type=click.Choice(['text', 'json', 'table']),
    default='table',
    help='Output format for health information'
)
@click.pass_context
def health(click_ctx, output_format: str):
    """Check system health and connectivity."""
    settings = click_ctx.obj['settings']
    console = click_ctx.obj['console']
    
    try:
        # Basic configuration check
        config_validation = settings.validate_configuration()
        
        # Test Azure OpenAI connectivity
        health_results = {
            'configuration': config_validation,
            'azure_openai': None,
            'dual_observability': {
                'available': DUAL_OBSERVABILITY_AVAILABLE,
                'initialized': ctx.dual_observability_initialized,
                'telemetry_active': is_telemetry_initialized() if DUAL_OBSERVABILITY_AVAILABLE else False
            },
            'overall_status': 'unknown'
        }
        
        if config_validation['azure_openai_configured']:
            try:
                client = AzureOpenAIClient(settings)
                azure_health = client.health_check()
                health_results['azure_openai'] = azure_health
            except Exception as e:
                health_results['azure_openai'] = {
                    'status': 'unhealthy',
                    'error': str(e)
                }
        
        # Determine overall status
        overall_healthy = (
            config_validation['configuration_complete'] and
            (health_results['azure_openai'] is None or 
             health_results['azure_openai']['status'] == 'healthy')
            # Note: Dual observability is optional - don't fail health check if not available
        )
        
        health_results['overall_status'] = 'healthy' if overall_healthy else 'unhealthy'
        
        # Output results
        if output_format == 'json':
            import json
            click.echo(json.dumps(health_results, indent=2, default=str))
        
        elif output_format == 'table':
            # Configuration status
            config_table = [
                {'Component': 'Azure OpenAI Config', 'Status': '✅' if config_validation['azure_openai_configured'] else '❌'},
                {'Component': 'Logging Config', 'Status': '✅' if config_validation['logging_configured'] else '❌'},
                {'Component': 'Key Vault Config', 'Status': '✅' if config_validation['key_vault_configured'] else '❌'},
                {'Component': 'Dual Observability', 'Status': '✅' if health_results['dual_observability']['initialized'] else '⚠️' if health_results['dual_observability']['available'] else '❌'},
            ]
            
            console.print_table(config_table, title="Configuration Status")
            
            # Service health
            service_table = []
            
            if health_results['azure_openai']:
                azure_status = health_results['azure_openai']
                service_table.extend([
                    {'Service': 'Azure OpenAI', 'Status': azure_status['status'].title()},
                    {'Service': 'Response Time', 'Status': f"{azure_status.get('response_time', 'N/A')}s"},
                    {'Service': 'Endpoint', 'Status': azure_status.get('endpoint', 'N/A')[:50]},
                ])
            
            # Add dual observability status
            dual_obs = health_results['dual_observability']
            service_table.extend([
                {'Service': 'Dual Observability', 'Status': 'Active' if dual_obs['initialized'] else 'Legacy Mode'},
                {'Service': 'Telemetry Status', 'Status': 'Active' if dual_obs['telemetry_active'] else 'Inactive'},
            ])
            
            if service_table:
                console.print_table(service_table, title="Service Health")
            
            # Overall status
            overall_emoji = '✅' if overall_healthy else '❌'
            console.print_status(
                f"Overall System Status: {overall_emoji} {health_results['overall_status'].title()}",
                'success' if overall_healthy else 'error'
            )
        
        else:  # text format
            click.echo(f"Overall Status: {health_results['overall_status'].upper()}")
            click.echo(f"Configuration Complete: {'Yes' if config_validation['configuration_complete'] else 'No'}")
            
            # Dual observability status
            dual_obs = health_results['dual_observability']
            dual_status = 'ACTIVE' if dual_obs['initialized'] else 'LEGACY' if dual_obs['available'] else 'UNAVAILABLE'
            click.echo(f"Dual Observability: {dual_status}")
            
            if health_results['azure_openai']:
                azure_status = health_results['azure_openai']
                click.echo(f"Azure OpenAI: {azure_status['status'].upper()}")
                if azure_status['status'] == 'healthy':
                    click.echo(f"Response Time: {azure_status.get('response_time', 'N/A')}s")
    
    except Exception as e:
        console.print_error(f"Health check failed: {str(e)}")
        raise click.ClickException("Health check failed")


@cli.command()
@click.pass_context
def config(click_ctx):
    """Show current configuration (excluding sensitive data)."""
    settings = click_ctx.obj['settings']
    console = click_ctx.obj['console']
    
    try:
        # Prepare configuration info (without sensitive data)
        config_info = [
            {'Setting': 'Environment', 'Value': settings.environment},
            {'Setting': 'Log Level', 'Value': settings.log_level},
            {'Setting': 'Temperature', 'Value': str(settings.temperature)},
            {'Setting': 'Max Tokens', 'Value': str(settings.max_tokens)},
            {'Setting': 'Max Conversation Turns', 'Value': str(settings.max_conversation_turns)},
            {'Setting': 'Conversation Memory Type', 'Value': settings.conversation_memory_type},
            {'Setting': 'Azure OpenAI Endpoint', 'Value': settings.azure_openai_endpoint or 'Not configured'},
            {'Setting': 'Azure OpenAI API Version', 'Value': settings.azure_openai_api_version},
            {'Setting': 'Key Vault URL', 'Value': settings.key_vault_url or 'Not configured'},
            {'Setting': 'Log File Path', 'Value': settings.log_file_path},
            {'Setting': 'Dual Observability', 'Value': 'Active' if ctx.dual_observability_initialized else 'Legacy Mode'},
            {'Setting': 'Chat Observability', 'Value': 'Enabled' if settings.enable_chat_observability else 'Disabled'},
        ]
        
        console.print_table(config_info, title="Current Configuration")
        
        # Show validation status
        validation = settings.validate_configuration()
        console.print_separator("Configuration Status")
        
        for key, status in validation.items():
            if key != 'configuration_complete':
                emoji = '✅' if status else '❌'
                console.print_status(f"{key.replace('_', ' ').title()}: {emoji}", 
                                   'success' if status else 'error')
    
    except Exception as e:
        console.print_error(f"Failed to show configuration: {str(e)}")


@cli.command()
@click.pass_context
def prompts(click_ctx):
    """List available system prompt types."""
    console = click_ctx.obj['console']
    
    try:
        prompt_types = SystemPrompts.get_available_prompt_types()
        
        prompt_info = []
        for prompt_type in prompt_types:
            description = SystemPrompts.get_prompt_description(prompt_type)
            prompt_info.append({
                'Type': prompt_type,
                'Description': description
            })
        
        console.print_table(prompt_info, title="Available System Prompts")
        
        console.print_status(
            "Use --prompt-type option with 'chat' or 'ask' commands to select a prompt type",
            "info"
        )
    
    except Exception as e:
        console.print_error(f"Failed to list prompts: {str(e)}")


@cli.command()
@click.option(
    '--reload',
    is_flag=True,
    help='Reload configuration from files and Key Vault'
)
@click.pass_context
def reload(click_ctx, reload: bool):
    """Reload application configuration."""
    console = click_ctx.obj['console']
    
    try:
        if reload:
            with console.show_status("Reloading configuration..."):
                new_settings = reload_settings()
            
            # Update global context
            ctx.settings = new_settings
            click_ctx.obj['settings'] = new_settings
            
            console.print_status("Configuration reloaded successfully", "success")
            
            # Show validation status
            validation = new_settings.validate_configuration()
            if validation['configuration_complete']:
                console.print_status("✅ Configuration is complete", "success")
            else:
                console.print_status("⚠️  Configuration has issues", "warning")
        
        else:
            console.print_status("Use --reload flag to actually reload configuration", "info")
    
    except Exception as e:
        console.print_error(f"Failed to reload configuration: {str(e)}")


@cli.command()
@click.argument(
    'conversation_file',
    type=click.Path(exists=True),
    required=True
)
@click.option(
    '--output-format',
    type=click.Choice(['text', 'json', 'markdown']),
    default='text',
    help='Output format'
)
@click.pass_context
def show_conversation(click_ctx, conversation_file: str, output_format: str):
    """Display a saved conversation."""
    console = click_ctx.obj['console']
    
    try:
        # Load conversation data
        import json
        with open(conversation_file, 'r', encoding='utf-8') as f:
            conversation_data = json.load(f)
        
        messages = conversation_data.get('messages', [])
        metadata = conversation_data.get('metadata', {})
        
        if output_format == 'json':
            click.echo(json.dumps(conversation_data, indent=2, ensure_ascii=False))
        
        elif output_format == 'markdown':
            click.echo(f"# Conversation: {metadata.get('title', 'Untitled')}")
            click.echo(f"**ID:** {metadata.get('conversation_id', 'Unknown')}")
            click.echo(f"**Messages:** {len(messages)}")
            click.echo(f"**Created:** {metadata.get('created_at', 'Unknown')}")
            click.echo()
            
            for msg in messages:
                role = msg.get('role', 'unknown').title()
                content = msg.get('content', '')
                timestamp = msg.get('timestamp', '')
                
                click.echo(f"## {role}")
                if timestamp:
                    click.echo(f"*{timestamp}*")
                click.echo()
                click.echo(content)
                click.echo()
        
        else:  # text format
            console.print_separator(f"Conversation: {metadata.get('title', 'Untitled')}")
            
            # Show metadata
            if metadata:
                console.print_status(f"ID: {metadata.get('conversation_id', 'Unknown')}", "info")
                console.print_status(f"Messages: {len(messages)}", "info")
                console.print_status(f"Total Tokens: {metadata.get('total_tokens', 'Unknown')}", "info")
            
            # Show messages
            for msg in messages:
                if msg.get('role') != 'system':  # Skip system messages for display
                    console.print_conversation_message(
                        role=msg.get('role', 'unknown'),
                        content=msg.get('content', ''),
                        timestamp=None,  # Could parse timestamp here
                        token_count=msg.get('token_count')
                    )
    
    except Exception as e:
        console.print_error(f"Failed to show conversation: {str(e)}")


@cli.command()
@click.option(
    '--port',
    type=int,
    default=8501,
    help='Port to run Streamlit on (default: 8501)'
)
@click.option(
    '--host',
    type=str,
    default='localhost',
    help='Host to bind Streamlit to (default: localhost)'
)
@click.pass_context
def streamlit(click_ctx, port: int, host: str):
    """Launch the Streamlit web interface (default interface)."""
    console = click_ctx.obj['console']
    settings = click_ctx.obj['settings']
    debug = click_ctx.obj['debug']
    
    if not STREAMLIT_AVAILABLE:
        console.print_error("Streamlit interface is not available. Please install streamlit and related dependencies.")
        raise click.ClickException("Streamlit not available")
    
    try:
        console.print_status("🚀 Starting RAG-Enabled Chatbot Web Interface", "info")
        console.print_status("⚡ Upload documents and start chatting!", "info")
        console.print_status("🛑 Press Ctrl+C to stop the server", "info")
        
        if debug:
            console.print_status("Debug mode enabled", "info")
        
        # Update settings with Streamlit configuration
        if hasattr(settings, 'streamlit_port'):
            settings.streamlit_port = port
        
        log_startup_event(
            message="Starting Streamlit web interface",
            component="streamlit",
            success=True
        )
        
        # Launch Streamlit app
        try:
            # Try to launch Streamlit programmatically first
            import subprocess
            import sys
            import socket
            
            # Find an available port starting from the requested port
            def find_available_port(start_port, max_attempts=10):
                for attempt in range(max_attempts):
                    test_port = start_port + attempt
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        try:
                            s.bind((host, test_port))
                            return test_port
                        except OSError:
                            continue
                return None
            
            # Find available port
            available_port = find_available_port(port)
            if available_port is None:
                raise Exception(f"No available ports found starting from {port}")
            
            if available_port != port:
                console.print_status(f"Port {port} is busy, using port {available_port}", "warning")
                port = available_port
            
            # Get the path to the streamlit app
            streamlit_app_path = str(Path(__file__).parent / "ui" / "streamlit_app.py")
            
            # Launch streamlit run command
            cmd = [
                sys.executable, "-m", "streamlit", "run", 
                streamlit_app_path,
                "--server.port", str(port),
                "--server.headless", "true",
                "--server.address", host
            ]
            
            if debug:
                console.print_status(f"Running command: {' '.join(cmd)}", "info")
            
            # Update the console message with the actual port
            console.print_status(f"📱 Access the app at: http://{host}:{port}", "info")
            
            # Run Streamlit
            subprocess.run(cmd, check=True)
            
        except subprocess.CalledProcessError as e:
            console.print_error(f"Failed to start Streamlit: {str(e)}")
            console.print_status("Trying alternative launch method...", "info")
            
            # Fallback: try to run Streamlit app directly
            os.environ['STREAMLIT_SERVER_PORT'] = str(port)
            os.environ['STREAMLIT_SERVER_ADDRESS'] = host
            streamlit_main()
            
    except KeyboardInterrupt:
        console.print_status("👋 Streamlit server stopped by user", "info")
        
    except Exception as e:
        error = handle_error(e)
        console.print_error(f"Failed to start Streamlit interface: {error}")
        
        if debug:
            import traceback
            traceback.print_exc()
        
        # Fallback to CLI chat
        console.print_status("Falling back to CLI interface...", "warning")
        click_ctx.invoke(chat)


if __name__ == '__main__':
    try:
        # Ensure we're in the correct directory
        os.chdir(Path(__file__).parent.parent)
        
        # Run CLI
        cli()
        
    except KeyboardInterrupt:
        # Graceful shutdown on Ctrl+C
        click.echo("\n👋 Goodbye!", err=True)
        
    except Exception as e:
        click.echo(f"Fatal error: {str(e)}", err=True)
        sys.exit(1)
        
    finally:
        # Graceful shutdown of telemetry services
        if DUAL_OBSERVABILITY_AVAILABLE and ctx.dual_observability_initialized:
            try:
                shutdown_telemetry()
            except Exception as e:
                # Don't fail on shutdown errors
                pass