"""
Guest Agent - Single entry point for all guest interactions.

Solves:
G1: Understand guest intent (LLM comprehension)
G2: Respond to guest (LLM generation)  
G3: Personalize experience (LLM adaptation)

Dependencies:
- Booking Agent (when booking intent detected)
- Decision Agent (when confused/ambiguous/complaint)
- State Layer (guest profile access)
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import json
import logging
from datetime import datetime

from langchain.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent

from ..domain.state_layer import state_layer, GuestProfile, RoomStatus, BookingStatus, CustomerMemory
from ..config.settings import Settings
from ..monitoring.workflow_monitor import workflow_monitor

# Set up logging
logger = logging.getLogger(__name__)


# Standalone tool functions for LangChain
@tool
def get_guest_profile_tool(guest_id: str) -> str:
    """Get guest profile information and preferences for personalization. Use this when you need to personalize responses or access guest history."""
    try:
        # First try to get from customer memory (persistent)
        customer_memory = state_layer.get_customer_memory(guest_id)
        if customer_memory:
            profile_data = {
                "guest_id": customer_memory.customer_id,
                "name": customer_memory.personal_info.get("name", "Guest"),
                "preferences": customer_memory.preferences,
                "communication_style": customer_memory.personal_info.get("communication_style", "friendly"),
                "loyalty_status": customer_memory.loyalty_info.get("status", "new"),
                "total_stays": len(customer_memory.stay_history),
                "last_stay": customer_memory.stay_history[-1] if customer_memory.stay_history else None
            }
            return json.dumps(profile_data)
        
        # Fallback to guest profile (in-memory)
        profile = state_layer.get_guest_profile(guest_id)
        if profile:
            return json.dumps({
                "guest_id": profile.guest_id,
                "name": profile.name,
                "preferences": profile.preferences,
                "communication_style": profile.communication_style,
                "history": profile.history[-5:] if profile.history else []  # Last 5 interactions
            })
        return json.dumps({"error": "Guest profile not found"})
    except Exception as e:
        logger.error(f"Error getting guest profile: {str(e)}", exc_info=True)
        return json.dumps({"error": str(e)})
    profile = state_layer.get_guest_profile(guest_id)
    if profile:
        return json.dumps({
            "guest_id": profile.guest_id,
            "name": profile.name,
            "preferences": profile.preferences,
            "communication_style": profile.communication_style,
            "history": profile.history[-5:] if profile.history else []  # Last 5 interactions
        })
    return json.dumps({"error": "Guest profile not found"})


@tool
def check_availability_tool(room_type: Optional[str] = None, check_in: Optional[str] = None, check_out: Optional[str] = None) -> str:
    """Check room availability for specific dates and room types. Use this for any availability questions like 'do you have rooms' or 'what rooms are available'."""
    try:
        logger.debug(f"Checking availability for room_type: {room_type}, check_in: {check_in}, check_out: {check_out}")
        available_rooms = state_layer.get_available_rooms(room_type)
        rooms_data = []
        
        for room in available_rooms:
            pricing_rule = state_layer.get_pricing_rule(room.room_type)
            rooms_data.append({
                "room_id": room.room_id,
                "room_type": room.room_type,
                "floor": room.floor,
                "price": room.current_price,
                "amenities": room.amenities
            })
        
        result = json.dumps({
            "available_rooms": rooms_data,
            "count": len(rooms_data)
        })
        logger.debug(f"Availability check completed: {len(rooms_data)} rooms found")
        return result
    except Exception as e:
        logger.debug(f"Error checking availability: {str(e)}", exc_info=True)
        return json.dumps({"error": str(e)})

@tool
def add_stay_to_history_tool(guest_id: str, stay_info: str) -> str:
    """Add stay information to customer history for better personalization."""
    try:
        # Parse stay info from JSON string
        stay_data = json.loads(stay_info) if isinstance(stay_info, str) else stay_info
        
        # Add to customer memory (persistent)
        state_layer.add_stay_to_history(guest_id, stay_data)
        
        return json.dumps({
            "guest_id": guest_id,
            "action": "stay_history_updated",
            "message": "Stay information added to customer history"
        })
    except Exception as e:
        logger.error(f"Error adding stay to history: {str(e)}", exc_info=True)
        return json.dumps({"error": str(e)})

@tool
def add_service_request_tool(guest_id: str, service_info: str) -> str:
    """Add service request to customer history for better service personalization."""
    try:
        # Parse service info from JSON string
        service_data = json.loads(service_info) if isinstance(service_info, str) else service_info
        
        # Add to customer memory (persistent)
        state_layer.add_service_request(guest_id, service_data)
        
        return json.dumps({
            "guest_id": guest_id,
            "action": "service_request_added",
            "message": "Service request added to customer history"
        })
    except Exception as e:
        logger.error(f"Error adding service request: {str(e)}", exc_info=True)
        return json.dumps({"error": str(e)})

@tool
def add_complaint_tool(guest_id: str, complaint_info: str) -> str:
    """Add complaint to customer history for better issue resolution."""
    try:
        # Parse complaint info from JSON string
        complaint_data = json.loads(complaint_info) if isinstance(complaint_info, str) else complaint_info
        
        # Add to customer memory (persistent)
        state_layer.add_complaint(guest_id, complaint_data)
        
        return json.dumps({
            "guest_id": guest_id,
            "action": "complaint_history_updated", 
            "message": "Complaint added to customer history"
        })
    except Exception as e:
        logger.error(f"Error adding complaint: {str(e)}", exc_info=True)
        return json.dumps({"error": str(e)})


@tool
def route_to_orchestrator_tool(guest_id: str, intent: str, message: str, details: Optional[dict] = None) -> str:
    """Route requests to specialized agents. CRITICAL: Use this for ALL pricing/cost questions, booking/reservations, service requests, complaints, or any complex issues. This includes calculating total costs, taxes, multi-night pricing, or any price-related inquiries."""
    try:
        logger.debug(f"Routing to Orchestrator: guest_id={guest_id}, intent={intent}")
        
        # Import here to avoid circular imports
        from ..agents.orchestrator import orchestrator
        
        # Create routing request
        routing_request = {
            "source_agent": "guest_agent",
            "guest_id": guest_id,
            "intent": intent,
            "message": message,
            "details": details or {},
            "timestamp": datetime.now().isoformat()
        }
        
        # Route through orchestrator
        result = orchestrator.route_request(routing_request)
        
        logger.debug(f"Orchestrator routing completed: {result.get('status', 'unknown')}")
        return json.dumps(result)
        
    except Exception as e:
        logger.error(f"Error routing to Orchestrator: {str(e)}", exc_info=True)
        return json.dumps({
            "status": "error",
            "message": f"Routing failed: {str(e)}",
            "action": "retry_or_escalate"
        })


@dataclass
class GuestMessage:
    """Guest message data model."""
    guest_id: str
    message: str
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class GuestResponse:
    """Guest Agent response data model."""
    message: str
    action: str
    confidence: float = 1.0
    requires_human: bool = False


class GuestAgent:
    """
    LLM-powered Guest Agent using LangChain.
    
    Single entry point for all guest interactions with intelligent routing.
    """
    
    def __init__(self, llm: Optional[ChatOpenAI] = None, settings: Optional[Settings] = None):
        self.settings = settings or Settings.from_env()
        self.state_layer = state_layer
        self.conversation_history: Dict[str, List[Dict]] = {}
        
        # Configure LLM from environment variables
        if llm:
            self.llm = llm
        else:
            self.llm = self._create_llm()
        
        # Initialize LangChain agent with tools
        self.agent = self._create_agent()
    
    def _create_llm(self) -> ChatOpenAI:
        """Create LLM instance from environment configuration."""
        logger.debug(f"Creating LLM with model: {self.settings.llm_model}")
        logger.debug(f"Base URL: {self.settings.llm_base_url}")
        logger.debug(f"Temperature: {self.settings.llm_temperature}")
        logger.debug(f"Max tokens: {self.settings.llm_max_tokens}")
        
        return ChatOpenAI(
            model=self.settings.llm_model,
            base_url=self.settings.llm_base_url,
            api_key=self.settings.llm_api_key,
            temperature=self.settings.llm_temperature,
            max_tokens=self.settings.llm_max_tokens,
            timeout=self.settings.llm_timeout_seconds,
            tool_choice="auto"  # Allow model to choose when to use tools
        )
    
    def _create_agent(self):
        """Create LangChain agent with tools."""
        tools = [
            get_guest_profile_tool,
            check_availability_tool,
            route_to_orchestrator_tool
        ]
        
        system_prompt = """You are a Guest Agent for a hospitality AI system.

