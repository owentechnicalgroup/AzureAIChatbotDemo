"""
Tool Card Component for Streamlit Tools Dashboard.

Displays individual tool information, status, and usage statistics.
"""

import streamlit as st
import asyncio
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from tools.base import BaseTool


class ToolCard:
    """
    Streamlit component for displaying tool information and status.
    
    Provides a card-based interface showing tool details, configuration status,
    usage statistics, and interactive testing capabilities.
    """
    
    def __init__(self, tool: BaseTool, tool_stats: Optional[Dict[str, Any]] = None):
        """
        Initialize tool card component.
        
        Args:
            tool: BaseTool instance to display
            tool_stats: Usage statistics for the tool
        """
        self.tool = tool
        self.tool_stats = tool_stats or {}
    
    def render(self):
        """Render the tool card in Streamlit."""
        with st.container():
            # Tool header with status
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.subheader(f"{self._get_tool_icon()} {self.tool.name}")
                st.caption(self.tool.description)
            
            with col2:
                status_icon, status_text = self._get_tool_status()
                st.markdown(f"**Status:** {status_icon} {status_text}")
            
            # Tool details in expandable section
            with st.expander("📋 Tool Details", expanded=False):
                self._render_tool_details()
            
            # Usage statistics
            if self.tool_stats:
                self._render_usage_stats()
            
            # Action buttons
            self._render_action_buttons()
            
            st.divider()
    
    def _get_tool_icon(self) -> str:
        """Get emoji icon for the tool based on its name/type."""
        tool_name = self.tool.name.lower()
        
        if 'restaurant' in tool_name or 'rating' in tool_name:
            return "🍕"
        elif 'weather' in tool_name:
            return "🌤️"
        elif 'movie' in tool_name or 'film' in tool_name:
            return "🎬"
        elif 'stock' in tool_name or 'finance' in tool_name:
            return "📈"
        elif 'news' in tool_name:
            return "📰"
        elif 'calculator' in tool_name or 'math' in tool_name:
            return "🧮"
        elif 'translate' in tool_name:
            return "🌐"
        elif 'email' in tool_name:
            return "📧"
        else:
            return "🔧"
    
    def _get_tool_status(self) -> tuple[str, str]:
        """Get tool status icon and text."""
        if not self.tool.is_available():
            return "🔴", "Disabled"
        elif hasattr(self.tool, '_last_error') and self.tool._last_error:
            return "🟡", "Warning"
        else:
            return "🟢", "Available"
    
    def _render_tool_details(self):
        """Render detailed tool information."""
        # Tool schema information
        try:
            schema = self.tool.get_schema()
            function_info = schema.get('function', {})
            parameters = function_info.get('parameters', {}).get('properties', {})
            required = function_info.get('parameters', {}).get('required', [])
            
            # Parameters section
            if parameters:
                st.write("**Parameters:**")
                for param_name, param_info in parameters.items():
                    is_required = param_name in required
                    param_type = param_info.get('type', 'unknown')
                    param_desc = param_info.get('description', 'No description')
                    default_val = param_info.get('default')
                    
                    status_badge = "🔸 Required" if is_required else "🔹 Optional"
                    
                    st.write(f"- **{param_name}** ({param_type}) {status_badge}")
                    st.write(f"  {param_desc}")
                    
                    if default_val is not None:
                        st.write(f"  *Default: {default_val}*")
                    
                    # Show enum values if available
                    if 'enum' in param_info:
                        enum_vals = ', '.join(param_info['enum'])
                        st.write(f"  *Options: {enum_vals}*")
            
            # Example usage
            st.write("**Example Usage:**")
            examples = self._get_usage_examples()
            for example in examples:
                st.write(f"- *{example}*")
                
        except Exception as e:
            st.error(f"Error loading tool details: {str(e)}")
    
    def _get_usage_examples(self) -> list[str]:
        """Get example usage queries for the tool."""
        tool_name = self.tool.name.lower()
        
        if 'restaurant' in tool_name:
            return [
                "What are the ratings for Italian restaurants near me?",
                "Find pizza places in downtown Seattle",
                "Show me highly rated sushi restaurants"
            ]
        elif 'weather' in tool_name:
            return [
                "What's the weather like in New York?",
                "Give me the 5-day forecast for Los Angeles",
                "Is it raining in Seattle right now?"
            ]
        elif 'movie' in tool_name:
            return [
                "What are the ratings for the latest Marvel movie?",
                "Tell me about Inception movie ratings",
                "Find highly rated movies from 2023"
            ]
        elif 'stock' in tool_name:
            return [
                "What's the current price of Apple stock?",
                "Show me Microsoft stock performance",
                "Get Tesla stock information"
            ]
        else:
            return [
                f"Use the {self.tool.name} tool to get information",
                f"Ask questions that require {self.tool.name} functionality"
            ]
    
    def _render_usage_stats(self):
        """Render usage statistics for the tool."""
        stats = self.tool_stats
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Calls", stats.get('calls', 0))
        
        with col2:
            success_rate = 0
            if stats.get('calls', 0) > 0:
                success_rate = (stats.get('successes', 0) / stats['calls']) * 100
            st.metric("Success Rate", f"{success_rate:.1f}%")
        
        with col3:
            avg_time = 0
            if stats.get('calls', 0) > 0:
                avg_time = stats.get('total_time', 0) / stats['calls']
            st.metric("Avg Response", f"{avg_time:.2f}s")
        
        with col4:
            last_used = stats.get('last_used')
            if last_used:
                if isinstance(last_used, str):
                    try:
                        last_used = datetime.fromisoformat(last_used.replace('Z', '+00:00'))
                    except:
                        pass
                
                if isinstance(last_used, datetime):
                    time_diff = datetime.now(timezone.utc) - last_used.replace(tzinfo=timezone.utc)
                    if time_diff.days > 0:
                        last_used_text = f"{time_diff.days}d ago"
                    elif time_diff.seconds > 3600:
                        last_used_text = f"{time_diff.seconds // 3600}h ago"
                    elif time_diff.seconds > 60:
                        last_used_text = f"{time_diff.seconds // 60}m ago"
                    else:
                        last_used_text = "Just now"
                else:
                    last_used_text = str(last_used)
            else:
                last_used_text = "Never"
            
            st.metric("Last Used", last_used_text)
    
    def _render_action_buttons(self):
        """Render action buttons for the tool."""
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button(f"🧪 Test {self.tool.name}", key=f"test_{self.tool.name}"):
                self._show_tool_tester()
        
        with col2:
            if st.button(f"📊 Stats", key=f"stats_{self.tool.name}"):
                self._show_detailed_stats()
        
        with col3:
            if not self.tool.is_available():
                if st.button(f"⚙️ Setup", key=f"setup_{self.tool.name}"):
                    self._show_setup_guide()
    
    def _show_tool_tester(self):
        """Show interactive tool testing interface."""
        st.session_state[f'show_tester_{self.tool.name}'] = True
        st.rerun()
    
    def _show_detailed_stats(self):
        """Show detailed statistics for the tool."""
        if not self.tool_stats:
            st.info("No usage statistics available yet.")
            return
        
        st.subheader(f"📊 {self.tool.name} Statistics")
        
        # Detailed metrics
        stats = self.tool_stats
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Usage Metrics:**")
            st.write(f"- Total Calls: {stats.get('calls', 0)}")
            st.write(f"- Successful Calls: {stats.get('successes', 0)}")
            st.write(f"- Failed Calls: {stats.get('calls', 0) - stats.get('successes', 0)}")
            st.write(f"- Success Rate: {(stats.get('successes', 0) / max(stats.get('calls', 1), 1) * 100):.2f}%")
        
        with col2:
            st.write("**Performance Metrics:**")
            st.write(f"- Total Response Time: {stats.get('total_time', 0):.2f}s")
            avg_time = stats.get('total_time', 0) / max(stats.get('calls', 1), 1)
            st.write(f"- Average Response Time: {avg_time:.2f}s")
            st.write(f"- Last Used: {stats.get('last_used', 'Never')}")
        
        # Error information if available
        if hasattr(self.tool, '_last_error') and self.tool._last_error:
            st.write("**Last Error:**")
            st.error(str(self.tool._last_error))
    
    def _show_setup_guide(self):
        """Show setup guide for disabled tools."""
        st.subheader(f"⚙️ Setup Guide: {self.tool.name}")
        
        tool_name = self.tool.name.lower()
        
        if 'restaurant' in tool_name:
            st.write("**Yelp API Setup:**")
            st.write("1. Visit https://www.yelp.com/developers")
            st.write("2. Create a developer account")
            st.write("3. Create a new app")
            st.write("4. Copy the API key")
            st.write("5. Set environment variable: `YELP_API_KEY=your_key_here`")
            
            st.code("export YELP_API_KEY=your_api_key_here", language="bash")
            
        elif 'weather' in tool_name:
            st.write("**OpenWeatherMap API Setup:**")
            st.write("1. Visit https://openweathermap.org/api")
            st.write("2. Sign up for a free account")
            st.write("3. Generate an API key")
            st.write("4. Set environment variable: `OPENWEATHER_API_KEY=your_key_here`")
            
            st.code("export OPENWEATHER_API_KEY=your_api_key_here", language="bash")
            
        else:
            st.info(f"Setup instructions for {self.tool.name} are not available yet.")
            st.write("Check the tool documentation or contact support for setup guidance.")
        
        st.write("**After setting the API key:**")
        st.write("1. Restart the Streamlit application")
        st.write("2. The tool should show as 'Available' in the dashboard")
        st.write("3. Test the tool using the 🧪 Test button")