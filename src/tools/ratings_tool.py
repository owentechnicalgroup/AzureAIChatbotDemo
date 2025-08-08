"""
Restaurant ratings tool using Yelp API.

Provides functionality to search for restaurants and retrieve ratings,
reviews, and business information.
"""

import aiohttp
import asyncio
from typing import Dict, Any, List, Optional
from urllib.parse import urlencode
import os

from .base import BaseTool, ToolExecutionResult, ToolStatus


class RestaurantRatingsTool(BaseTool):
    """
    Tool for retrieving restaurant ratings and information from Yelp API.
    
    Provides search functionality for restaurants with ratings, reviews,
    location information, and business details.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the restaurant ratings tool.
        
        Args:
            api_key: Yelp API key (if None, will try to get from environment)
        """
        super().__init__(
            name="get_restaurant_ratings",
            description="Search for restaurants and get ratings, reviews, and business information"
        )
        
        self.api_key = api_key or os.getenv('YELP_API_KEY')
        self.base_url = "https://api.yelp.com/v3"
        
        if not self.api_key:
            self.logger.warning("No Yelp API key provided - tool will be disabled")
            self.disable()
    
    def is_available(self) -> bool:
        """Check if the tool is available (has API key and is enabled)."""
        return self._enabled and bool(self.api_key)
    
    async def execute(
        self,
        query: str,
        location: str = "current location",
        limit: int = 5,
        radius: int = 10000,  # meters
        categories: str = "restaurants",
        price: Optional[str] = None,
        sort_by: str = "best_match"
    ) -> ToolExecutionResult:
        """
        Search for restaurants and get ratings information.
        
        Args:
            query: Search term (restaurant name, cuisine type, etc.)
            location: Location to search in (address, city, or coordinates)
            limit: Number of results to return (1-50)
            radius: Search radius in meters (max 40,000)
            categories: Business categories to search in
            price: Price level (1, 2, 3, 4 for $, $$, $$$, $$$$)
            sort_by: Sort results by (best_match, rating, review_count, distance)
            
        Returns:
            ToolExecutionResult containing restaurant data
        """
        try:
            # Validate parameters
            limit = max(1, min(50, limit))  # Yelp API limits
            radius = max(1, min(40000, radius))
            
            # Build search parameters
            search_params = {
                "term": query,
                "location": location,
                "limit": limit,
                "radius": radius,
                "categories": categories,
                "sort_by": sort_by
            }
            
            if price:
                search_params["price"] = price
            
            # Make API request
            restaurants = await self._search_businesses(search_params)
            
            if not restaurants:
                return ToolExecutionResult(
                    status=ToolStatus.SUCCESS,
                    data={
                        "restaurants": [],
                        "total_found": 0,
                        "search_query": query,
                        "search_location": location,
                        "message": f"No restaurants found for '{query}' in {location}"
                    }
                )
            
            # Get detailed information for each restaurant
            detailed_restaurants = []
            for business in restaurants:
                detailed_info = await self._get_business_details(business["id"])
                if detailed_info:
                    # Combine search result with detailed info
                    combined_info = {**business, **detailed_info}
                    detailed_restaurants.append(self._format_restaurant_info(combined_info))
            
            return ToolExecutionResult(
                status=ToolStatus.SUCCESS,
                data={
                    "restaurants": detailed_restaurants,
                    "total_found": len(detailed_restaurants),
                    "search_query": query,
                    "search_location": location,
                    "summary": self._generate_summary(detailed_restaurants, query)
                }
            )
            
        except Exception as e:
            self.logger.error("Restaurant search failed", error=str(e))
            return ToolExecutionResult(
                status=ToolStatus.ERROR,
                error=f"Failed to search restaurants: {str(e)}"
            )
    
    async def _search_businesses(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Search for businesses using Yelp API.
        
        Args:
            params: Search parameters
            
        Returns:
            List of business data from Yelp
        """
        url = f"{self.base_url}/businesses/search"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("businesses", [])
                else:
                    error_text = await response.text()
                    raise Exception(f"Yelp API error {response.status}: {error_text}")
    
    async def _get_business_details(self, business_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information for a specific business.
        
        Args:
            business_id: Yelp business ID
            
        Returns:
            Detailed business information or None if failed
        """
        try:
            url = f"{self.base_url}/businesses/{business_id}"
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Accept": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        self.logger.warning(
                            "Failed to get business details",
                            business_id=business_id,
                            status=response.status
                        )
                        return None
                        
        except Exception as e:
            self.logger.error(
                "Error getting business details",
                business_id=business_id,
                error=str(e)
            )
            return None
    
    def _format_restaurant_info(self, business: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format business information for consistent output.
        
        Args:
            business: Raw business data from Yelp
            
        Returns:
            Formatted restaurant information
        """
        # Extract location information
        location = business.get("location", {})
        address = ", ".join(filter(None, [
            location.get("address1"),
            location.get("city"),
            location.get("state"),
            location.get("zip_code")
        ]))
        
        # Extract coordinates
        coordinates = business.get("coordinates", {})
        
        # Format hours
        hours_info = self._format_hours(business.get("hours", []))
        
        # Format categories
        categories = [cat["title"] for cat in business.get("categories", [])]
        
        return {
            "name": business.get("name"),
            "yelp_id": business.get("id"),
            "rating": business.get("rating"),
            "review_count": business.get("review_count"),
            "price": business.get("price"),
            "phone": business.get("phone") or business.get("display_phone"),
            "address": address,
            "city": location.get("city"),
            "state": location.get("state"),
            "zip_code": location.get("zip_code"),
            "latitude": coordinates.get("latitude"),
            "longitude": coordinates.get("longitude"),
            "url": business.get("url"),
            "image_url": business.get("image_url"),
            "categories": categories,
            "is_closed": business.get("is_closed", False),
            "hours": hours_info,
            "distance_meters": business.get("distance"),
            "transactions": business.get("transactions", []),
            "yelp_url": business.get("url")
        }
    
    def _format_hours(self, hours_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Format business hours information.
        
        Args:
            hours_data: Hours data from Yelp API
            
        Returns:
            Formatted hours information
        """
        if not hours_data:
            return {"is_open_now": None, "hours": []}
        
        # Get the first (regular) hours entry
        regular_hours = hours_data[0] if hours_data else {}
        
        # Map day numbers to names
        day_names = {
            0: "Monday", 1: "Tuesday", 2: "Wednesday", 3: "Thursday",
            4: "Friday", 5: "Saturday", 6: "Sunday"
        }
        
        formatted_hours = []
        for day_info in regular_hours.get("open", []):
            day_name = day_names.get(day_info["day"], f"Day {day_info['day']}")
            start_time = self._format_time(day_info["start"])
            end_time = self._format_time(day_info["end"])
            
            formatted_hours.append({
                "day": day_name,
                "start": start_time,
                "end": end_time,
                "is_overnight": day_info.get("is_overnight", False)
            })
        
        return {
            "is_open_now": regular_hours.get("is_open_now"),
            "hours": formatted_hours,
            "hours_type": regular_hours.get("hours_type", "REGULAR")
        }
    
    def _format_time(self, time_str: str) -> str:
        """
        Format time string from 24-hour to 12-hour format.
        
        Args:
            time_str: Time in HHMM format (e.g., "1830")
            
        Returns:
            Formatted time string (e.g., "6:30 PM")
        """
        if not time_str or len(time_str) != 4:
            return time_str
        
        try:
            hour = int(time_str[:2])
            minute = int(time_str[2:])
            
            # Convert to 12-hour format
            if hour == 0:
                return f"12:{minute:02d} AM"
            elif hour < 12:
                return f"{hour}:{minute:02d} AM"
            elif hour == 12:
                return f"12:{minute:02d} PM"
            else:
                return f"{hour - 12}:{minute:02d} PM"
        except (ValueError, IndexError):
            return time_str
    
    def _generate_summary(
        self, 
        restaurants: List[Dict[str, Any]], 
        query: str
    ) -> str:
        """
        Generate a human-readable summary of search results.
        
        Args:
            restaurants: List of restaurant information
            query: Original search query
            
        Returns:
            Summary string
        """
        if not restaurants:
            return f"No restaurants found for '{query}'"
        
        count = len(restaurants)
        avg_rating = sum(r.get("rating", 0) for r in restaurants) / count
        total_reviews = sum(r.get("review_count", 0) for r in restaurants)
        
        # Get top-rated restaurant
        top_rated = max(restaurants, key=lambda r: r.get("rating", 0))
        
        summary = f"Found {count} restaurants for '{query}'. "
        summary += f"Average rating: {avg_rating:.1f} stars across {total_reviews} total reviews. "
        summary += f"Top-rated: {top_rated['name']} ({top_rated.get('rating', 0)} stars, {top_rated.get('review_count', 0)} reviews)."
        
        return summary
    
    def get_schema(self) -> Dict[str, Any]:
        """
        Get the OpenAI function schema for this tool.
        
        Returns:
            Function schema dictionary for OpenAI function calling
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search term for restaurants (name, cuisine type, etc.)"
                        },
                        "location": {
                            "type": "string",
                            "description": "Location to search in (address, city, coordinates)",
                            "default": "current location"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Number of results to return (1-50)",
                            "minimum": 1,
                            "maximum": 50,
                            "default": 5
                        },
                        "radius": {
                            "type": "integer", 
                            "description": "Search radius in meters (max 40,000)",
                            "minimum": 1,
                            "maximum": 40000,
                            "default": 10000
                        },
                        "price": {
                            "type": "string",
                            "description": "Price level filter: 1($), 2($$), 3($$$), 4($$$$)",
                            "enum": ["1", "2", "3", "4"]
                        },
                        "sort_by": {
                            "type": "string",
                            "description": "Sort results by",
                            "enum": ["best_match", "rating", "review_count", "distance"],
                            "default": "best_match"
                        }
                    },
                    "required": ["query"]
                }
            }
        }