CRITICAL INSTRUCTIONS - YOU MUST FOLLOW THESE EXACTLY:

FOR PRICING/COST QUESTIONS:
- If user asks "how much", "what's the price", "cost", "rate", "total", "including taxes"
- YOU MUST use route_to_orchestrator_tool with intent="pricing"
- DO NOT respond directly - ALWAYS use the tool
- DO NOT ask for dates, location, or any other information

FOR AVAILABILITY QUESTIONS:
- If user asks "do you have rooms", "available", "what rooms"
- YOU MUST use check_availability_tool

FOR BOOKING REQUESTS:
- If user says "book", "reserve", "make reservation"
- YOU MUST use route_to_orchestrator_tool with intent="booking"

FOR SERVICE REQUESTS:
- If user says "housekeeping", "room service", "maintenance", "need help"
- YOU MUST use route_to_orchestrator_tool with intent="service"

FOR GUEST PROFILE QUESTIONS:
- If user asks "what do you know about me", "my preferences", "my history"
- YOU MUST use get_guest_profile_tool

FOR GENERAL QUESTIONS:
- Only answer questions about hotel amenities, breakfast times, checkout, etc.
- Do NOT answer about pricing, availability, or booking

EXAMPLES:
- "How much is a room?" → Use route_to_orchestrator_tool
- "Do you have rooms available?" → Use check_availability_tool  
- "What time is breakfast?" → Answer directly
- "I want to book a room" → Use route_to_orchestrator_tool

