"""
AI Guest Simulator for Automated Workflow Testing

Uses an LLM to simulate a human guest chatting with the Guest Agent.
This allows fully automated testing of conversational workflows without human input.
"""

import json
import os
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass
from datetime import datetime

# Try to use same LLM setup as the agents
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage


@dataclass
class SimulatedGuest:
    """Configuration for a simulated guest persona"""
    guest_id: str
    name: str
    persona: str  # e.g., "business_traveler", "family_vacation", "complainer"
    goal: str  # What they want to achieve
    traits: List[str]  # e.g., ["impatient", "polite", "detail_oriented"]
    max_turns: int = 10


class AIGuestSimulator:
    """
    Simulates a human guest using an LLM.
    
    Usage:
        simulator = AIGuestSimulator()
        guest = SimulatedGuest(
            guest_id="G123",
            name="Business Bob",
            persona="business_traveler",
            goal="Book a room for 2 nights starting tomorrow",
            traits=["impatient", "direct"]
        )
        
        conversation = simulator.simulate_conversation(
            guest=guest,
            agent_endpoint=your_agent_api_endpoint
        )
    """
    
    def __init__(self, model_name: Optional[str] = None):
        """Initialize with same LLM config as agents"""
        # Use HOSPITALITY_LLM environment variables like the agents do
        import os
        llm_config = {
            "model": os.getenv("HOSPITALITY_LLM_MODEL", "Qwen/Qwen2.5-1.5B-Instruct"),
            "base_url": os.getenv("HOSPITALITY_LLM_BASE_URL"),
            "api_key": os.getenv("HOSPITALITY_LLM_API_KEY")
        }
        
        self.model_name = model_name or llm_config.get("model")
        self.base_url = llm_config.get("base_url")
        self.api_key = llm_config.get("api_key")
        
        # Initialize LLM with the same configuration as agents
        self.llm = ChatOpenAI(
            model=self.model_name,
            base_url=self.base_url,
            api_key=self.api_key or "dummy-key",
            temperature=0.7
        )
        
        self.conversation_history: List[Dict[str, str]] = []
    
    def _create_system_prompt(self, guest: SimulatedGuest) -> str:
        """Create persona-based system prompt for the simulated guest"""
        return f"""You are simulating a hotel guest with the following persona:

Name: {guest.name}
Type: {guest.persona.replace('_', ' ').title()}
Personality Traits: {', '.join(guest.traits)}

Your Goal: {guest.goal}

Instructions:
- Stay in character throughout the conversation
- React naturally based on your personality traits
- If the agent asks for information you don't know, make up realistic details
- If the agent is helpful and meets your goal, thank them and end the conversation
- If the agent is unhelpful or rude, express frustration appropriately
- Keep responses conversational (1-3 sentences typically)
- Don't use formatting like "Guest:" or quotes - just respond naturally

Current conversation history:
{self._format_history()}

Respond as the guest would to the agent's last message."""
    
    def _format_history(self) -> str:
        """Format conversation history for the prompt"""
        if not self.conversation_history:
            return "This is the start of the conversation."
        
        formatted = []
        for turn in self.conversation_history:
            role = "Agent" if turn["role"] == "agent" else "You (Guest)"
            formatted.append(f"{role}: {turn['message']}")
        return "\n".join(formatted)
    
    def generate_guest_message(
        self, 
        guest: SimulatedGuest, 
        agent_message: Optional[str] = None
    ) -> str:
        """Generate a guest message based on persona and conversation history"""
        
        if agent_message:
            self.conversation_history.append({"role": "agent", "message": agent_message})
        
        system_prompt = self._create_system_prompt(guest)
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content="What do you say next? (Respond naturally as the guest)")
        ]
        
        response = self.llm.invoke(messages)
        guest_message = response.content.strip()
        
        self.conversation_history.append({"role": "guest", "message": guest_message})
        
        return guest_message
    
    def simulate_conversation(
        self,
        guest: SimulatedGuest,
        agent_callback: Callable[[str, str], str],
        initial_message: Optional[str] = None,
        verbose: bool = False
    ) -> Dict[str, Any]:
        """
        Simulate a full conversation between AI guest and your agent.
        
        Args:
            guest: SimulatedGuest configuration
            agent_callback: Function that takes (guest_id, message) and returns agent_response
            initial_message: First message from guest (optional)
            verbose: Print conversation to console
            
        Returns:
            Conversation log with success metrics
        """
        self.conversation_history = []
        
        if verbose:
            print(f"\n{'='*60}")
            print(f"Starting conversation: {guest.name} ({guest.persona})")
            print(f"Goal: {guest.goal}")
            print(f"{'='*60}\n")
        
        # Generate or use initial message
        if initial_message:
            guest_message = initial_message
            self.conversation_history.append({"role": "guest", "message": guest_message})
        else:
            guest_message = self.generate_guest_message(guest, None)
        
        if verbose:
            print(f"Guest: {guest_message}")
        
        turn = 0
        goal_achieved = False
        
        while turn < guest.max_turns:
            # Send to agent
            agent_response = agent_callback(guest.guest_id, guest_message)
            
            if verbose:
                print(f"Agent: {agent_response}")
            
            # Check if conversation should end
            if self._should_end_conversation(agent_response, guest):
                goal_achieved = True
                if verbose:
                    print("\n[Conversation ended - goal appears achieved or conversation complete]")
                break
            
            # Generate next guest message
            guest_message = self.generate_guest_message(guest, agent_response)
            
            if verbose:
                print(f"Guest: {guest_message}")
            
            turn += 1
        
        if verbose:
            print(f"\n{'='*60}")
            print(f"Conversation ended after {turn} turns")
            print(f"Goal achieved: {goal_achieved}")
            print(f"{'='*60}\n")
        
        return {
            "guest": guest,
            "conversation": self.conversation_history,
            "turns": turn,
            "goal_achieved": goal_achieved,
            "ended_by": "goal_achieved" if goal_achieved else "max_turns"
        }
    
    def _should_end_conversation(self, agent_response: str, guest: SimulatedGuest) -> bool:
        """Check if conversation should end based on agent response"""
        # Check for booking confirmation
        confirmation_indicators = [
            "confirmed", "booking successful", "reserved", "booked",
            "your reservation", "booking id", "confirmation number"
        ]
        
        # Check for service completion
        service_indicators = [
            "on its way", "will be there", "task created", 
            "housekeeping dispatched", "maintenance scheduled"
        ]
        
        # Check for escalation (human will take over)
        escalation_indicators = [
            "manager will contact you", "escalated to", "human agent",
            "supervisor will", "transferred to"
        ]
        
        response_lower = agent_response.lower()
        
        if any(ind in response_lower for ind in confirmation_indicators):
            if "book" in guest.goal.lower() or "reserv" in guest.goal.lower():
                return True
        
        if any(ind in response_lower for ind in service_indicators):
            if "service" in guest.goal.lower() or "help" in guest.goal.lower():
                return True
        
        if any(ind in response_lower for ind in escalation_indicators):
            return True
        
        return False


