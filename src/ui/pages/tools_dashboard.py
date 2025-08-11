"""
Tools Dashboard Page for Streamlit Application.

Comprehensive dashboard showing available tools, their status, usage analytics,
and interactive testing capabilities.
"""

import streamlit as st
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime

from tools import ToolRegistry, RestaurantRatingsTool
from tools.base import BaseTool
from config.settings import Settings

# Import custom components
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from components.tool_card import ToolCard
from components.tool_tester import ToolTester
from components.usage_analytics import UsageAnalytics


class ToolsDashboard:
    """
    Comprehensive tools dashboard for the Streamlit application.
    
    Provides overview of available tools, their status, usage statistics,
    and interactive testing capabilities.
    """
    
    def __init__(self, settings: Settings):
        """
        Initialize tools dashboard.
        
        Args:
            settings: Application settings
        """
        self.settings = settings
        self._initialize_tools_registry()
        self._initialize_session_state()
    
    def _initialize_tools_registry(self):
        """Initialize tools registry with available tools."""
        if "tools_registry" not in st.session_state:
            registry = ToolRegistry()
            
            # Register available tools
            if self.settings.yelp_api_key:
                restaurant_tool = RestaurantRatingsTool(self.settings.yelp_api_key)
                registry.register_tool(restaurant_tool)
            
            # Future tools would be registered here
            # if self.settings.openweather_api_key:
            #     weather_tool = WeatherTool(self.settings.openweather_api_key)
            #     registry.register_tool(weather_tool)
            
            st.session_state.tools_registry = registry
    
    def _initialize_session_state(self):
        """Initialize session state for tools dashboard."""
        # Tool usage statistics
        if "tool_stats" not in st.session_state:
            st.session_state.tool_stats = {}
        
        # Tool tester states
        if "active_tool_tester" not in st.session_state:
            st.session_state.active_tool_tester = None
        
        # Dashboard view preferences
        if "tools_view_mode" not in st.session_state:
            st.session_state.tools_view_mode = "overview"  # overview, detailed, analytics
    
    def render(self):
        """Render the complete tools dashboard."""
        st.title("🔧 Tools Dashboard")
        st.caption("Manage and monitor external tools and integrations")
        
        # Dashboard navigation
        self._render_dashboard_navigation()
        
        # Render content based on selected view
        view_mode = st.session_state.tools_view_mode
        
        if view_mode == "overview":
            self._render_overview()
        elif view_mode == "detailed":
            self._render_detailed_view()
        elif view_mode == "analytics":
            self._render_analytics_view()
        elif view_mode == "tester":
            self._render_testing_interface()
    
    def _render_dashboard_navigation(self):
        """Render navigation tabs for different dashboard views."""
        tab1, tab2, tab3, tab4 = st.tabs(["📊 Overview", "🔧 Tools", "📈 Analytics", "🧪 Testing"])
        
        # Store active tab in session state
        if st.session_state.get('active_tools_tab') != st.session_state.get('last_active_tab'):
            st.session_state.last_active_tab = st.session_state.get('active_tools_tab')
        
        # Tab content rendering is handled by render() method based on tools_view_mode
        with tab1:
            if st.button("View Overview", key="nav_overview", help="System overview and status"):
                st.session_state.tools_view_mode = "overview"
                st.rerun()
        
        with tab2:
            if st.button("View Tools", key="nav_detailed", help="Detailed tool information"):
                st.session_state.tools_view_mode = "detailed"
                st.rerun()
        
        with tab3:
            if st.button("View Analytics", key="nav_analytics", help="Usage analytics and insights"):
                st.session_state.tools_view_mode = "analytics"
                st.rerun()
        
        with tab4:
            if st.button("View Testing", key="nav_testing", help="Interactive tool testing"):
                st.session_state.tools_view_mode = "tester"
                st.rerun()
    
    def _render_overview(self):
        """Render system overview with key metrics and status."""
        st.subheader("📊 System Overview")
        
        # Get tools registry
        registry = st.session_state.tools_registry
        tools = registry.list_tools(available_only=False)
        available_tools = registry.list_tools(available_only=True)
        
        # System metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Tools", len(tools))
        
        with col2:
            st.metric("Available Tools", len(available_tools))
        
        with col3:
            total_calls = sum(stats.get('calls', 0) for stats in st.session_state.tool_stats.values())
            st.metric("Total Calls", total_calls)
        
        with col4:
            tools_enabled = "Yes" if self.settings.enable_tools else "No"
            st.metric("Tools Enabled", tools_enabled)
        
        st.divider()
        
        # System status
        self._render_system_status()
        
        st.divider()
        
        # Quick tool status overview
        self._render_quick_tool_status(tools)
        
        st.divider()
        
        # Recent activity
        self._render_recent_activity()
    
    def _render_system_status(self):
        """Render overall system status information."""
        st.subheader("🚦 System Status")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Configuration Status:**")
            
            # Tools enabled status
            if self.settings.enable_tools:
                st.success("✅ Tools system enabled")
            else:
                st.error("❌ Tools system disabled")
            
            # API keys status
            api_keys_status = []
            if self.settings.yelp_api_key:
                api_keys_status.append("Yelp API")
            if self.settings.openweather_api_key:
                api_keys_status.append("OpenWeather API")
            if self.settings.tmdb_api_key:
                api_keys_status.append("TMDB API")
            if self.settings.google_places_api_key:
                api_keys_status.append("Google Places API")
            
            if api_keys_status:
                st.info(f"🔑 Configured APIs: {', '.join(api_keys_status)}")
            else:
                st.warning("⚠️ No API keys configured")
        
        with col2:
            st.write("**Performance Settings:**")
            st.write(f"• Tool timeout: {self.settings.tools_timeout_seconds}s")
            st.write(f"• Cache TTL: {self.settings.tools_cache_ttl_minutes}m")
            
            # Health check
            try:
                registry = st.session_state.tools_registry
                if registry and len(registry.list_tools(available_only=True)) > 0:
                    st.success("✅ Tools registry healthy")
                else:
                    st.warning("⚠️ No tools available")
            except Exception as e:
                st.error(f"❌ Tools registry error: {str(e)}")
    
    def _render_quick_tool_status(self, tools: List[BaseTool]):
        """Render quick status overview of all tools."""
        st.subheader("⚡ Quick Tool Status")
        
        if not tools:
            st.info("No tools registered yet.")
            return
        
        # Create status summary
        for tool in tools:
            col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
            
            with col1:
                icon = self._get_tool_icon(tool.name)
                st.write(f"{icon} **{tool.name}**")
            
            with col2:
                if tool.is_available():
                    st.success("Available")
                else:
                    st.error("Disabled")
            
            with col3:
                stats = st.session_state.tool_stats.get(tool.name, {})
                calls = stats.get('calls', 0)
                st.write(f"{calls} calls")
            
            with col4:
                if calls > 0:
                    success_rate = (stats.get('successes', 0) / calls) * 100
                    if success_rate > 80:
                        st.success(f"{success_rate:.0f}%")
                    elif success_rate > 50:
                        st.warning(f"{success_rate:.0f}%")
                    else:
                        st.error(f"{success_rate:.0f}%")
                else:
                    st.write("No data")
    
    def _render_recent_activity(self):
        """Render recent tool activity and usage."""
        st.subheader("📅 Recent Activity")
        
        # Get recent activity from tool stats
        recent_tools = []
        for tool_name, stats in st.session_state.tool_stats.items():
            last_used = stats.get('last_used')
            if last_used:
                recent_tools.append((tool_name, last_used, stats))
        
        if not recent_tools:
            st.info("No recent tool activity. Start using tools to see activity here!")
            return
        
        # Sort by last used (most recent first)
        recent_tools.sort(key=lambda x: x[1] if isinstance(x[1], datetime) else datetime.min, reverse=True)
        
        # Show last 5 activities
        for tool_name, last_used, stats in recent_tools[:5]:
            col1, col2, col3 = st.columns([2, 1, 1])
            
            with col1:
                icon = self._get_tool_icon(tool_name)
                st.write(f"{icon} {tool_name}")
            
            with col2:
                if isinstance(last_used, datetime):
                    time_ago = datetime.now() - last_used
                    if time_ago.days > 0:
                        st.write(f"{time_ago.days}d ago")
                    elif time_ago.seconds > 3600:
                        st.write(f"{time_ago.seconds // 3600}h ago")
                    else:
                        st.write(f"{time_ago.seconds // 60}m ago")
                else:
                    st.write("Recently")
            
            with col3:
                calls = stats.get('calls', 0)
                st.write(f"{calls} total calls")
    
    def _render_detailed_view(self):
        """Render detailed view of all tools with full information."""
        st.subheader("🔧 Detailed Tools Information")
        
        registry = st.session_state.tools_registry
        tools = registry.list_tools(available_only=False)
        
        if not tools:
            st.info("No tools registered. Check your configuration and API keys.")
            return
        
        # Group tools by category
        categories = self._categorize_tools(tools)
        
        for category, category_tools in categories.items():
            if category_tools:
                st.subheader(f"{category}")
                
                for tool in category_tools:
                    tool_stats = st.session_state.tool_stats.get(tool.name, {})
                    tool_card = ToolCard(tool, tool_stats)
                    tool_card.render()
                
                st.divider()
    
    def _render_analytics_view(self):
        """Render analytics and insights view."""
        st.subheader("📈 Usage Analytics & Insights")
        
        if not st.session_state.tool_stats:
            st.info("No usage data available yet. Start using tools to see analytics!")
            
            # Show example of what analytics would look like
            with st.expander("Preview: What you'll see with usage data"):
                st.write("**Available Analytics:**")
                st.write("• Tool usage distribution charts")
                st.write("• Success rate comparisons")
                st.write("• Response time analysis")
                st.write("• Performance insights and recommendations")
                st.write("• System health overview")
            
            return
        
        # Render analytics dashboard
        analytics = UsageAnalytics(st.session_state.tool_stats)
        analytics.render()
    
    def _render_testing_interface(self):
        """Render interactive tool testing interface."""
        st.subheader("🧪 Interactive Tool Testing")
        
        registry = st.session_state.tools_registry
        available_tools = registry.list_tools(available_only=True)
        
        if not available_tools:
            st.warning("No tools available for testing. Please configure API keys and check tool status.")
            return
        
        # Tool selection
        tool_names = [tool.name for tool in available_tools]
        selected_tool_name = st.selectbox(
            "Select tool to test:",
            options=tool_names,
            help="Choose a tool to test interactively"
        )
        
        if selected_tool_name:
            # Get selected tool
            selected_tool = registry.get_tool(selected_tool_name)
            
            if selected_tool:
                # Render tool tester
                tester = ToolTester(selected_tool)
                tester.render()
            else:
                st.error(f"Tool '{selected_tool_name}' not found in registry.")
    
    def _categorize_tools(self, tools: List[BaseTool]) -> Dict[str, List[BaseTool]]:
        """Categorize tools by their functionality."""
        categories = {
            "🍕 Business & Reviews": [],
            "🌤️ Real-Time Data": [],
            "🧮 Utilities": [],
            "📧 Communication": [],
            "🔧 Other": []
        }
        
        for tool in tools:
            tool_name = tool.name.lower()
            
            if any(keyword in tool_name for keyword in ['restaurant', 'rating', 'review', 'business']):
                categories["🍕 Business & Reviews"].append(tool)
            elif any(keyword in tool_name for keyword in ['weather', 'stock', 'news', 'market']):
                categories["🌤️ Real-Time Data"].append(tool)
            elif any(keyword in tool_name for keyword in ['calculator', 'convert', 'math', 'date', 'time']):
                categories["🧮 Utilities"].append(tool)
            elif any(keyword in tool_name for keyword in ['email', 'message', 'notification']):
                categories["📧 Communication"].append(tool)
            else:
                categories["🔧 Other"].append(tool)
        
        # Remove empty categories
        return {k: v for k, v in categories.items() if v}
    
    def _get_tool_icon(self, tool_name: str) -> str:
        """Get emoji icon for tool based on its name."""
        tool_name = tool_name.lower()
        
        if 'restaurant' in tool_name or 'rating' in tool_name:
            return "🍕"
        elif 'weather' in tool_name:
            return "🌤️"
        elif 'movie' in tool_name:
            return "🎬"
        elif 'stock' in tool_name:
            return "📈"
        elif 'news' in tool_name:
            return "📰"
        elif 'calculator' in tool_name:
            return "🧮"
        elif 'email' in tool_name:
            return "📧"
        else:
            return "🔧"
    
    def update_tool_stats(self, tool_name: str, success: bool, response_time: float):
        """
        Update tool usage statistics.
        
        Args:
            tool_name: Name of the tool that was executed
            success: Whether the execution was successful
            response_time: Time taken for execution in seconds
        """
        if tool_name not in st.session_state.tool_stats:
            st.session_state.tool_stats[tool_name] = {
                "calls": 0,
                "successes": 0,
                "total_time": 0.0,
                "last_used": None
            }
        
        stats = st.session_state.tool_stats[tool_name]
        stats["calls"] += 1
        
        if success:
            stats["successes"] += 1
        
        stats["total_time"] += response_time
        stats["last_used"] = datetime.now()
        
        # Trigger rerun to update display
        st.rerun()