REMEMBER: Your job is to identify intent and route to the right specialist, not to answer everything yourself."""
        
        return create_agent(
            model=self.llm,
            tools=tools,
            system_prompt=system_prompt
        )
    
        
    def _build_context(self, guest_id: str) -> str:
        """Build context for LLM from guest profile and history."""
        profile = self.state_layer.get_guest_profile(guest_id)
        history = self.conversation_history.get(guest_id, [])
        
        context_parts = []
        
        if profile:
            context_parts.append(f"Guest: {profile.name}")
            context_parts.append(f"Preferences: {profile.preferences}")
            context_parts.append(f"Communication Style: {profile.communication_style}")
        
        if history:
            context_parts.append("Recent Conversation:")
            for msg in history[-3:]:  # Last 3 messages
                content = msg.get('content', '')
                # Truncate long messages to prevent token overflow
                if len(content) > 200:
                    content = content[:200] + "..."
                context_parts.append(f"- {msg.get('role', 'unknown')}: {content}")
        
        return "\n".join(context_parts)
    
    def _update_conversation_history(self, guest_id: str, role: str, content: str):
        """Update conversation history for context."""
        if guest_id not in self.conversation_history:
            self.conversation_history[guest_id] = []
        
        self.conversation_history[guest_id].append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        
        # Keep last 10 messages per guest for context (balanced memory vs tokens)
        if len(self.conversation_history[guest_id]) > 10:
            self.conversation_history[guest_id] = self.conversation_history[guest_id][-10:]
    
    def _detect_intent_and_force_tool(self, message: str, guest_id: str) -> Optional[str]:
        """Detect intent and force tool usage if needed."""
        message_lower = message.lower()
        
        # Pricing queries - MUST route to orchestrator
        pricing_keywords = [
            "how much", "what's the price", "what is the price", "cost", 
            "rate", "total", "including taxes", "price for", "cost of"
        ]
        if any(keyword in message_lower for keyword in pricing_keywords):
            logger.debug(f"Detected pricing intent for guest {guest_id}")
            return "route_to_orchestrator"
        
        # Availability queries - MUST use availability tool
        availability_keywords = [
            "do you have rooms", "rooms available", "any rooms", 
            "available", "availability", "do you have"
        ]
        if any(keyword in message_lower for keyword in availability_keywords):
            logger.debug(f"Detected availability intent for guest {guest_id}")
            return "check_availability"
        
        # Booking requests - MUST route to orchestrator
        booking_keywords = [
            "book", "reserve", "make a reservation", "booking", 
            "i want to book", "reserve a room"
        ]
        if any(keyword in message_lower for keyword in booking_keywords):
            logger.debug(f"Detected booking intent for guest {guest_id}")
            return "route_to_orchestrator"
        
        # Service requests - MUST route to orchestrator
        service_keywords = [
            "housekeeping", "room service", "maintenance", "need help",
            "service", " towels", "clean", "broken", "not working",
            "dirty", "grim", "issues", "problems", "complaint", "uncomfortable"
        ]
        if any(keyword in message_lower for keyword in service_keywords):
            logger.debug(f"Detected service intent for guest {guest_id}")
            return "route_to_orchestrator"
        
        # Profile requests - MUST use profile tool
        profile_keywords = [
            "what do you know about me", "my preferences", "my history",
            "my profile", "about me", "my information"
        ]
        if any(keyword in message_lower for keyword in profile_keywords):
            logger.debug(f"Detected profile intent for guest {guest_id}")
            return "get_profile"
        
        return None

    def process_message(self, guest_message: GuestMessage) -> GuestResponse:
        """
        Process guest message and generate response.
        
        Args:
            guest_message: Guest message with ID and content
            
        Returns:
            AgentResponse with reply and action
        """
        logger.debug(f"Processing message from guest {guest_message.guest_id}: {guest_message.message}")
        
        # Force tool usage based on intent detection
        forced_tool = self._detect_intent_and_force_tool(guest_message.message, guest_message.guest_id)
        
        if forced_tool == "route_to_orchestrator":
            # Directly call the orchestrator routing tool
            logger.debug(f"Forcing orchestrator routing for guest {guest_message.guest_id}")
            
            # Determine intent type
            intent = "general"
            message_lower = guest_message.message.lower()
            if any(k in message_lower for k in ["how much", "price", "cost", "rate"]):
                intent = "pricing"
            elif any(k in message_lower for k in ["book", "reserve", "reservation"]):
                intent = "booking"
            elif any(k in message_lower for k in ["service", "housekeeping", "maintenance", "dirty", "complaint", "issues", "problems", "broken", "not working"]):
                intent = "service"
            
            tool_result = route_to_orchestrator_tool.invoke({
                "guest_id": guest_message.guest_id,
                "intent": intent,
                "message": guest_message.message
            })
            
            # Update conversation history
            self._update_conversation_history(guest_message.guest_id, "guest", guest_message.message)
            self._update_conversation_history(guest_message.guest_id, "agent", f"Routing to {intent} specialist...")
            
            return GuestResponse(
                message=f"I'll connect you with our {intent} specialist to help with that.",
                action="routed_to_orchestrator",
                confidence=0.9
            )
        
        elif forced_tool == "check_availability":
            # Directly call availability tool
            logger.debug(f"Forcing availability check for guest {guest_message.guest_id}")
            
            tool_result = check_availability_tool.invoke({})
            
            # Update conversation history
            self._update_conversation_history(guest_message.guest_id, "guest", guest_message.message)
            self._update_conversation_history(guest_message.guest_id, "agent", tool_result)
            
            return GuestResponse(
                message=tool_result,
                action="checked_availability",
                confidence=0.9
            )
        
        elif forced_tool == "get_profile":
            # Directly call profile tool
            logger.debug(f"Forcing profile retrieval for guest {guest_message.guest_id}")
            
            tool_result = get_guest_profile_tool.invoke({"guest_id": guest_message.guest_id})
            
            # Update conversation history
            self._update_conversation_history(guest_message.guest_id, "guest", guest_message.message)
            self._update_conversation_history(guest_message.guest_id, "agent", tool_result)
            
            return GuestResponse(
                message=tool_result,
                action="retrieved_profile",
                confidence=0.9
            )
        
        # Update conversation history
        self._update_conversation_history(guest_message.guest_id, "guest", guest_message.message)
        
        # Build context
        context = self._build_context(guest_message.guest_id)
        logger.debug(f"Built context for guest {guest_message.guest_id}")
        
        # Build conversation history as messages
        messages = [
            SystemMessage(content=f"""You are a Guest Agent for a hospitality AI system.

