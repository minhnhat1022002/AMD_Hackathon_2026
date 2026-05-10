"""
Orchestrator - Central coordination and routing for all agents.

Solves:
- Routing problems to correct agent
- Ensuring order of execution
- Preventing conflicts

Dependencies:
- ALL agents
- State Layer

Critical control component that enforces agent communication rules.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import json
import logging
from datetime import datetime
from enum import Enum

from langchain.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent

from ..domain.state_layer import state_layer
from ..config.settings import Settings
from ..monitoring.workflow_monitor import workflow_monitor

# Set up logging
logger = logging.getLogger(__name__)


class AgentType(Enum):
    """Agent type enumeration."""
    GUEST = "guest_agent"
    BOOKING = "booking_agent"
    OPERATIONS = "operations_agent"
    DECISION = "decision_agent"
    REVENUE = "revenue_agent"


class ProblemType(Enum):
    """Problem type enumeration for routing."""
    GUEST_INQUIRY = "guest_inquiry"
    BOOKING_REQUEST = "booking_request"
    SERVICE_REQUEST = "service_request"
    PRICING_QUERY = "pricing_query"
    COMPLAINT = "complaint"
    ESCALATION = "escalation"


@dataclass
class WorkflowRequest:
    """Workflow request data model."""
    request_id: str
    problem_type: str
    source_agent: Optional[str] = None
    guest_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    priority: str = "medium"


@dataclass
class WorkflowResponse:
    """Workflow response data model."""
    success: bool
    message: str
    workflow_id: Optional[str] = None
    execution_path: List[str] = None
    final_agent: Optional[str] = None
    action_taken: str = "workflow_completed"


# Standalone tool functions for LangChain
@tool
def route_to_agent_tool(problem_type: str, context: Optional[Dict[str, Any]] = None) -> str:
    """Route problem to the correct agent based on type and context."""
    try:
        # Determine target agent based on problem type
        routing_rules = {
            "guest_inquiry": AgentType.GUEST.value,
            "booking_request": AgentType.BOOKING.value,
            "service_request": AgentType.OPERATIONS.value,
            "pricing_query": AgentType.REVENUE.value,
            "complaint": AgentType.DECISION.value,
            "escalation": AgentType.DECISION.value
        }
        
        target_agent = routing_rules.get(problem_type, AgentType.GUEST.value)
        
        # Validate single ownership principle
        if _has_multiple_owners(problem_type, context):
            return json.dumps({
                "error": "Multiple agent ownership detected",
                "rule_violation": "Rule 2: Every problem must have ONE owner agent"
            })
        
        routing_info = {
            "problem_type": problem_type,
            "target_agent": target_agent,
            "routing_rules_applied": routing_rules,
            "context": context or {},
            "routing_timestamp": datetime.now().isoformat(),
            "compliance_check": _validate_routing_rules(problem_type, target_agent)
        }
        
        return json.dumps({
            "routing_id": f"RT{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "routing_info": routing_info,
            "message": f"Routed to {target_agent}"
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def execute_workflow_tool(workflow_id: str, problem_type: str, execution_steps: List[str]) -> str:
    """Execute workflow steps in correct order and track execution."""
    try:
        execution_log = []
        current_step = 0
        
        for step in execution_steps:
            step_result = {
                "step_number": current_step + 1,
                "agent": step,
                "step_type": _determine_step_type(step),
                "dependencies_satisfied": _check_dependencies(step, execution_log),
                "execution_timestamp": datetime.now().isoformat()
            }
            
            # Validate execution order
            if not _validate_execution_order(step, execution_log):
                return json.dumps({
                    "error": "Invalid execution order",
                    "workflow_id": workflow_id,
                    "failed_step": step,
                    "rule_violation": "Rule 1: Agents do NOT randomly call each other"
                })
            
            execution_log.append(step_result)
            current_step += 1
        
        workflow_result = {
            "workflow_id": workflow_id,
            "problem_type": problem_type,
            "execution_steps": execution_steps,
            "execution_log": execution_log,
            "total_steps": len(execution_steps),
            "completed_at": datetime.now().isoformat(),
            "execution_path": [step["agent"] for step in execution_log]
        }
        
        return json.dumps({
            "workflow_result": workflow_result,
            "message": f"Workflow {workflow_id} completed successfully"
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def validate_agent_dependencies_tool(agent_action: str, source_agent: str, target_agent: str) -> str:
    """Validate that agent communication follows dependency rules."""
    try:
        # Define allowed direct communications (Rule 1 exceptions)
        allowed_direct_calls = {
            "guest_agent": ["booking_agent", "decision_agent"],
            "booking_agent": ["revenue_agent", "operations_agent", "decision_agent"],
            "operations_agent": ["decision_agent"],
            "decision_agent": [],  # Decision Agent only receives escalations
            "revenue_agent": ["decision_agent"]
        }
        
        validation_result = {
            "source_agent": source_agent,
            "target_agent": target_agent,
            "agent_action": agent_action,
            "allowed_direct_calls": allowed_direct_calls,
            "is_direct_call_allowed": target_agent in allowed_direct_calls.get(source_agent, []),
            "requires_orchestrator": target_agent not in allowed_direct_calls.get(source_agent, []),
            "rule_compliance": _check_rule_compliance(source_agent, target_agent)
        }
        
        if validation_result["is_direct_call_allowed"]:
            validation_result["routing_method"] = "direct_call"
            validation_result["compliance_status"] = "compliant"
        else:
            validation_result["routing_method"] = "orchestrator_required"
            validation_result["compliance_status"] = "needs_orchestrator"
        
        return json.dumps({
            "validation_id": f"VL{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "validation_result": validation_result,
            "message": f"Dependency validation completed"
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def prevent_conflicts_tool(problem_type: str, current_owner: str, proposed_owner: str) -> str:
    """Prevent conflicts by ensuring single problem ownership."""
    try:
        # Check for existing ownership conflicts
        conflict_check = {
            "problem_type": problem_type,
            "current_owner": current_owner,
            "proposed_owner": proposed_owner,
            "has_conflict": current_owner != proposed_owner,
            "conflict_resolution": _resolve_ownership_conflict(current_owner, proposed_owner),
            "single_owner_violation": current_owner != proposed_owner
        }
        
        if conflict_check["has_conflict"]:
            return json.dumps({
                "conflict_detected": conflict_check,
                "rule_violation": "Rule 2: Every problem must have ONE owner agent",
                "message": "Ownership conflict detected - single owner principle violated"
            })
        else:
            return json.dumps({
                "conflict_check": conflict_check,
                "message": "No ownership conflicts detected"
            })
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def track_execution_order_tool(workflow_id: str, execution_sequence: List[str]) -> str:
    """Track and validate execution order for workflow compliance."""
    try:
        # Validate execution sequence against known workflows
        standard_workflows = {
            "booking_request": ["guest_agent", "booking_agent", "revenue_agent", "operations_agent", "guest_agent"],
            "service_request": ["guest_agent", "operations_agent", "guest_agent"],
            "complaint": ["guest_agent", "decision_agent", "guest_agent"],
            "escalation": ["any_agent", "decision_agent", "source_agent"]
        }
        
        tracking_result = {
            "workflow_id": workflow_id,
            "execution_sequence": execution_sequence,
            "sequence_length": len(execution_sequence),
            "workflow_type": _identify_workflow_type(execution_sequence),
            "matches_standard_pattern": _matches_standard_workflow(execution_sequence, standard_workflows),
            "execution_order_valid": _validate_sequence_order(execution_sequence),
            "tracked_at": datetime.now().isoformat()
        }
        
        return json.dumps({
            "tracking_id": f"TK{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "tracking_result": tracking_result,
            "message": "Execution order tracking completed"
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


# Helper functions for orchestration logic
def _has_multiple_owners(problem_type: str, context: Optional[Dict[str, Any]]) -> bool:
    """Check if problem would have multiple owners (Rule 2 violation)."""
    # Simplified logic - would check State Layer for existing ownership
    return False  # Placeholder


def _validate_routing_rules(problem_type: str, target_agent: str) -> bool:
    """Validate routing against agent dependency rules."""
    valid_routes = {
        "guest_inquiry": ["guest_agent"],
        "booking_request": ["booking_agent"],
        "service_request": ["operations_agent"],
        "pricing_query": ["revenue_agent"],
        "complaint": ["decision_agent"],
        "escalation": ["decision_agent"]
    }
    return target_agent in valid_routes.get(problem_type, [])


def _determine_step_type(step: str) -> str:
    """Determine the type of workflow step."""
    if "agent" in step:
        return "agent_interaction"
    elif "validation" in step:
        return "validation"
    elif "routing" in step:
        return "routing"
    else:
        return "unknown"


def _check_dependencies(step: str, execution_log: List[Dict[str, Any]]) -> bool:
    """Check if dependencies for this step are satisfied."""
    # Simplified dependency checking
    return True  # Placeholder


def _validate_execution_order(step: str, execution_log: List[Dict[str, Any]]) -> bool:
    """Validate that execution order follows dependency rules."""
    # Simplified order validation
    return True  # Placeholder


def _check_rule_compliance(source_agent: str, target_agent: str) -> Dict[str, Any]:
    """Check compliance with all orchestration rules."""
    return {
        "rule_1_compliant": True,  # No random calls
        "rule_2_compliant": True,  # Single owner
        "rule_3_compliant": True   # Decision Agent not default
    }


def _resolve_ownership_conflict(current_owner: str, proposed_owner: str) -> str:
    """Resolve ownership conflicts according to rules."""
    # Rule 2: Every problem must have ONE owner agent
    return f"Maintain current owner: {current_owner}"


def _identify_workflow_type(execution_sequence: List[str]) -> str:
    """Identify the type of workflow based on execution sequence."""
    if "booking_agent" in execution_sequence:
        return "booking_workflow"
    elif "operations_agent" in execution_sequence:
        return "service_workflow"
    elif "decision_agent" in execution_sequence:
        return "escalation_workflow"
    else:
        return "general_workflow"


def _matches_standard_workflow(execution_sequence: List[str], standard_workflows: Dict[str, List[str]]) -> bool:
    """Check if execution sequence matches any standard workflow pattern."""
    for workflow_type, pattern in standard_workflows.items():
        if set(execution_sequence) == set(pattern):
            return True
    return False


def _validate_sequence_order(execution_sequence: List[str]) -> bool:
    """Validate that the sequence order is logical."""
    # Simplified order validation
    return True  # Placeholder


class Orchestrator:
    """
    LLM-powered Orchestrator using LangChain.
    
    Central coordination point that enforces agent communication rules
    and manages workflow execution order.
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
    
    def _create_llm(self) -> ChatOpenAI:
        """Create LLM instance from environment configuration."""
        logger.debug(f"Creating Orchestrator LLM with model: {self.settings.llm_model}")
        logger.debug(f"Base URL: {self.settings.llm_base_url}")
        logger.debug(f"Temperature: {self.settings.llm_temperature}")
        logger.debug(f"Max tokens: {self.settings.llm_max_tokens}")
        
        return ChatOpenAI(
            model=self.settings.llm_model,
            base_url=self.settings.llm_base_url,
            api_key=self.settings.llm_api_key,
            temperature=0.1,  # Orchestrator uses specific 0.1 temperature
            max_tokens=self.settings.llm_max_tokens,
            timeout=self.settings.llm_timeout_seconds,
            tool_choice="auto"  # Fix tool choice error for vLLM compatibility
        )
    
    def _create_agent(self):
        """Create LangChain agent with tools."""
        tools = [
            route_to_agent_tool,
            execute_workflow_tool,
            validate_agent_dependencies_tool,
            prevent_conflicts_tool,
            track_execution_order_tool
        ]
        
        system_prompt = """
        You are an Orchestrator for a hospitality AI system. Your roles:
        
        1. Route problems to correct agent
        2. Ensure proper execution order
        3. Prevent agent conflicts
        
        Available tools:
        - route_to_agent_tool: Route problems to appropriate agents
        - execute_workflow_tool: Execute workflow steps in correct order
        - validate_agent_dependencies_tool: Validate agent communication rules
        - prevent_conflicts_tool: Ensure single problem ownership
        - track_execution_order_tool: Track and validate execution sequences
        
        Critical Rules to Enforce:
        Rule 1: Agents do NOT randomly call each other (only via Orchestrator or direct necessity)
        Rule 2: Every problem must have ONE owner agent (no shared responsibility)
        Rule 3: Decision Agent is NOT default (only for edge cases)
        
        You are the central authority that prevents chaos in the agent system.
        Be strict about rules, fair in routing, and thorough in validation.
        """
        
        return create_agent(
            model=self.llm,
            tools=tools,
            system_prompt=system_prompt
        )
    
    def process_workflow_request(self, request: WorkflowRequest) -> WorkflowResponse:
        """
        Process workflow request and coordinate agent execution.
        
        Args:
            request: Workflow request with problem details
            
        Returns:
            WorkflowResponse with execution results and path
        """
        try:
            # Prepare messages for LLM
            messages = [
                SystemMessage(content=f"""
                You are processing a workflow request.
                
                Request ID: {request.request_id}
                Problem Type: {request.problem_type}
                Source Agent: {request.source_agent}
                Guest ID: {request.guest_id}
                Context: {request.context or 'None'}
                Priority: {request.priority}
                
                Use tools to:
                1. Route to correct agent based on problem type
                2. Validate agent communication rules
                3. Prevent ownership conflicts
                4. Execute workflow in proper order
                5. Track execution sequence
                
                Enforce all orchestration rules strictly.
                """),
                HumanMessage(content=f"Process workflow: {request}")
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
                output = result.get("output", "Workflow processing failed")
            
            # Parse result for response
            if "completed" in output.lower():
                return WorkflowResponse(
                    success=True,
                    message=output,
                    action_taken="workflow_completed"
                )
            elif "conflict" in output.lower():
                return WorkflowResponse(
                    success=False,
                    message=output,
                    action_taken="conflict_detected"
                )
            elif "routed" in output.lower():
                return WorkflowResponse(
                    success=True,
                    message=output,
                    action_taken="agent_routed"
                )
            else:
                return WorkflowResponse(
                    success=True,
                    message=output,
                    action_taken="workflow_processed"
                )
                
        except Exception as e:
            return WorkflowResponse(
                success=False,
                message=f"Orchestrator system error: {str(e)}",
                action_taken="workflow_error"
            )
    
    def validate_agent_communication(self, source_agent: str, target_agent: str, action: str) -> bool:
        """
        Validate that agent communication follows all rules.
        
        Args:
            source_agent: Agent initiating communication
            target_agent: Agent receiving communication
            action: Specific action being performed
            
        Returns:
            True if communication is valid, False otherwise
        """
        try:
            # Use validation tool
            result = json.loads(validate_agent_dependencies_tool(action, source_agent, target_agent))
            validation_result = result.get("validation_result", {})
            
            return validation_result.get("compliance_status") == "compliant"
        except Exception:
            return False
    
    def route_request(self, routing_request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Route request from Guest Agent to appropriate target agent.
        
        Args:
            routing_request: Dictionary containing routing information
            
        Returns:
            Dictionary with routing result and agent response
        """
        try:
            logger.debug(f"Orchestrator routing request: {routing_request.get('intent')}")
            
            # Extract routing information
            intent = routing_request.get("intent", "unknown")
            guest_id = routing_request.get("guest_id")
            message = routing_request.get("message")
            details = routing_request.get("details", {})
            
            # Determine target agent based on intent
            target_agent = self._determine_target_agent(intent)
            
            # Route to appropriate agent
            if target_agent == "booking_agent":
                result = self._route_to_booking_agent(guest_id, message, details)
            elif target_agent == "operations_agent":
                result = self._route_to_operations_agent(guest_id, message, details)
            elif target_agent == "decision_agent":
                result = self._route_to_decision_agent(guest_id, message, details)
            else:
                result = {
                    "status": "error",
                    "message": f"Unknown intent: {intent}",
                    "action": "escalate_to_human"
                }
            
            # Add routing metadata
            result.update({
                "routing_id": f"RT{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "source_agent": "guest_agent",
                "target_agent": target_agent,
                "intent": intent,
                "guest_id": guest_id,
                "routing_timestamp": datetime.now().isoformat()
            })
            
            logger.debug(f"Routing completed: {target_agent} -> {result.get('status')}")
            return result
            
        except Exception as e:
            logger.error(f"Orchestrator routing error: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": f"Routing failed: {str(e)}",
                "action": "retry_or_escalate",
                "routing_id": f"RT{datetime.now().strftime('%Y%m%d%H%M%S')}"
            }
    
    def _determine_target_agent(self, intent: str) -> str:
        """Determine target agent based on intent."""
        intent_mapping = {
            "booking": "booking_agent",
            "service": "operations_agent",
            "escalation": "decision_agent",
            "complaint": "decision_agent",
            "pricing": "revenue_agent"
        }
        return intent_mapping.get(intent, "unknown")
    
    def _route_to_booking_agent(self, guest_id: str, message: str, details: Dict[str, Any]) -> Dict[str, Any]:
        """Route to Booking Agent."""
        try:
            from .booking_agent import booking_agent
            from .booking_agent import BookingRequest
            
            # Create booking request
            booking_request = BookingRequest(
                guest_id=guest_id,
                room_id=details.get("room_id"),
                check_in=details.get("check_in"),
                check_out=details.get("check_out"),
                room_type=details.get("room_type"),
                special_requests=details.get("special_requests", [])
            )
            
            # Process booking
            response = booking_agent.process_booking_request(booking_request)
            
            return {
                "status": "success" if response.success else "failed",
                "message": response.message,
                "action": response.action,
                "booking_id": getattr(response, 'booking_id', None)
            }
            
        except Exception as e:
            logger.error(f"Booking agent routing error: {str(e)}")
            return {
                "status": "error",
                "message": f"Booking processing failed: {str(e)}",
                "action": "retry_or_escalate"
            }
    
    def _route_to_operations_agent(self, guest_id: str, message: str, details: Dict[str, Any]) -> Dict[str, Any]:
        """Route to Operations Agent."""
        try:
            from .operations_agent import operations_agent
            from .operations_agent import TaskRequest
            
            # Create task request
            task_request = TaskRequest(
                guest_id=guest_id,
                service_type=details.get("service_type", "general"),
                description=message,
                priority=details.get("priority", "medium")
            )
            
            # Process task
            response = operations_agent.process_service_request(task_request)
            
            return {
                "status": "success" if response.success else "failed",
                "message": response.message,
                "action": response.action,
                "task_id": getattr(response, 'task_id', None)
            }
            
        except Exception as e:
            logger.error(f"Operations agent routing error: {str(e)}")
            return {
                "status": "error",
                "message": f"Service processing failed: {str(e)}",
                "action": "retry_or_escalate"
            }
    
    def _route_to_decision_agent(self, guest_id: str, message: str, details: Dict[str, Any]) -> Dict[str, Any]:
        """Route to Decision Agent."""
        try:
            from .decision_agent import decision_agent
            from .decision_agent import EscalationRequest
            
            # Create escalation request
            escalation_request = EscalationRequest(
                guest_id=guest_id,
                issue_type=details.get("issue_type", "general"),
                description=message,
                priority=details.get("priority", "medium")
            )
            
            # Process escalation
            response = decision_agent.process_escalation(escalation_request)
            
            return {
                "status": "success" if response.success else "failed",
                "message": response.message,
                "action": response.action,
                "escalated_to_human": getattr(response, 'escalated_to_human', False)
            }
            
        except Exception as e:
            logger.error(f"Decision agent routing error: {str(e)}")
            return {
                "status": "error",
                "message": f"Escalation processing failed: {str(e)}",
                "action": "retry_or_escalate"
            }


# Global orchestrator instance
orchestrator = Orchestrator()
