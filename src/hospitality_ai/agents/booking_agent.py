"""
Booking Agent - Handles room availability, reservations, and pricing.

Solves:
B1: Availability checking
B2: Reservation creation  
B3: Pricing application

Dependencies:
- Revenue Agent (for pricing rules)
- Operations Agent (room prep tasks)
- Decision Agent (conflicts, special cases)
- State Layer (booking data, room status)

Does NOT talk to guests directly - only agent-to-agent communication.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import json
import logging
from datetime import datetime, timedelta

from langchain.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent

from ..domain.state_layer import state_layer, BookingStatus, RoomStatus
from ..config.settings import Settings
from ..monitoring.workflow_monitor import workflow_monitor

# Set up logging
logger = logging.getLogger(__name__)


@dataclass
class BookingRequest:
    """Booking request data model."""
    guest_id: str
    check_in: str
    check_out: str
    room_id: Optional[str] = None
    room_type: Optional[str] = None
    special_requests: List[str] = None


@dataclass
class BookingResponse:
    """Booking response data model."""
    success: bool
    message: str
    booking_id: Optional[str] = None
    total_price: Optional[float] = None
    action: str = "booking_processed"


# Standalone tool functions for LangChain
@tool
def check_room_availability_tool(room_type: Optional[str] = None, check_in: Optional[str] = None, check_out: Optional[str] = None) -> str:
    """Check room availability for given dates and room type."""
    try:
        available_rooms = state_layer.get_available_rooms(room_type)
        
        # Filter by room ID if specified
        if room_type:
            available_rooms = [r for r in available_rooms if r.room_type == room_type]
        
        rooms_data = []
        for room in available_rooms:
            pricing_rule = state_layer.get_pricing_rule(room.room_type)
            rooms_data.append({
                "room_id": room.room_id,
                "room_type": room.room_type,
                "floor": room.floor,
                "base_price": room.base_price,
                "current_price": room.current_price,
                "amenities": room.amenities
            })
        
        return json.dumps({
            "available_rooms": rooms_data,
            "count": len(rooms_data),
            "check_in": check_in,
            "check_out": check_out
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def calculate_pricing_tool(room_id: str, check_in: str, check_out: str, guest_id: str) -> str:
    """Calculate total pricing for booking."""
    try:
        # Get room details
        room = state_layer.get_room(room_id)
        if not room:
            return json.dumps({"error": "Room not found"})
        
        # Get pricing rule
        pricing_rule = state_layer.get_pricing_rule(room.room_type)
        if not pricing_rule:
            return json.dumps({"error": "Pricing rule not found"})
        
        # Calculate nights
        check_in_date = datetime.fromisoformat(check_in)
        check_out_date = datetime.fromisoformat(check_out)
        nights = (check_out_date - check_in_date).days
        
        if nights <= 0:
            return json.dumps({"error": "Invalid date range"})
        
        # Calculate base price
        base_total = room.base_price * nights
        
        # Apply multipliers (placeholder for Revenue Agent integration)
        demand_multiplier = pricing_rule.demand_multiplier
        seasonal_adjustment = pricing_rule.seasonal_adjustment
        
        final_price = base_total * demand_multiplier * seasonal_adjustment
        
        return json.dumps({
            "room_id": room_id,
            "nights": nights,
            "base_price_per_night": room.base_price,
            "base_total": base_total,
            "demand_multiplier": demand_multiplier,
            "seasonal_adjustment": seasonal_adjustment,
            "final_price": final_price,
            "guest_id": guest_id
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def create_reservation_tool(guest_id: str, room_id: str, check_in: str, check_out: str, total_price: float) -> str:
    """Create reservation in State Layer."""
    try:
        # Validate room availability
        room = state_layer.get_room(room_id)
        if not room:
            return json.dumps({"error": "Room not found"})
        
        if room.status != RoomStatus.AVAILABLE:
            return json.dumps({"error": "Room not available"})
        
        # Create booking
        from ..domain.state_layer import Booking
        booking_id = f"BK{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        booking = Booking(
            booking_id=booking_id,
            guest_id=guest_id,
            room_id=room_id,
            check_in=datetime.fromisoformat(check_in),
            check_out=datetime.fromisoformat(check_out),
            status=BookingStatus.CONFIRMED,
            total_price=total_price
        )
        
        # Update room status
        state_layer.update_room_status(room_id, RoomStatus.OCCUPIED)
        
        # Store booking
        created_booking = state_layer.create_booking(booking)
        
        return json.dumps({
            "booking_id": booking_id,
            "guest_id": guest_id,
            "room_id": room_id,
            "check_in": check_in,
            "check_out": check_out,
            "total_price": total_price,
            "status": "confirmed",
            "message": "Reservation created successfully"
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def trigger_room_prep_tool(room_id: str, check_in: str, guest_id: str, special_requests: List[str] = None) -> str:
    """Trigger Operations Agent for room preparation."""
    try:
        # Placeholder for Operations Agent integration
        prep_tasks = []
        
        # Standard prep tasks
        prep_tasks.extend([
            {"task": "clean_room", "room_id": room_id, "priority": "high"},
            {"task": "check_amenities", "room_id": room_id, "priority": "medium"},
            {"task": "prepare_keycard", "room_id": room_id, "priority": "high"}
        ])
        
        # Add special requests
        if special_requests:
            for request in special_requests:
                prep_tasks.append({
                    "task": "special_request",
                    "description": request,
                    "room_id": room_id,
                    "priority": "medium"
                })
        
        return json.dumps({
            "action": "route_to_operations_agent",
            "room_id": room_id,
            "guest_id": guest_id,
            "check_in": check_in,
            "prep_tasks": prep_tasks,
            "status": "room_prep_triggered"
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


class BookingAgent:
    """
    LLM-powered Booking Agent using LangChain.
    
    Handles availability checking, reservation creation, and pricing.
    Does NOT interact directly with guests - only agent-to-agent communication.
    """
    
    def __init__(self, llm: Optional[ChatOpenAI] = None, settings: Optional[Settings] = None):
        self.settings = settings or Settings.from_env()
        self.state_layer = state_layer
        
        # Configure LLM from environment variables
        if llm:
            self.llm = llm
        else:
            self.llm = self._create_llm()
        
        # Initialize LangChain agent with tools
        self.agent = self._create_agent()
    
    def _create_llm(self) -> ChatOpenAI:
        """Create LLM instance from environment configuration."""
        logger.debug(f"Creating Booking Agent LLM with model: {self.settings.llm_model}")
        logger.debug(f"Base URL: {self.settings.llm_base_url}")
        logger.debug(f"Temperature: {self.settings.llm_temperature}")
        logger.debug(f"Max tokens: {self.settings.llm_max_tokens}")
        
        return ChatOpenAI(
            model=self.settings.llm_model,
            base_url=self.settings.llm_base_url,
            api_key=self.settings.llm_api_key,
            temperature=self.settings.llm_temperature,  # Booking Agent uses 0.3
            max_tokens=self.settings.llm_max_tokens,
            timeout=self.settings.llm_timeout_seconds,
            tool_choice="auto"  # Fix tool choice error for vLLM compatibility
        )
    
    def _create_agent(self):
        """Create LangChain agent with tools."""
        tools = [
            check_room_availability_tool,
            calculate_pricing_tool,
            create_reservation_tool,
            trigger_room_prep_tool
        ]
        
        system_prompt = """
        You are a Booking Agent for a hospitality AI system. Your roles:
        
        1. Check room availability (B1)
        2. Create reservations (B2)  
        3. Apply pricing rules (B3)
        
        Available tools:
        - check_room_availability_tool: Check available rooms for dates
        - calculate_pricing_tool: Calculate total booking price
        - create_reservation_tool: Create booking in system
        - trigger_room_prep_tool: Send tasks to Operations Agent
        
        Rules:
        - Always verify room availability before booking
        - Calculate pricing with all applicable multipliers
        - Trigger room preparation for Operations Agent
        - Escalate conflicts to Decision Agent
        - Never interact directly with guests
        
        Be precise, efficient, and follow booking rules strictly.
        """
        
        return create_agent(
            model=self.llm,
            tools=tools,
            system_prompt=system_prompt
        )
    
    def process_booking_request(self, request: BookingRequest) -> BookingResponse:
        """
        Process booking request from other agents.
        
        Args:
            request: Booking request with guest, room, dates
            
        Returns:
            BookingResponse with result and details
        """
        try:
            # Prepare messages for LLM
            messages = [
                SystemMessage(content=f"""
                You are processing a booking request.
                
                Guest ID: {request.guest_id}
                Room ID: {request.room_id}
                Room Type: {request.room_type}
                Check-in: {request.check_in}
                Check-out: {request.check_out}
                Special Requests: {request.special_requests or 'None'}
                
                Use tools to:
                1. Check availability
                2. Calculate pricing
                3. Create reservation if available
                4. Trigger room preparation
                
                Follow all booking rules and verify availability first.
                """),
                HumanMessage(content=f"Process booking request: {request}")
            ]
            
            # Execute agent
            result = self.agent.invoke({"messages": messages}, config={"callbacks": [workflow_monitor]})
            
            # Extract response
            # Extract response from messages array (modern LangChain format)
            if "messages" in result and result["messages"]:
                last_message = result["messages"][-1]
                if hasattr(last_message, 'content'):
                    output = last_message.content
                elif isinstance(last_message, dict) and 'content' in last_message:
                    output = last_message['content']
                else:
                    output = str(last_message)
            else:
                # Fallback for older format or unexpected structure
                output = result.get("output", "Booking processing failed")
            
            # Parse result for response
            if "confirmed" in output.lower():
                return BookingResponse(
                    success=True,
                    message=output,
                    action="booking_confirmed"
                )
            elif "error" in output.lower():
                return BookingResponse(
                    success=False,
                    message=output,
                    action="booking_failed"
                )
            else:
                return BookingResponse(
                    success=True,
                    message=output,
                    action="booking_processed"
                )
                
        except Exception as e:
            return BookingResponse(
                success=False,
                message=f"Booking system error: {str(e)}",
                action="booking_error"
            )


# Global booking agent instance
booking_agent = BookingAgent()
