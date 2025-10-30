"""
Web Search MCP Server
Uses Brave Search API and web scraping for information retrieval
Helps elderly find ANY information, local services, community events
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
import httpx
from bs4 import BeautifulSoup
import json

from utils.mcp_client import MCPServer, MCPTool

logger = logging.getLogger(__name__)


class WebSearchMCPServer(MCPServer):
    """
    MCP Server for web search and information retrieval
    
    Features:
    - General web search (Brave Search API or fallback to scraping)
    - Local services search (NHS, pharmacies, libraries, etc.)
    - Community events and activities
    - Safe search for elderly users (scam-free)
    """
    
    def __init__(self, brave_api_key: Optional[str] = None):
        super().__init__(
            name="web_search",
            description="Search web for information, local services, and community events"
        )
        self.brave_api_key = brave_api_key
        self.use_brave = brave_api_key is not None
        self.http_client: Optional[httpx.AsyncClient] = None
        
        # Register tools
        self._register_tools()
    
    def _register_tools(self):
        """Register all web search tools"""
        
        # Tool 1: General web search
        self.register_tool(MCPTool(
            name="search_web_information",
            description=(
                "Search the web for ANY information. Use this when the user asks "
                "about topics not in your knowledge, current events, local services, "
                "or needs up-to-date information. Safe for elderly users (filters scams)."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "What to search for (e.g., 'chiropodist in Middlesbrough', 'what is atrial fibrillation')"
                    },
                    "result_count": {
                        "type": "integer",
                        "description": "Number of results to return (1-10, default 5)",
                        "default": 5
                    }
                },
                "required": ["query"]
            },
            server_name=self.name
        ))
        
        # Tool 2: Find local services
        self.register_tool(MCPTool(
            name="find_local_services",
            description=(
                "Find LOCAL services near the user (pharmacies, chiropodists, libraries, "
                "community centers, etc.). Returns addresses, phone numbers, and opening hours."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "service_type": {
                        "type": "string",
                        "description": "Type of service (e.g., 'pharmacy', 'chiropodist', 'library', 'community center')"
                    },
                    "postcode": {
                        "type": "string",
                        "description": "UK postcode or area (e.g., 'TS1 2AQ', 'Middlesbrough')"
                    },
                    "open_now": {
                        "type": "boolean",
                        "description": "Only return services open right now",
                        "default": False
                    }
                },
                "required": ["service_type", "postcode"]
            },
            server_name=self.name
        ))
        
        # Tool 3: Find community events
        self.register_tool(MCPTool(
            name="find_community_events",
            description=(
                "Find community events, activities, and social gatherings for elderly users "
                "(coffee mornings, lunch clubs, exercise classes, library events, etc.)"
            ),
            parameters={
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "UK postcode or area (e.g., 'TS1 2AQ', 'Middlesbrough')"
                    },
                    "interest": {
                        "type": "string",
                        "description": "Type of activity (e.g., 'social', 'exercise', 'arts', 'learning')",
                        "default": "social"
                    },
                    "date_range": {
                        "type": "string",
                        "description": "When (e.g., 'this week', 'this month', 'today')",
                        "default": "this week"
                    }
                },
                "required": ["location"]
            },
            server_name=self.name
        ))
    
    async def connect(self) -> bool:
        """Initialize HTTP client"""
        try:
            self.http_client = httpx.AsyncClient(
                timeout=10.0,
                follow_redirects=True,
                headers={
                    "User-Agent": "SerenityAI/1.0 (Elderly Care Assistant; +https://serenity.ai)"
                }
            )
            self.connected = True
            logger.info(f"Web Search MCP Server connected (Brave API: {self.use_brave})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect Web Search MCP: {e}")
            return False
    
    async def disconnect(self):
        """Close HTTP client"""
        if self.http_client:
            await self.http_client.aclose()
        self.connected = False
        logger.info("Web Search MCP Server disconnected")
    
    async def call_tool(self, tool_name: str, arguments: Dict) -> Any:
        """Execute web search tool"""
        
        if tool_name == "search_web_information":
            return await self._search_web(
                query=arguments["query"],
                result_count=arguments.get("result_count", 5)
            )
        
        elif tool_name == "find_local_services":
            return await self._find_local_services(
                service_type=arguments["service_type"],
                postcode=arguments["postcode"],
                open_now=arguments.get("open_now", False)
            )
        
        elif tool_name == "find_community_events":
            return await self._find_community_events(
                location=arguments["location"],
                interest=arguments.get("interest", "social"),
                date_range=arguments.get("date_range", "this week")
            )
        
        else:
            return {"error": f"Unknown tool: {tool_name}"}
    
    async def _search_web(self, query: str, result_count: int = 5) -> Dict:
        """
        Search web using Brave Search API (or fallback)
        
        Args:
            query: Search query
            result_count: Number of results (1-10)
            
        Returns:
            Search results with titles, snippets, and URLs
        """
        try:
            if self.use_brave:
                # Use Brave Search API (preferred)
                return await self._search_brave(query, result_count)
            else:
                # Fallback to DuckDuckGo HTML scraping (free, no API key)
                return await self._search_duckduckgo(query, result_count)
                
        except Exception as e:
            logger.error(f"Web search error: {e}", exc_info=True)
            return {
                "error": "Search temporarily unavailable",
                "results": []
            }
    
    async def _search_brave(self, query: str, count: int) -> Dict:
        """Search using Brave Search API"""
        try:
            url = "https://api.search.brave.com/res/v1/web/search"
            headers = {
                "Accept": "application/json",
                "X-Subscription-Token": self.brave_api_key
            }
            params = {
                "q": query,
                "count": min(count, 10),
                "safesearch": "strict",  # Important for elderly users!
                "country": "GB",  # UK results
                "search_lang": "en"
            }
            
            response = await self.http_client.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            web_results = data.get("web", {}).get("results", [])
            
            results = []
            for item in web_results[:count]:
                results.append({
                    "title": item.get("title", ""),
                    "snippet": item.get("description", ""),
                    "url": item.get("url", ""),
                    "source": "Brave Search"
                })
            
            logger.info(f"Brave Search returned {len(results)} results for: {query}")
            
            return {
                "query": query,
                "result_count": len(results),
                "results": results
            }
            
        except Exception as e:
            logger.error(f"Brave Search error: {e}")
            # Fallback to DuckDuckGo
            return await self._search_duckduckgo(query, count)
    
    async def _search_duckduckgo(self, query: str, count: int) -> Dict:
        """
        Fallback: Search using DuckDuckGo HTML scraping
        Free, no API key required, safe for elderly users
        """
        try:
            url = "https://html.duckduckgo.com/html/"
            data = {"q": query, "kl": "uk-en"}  # UK English
            
            response = await self.http_client.post(url, data=data)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            result_divs = soup.find_all('div', class_='result', limit=count)
            
            results = []
            for div in result_divs:
                title_tag = div.find('a', class_='result__a')
                snippet_tag = div.find('a', class_='result__snippet')
                
                if title_tag:
                    results.append({
                        "title": title_tag.get_text(strip=True),
                        "snippet": snippet_tag.get_text(strip=True) if snippet_tag else "",
                        "url": title_tag.get('href', ''),
                        "source": "DuckDuckGo"
                    })
            
            logger.info(f"DuckDuckGo returned {len(results)} results for: {query}")
            
            return {
                "query": query,
                "result_count": len(results),
                "results": results
            }
            
        except Exception as e:
            logger.error(f"DuckDuckGo search error: {e}")
            return {
                "query": query,
                "error": "Search temporarily unavailable",
                "results": []
            }
    
    async def _find_local_services(
        self,
        service_type: str,
        postcode: str,
        open_now: bool = False
    ) -> Dict:
        """
        Find local services near user
        
        Searches for NHS services, pharmacies, libraries, etc.
        """
        try:
            # Build search query optimized for local results
            query = f"{service_type} near {postcode} UK"
            if open_now:
                query += " open now"
            
            # Add relevant keywords for better results
            if service_type.lower() in ["pharmacy", "chemist"]:
                query += " NHS"
            elif service_type.lower() in ["doctor", "gp"]:
                query += " NHS surgery"
            elif service_type.lower() == "library":
                query += " public library"
            
            # Search web
            search_results = await self._search_web(query, result_count=10)
            
            # Filter and format for local services
            services = []
            for result in search_results.get("results", []):
                # Look for service indicators in title/snippet
                text = (result["title"] + " " + result["snippet"]).lower()
                
                # Extract useful info
                service = {
                    "name": result["title"],
                    "description": result["snippet"],
                    "url": result["url"],
                    "type": service_type
                }
                
                # Try to extract phone/address from snippet
                if "tel:" in text or "phone:" in text:
                    service["has_phone"] = True
                if any(word in text for word in ["address", "location", "street", "road"]):
                    service["has_address"] = True
                
                services.append(service)
            
            logger.info(f"Found {len(services)} local services for {service_type} near {postcode}")
            
            return {
                "service_type": service_type,
                "location": postcode,
                "open_now_filter": open_now,
                "count": len(services),
                "services": services[:5]  # Top 5 results
            }
            
        except Exception as e:
            logger.error(f"Local services search error: {e}", exc_info=True)
            return {
                "error": "Service search temporarily unavailable",
                "services": []
            }
    
    async def _find_community_events(
        self,
        location: str,
        interest: str = "social",
        date_range: str = "this week"
    ) -> Dict:
        """
        Find community events and activities for elderly users
        
        Searches for:
        - Coffee mornings, lunch clubs
        - Exercise classes (chair yoga, tai chi)
        - Social groups, library events
        - Age UK activities
        """
        try:
            # Build query for elderly-friendly events
            query = f"community events {location} {interest} {date_range} elderly seniors"
            
            # Add specific activity keywords
            if interest.lower() == "social":
                query += " coffee morning lunch club befriending"
            elif interest.lower() == "exercise":
                query += " chair exercise tai chi walking group"
            elif interest.lower() == "arts":
                query += " art class craft group"
            elif interest.lower() == "learning":
                query += " computer class workshop talks"
            
            # Search web
            search_results = await self._search_web(query, result_count=10)
            
            # Filter for event-related results
            events = []
            for result in search_results.get("results", []):
                text = (result["title"] + " " + result["snippet"]).lower()
                
                # Look for event indicators
                event_keywords = [
                    "event", "activity", "group", "club", "class",
                    "meeting", "session", "coffee", "lunch", "exercise"
                ]
                
                if any(keyword in text for keyword in event_keywords):
                    event = {
                        "title": result["title"],
                        "description": result["snippet"],
                        "url": result["url"],
                        "interest": interest
                    }
                    
                    # Try to detect dates/times
                    if any(word in text for word in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]):
                        event["has_schedule"] = True
                    if any(word in text for word in ["free", "£", "cost"]):
                        event["has_pricing"] = True
                    
                    events.append(event)
            
            logger.info(f"Found {len(events)} community events in {location}")
            
            return {
                "location": location,
                "interest": interest,
                "date_range": date_range,
                "count": len(events),
                "events": events[:5]  # Top 5 events
            }
            
        except Exception as e:
            logger.error(f"Community events search error: {e}", exc_info=True)
            return {
                "error": "Event search temporarily unavailable",
                "events": []
            }