# Predefined guest personas for testing
PREDEFINED_GUESTS = {
    "business_booking": SimulatedGuest(
        guest_id="SIM_BUS_001",
        name="Business Bob",
        persona="business_traveler",
        goal="Book a room for 2 nights starting tomorrow, need quiet room for meetings",
        traits=["impatient", "direct", "professional"],
        max_turns=8
    ),
    
    "family_vacation": SimulatedGuest(
        guest_id="SIM_FAM_001",
        name="Family Fiona",
        persona="family_vacation",
        goal="Book a room for family of 4 (2 adults, 2 kids) for 5 nights with breakfast",
        traits=["detail_oriented", "friendly", "budget_conscious"],
        max_turns=12
    ),
    
    "complainer": SimulatedGuest(
        guest_id="SIM_COM_001",
        name="Complaining Carl",
        persona="dissatisfied_guest",
        goal="Complain about dirty room and AC not working, demand to speak to manager",
        traits=["frustrated", "demanding", "escalation_prone"],
        max_turns=6
    ),
    
    "price_shopper": SimulatedGuest(
        guest_id="SIM_PRI_001",
        name="Price Patty",
        persona="price_sensitive",
        goal="Find the cheapest room for next weekend, compare prices",
        traits=["price_conscious", "comparative", "decisive"],
        max_turns=10
    ),
    
    "service_requester": SimulatedGuest(
        guest_id="SIM_SER_001",
        name="Service Sam",
        persona="service_needy",
        goal="Request extra towels, room service for dinner, and late checkout",
        traits=["polite", "specific", "grateful"],
        max_turns=8
    ),
    
    "confused_guest": SimulatedGuest(
        guest_id="SIM_CON_001",
        name="Confused Clara",
        persona="confused_uncertain",
        goal="Not sure what to ask, needs guidance on hotel amenities and services",
        traits=["uncertain", "questioning", "appreciative"],
        max_turns=10
    )
}


def test_with_simulated_guest(
    guest_key: str,
    agent_callback: Callable[[str, str], str],
    verbose: bool = True
) -> Dict[str, Any]:
    """
    Quick test function using predefined guest personas.
    
    Usage:
        from tests.test_helpers.ai_guest_simulator import test_with_simulated_guest
        
        def my_agent_api(guest_id, message):
            # Your API call here
            return agent_response
        
        result = test_with_simulated_guest("business_booking", my_agent_api)
        assert result["goal_achieved"] is True
    """
    if guest_key not in PREDEFINED_GUESTS:
        raise ValueError(f"Unknown guest key: {guest_key}. Available: {list(PREDEFINED_GUESTS.keys())}")
    
    guest = PREDEFINED_GUESTS[guest_key]
    simulator = AIGuestSimulator()
    
    return simulator.simulate_conversation(
        guest=guest,
        agent_callback=agent_callback,
        verbose=verbose
    )


if __name__ == "__main__":
    # Example usage
    print("AI Guest Simulator - Example Usage")
    print("="*60)
    
    # Mock agent callback for testing
    def mock_agent(guest_id: str, message: str) -> str:
        """Mock agent for demonstration"""
        msg_lower = message.lower()
        
        if "book" in msg_lower or "room" in msg_lower:
            return "I'd be happy to help you book a room! Let me check availability. What dates do you need?"
        elif "price" in msg_lower or "cost" in msg_lower:
            return "Our rooms range from $120-300/night depending on type and dates. What room type are you interested in?"
        elif "tomorrow" in msg_lower or "night" in msg_lower:
            return "Great! I found availability for tomorrow. Would you like me to proceed with the booking?"
        elif "yes" in msg_lower or "sure" in msg_lower or "ok" in msg_lower:
            return "Perfect! Your booking is confirmed. Your confirmation number is BK12345. Is there anything else I can help with?"
        else:
            return "I understand. How can I assist you today?"
    
    # Test with business traveler
    result = test_with_simulated_guest(
        "business_booking",
        mock_agent,
        verbose=True
    )
    
    print("\nTest Result:")
    print(f"  Goal Achieved: {result['goal_achieved']}")
    print(f"  Turns: {result['turns']}")
    print(f"  Ended by: {result['ended_by']}")
