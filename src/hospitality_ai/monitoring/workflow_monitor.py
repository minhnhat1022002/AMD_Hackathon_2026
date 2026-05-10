"""
Real-time Agent Workflow Monitor
Provides live visualization of agent communication and tool usage.
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

from langchain_core.callbacks.base import BaseCallbackHandler

logger = logging.getLogger(__name__)


class WorkflowMonitor(BaseCallbackHandler):
    """Real-time workflow monitoring for all agents."""

    def __init__(self):
        self.workflow_events = []
        self.tool_usage = {}
        self.communication_flows = []
        self.agent_runs = []
        logger.info("WorkflowMonitor initialized")
        
    def on_llm_start(self, serialized: Dict[str, Any], prompts: List[str], **kwargs) -> None:
        """Track LLM start."""
        logger.debug(f"LLM start: {serialized.get('name', 'unknown')}")
        self.workflow_events.append({
            "timestamp": datetime.now().isoformat(),
            "event_type": "llm_start",
            "agent": serialized.get("name", "unknown")
        })

    def on_llm_end(self, response: Any, **kwargs) -> None:
        """Track LLM end."""
        logger.debug("LLM end")
        self.workflow_events.append({
            "timestamp": datetime.now().isoformat(),
            "event_type": "llm_end"
        })

    def on_chain_start(self, serialized: Dict[str, Any], inputs: Dict[str, Any], **kwargs) -> None:
        """Track chain start."""
        logger.debug(f"Chain start: {serialized.get('name', 'unknown')}")
        self.workflow_events.append({
            "timestamp": datetime.now().isoformat(),
            "event_type": "chain_start",
            "chain": serialized.get("name", "unknown")
        })

    def on_chain_end(self, outputs: Dict[str, Any], **kwargs) -> None:
        """Track chain end."""
        logger.debug("Chain end")
        self.workflow_events.append({
            "timestamp": datetime.now().isoformat(),
            "event_type": "chain_end"
        })

    def on_tool_start(self, serialized: Dict[str, Any], input_str: str, **kwargs) -> None:
        """Track tool usage with detailed agent interaction mapping."""
        tool_name = serialized.get("name", "unknown")
        logger.debug(f"Tool start: {tool_name}")
        
        # Track tool usage
        if tool_name not in self.tool_usage:
            self.tool_usage[tool_name] = {"count": 0, "agents": set()}
        
        self.tool_usage[tool_name]["count"] += 1
        
        # Parse input for agent interaction details
        from_agent = self._determine_source_agent(tool_name, kwargs)
        to_agent = self._map_tool_to_agent(tool_name)
        guest_id = "unknown"
        intent = "unknown"
        details = f"Tool call: {tool_name}"
        
        try:
            # Try to parse JSON input
            if input_str and input_str.strip().startswith('{'):
                input_data = json.loads(input_str)
                guest_id = input_data.get("guest_id", "unknown")
                intent = input_data.get("intent", "unknown")
                details = f"{intent} for {guest_id}" if intent != "unknown" and guest_id != "unknown" else f"Tool call: {tool_name}"
        except (json.JSONDecodeError, Exception):
            # Use raw input for non-JSON
            details = f"Tool call: {tool_name}"
        
        # Track communication flow for routing tools
        if "route" in tool_name or "orchestrator" in tool_name:
            self.communication_flows.append({
                "timestamp": datetime.now().isoformat(),
                "tool": tool_name,
                "from": from_agent,
                "to": to_agent,
                "guest_id": guest_id,
                "intent": intent,
                "input": input_str[:200] + "..." if len(input_str) > 200 else input_str
            })
        
        self.workflow_events.append({
            "timestamp": datetime.now().isoformat(),
            "event_type": "tool_start",
            "tool": tool_name,
            "from": from_agent,
            "to": to_agent,
            "guest_id": guest_id,
            "intent": intent,
            "input": input_str[:100] if input_str else "",
            "details": details
        })
    
    def on_tool_end(self, serialized: Dict[str, Any], output: str, **kwargs) -> None:
        """Track tool completion."""
        tool_name = serialized.get("name", "unknown")
        logger.debug(f"Tool end: {tool_name}")

        self.workflow_events.append({
            "timestamp": datetime.now().isoformat(),
            "event_type": "tool_end",
            "tool": tool_name
        })

    def _determine_source_agent(self, tool_name: str, kwargs: Dict[str, Any]) -> str:
        """Determine which agent is calling the tool."""
        # Try to get agent name from kwargs or context
        if "agent_name" in kwargs:
            return kwargs["agent_name"]
        
        # Map tool names to likely source agents
        tool_to_source = {
            "route_to_orchestrator_tool": "guest_agent",
            "check_availability_tool": "guest_agent", 
            "get_guest_profile_tool": "guest_agent",
            "check_room_availability_tool": "booking_agent",
            "calculate_pricing_tool": "booking_agent",
            "create_reservation_tool": "booking_agent",
            "trigger_room_prep_tool": "booking_agent",
            "process_maintenance_request": "operations_agent",
            "assign_housekeeping_task": "operations_agent",
            "handle_service_complaint": "operations_agent",
            "resolve_booking_conflict": "decision_agent",
            "escalate_to_human": "decision_agent",
            "calculate_dynamic_pricing": "revenue_agent",
            "apply_seasonal_rates": "revenue_agent"
        }
        
        return tool_to_source.get(tool_name, "unknown")
    
    def _map_tool_to_agent(self, tool_name: str) -> str:
        """Map tool names to target agents."""
        tool_to_agent = {
            "route_to_orchestrator_tool": "orchestrator",
            "check_availability_tool": "guest_agent",
            "get_guest_profile_tool": "guest_agent",
            "check_room_availability_tool": "booking_agent",
            "calculate_pricing_tool": "booking_agent", 
            "create_reservation_tool": "booking_agent",
            "trigger_room_prep_tool": "operations_agent",
            "process_maintenance_request": "operations_agent",
            "assign_housekeeping_task": "operations_agent",
            "handle_service_complaint": "operations_agent",
            "resolve_booking_conflict": "decision_agent",
            "escalate_to_human": "decision_agent",
            "calculate_dynamic_pricing": "revenue_agent",
            "apply_seasonal_rates": "revenue_agent"
        }
        
        return tool_to_agent.get(tool_name, "unknown")

    def get_workflow_summary(self) -> Dict[str, Any]:
        """Get current workflow summary."""
        summary = {
            "total_events": len(self.workflow_events),
            "active_tools": {k: v["count"] for k, v in self.tool_usage.items()},
            "communication_flows": self.communication_flows[-10:],  # Last 10 flows
            "recent_events": self.workflow_events[-5:]  # Last 5 events for debugging
        }
        logger.debug(f"Workflow summary requested: {len(self.workflow_events)} events")
        return summary


# Global monitor instance
workflow_monitor = WorkflowMonitor()
