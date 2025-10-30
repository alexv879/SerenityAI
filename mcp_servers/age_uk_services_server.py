"""
Age UK Services MCP Server
Connects elderly users to support services, befriending, practical help
Helps combat loneliness and maintain independence
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
import httpx
from bs4 import BeautifulSoup
import json

from utils.mcp_client import MCPServer, MCPTool

logger = logging.getLogger(__name__)


class AgeUKServicesMCPServer(MCPServer):
    """
    MCP Server for Age UK and elderly support services
    
    Features:
    - Befriending services (combat loneliness)
    - Practical help (shopping, home repairs, gardening)
    - Social activities (lunch clubs, coffee mornings, day centres)
    - Benefits advice (Winter Fuel Payment, Attendance Allowance, etc.)
    - Community transport and accessibility support
    
    Mission: Help elderly people stay connected and independent
    """
    
    def __init__(self):
        super().__init__(
            name="age_uk_services",
            description="Age UK and elderly support services"
        )
        self.http_client: Optional[httpx.AsyncClient] = None
        
        # Service directories (in production, these would be proper APIs/databases)
        self.age_uk_services = self._load_service_directory()
        
        # Register tools
        self._register_tools()
    
    def _load_service_directory(self) -> Dict:
        """
        Load Age UK service directory
        
        In production: This would connect to Age UK APIs or curated database
        For MVP: Using structured data that can be searched
        """
        return {
            "befriending": {
                "description": "Telephone or in-person befriending to combat loneliness",
                "national_service": "Age UK Befriending",
                "phone": "0800 678 1602",
                "website": "https://www.ageuk.org.uk/services/befriending-services/"
            },
            "practical_help": {
                "description": "Help with shopping, household tasks, gardening, odd jobs",
                "services": ["handyperson service", "shopping assistance", "gardening help"],
                "phone": "0800 055 6112",
                "website": "https://www.ageuk.org.uk/services/in-your-area/"
            },
            "social_activities": {
                "description": "Lunch clubs, coffee mornings, exercise classes, day centres",
                "activities": ["lunch clubs", "coffee mornings", "exercise classes", "day centres"],
                "phone": "0800 055 6112",
                "website": "https://www.ageuk.org.uk/services/in-your-area/"
            },
            "benefits_advice": {
                "description": "Free benefits advice and help claiming entitlements",
                "benefits": [
                    "Attendance Allowance",
                    "Pension Credit",
                    "Winter Fuel Payment",
                    "Warm Home Discount",
                    "Council Tax Reduction",
                    "Housing Benefit"
                ],
                "phone": "0800 169 6565",
                "website": "https://www.ageuk.org.uk/information-advice/money-legal/benefits-entitlements/"
            },
            "transport": {
                "description": "Community transport and dial-a-ride services",
                "phone": "0800 055 6112",
                "website": "https://www.ageuk.org.uk/services/in-your-area/"
            }
        }
    
    def _register_tools(self):
        """Register all Age UK service tools"""
        
        # Tool 1: Find befriending services
        self.register_tool(MCPTool(
            name="find_befriending_service",
            description=(
                "Find befriending services to combat loneliness. Telephone befriending, "
                "in-person visits, social groups. Age UK and local charities. "
                "Perfect for isolated elderly users who need social connection."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "postcode": {
                        "type": "string",
                        "description": "UK postcode to find local befriending services"
                    },
                    "preference": {
                        "type": "string",
                        "enum": ["telephone", "in-person", "group", "any"],
                        "description": "Type of befriending preferred",
                        "default": "any"
                    }
                },
                "required": ["postcode"]
            },
            server_name=self.name
        ))
        
        # Tool 2: Find practical help
        self.register_tool(MCPTool(
            name="find_practical_help",
            description=(
                "Find practical help services: shopping assistance, handyperson service, "
                "gardening, home repairs, cleaning. Age UK and local community services."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "postcode": {
                        "type": "string",
                        "description": "UK postcode"
                    },
                    "help_needed": {
                        "type": "string",
                        "enum": ["shopping", "handyperson", "gardening", "cleaning", "general"],
                        "description": "Type of help needed",
                        "default": "general"
                    }
                },
                "required": ["postcode"]
            },
            server_name=self.name
        ))
        
        # Tool 3: Find social activities
        self.register_tool(MCPTool(
            name="find_social_activities",
            description=(
                "Find social activities for elderly: lunch clubs, coffee mornings, "
                "exercise classes, day centres, hobby groups. Combat isolation!"
            ),
            parameters={
                "type": "object",
                "properties": {
                    "postcode": {
                        "type": "string",
                        "description": "UK postcode"
                    },
                    "activity_type": {
                        "type": "string",
                        "enum": ["lunch-club", "coffee-morning", "exercise", "day-centre", "hobbies", "any"],
                        "description": "Type of activity",
                        "default": "any"
                    }
                },
                "required": ["postcode"]
            },
            server_name=self.name
        ))
        
        # Tool 4: Get benefits advice
        self.register_tool(MCPTool(
            name="get_benefits_advice",
            description=(
                "Get information about benefits elderly people may be entitled to: "
                "Attendance Allowance, Pension Credit, Winter Fuel Payment, Warm Home Discount, "
                "Council Tax Reduction. FREE Age UK benefits advice service."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "situation": {
                        "type": "string",
                        "description": "User's situation (e.g., 'need help with heating costs', 'care needs', 'low income')"
                    },
                    "age": {
                        "type": "integer",
                        "description": "User's age (optional, helps determine eligibility)",
                        "minimum": 60
                    }
                },
                "required": ["situation"]
            },
            server_name=self.name
        ))
        
        # Tool 5: Find transport help
        self.register_tool(MCPTool(
            name="find_transport_help",
            description=(
                "Find community transport services: dial-a-ride, hospital transport, "
                "volunteer drivers, accessible transport options for elderly users."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "postcode": {
                        "type": "string",
                        "description": "UK postcode"
                    },
                    "destination_type": {
                        "type": "string",
                        "enum": ["hospital", "shopping", "social", "general"],
                        "description": "Type of journey",
                        "default": "general"
                    },
                    "accessibility_needs": {
                        "type": "boolean",
                        "description": "Requires wheelchair-accessible or assisted transport",
                        "default": False
                    }
                },
                "required": ["postcode"]
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
                    "User-Agent": "SerenityAI/1.0 Elderly Support Service"
                }
            )
            self.connected = True
            logger.info("Age UK Services MCP Server connected")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect Age UK MCP: {e}")
            return False
    
    async def disconnect(self):
        """Close HTTP client"""
        if self.http_client:
            await self.http_client.aclose()
        self.connected = False
        logger.info("Age UK Services MCP Server disconnected")
    
    async def call_tool(self, tool_name: str, arguments: Dict) -> Any:
        """Execute Age UK service tool"""
        
        if tool_name == "find_befriending_service":
            return await self._find_befriending(
                postcode=arguments["postcode"],
                preference=arguments.get("preference", "any")
            )
        
        elif tool_name == "find_practical_help":
            return await self._find_practical_help(
                postcode=arguments["postcode"],
                help_needed=arguments.get("help_needed", "general")
            )
        
        elif tool_name == "find_social_activities":
            return await self._find_social_activities(
                postcode=arguments["postcode"],
                activity_type=arguments.get("activity_type", "any")
            )
        
        elif tool_name == "get_benefits_advice":
            return await self._get_benefits_advice(
                situation=arguments["situation"],
                age=arguments.get("age")
            )
        
        elif tool_name == "find_transport_help":
            return await self._find_transport_help(
                postcode=arguments["postcode"],
                destination_type=arguments.get("destination_type", "general"),
                accessibility_needs=arguments.get("accessibility_needs", False)
            )
        
        else:
            return {"error": f"Unknown tool: {tool_name}"}
    
    async def _find_befriending(self, postcode: str, preference: str = "any") -> Dict:
        """
        Find befriending services to combat loneliness
        
        Returns Age UK and local charity befriending services
        """
        try:
            # Get national Age UK befriending service
            national_service = self.age_uk_services["befriending"]
            
            # In production: Search Age UK local services API + local charities database
            # For MVP: Return structured information
            
            services = [
                {
                    "name": "Age UK Telephone Befriending",
                    "type": "telephone",
                    "description": (
                        "Regular weekly phone calls from friendly trained volunteers. "
                        "Helps combat loneliness and provides social connection."
                    ),
                    "phone": national_service["phone"],
                    "website": national_service["website"],
                    "coverage": "National",
                    "cost": "FREE",
                    "referral": "Self-referral or family can refer"
                },
                {
                    "name": "Age UK Local Befriending",
                    "type": "in-person",
                    "description": (
                        "In-person visits from volunteers. Chat over tea, "
                        "help with tasks, companionship. Typically weekly or fortnightly."
                    ),
                    "phone": "0800 055 6112",
                    "website": national_service["website"],
                    "coverage": f"Check availability in {postcode} area",
                    "cost": "FREE or small contribution",
                    "referral": "Contact local Age UK"
                },
                {
                    "name": "The Silver Line",
                    "type": "telephone",
                    "description": (
                        "24/7 helpline for older people. Friendship, advice, or just someone to talk to. "
                        "Also offers telephone friendship groups."
                    ),
                    "phone": "0800 4 70 80 90",
                    "website": "https://www.thesilverline.org.uk/",
                    "coverage": "National - 24/7",
                    "cost": "FREE",
                    "referral": "Just call anytime"
                }
            ]
            
            # Filter by preference
            if preference != "any":
                services = [s for s in services if s["type"] == preference]
            
            logger.info(f"Found {len(services)} befriending services for {postcode}")
            
            return {
                "postcode": postcode,
                "preference": preference,
                "count": len(services),
                "services": services,
                "message": (
                    "These befriending services can help combat loneliness. "
                    "They're run by trained volunteers and are completely FREE. "
                    "Don't hesitate to reach out - you deserve companionship!"
                )
            }
            
        except Exception as e:
            logger.error(f"Befriending service search error: {e}", exc_info=True)
            return {
                "error": "Service search temporarily unavailable",
                "fallback": {
                    "name": "Age UK National",
                    "phone": "0800 678 1602",
                    "message": "Call Age UK for befriending services in your area"
                }
            }
    
    async def _find_practical_help(self, postcode: str, help_needed: str = "general") -> Dict:
        """Find practical help services"""
        try:
            services = []
            
            # Age UK Handyperson Service
            if help_needed in ["handyperson", "general"]:
                services.append({
                    "name": "Age UK Handyperson Service",
                    "type": "handyperson",
                    "description": (
                        "Trusted handyperson for small jobs: changing light bulbs, "
                        "fitting grab rails, minor repairs, putting up shelves. "
                        "DBS-checked, reliable, elderly-friendly."
                    ),
                    "phone": "0800 055 6112",
                    "website": "https://www.ageuk.org.uk/services/handyperson-service/",
                    "cost": "Small charge per hour (concessions available)",
                    "availability": f"Contact to check availability in {postcode}"
                })
            
            # Shopping assistance
            if help_needed in ["shopping", "general"]:
                services.append({
                    "name": "Age UK Shopping Service",
                    "type": "shopping",
                    "description": (
                        "Volunteer assistance with shopping - either accompanying you "
                        "or shopping on your behalf. Weekly grocery shopping help."
                    ),
                    "phone": "0800 055 6112",
                    "cost": "FREE or small contribution",
                    "availability": "Subject to volunteer availability"
                })
            
            # Gardening help
            if help_needed in ["gardening", "general"]:
                services.append({
                    "name": "Age UK Gardening Service",
                    "type": "gardening",
                    "description": (
                        "Help with garden maintenance: lawn mowing, hedge trimming, "
                        "weeding, general tidying. Keep your garden safe and tidy."
                    ),
                    "phone": "0800 055 6112",
                    "cost": "Charges apply (concessions available)",
                    "availability": "Seasonal availability"
                })
            
            logger.info(f"Found {len(services)} practical help services for {postcode}")
            
            return {
                "postcode": postcode,
                "help_needed": help_needed,
                "count": len(services),
                "services": services,
                "note": (
                    "All services use DBS-checked staff/volunteers. "
                    "Contact your local Age UK to check availability in your area."
                )
            }
            
        except Exception as e:
            logger.error(f"Practical help search error: {e}", exc_info=True)
            return {
                "error": "Service search temporarily unavailable",
                "fallback": "Call Age UK on 0800 055 6112 for practical help services"
            }
    
    async def _find_social_activities(self, postcode: str, activity_type: str = "any") -> Dict:
        """Find social activities and groups"""
        try:
            activities = [
                {
                    "name": "Lunch Clubs",
                    "type": "lunch-club",
                    "description": (
                        "Enjoy a hot meal and good company. Weekly lunch clubs at "
                        "community venues. Great way to meet friends and socialize."
                    ),
                    "frequency": "Weekly (typically)",
                    "cost": "Small charge for meal (£3-5 usually)",
                    "phone": "0800 055 6112",
                    "benefits": ["Social connection", "Nutritious meal", "Regular routine"]
                },
                {
                    "name": "Coffee Mornings",
                    "type": "coffee-morning",
                    "description": (
                        "Informal coffee and chat sessions. Drop in when you like, "
                        "no commitment. Usually at local community centers or churches."
                    ),
                    "frequency": "Weekly or more frequent",
                    "cost": "Donation or £1-2",
                    "phone": "0800 055 6112",
                    "benefits": ["Relaxed atmosphere", "Make friends", "Get out of house"]
                },
                {
                    "name": "Exercise Classes",
                    "type": "exercise",
                    "description": (
                        "Gentle exercise classes for older people: chair exercise, "
                        "tai chi, yoga, walking groups. Keep active and healthy."
                    ),
                    "frequency": "Weekly classes",
                    "cost": "FREE to £5 per session",
                    "phone": "0800 055 6112",
                    "benefits": ["Stay fit", "Social", "Qualified instructors"]
                },
                {
                    "name": "Day Centres",
                    "type": "day-centre",
                    "description": (
                        "Full day of activities, lunch, and companionship. "
                        "Activities like crafts, games, outings. Transport often provided."
                    ),
                    "frequency": "1-5 days per week",
                    "cost": "Daily rate (varies, financial help available)",
                    "phone": "0800 055 6112",
                    "benefits": ["All-day care", "Hot meal", "Transport", "Activities"]
                }
            ]
            
            # Filter by activity type
            if activity_type != "any":
                activities = [a for a in activities if a["type"] == activity_type]
            
            logger.info(f"Found {len(activities)} social activities for {postcode}")
            
            return {
                "postcode": postcode,
                "activity_type": activity_type,
                "count": len(activities),
                "activities": activities,
                "message": (
                    "These activities are great for staying active and meeting people. "
                    "Contact your local Age UK to find specific groups in your area. "
                    "Going to social activities can really help combat loneliness!"
                )
            }
            
        except Exception as e:
            logger.error(f"Social activities search error: {e}", exc_info=True)
            return {
                "error": "Activity search temporarily unavailable",
                "fallback": "Call Age UK on 0800 055 6112 for activities near you"
            }
    
    async def _get_benefits_advice(self, situation: str, age: Optional[int] = None) -> Dict:
        """Get benefits advice and entitlement information"""
        try:
            benefits_info = self.age_uk_services["benefits_advice"]
            
            # Build response based on situation
            relevant_benefits = []
            
            # Attendance Allowance (care needs)
            if any(word in situation.lower() for word in ["care", "help", "disabled", "illness", "mobility"]):
                relevant_benefits.append({
                    "name": "Attendance Allowance",
                    "description": (
                        "If you need help with personal care or supervision due to "
                        "illness or disability. £72.65 or £108.55 per week (2024 rates)."
                    ),
                    "eligibility": "Age 65+, need help with daily living",
                    "amount": "£72.65 - £108.55 per week",
                    "how_to_claim": "Call DWP: 0800 731 0122"
                })
            
            # Pension Credit (low income)
            if any(word in situation.lower() for word in ["money", "income", "afford", "bills", "pension"]):
                relevant_benefits.append({
                    "name": "Pension Credit",
                    "description": (
                        "Tops up your income if you're over State Pension age. "
                        "Also unlocks other benefits like housing benefit, council tax reduction."
                    ),
                    "eligibility": "State Pension age, low income",
                    "amount": "Varies - tops up to guaranteed minimum",
                    "how_to_claim": "Call DWP: 0800 99 1234"
                })
            
            # Winter Fuel Payment (heating)
            if any(word in situation.lower() for word in ["heating", "cold", "winter", "warm", "fuel"]):
                relevant_benefits.append({
                    "name": "Winter Fuel Payment",
                    "description": (
                        "Annual payment to help with heating costs. £250-£600 depending "
                        "on circumstances. Paid automatically if you get State Pension."
                    ),
                    "eligibility": "Born before specific date (changes yearly)",
                    "amount": "£250 - £600 per year",
                    "how_to_claim": "Usually automatic, or call: 0800 731 0160"
                })
                
                relevant_benefits.append({
                    "name": "Warm Home Discount",
                    "description": (
                        "£150 off winter electricity bill. If you get Pension Credit, "
                        "you should qualify automatically."
                    ),
                    "eligibility": "Pension Credit or low income",
                    "amount": "£150 off bill",
                    "how_to_claim": "Contact your energy supplier"
                })
            
            # Council Tax Reduction (always relevant!)
            relevant_benefits.append({
                "name": "Council Tax Reduction",
                "description": (
                    "Reduction in council tax bill if you're on low income. "
                    "Some councils offer 100% reduction for pensioners."
                ),
                "eligibility": "Low income, varies by council",
                "amount": "Up to 100% reduction",
                "how_to_claim": "Apply through your local council"
            })
            
            # If no specific benefits identified, show all
            if not relevant_benefits:
                relevant_benefits = [
                    {"name": benefit, "description": "Contact Age UK for information"}
                    for benefit in benefits_info["benefits"]
                ]
            
            logger.info(f"Provided benefits advice for situation: {situation}")
            
            return {
                "situation": situation,
                "count": len(relevant_benefits),
                "benefits": relevant_benefits,
                "free_advice_service": {
                    "name": "Age UK Benefits Advice",
                    "phone": benefits_info["phone"],
                    "description": (
                        "FREE expert benefits advice. They can check what you're entitled to "
                        "and help you claim. Many people miss out on benefits they're entitled to!"
                    )
                },
                "important_note": (
                    "These are just some benefits you might be entitled to. "
                    "Age UK can do a full benefits check for you - it's completely free. "
                    "Many people are missing out on £1000s they're entitled to!"
                )
            }
            
        except Exception as e:
            logger.error(f"Benefits advice error: {e}", exc_info=True)
            return {
                "error": "Benefits advice temporarily unavailable",
                "fallback": {
                    "name": "Age UK Benefits Helpline",
                    "phone": "0800 169 6565",
                    "message": "Call for FREE expert benefits advice"
                }
            }
    
    async def _find_transport_help(
        self,
        postcode: str,
        destination_type: str = "general",
        accessibility_needs: bool = False
    ) -> Dict:
        """Find community transport and accessible transport services"""
        try:
            transport_services = [
                {
                    "name": "Age UK Community Transport",
                    "description": (
                        "Door-to-door transport service for shopping, medical appointments, "
                        "social activities. Drivers help you in and out of vehicle."
                    ),
                    "accessibility": "Wheelchair-accessible vehicles available",
                    "phone": "0800 055 6112",
                    "cost": "Small charge per journey (varies by area)",
                    "booking": "Call to book in advance",
                    "coverage": f"Check availability in {postcode}"
                },
                {
                    "name": "NHS Patient Transport",
                    "description": (
                        "FREE transport to hospital appointments if you have medical need "
                        "and can't use public transport or taxi."
                    ),
                    "accessibility": "Wheelchair accessible",
                    "phone": "Call your hospital to arrange",
                    "cost": "FREE for eligible patients",
                    "eligibility": "Medical need, can't use other transport",
                    "booking": "Book through hospital when appointment made"
                },
                {
                    "name": "Red Cross Transport Service",
                    "description": (
                        "Volunteer drivers for medical appointments. Driver waits and "
                        "brings you home. Friendly, supportive service."
                    ),
                    "phone": "0800 104 0105",
                    "cost": "Donation requested (not compulsory)",
                    "booking": "Call to arrange",
                    "coverage": "Many areas in UK"
                },
                {
                    "name": "Local Dial-a-Ride",
                    "description": (
                        "Community bus service for people who can't use regular buses. "
                        "Pre-booked door-to-door service within local area."
                    ),
                    "accessibility": "Designed for wheelchair users and mobility aids",
                    "cost": "Similar to bus fare",
                    "booking": "Register and book in advance",
                    "coverage": "Contact local council for your area"
                }
            ]
            
            # Filter for accessibility if needed
            if accessibility_needs:
                transport_services = [
                    s for s in transport_services
                    if "wheelchair" in s.get("accessibility", "").lower()
                ]
            
            logger.info(f"Found {len(transport_services)} transport services for {postcode}")
            
            return {
                "postcode": postcode,
                "destination_type": destination_type,
                "accessibility_needs": accessibility_needs,
                "count": len(transport_services),
                "services": transport_services,
                "message": (
                    "These transport services can help you get to appointments and activities. "
                    "Don't let transport stop you from getting out! Many services are free or very low cost."
                )
            }
            
        except Exception as e:
            logger.error(f"Transport help search error: {e}", exc_info=True)
            return {
                "error": "Transport search temporarily unavailable",
                "fallback": "Call Age UK on 0800 055 6112 for transport help in your area"
            }

