"""
Interactive Tool Tester Component for Streamlit.

Provides a form-based interface for testing tools with parameter inputs
and response visualization.
"""

import streamlit as st
import asyncio
import json
from typing import Dict, Any, Optional
from datetime import datetime

from tools.base import BaseTool, ToolExecutionResult


class ToolTester:
    """
    Interactive tool testing interface for Streamlit.
    
    Generates parameter input forms based on tool schemas and provides
    real-time tool execution with response visualization.
    """
    
    def __init__(self, tool: BaseTool):
        """
        Initialize tool tester.
        
        Args:
            tool: BaseTool instance to test
        """
        self.tool = tool
    
    def render(self):
        """Render the tool testing interface."""
        st.subheader(f"🧪 Test Tool: {self.tool.name}")
        
        if not self.tool.is_available():
            st.error(f"Tool '{self.tool.name}' is not available. Please check configuration.")
            return
        
        # Get tool schema for parameter generation
        try:
            schema = self.tool.get_schema()
            function_info = schema.get('function', {})
            parameters = function_info.get('parameters', {}).get('properties', {})
            required = function_info.get('parameters', {}).get('required', [])
            
            if not parameters:
                st.info("This tool doesn't require any parameters.")
                if st.button("Execute Tool", key=f"execute_no_params_{self.tool.name}"):
                    self._execute_tool({})
                return
            
            # Create parameter input form
            with st.form(f"tool_test_form_{self.tool.name}"):
                st.write("**Tool Parameters:**")
                
                # Collect parameter values
                param_values = {}
                
                for param_name, param_info in parameters.items():
                    param_values[param_name] = self._render_parameter_input(
                        param_name, param_info, param_name in required
                    )
                
                # Submit button
                submitted = st.form_submit_button("🚀 Execute Tool")
                
                if submitted:
                    # Validate required parameters
                    missing_required = []
                    for req_param in required:
                        if not param_values.get(req_param):
                            missing_required.append(req_param)
                    
                    if missing_required:
                        st.error(f"Missing required parameters: {', '.join(missing_required)}")
                    else:
                        # Filter out empty optional parameters
                        filtered_params = {
                            k: v for k, v in param_values.items() 
                            if v is not None and v != ""
                        }
                        self._execute_tool(filtered_params)
                        
        except Exception as e:
            st.error(f"Error setting up tool tester: {str(e)}")
    
    def _render_parameter_input(
        self, 
        param_name: str, 
        param_info: Dict[str, Any], 
        is_required: bool
    ) -> Any:
        """
        Render input widget for a parameter based on its schema.
        
        Args:
            param_name: Name of the parameter
            param_info: Parameter schema information
            is_required: Whether the parameter is required
            
        Returns:
            Parameter value from user input
        """
        param_type = param_info.get('type', 'string')
        description = param_info.get('description', '')
        default_value = param_info.get('default')
        enum_values = param_info.get('enum')
        minimum = param_info.get('minimum')
        maximum = param_info.get('maximum')
        
        # Create label with required indicator
        label = f"{param_name}"
        if is_required:
            label += " *"
        
        help_text = description
        if default_value is not None:
            help_text += f" (Default: {default_value})"
        
        # Render appropriate input widget based on parameter type
        if enum_values:
            # Select box for enum values
            index = 0
            if default_value and default_value in enum_values:
                index = enum_values.index(default_value)
            
            return st.selectbox(
                label,
                options=enum_values,
                index=index,
                help=help_text,
                key=f"param_{self.tool.name}_{param_name}"
            )
            
        elif param_type == 'boolean':
            # Checkbox for boolean
            default_bool = bool(default_value) if default_value is not None else False
            return st.checkbox(
                label,
                value=default_bool,
                help=help_text,
                key=f"param_{self.tool.name}_{param_name}"
            )
            
        elif param_type == 'integer':
            # Number input for integers
            default_int = int(default_value) if default_value is not None else (minimum or 0)
            return st.number_input(
                label,
                value=default_int,
                min_value=minimum,
                max_value=maximum,
                step=1,
                help=help_text,
                key=f"param_{self.tool.name}_{param_name}"
            )
            
        elif param_type == 'number':
            # Number input for floats
            default_float = float(default_value) if default_value is not None else (minimum or 0.0)
            return st.number_input(
                label,
                value=default_float,
                min_value=minimum,
                max_value=maximum,
                step=0.1,
                help=help_text,
                key=f"param_{self.tool.name}_{param_name}"
            )
            
        else:
            # Text input for strings and other types
            default_str = str(default_value) if default_value is not None else ""
            
            # Use text area for longer descriptions or certain parameter names
            if ('description' in param_name.lower() or 
                'message' in param_name.lower() or 
                len(description) > 100):
                return st.text_area(
                    label,
                    value=default_str,
                    help=help_text,
                    key=f"param_{self.tool.name}_{param_name}"
                )
            else:
                return st.text_input(
                    label,
                    value=default_str,
                    help=help_text,
                    key=f"param_{self.tool.name}_{param_name}"
                )
    
    def _execute_tool(self, parameters: Dict[str, Any]):
        """
        Execute the tool with given parameters and display results.
        
        Args:
            parameters: Dictionary of parameter values
        """
        st.subheader("🔄 Executing Tool...")
        
        # Show parameters being used
        with st.expander("📋 Parameters Used", expanded=False):
            if parameters:
                st.json(parameters)
            else:
                st.write("No parameters")
        
        # Execute tool
        try:
            with st.spinner(f"Executing {self.tool.name}..."):
                # Create event loop for async execution
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                # Execute tool with timeout
                result = loop.run_until_complete(
                    self.tool.execute_with_timeout(**parameters)
                )
            
            # Display results
            self._display_results(result, parameters)
            
        except Exception as e:
            st.error(f"Error executing tool: {str(e)}")
            st.exception(e)
    
    def _display_results(self, result: ToolExecutionResult, parameters: Dict[str, Any]):
        """
        Display tool execution results.
        
        Args:
            result: Tool execution result
            parameters: Parameters used for execution
        """
        # Status indicator
        if result.success:
            st.success(f"✅ Tool executed successfully in {result.execution_time:.2f} seconds")
        else:
            st.error(f"❌ Tool execution failed: {result.error}")
        
        # Result tabs
        tab1, tab2, tab3, tab4 = st.tabs(["📊 Results", "🔧 Raw Data", "📈 Metrics", "🐛 Debug"])
        
        with tab1:
            self._display_formatted_results(result)
        
        with tab2:
            st.subheader("Raw Tool Output")
            if result.data:
                st.json(result.data)
            else:
                st.write("No data returned")
        
        with tab3:
            self._display_execution_metrics(result)
        
        with tab4:
            self._display_debug_info(result, parameters)
    
    def _display_formatted_results(self, result: ToolExecutionResult):
        """Display results in a user-friendly format."""
        if not result.success:
            st.error(f"Execution failed: {result.error}")
            return
        
        if not result.data:
            st.info("Tool executed successfully but returned no data.")
            return
        
        # Format results based on tool type
        tool_name = self.tool.name.lower()
        
        if 'restaurant' in tool_name and 'restaurants' in result.data:
            self._display_restaurant_results(result.data)
        elif 'weather' in tool_name:
            self._display_weather_results(result.data)
        else:
            # Generic result display
            st.subheader("Tool Results")
            
            # Try to display key-value pairs nicely
            for key, value in result.data.items():
                if isinstance(value, (dict, list)):
                    st.write(f"**{key}:**")
                    st.json(value)
                else:
                    st.write(f"**{key}:** {value}")
    
    def _display_restaurant_results(self, data: Dict[str, Any]):
        """Display restaurant search results in a formatted way."""
        restaurants = data.get('restaurants', [])
        summary = data.get('summary', '')
        
        if summary:
            st.info(summary)
        
        if not restaurants:
            st.warning("No restaurants found.")
            return
        
        st.subheader(f"🍕 Found {len(restaurants)} Restaurants")
        
        for i, restaurant in enumerate(restaurants, 1):
            with st.container():
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.write(f"**{i}. {restaurant.get('name', 'Unknown')}**")
                    if restaurant.get('address'):
                        st.write(f"📍 {restaurant['address']}")
                    if restaurant.get('categories'):
                        categories = ', '.join(restaurant['categories'])
                        st.write(f"🏷️ {categories}")
                
                with col2:
                    rating = restaurant.get('rating', 0)
                    review_count = restaurant.get('review_count', 0)
                    price = restaurant.get('price', '')
                    
                    st.metric("Rating", f"{rating}/5 ⭐")
                    st.write(f"{review_count} reviews")
                    if price:
                        st.write(f"Price: {price}")
                
                # Additional details in expander
                if restaurant.get('phone') or restaurant.get('hours'):
                    with st.expander(f"More details for {restaurant.get('name', 'restaurant')}"):
                        if restaurant.get('phone'):
                            st.write(f"📞 {restaurant['phone']}")
                        
                        if restaurant.get('hours') and restaurant['hours'].get('hours'):
                            st.write("**Hours:**")
                            for hour_info in restaurant['hours']['hours']:
                                day = hour_info.get('day', 'Unknown')
                                start = hour_info.get('start', '')
                                end = hour_info.get('end', '')
                                st.write(f"- {day}: {start} - {end}")
                
                st.divider()
    
    def _display_weather_results(self, data: Dict[str, Any]):
        """Display weather results in a formatted way."""
        st.subheader(f"🌤️ Weather for {data.get('location', 'Unknown Location')}")
        
        current = data.get('current_weather', {})
        if current:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                temp = current.get('temperature', 'N/A')
                st.metric("Temperature", f"{temp}°")
            
            with col2:
                humidity = current.get('humidity', 'N/A')
                st.metric("Humidity", f"{humidity}%")
            
            with col3:
                wind = current.get('wind_speed', 'N/A')
                st.metric("Wind Speed", f"{wind} m/s")
            
            # Weather description
            description = current.get('description', '').title()
            if description:
                st.info(f"Conditions: {description}")
        
        # Forecast if available
        forecast = data.get('forecast', [])
        if forecast:
            st.subheader("📅 5-Day Forecast")
            for day in forecast[:5]:
                with st.container():
                    col1, col2, col3 = st.columns([2, 1, 1])
                    
                    with col1:
                        date = day.get('date', 'Unknown')
                        desc = day.get('description', '').title()
                        st.write(f"**{date}**")
                        st.write(desc)
                    
                    with col2:
                        high = day.get('high_temp', 'N/A')
                        st.write(f"High: {high}°")
                    
                    with col3:
                        low = day.get('low_temp', 'N/A')
                        st.write(f"Low: {low}°")
    
    def _display_execution_metrics(self, result: ToolExecutionResult):
        """Display execution performance metrics."""
        st.subheader("📈 Execution Metrics")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Execution Time", f"{result.execution_time:.3f}s")
        
        with col2:
            status_color = "🟢" if result.success else "🔴"
            st.metric("Status", f"{status_color} {result.status.value}")
        
        with col3:
            timestamp = result.timestamp.strftime("%H:%M:%S")
            st.metric("Executed At", timestamp)
        
        # Performance assessment
        if result.execution_time < 1.0:
            st.success("⚡ Fast response time")
        elif result.execution_time < 3.0:
            st.info("⏱️ Normal response time")
        else:
            st.warning("🐌 Slow response time")
    
    def _display_debug_info(self, result: ToolExecutionResult, parameters: Dict[str, Any]):
        """Display debug information for troubleshooting."""
        st.subheader("🐛 Debug Information")
        
        # Tool information
        st.write("**Tool Details:**")
        st.write(f"- Name: {self.tool.name}")
        st.write(f"- Available: {self.tool.is_available()}")
        st.write(f"- Timeout: {self.tool._timeout}s")
        
        # Execution details
        st.write("**Execution Details:**")
        st.write(f"- Parameters: {len(parameters)} provided")
        st.write(f"- Result status: {result.status.value}")
        st.write(f"- Execution time: {result.execution_time:.3f}s")
        st.write(f"- Timestamp: {result.timestamp}")
        
        # Error information
        if result.error:
            st.write("**Error Information:**")
            st.error(result.error)
        
        # Full result object
        with st.expander("Full Result Object"):
            st.json(result.to_dict())
        
        # Parameters used
        with st.expander("Parameters Used"):
            if parameters:
                st.json(parameters)
            else:
                st.write("No parameters")