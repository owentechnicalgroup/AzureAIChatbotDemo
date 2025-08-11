"""
Usage Analytics Component for Tools Dashboard.

Provides visualizations and insights about tool usage patterns,
performance metrics, and system health.
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, List

# Optional imports for visualization
try:
    import plotly.express as px
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False


class UsageAnalytics:
    """
    Analytics component for tool usage visualization and insights.
    
    Provides charts, metrics, and insights about tool performance,
    usage patterns, and system health.
    """
    
    def __init__(self, tool_stats: Dict[str, Dict[str, Any]]):
        """
        Initialize usage analytics.
        
        Args:
            tool_stats: Dictionary of tool statistics keyed by tool name
        """
        self.tool_stats = tool_stats
    
    def render(self):
        """Render the complete analytics dashboard."""
        if not self.tool_stats:
            st.info("No usage data available yet. Start using tools to see analytics!")
            return
        
        if not PLOTLY_AVAILABLE:
            st.warning("📊 Advanced charts require plotly. Install with: `pip install plotly`")
            st.info("Showing basic analytics without charts...")
            self._render_basic_analytics()
            return
        
        # Overview metrics
        self._render_overview_metrics()
        
        st.divider()
        
        # Usage charts
        col1, col2 = st.columns(2)
        
        with col1:
            self._render_usage_distribution()
        
        with col2:
            self._render_success_rates()
        
        st.divider()
        
        # Performance metrics
        col1, col2 = st.columns(2)
        
        with col1:
            self._render_response_times()
        
        with col2:
            self._render_tool_status_overview()
        
        # Detailed insights
        st.divider()
        self._render_insights()
    
    def _render_overview_metrics(self):
        """Render high-level overview metrics."""
        st.subheader("📊 System Overview")
        
        # Calculate aggregate metrics
        total_calls = sum(stats.get('calls', 0) for stats in self.tool_stats.values())
        total_successes = sum(stats.get('successes', 0) for stats in self.tool_stats.values())
        total_time = sum(stats.get('total_time', 0) for stats in self.tool_stats.values())
        active_tools = len([t for t in self.tool_stats.values() if t.get('calls', 0) > 0])
        
        # Display metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Tool Calls", total_calls)
        
        with col2:
            success_rate = (total_successes / max(total_calls, 1)) * 100
            st.metric("Overall Success Rate", f"{success_rate:.1f}%")
        
        with col3:
            avg_response_time = total_time / max(total_calls, 1)
            st.metric("Avg Response Time", f"{avg_response_time:.2f}s")
        
        with col4:
            st.metric("Active Tools", f"{active_tools}/{len(self.tool_stats)}")
    
    def _render_basic_analytics(self):
        """Render basic analytics without plotly charts."""
        # Overview metrics
        self._render_overview_metrics()
        
        st.divider()
        
        # Basic tool information
        st.subheader("🔧 Tool Usage Summary")
        
        for tool_name, stats in self.tool_stats.items():
            calls = stats.get('calls', 0)
            if calls > 0:
                successes = stats.get('successes', 0)
                success_rate = (successes / calls) * 100
                avg_time = stats.get('total_time', 0) / calls
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.write(f"**{tool_name}**")
                
                with col2:
                    st.metric("Calls", calls)
                
                with col3:
                    st.metric("Success Rate", f"{success_rate:.1f}%")
                
                with col4:
                    st.metric("Avg Time", f"{avg_time:.2f}s")
        
        st.divider()
        self._render_insights()
    
    def _render_usage_distribution(self):
        """Render tool usage distribution chart."""
        if not PLOTLY_AVAILABLE:
            return
            
        st.subheader("🔧 Tool Usage Distribution")
        
        # Prepare data
        tools = []
        calls = []
        
        for tool_name, stats in self.tool_stats.items():
            tool_calls = stats.get('calls', 0)
            if tool_calls > 0:  # Only show tools that have been used
                tools.append(tool_name)
                calls.append(tool_calls)
        
        if not tools:
            st.info("No tool usage data available yet.")
            return
        
        # Create bar chart
        df = pd.DataFrame({'Tool': tools, 'Calls': calls})
        df = df.sort_values('Calls', ascending=True)
        
        fig = px.bar(
            df, 
            x='Calls', 
            y='Tool',
            orientation='h',
            title="Tool Usage (Number of Calls)",
            color='Calls',
            color_continuous_scale='Blues'
        )
        
        fig.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    
    def _render_success_rates(self):
        """Render success rate comparison chart."""
        if not PLOTLY_AVAILABLE:
            return
            
        st.subheader("✅ Success Rates by Tool")
        
        # Prepare data
        tools = []
        success_rates = []
        
        for tool_name, stats in self.tool_stats.items():
            tool_calls = stats.get('calls', 0)
            if tool_calls > 0:
                successes = stats.get('successes', 0)
                success_rate = (successes / tool_calls) * 100
                tools.append(tool_name)
                success_rates.append(success_rate)
        
        if not tools:
            st.info("No success rate data available yet.")
            return
        
        # Create horizontal bar chart
        df = pd.DataFrame({'Tool': tools, 'Success Rate': success_rates})
        df = df.sort_values('Success Rate', ascending=True)
        
        # Color code based on success rate
        colors = ['red' if rate < 50 else 'orange' if rate < 80 else 'green' for rate in df['Success Rate']]
        
        fig = go.Figure(data=[
            go.Bar(
                x=df['Success Rate'],
                y=df['Tool'],
                orientation='h',
                marker_color=colors,
                text=[f"{rate:.1f}%" for rate in df['Success Rate']],
                textposition='inside'
            )
        ])
        
        fig.update_layout(
            title="Success Rates by Tool (%)",
            xaxis_title="Success Rate (%)",
            height=400,
            xaxis=dict(range=[0, 100])
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    def _render_response_times(self):
        """Render response time comparison chart."""
        if not PLOTLY_AVAILABLE:
            return
            
        st.subheader("⚡ Response Time Comparison")
        
        # Prepare data
        tools = []
        avg_times = []
        
        for tool_name, stats in self.tool_stats.items():
            tool_calls = stats.get('calls', 0)
            if tool_calls > 0:
                total_time = stats.get('total_time', 0)
                avg_time = total_time / tool_calls
                tools.append(tool_name)
                avg_times.append(avg_time)
        
        if not tools:
            st.info("No response time data available yet.")
            return
        
        # Create scatter plot
        df = pd.DataFrame({'Tool': tools, 'Avg Response Time': avg_times})
        df = df.sort_values('Avg Response Time', ascending=False)
        
        # Color code based on response time
        colors = ['red' if time > 5 else 'orange' if time > 2 else 'green' for time in df['Avg Response Time']]
        
        fig = go.Figure(data=[
            go.Bar(
                x=df['Tool'],
                y=df['Avg Response Time'],
                marker_color=colors,
                text=[f"{time:.2f}s" for time in df['Avg Response Time']],
                textposition='outside'
            )
        ])
        
        fig.update_layout(
            title="Average Response Time by Tool",
            xaxis_title="Tool",
            yaxis_title="Response Time (seconds)",
            height=400
        )
        
        # Add reference lines
        fig.add_hline(y=1.0, line_dash="dash", line_color="green", 
                     annotation_text="Fast (1s)", annotation_position="top right")
        fig.add_hline(y=3.0, line_dash="dash", line_color="orange", 
                     annotation_text="Acceptable (3s)", annotation_position="top right")
        
        st.plotly_chart(fig, use_container_width=True)
    
    def _render_tool_status_overview(self):
        """Render tool status overview."""
        if not PLOTLY_AVAILABLE:
            return
            
        st.subheader("🚦 Tool Status Overview")
        
        # Count tools by performance category
        fast_tools = 0
        slow_tools = 0
        failed_tools = 0
        unused_tools = 0
        
        for tool_name, stats in self.tool_stats.items():
            calls = stats.get('calls', 0)
            
            if calls == 0:
                unused_tools += 1
            else:
                successes = stats.get('successes', 0)
                success_rate = (successes / calls) * 100
                avg_time = stats.get('total_time', 0) / calls
                
                if success_rate < 50:
                    failed_tools += 1
                elif avg_time > 3.0:
                    slow_tools += 1
                else:
                    fast_tools += 1
        
        # Create donut chart
        labels = ['Fast & Reliable', 'Slow but Working', 'Failing', 'Unused']
        values = [fast_tools, slow_tools, failed_tools, unused_tools]
        colors = ['green', 'orange', 'red', 'gray']
        
        fig = go.Figure(data=[go.Pie(
            labels=labels, 
            values=values, 
            hole=0.4,
            marker_colors=colors
        )])
        
        fig.update_layout(
            title="Tool Health Distribution",
            height=400,
            showlegend=True
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Status legend
        st.write("**Status Categories:**")
        st.write("🟢 **Fast & Reliable:** >50% success rate, <3s response time")
        st.write("🟠 **Slow but Working:** >50% success rate, >3s response time")  
        st.write("🔴 **Failing:** <50% success rate")
        st.write("⚪ **Unused:** No calls made yet")
    
    def _render_insights(self):
        """Render intelligent insights and recommendations."""
        st.subheader("💡 Insights & Recommendations")
        
        insights = self._generate_insights()
        
        if not insights:
            st.info("Not enough data to generate insights yet.")
            return
        
        # Display insights in tabs
        if len(insights) > 3:
            # Multiple tabs for many insights
            insight_tabs = st.tabs(["Performance", "Usage", "Reliability", "Recommendations"])
            
            for i, (tab, insight_group) in enumerate(zip(insight_tabs, [
                [i for i in insights if 'fast' in i.lower() or 'slow' in i.lower()],
                [i for i in insights if 'usage' in i.lower() or 'popular' in i.lower()],
                [i for i in insights if 'fail' in i.lower() or 'error' in i.lower()],
                [i for i in insights if 'recommend' in i.lower() or 'suggest' in i.lower()]
            ])):
                with tab:
                    if insight_group:
                        for insight in insight_group:
                            st.write(f"• {insight}")
                    else:
                        st.info("No insights available in this category.")
        else:
            # Simple list for few insights
            for insight in insights:
                st.info(insight)
    
    def _generate_insights(self) -> List[str]:
        """Generate intelligent insights from usage data."""
        insights = []
        
        if not self.tool_stats:
            return insights
        
        # Calculate metrics for insights
        total_calls = sum(stats.get('calls', 0) for stats in self.tool_stats.values())
        
        if total_calls == 0:
            return ["Start using tools to see personalized insights and recommendations!"]
        
        # Usage insights
        most_used_tool = max(self.tool_stats.items(), key=lambda x: x[1].get('calls', 0))
        if most_used_tool[1].get('calls', 0) > 0:
            insights.append(f"Most popular tool: {most_used_tool[0]} ({most_used_tool[1]['calls']} calls)")
        
        # Performance insights
        for tool_name, stats in self.tool_stats.items():
            calls = stats.get('calls', 0)
            if calls > 0:
                avg_time = stats.get('total_time', 0) / calls
                success_rate = (stats.get('successes', 0) / calls) * 100
                
                if avg_time > 5.0:
                    insights.append(f"⚠️ {tool_name} is slow (avg {avg_time:.1f}s) - consider API optimization")
                elif avg_time < 1.0 and success_rate > 90:
                    insights.append(f"⚡ {tool_name} performs excellently (fast & reliable)")
                
                if success_rate < 50:
                    insights.append(f"🔴 {tool_name} has low success rate ({success_rate:.1f}%) - check configuration")
                elif success_rate > 95:
                    insights.append(f"✅ {tool_name} is highly reliable ({success_rate:.1f}% success rate)")
        
        # Usage pattern insights
        unused_tools = [name for name, stats in self.tool_stats.items() if stats.get('calls', 0) == 0]
        if unused_tools:
            insights.append(f"📭 Unused tools: {', '.join(unused_tools)} - consider promoting these features")
        
        # Recommendations
        if total_calls > 10:
            insights.append("📈 You're actively using the tools system! Consider adding more tools for additional capabilities")
        
        # System health
        total_successes = sum(stats.get('successes', 0) for stats in self.tool_stats.values())
        overall_success_rate = (total_successes / total_calls) * 100
        
        if overall_success_rate > 90:
            insights.append("🎉 Excellent system reliability! All tools are working well")
        elif overall_success_rate < 70:
            insights.append("⚠️ System reliability needs attention - check API keys and configurations")
        
        return insights