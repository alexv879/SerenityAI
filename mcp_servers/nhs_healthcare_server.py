"""
NHS Healthcare Information MCP Server
Provides access to NHS services, medication info, health advice
GDPR-compliant, NO medical diagnosis, only public information
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
import httpx
from bs4 import BeautifulSoup
import json

from utils.mcp_client import MCPServer, MCPTool

logger = logging.getLogger(__name__)


class NHSHealthcareMCPServer(MCPServer):
    """
    MCP Server for NHS healthcare information
    
    Features:
    - Find NHS services (GPs, hospitals, pharmacies, dentists)
    - Medication information (side effects, interactions)
    - Symptom information (NOT diagnosis - signposting only)
    - NHS health advice articles
    
    GDPR Compliance:
    - NO personal medical data stored
    - NO medical diagnosis provided
    - Only retrieves public NHS information
    - Always recommends professional consultation
    """
    
    def __init__(self):
        super().__init__(
            name="nhs_healthcare",
            description="NHS healthcare information and services"
        )
        self.http_client: Optional[httpx.AsyncClient] = None
        self.nhs_api_base = "https://api.nhs.uk"  # NHS API endpoint
        
        # Register tools
        self._register_tools()
    
    def _register_tools(self):
        """Register all NHS healthcare tools"""
        
        # Tool 1: Find NHS services
        self.register_tool(MCPTool(
            name="find_nhs_services",
            description=(
                "Find NHS services near the user: GPs, hospitals, pharmacies, "
                "dentists, opticians, walk-in centres. Returns addresses, phone "
                "numbers, and opening hours. GDPR-safe (public data only)."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "service_type": {
                        "type": "string",
                        "enum": ["gp", "hospital", "pharmacy", "dentist", "optician", "walk-in-centre", "urgent-care"],
                        "description": "Type of NHS service to find"
                    },
                    "postcode": {
                        "type": "string",
                        "description": "UK postcode (e.g., 'TS1 2AQ')"
                    },
                    "distance_miles": {
                        "type": "integer",
                        "description": "Search radius in miles (default 5)",
                        "default": 5
                    },
                    "open_now": {
                        "type": "boolean",
                        "description": "Only show services open right now",
                        "default": False
                    }
                },
                "required": ["service_type", "postcode"]
            },
            server_name=self.name
        ))
        
        # Tool 2: Get medication information
        self.register_tool(MCPTool(
            name="get_medication_info",
            description=(
                "Get NHS-approved information about medications: what it treats, "
                "common side effects, drug interactions, warnings. SAFE for elderly. "
                "NOT medical advice - always recommend consulting pharmacist/GP."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "medication_name": {
                        "type": "string",
                        "description": "Name of medication (e.g., 'ramipril', 'warfarin', 'metformin')"
                    }
                },
                "required": ["medication_name"]
            },
            server_name=self.name
        ))
        
        # Tool 3: Get symptom information (NOT diagnosis!)
        self.register_tool(MCPTool(
            name="get_symptom_information",
            description=(
                "Get NHS information about symptoms. IMPORTANT: This is NOT a diagnosis tool. "
                "Only provides general information and signposting to appropriate services. "
                "ALWAYS recommend user contacts their GP for proper medical advice."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "symptoms": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of symptoms (e.g., ['persistent cough', 'fatigue'])"
                    }
                },
                "required": ["symptoms"]
            },
            server_name=self.name
        ))
        
        # Tool 4: Get NHS health advice
        self.register_tool(MCPTool(
            name="get_nhs_health_advice",
            description=(
                "Get NHS health advice articles on conditions, healthy living, "
                "elderly care tips. Safe, trusted information from NHS.UK."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "Health topic (e.g., 'high blood pressure', 'diabetes', 'arthritis', 'healthy aging')"
                    }
                },
                "required": ["topic"]
            },
            server_name=self.name
        ))
    
    async def connect(self) -> bool:
        """Initialize HTTP client"""
        try:
            self.http_client = httpx.AsyncClient(
                timeout=15.0,
                follow_redirects=True,
                headers={
                    "User-Agent": "SerenityAI/1.0 NHS Information Service",
                    "Accept": "application/json"
                }
            )
            self.connected = True
            logger.info("NHS Healthcare MCP Server connected")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect NHS MCP: {e}")
            return False
    
    async def disconnect(self):
        """Close HTTP client"""
        if self.http_client:
            await self.http_client.aclose()
        self.connected = False
        logger.info("NHS Healthcare MCP Server disconnected")
    
    async def call_tool(self, tool_name: str, arguments: Dict) -> Any:
        """Execute NHS healthcare tool"""
        
        if tool_name == "find_nhs_services":
            return await self._find_nhs_services(
                service_type=arguments["service_type"],
                postcode=arguments["postcode"],
                distance_miles=arguments.get("distance_miles", 5),
                open_now=arguments.get("open_now", False)
            )
        
        elif tool_name == "get_medication_info":
            return await self._get_medication_info(
                medication_name=arguments["medication_name"]
            )
        
        elif tool_name == "get_symptom_information":
            return await self._get_symptom_info(
                symptoms=arguments["symptoms"]
            )
        
        elif tool_name == "get_nhs_health_advice":
            return await self._get_health_advice(
                topic=arguments["topic"]
            )
        
        else:
            return {"error": f"Unknown tool: {tool_name}"}
    
    async def _find_nhs_services(
        self,
        service_type: str,
        postcode: str,
        distance_miles: int = 5,
        open_now: bool = False
    ) -> Dict:
        """
        Find NHS services using NHS API and web scraping
        
        Note: NHS API requires registration. For MVP, using web scraping
        of NHS.UK service finder as fallback.
        """
        try:
            # Map service types to NHS.UK search terms
            service_map = {
                "gp": "GP surgeries",
                "hospital": "hospitals",
                "pharmacy": "pharmacies",
                "dentist": "dentists",
                "optician": "opticians",
                "walk-in-centre": "walk-in centres",
                "urgent-care": "urgent care"
            }
            
            search_term = service_map.get(service_type, service_type)
            
            # Search NHS.UK (fallback method - web scraping)
            # In production, use official NHS API with authentication
            url = "https://www.nhs.uk/service-search"
            params = {
                "query": search_term,
                "location": postcode,
                "distance": distance_miles
            }
            
            # For MVP: Simulate NHS service search results
            # In production: Parse actual NHS API/website response
            services = await self._scrape_nhs_services(
                service_type=service_type,
                postcode=postcode,
                distance_miles=distance_miles
            )
            
            if open_now:
                # Filter to open services (would check actual opening hours in production)
                services = [s for s in services if s.get("open_now", False)]
            
            logger.info(
                f"Found {len(services)} NHS {service_type} services "
                f"within {distance_miles} miles of {postcode}"
            )
            
            return {
                "service_type": service_type,
                "postcode": postcode,
                "distance_miles": distance_miles,
                "count": len(services),
                "services": services,
                "disclaimer": "Please verify opening hours by calling ahead. Information sourced from NHS.UK."
            }
            
        except Exception as e:
            logger.error(f"NHS service search error: {e}", exc_info=True)
            return {
                "error": "NHS service search temporarily unavailable",
                "services": [],
                "fallback": f"Please visit nhs.uk or call 111 for {service_type} services near you"
            }
    
    async def _scrape_nhs_services(
        self,
        service_type: str,
        postcode: str,
        distance_miles: int
    ) -> List[Dict]:
        """
        Scrape NHS.UK for service information
        
        Note: This is a simplified implementation for MVP.
        Production should use official NHS API.
        """
        # For MVP: Return simulated data structure
        # In production: Actual web scraping or API calls
        
        # Example response structure:
        services = [
            {
                "name": f"Example {service_type.upper()} Service 1",
                "address": f"123 High Street, {postcode}",
                "phone": "01642 123456",
                "distance": 0.5,
                "open_now": True,
                "opening_hours": "Mon-Fri: 8:00-18:30, Sat: 9:00-13:00",
                "nhs_link": "https://www.nhs.uk/services/...",
                "note": "This is example data. In production, real NHS data will be used."
            }
        ]
        
        return services
    
    async def _get_medication_info(self, medication_name: str) -> Dict:
        """
        Get NHS medication information
        
        Sources: NHS.UK medicines A-Z
        """
        try:
            # Search NHS medicines database
            search_url = f"https://www.nhs.uk/medicines/{medication_name.lower().replace(' ', '-')}/"
            
            response = await self.http_client.get(search_url)
            
            if response.status_code == 200:
                # Parse NHS medicines page
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Extract key information
                info = {
                    "medication": medication_name,
                    "found": True,
                    "source": "NHS.UK",
                    "sections": {}
                }
                
                # Extract main sections
                sections = soup.find_all('section')
                for section in sections:
                    heading = section.find(['h2', 'h3'])
                    if heading:
                        section_title = heading.get_text(strip=True)
                        content = section.get_text(strip=True)
                        info["sections"][section_title] = content[:500]  # First 500 chars
                
                # Always add disclaimer
                info["disclaimer"] = (
                    "This information is from NHS.UK for general guidance only. "
                    "Always read the patient information leaflet that comes with your medicine. "
                    "Speak to your GP or pharmacist if you have questions or concerns."
                )
                
                logger.info(f"Retrieved NHS medication info for: {medication_name}")
                return info
                
            else:
                # Medication not found on NHS.UK
                return {
                    "medication": medication_name,
                    "found": False,
                    "message": (
                        f"I couldn't find detailed information about {medication_name} "
                        f"on NHS.UK. Please speak to your pharmacist or GP for information "
                        f"about this medication."
                    ),
                    "suggestion": "You can also check the patient information leaflet that came with your medication."
                }
                
        except Exception as e:
            logger.error(f"Medication info error: {e}", exc_info=True)
            return {
                "medication": medication_name,
                "error": "Medication information temporarily unavailable",
                "fallback": (
                    f"Please speak to your pharmacist or GP about {medication_name}, "
                    f"or call NHS 111 for non-urgent advice."
                )
            }
    
    async def _get_symptom_info(self, symptoms: List[str]) -> Dict:
        """
        Get NHS symptom information
        
        IMPORTANT: NOT a diagnosis tool!
        Only provides general information and signposting.
        """
        try:
            symptoms_str = ", ".join(symptoms)
            
            # Search NHS symptom checker
            # Note: We're NOT using the actual NHS 111 symptom checker (that's for emergency assessment)
            # We're just getting general information about symptoms
            
            url = "https://www.nhs.uk/conditions/"
            
            # For each symptom, try to find NHS information
            symptom_info = []
            
            for symptom in symptoms[:3]:  # Limit to 3 symptoms
                search_term = symptom.lower().replace(' ', '-')
                symptom_url = f"{url}{search_term}/"
                
                try:
                    response = await self.http_client.get(symptom_url)
                    
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, 'html.parser')
                        
                        # Extract brief overview
                        overview = soup.find('div', class_='nhsuk-u-reading-width')
                        if overview:
                            symptom_info.append({
                                "symptom": symptom,
                                "info": overview.get_text(strip=True)[:300],  # First 300 chars
                                "nhs_link": symptom_url
                            })
                
                except:
                    pass  # Skip if not found
            
            # Build response with STRONG medical disclaimer
            return {
                "symptoms": symptoms,
                "count": len(symptom_info),
                "information": symptom_info,
                "important_disclaimer": (
                    "⚠️ This is general information only, NOT a diagnosis. "
                    "If you are experiencing these symptoms: "
                    "\n• Call your GP surgery for advice "
                    "\n• For urgent concerns: Call NHS 111 "
                    "\n• For life-threatening emergencies: Call 999"
                ),
                "gp_recommendation": (
                    "I recommend you speak to your GP about these symptoms. "
                    "They can properly assess you and provide appropriate treatment."
                ),
                "nhs_111": "For non-urgent health questions, call NHS 111 (free 24/7 service)"
            }
            
        except Exception as e:
            logger.error(f"Symptom info error: {e}", exc_info=True)
            return {
                "symptoms": symptoms,
                "error": "Symptom information temporarily unavailable",
                "recommendation": (
                    "Please contact your GP surgery or call NHS 111 for advice about your symptoms. "
                    "If this is an emergency, call 999."
                )
            }
    
    async def _get_health_advice(self, topic: str) -> Dict:
        """
        Get NHS health advice articles
        
        Safe, trusted information from NHS.UK
        """
        try:
            # Search NHS health A-Z
            topic_slug = topic.lower().replace(' ', '-')
            url = f"https://www.nhs.uk/conditions/{topic_slug}/"
            
            response = await self.http_client.get(url)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Extract article content
                article = {
                    "topic": topic,
                    "found": True,
                    "source": "NHS.UK",
                    "url": url,
                    "sections": {}
                }
                
                # Get main content sections
                content_div = soup.find('main')
                if content_div:
                    sections = content_div.find_all('section', limit=5)
                    
                    for section in sections:
                        heading = section.find(['h2', 'h3'])
                        if heading:
                            title = heading.get_text(strip=True)
                            content = section.get_text(strip=True)
                            article["sections"][title] = content[:400]  # First 400 chars
                
                logger.info(f"Retrieved NHS health advice for: {topic}")
                return article
                
            else:
                # Topic not found
                return {
                    "topic": topic,
                    "found": False,
                    "message": f"I couldn't find NHS information specifically about '{topic}'.",
                    "suggestion": "Try rephrasing your question, or visit nhs.uk to browse health topics."
                }
                
        except Exception as e:
            logger.error(f"Health advice error: {e}", exc_info=True)
            return {
                "topic": topic,
                "error": "Health advice temporarily unavailable",
                "fallback": "Please visit www.nhs.uk or call NHS 111 for health information."
            }