Guest Profile and Context:
{context}

Respond naturally and helpfully. Use tools when needed to:
- Get guest information
- Check room availability
- Handle bookings
- Process service requests
- Escalate complex issues

Always be polite, personalized, and solution-oriented.""")
        ]

        # Add conversation history (excluding the current message which we'll add at the end)
        history = self.conversation_history.get(guest_message.guest_id, [])
        for msg in history[:-1]:  # All except current (which was just added)
            if msg["role"] == "guest":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "agent":
                messages.append(AIMessage(content=msg["content"]))

        # Add current message
        messages.append(HumanMessage(content=guest_message.message))
        
        try:
            logger.debug(f"Invoking agent for guest {guest_message.guest_id}")
            # Execute agent using new LangChain v1.2.0 pattern
            result = self.agent.invoke({"messages": messages}, config={"callbacks": [workflow_monitor]})
            logger.debug(f"Agent invoked successfully for guest {guest_message.guest_id}")
            
            # Extract response from messages array (modern LangChain format)
            if "messages" in result and result["messages"]:
                last_message = result["messages"][-1]
                if hasattr(last_message, 'content'):
                    reply = last_message.content
                elif isinstance(last_message, dict) and 'content' in last_message:
                    reply = last_message['content']
                else:
                    reply = str(last_message)
            else:
                # Fallback for older format or unexpected structure
                reply = result.get("output", "I apologize, but I'm having trouble processing your request right now.")
                    
            logger.debug(f"Generated reply for guest {guest_message.guest_id}: {reply[:100]}...")

            # Check if any tools were called by looking at the result
            tool_calls = []
            if "messages" in result:
                for msg in result["messages"]:
                    if hasattr(msg, 'tool_calls') and msg.tool_calls:
                        tool_calls.extend(msg.tool_calls)
                    elif isinstance(msg, dict) and msg.get('tool_calls'):
                        tool_calls.extend(msg['tool_calls'])

            if tool_calls:
                tool_names = [tc.get('name', 'unknown') for tc in tool_calls]
                logger.debug(f"Tools called for guest {guest_message.guest_id}: {tool_names}")

            # Update conversation history with agent response
            self._update_conversation_history(guest_message.guest_id, "agent", reply)

            # Determine action based on tool usage and content
            action = "responded"
            if tool_calls:
                tool_name = tool_calls[0].get('name', '')
                if 'orchestrator' in tool_name or 'route' in tool_name:
                    action = "routed_to_orchestrator"
                elif 'availability' in tool_name:
                    action = "checked_availability"
                elif 'profile' in tool_name:
                    action = "retrieved_profile"
            elif "booking_initiated" in reply:
                action = "booking_intent_detected"
            elif "service_request_created" in reply:
                action = "service_request_detected"
            elif "escalation_initiated" in reply:
                action = "escalation_detected"

            logger.debug(f"Determined action for guest {guest_message.guest_id}: {action}")
            
            return GuestResponse(
                message=reply,
                action=action,
                confidence=0.8,
                requires_human="escalation" in action
            )
            
        except Exception as e:
            logger.debug(f"Error processing message for guest {guest_message.guest_id}: {str(e)}", exc_info=True)
            error_response = "I apologize, but I'm experiencing technical difficulties. Please try again or contact our front desk directly."
            
            return GuestResponse(
                message=error_response,
                action="error",
                confidence=0.0,
                requires_human=True
            )


# Global guest agent instance
guest_agent = GuestAgent()
