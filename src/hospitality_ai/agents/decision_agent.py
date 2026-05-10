"""
Decision Agent - Handles edge cases, policy enforcement, and human escalation.

Solves:
D1: Edge cases
D2: Policy enforcement
D3: Human escalation

Dependencies:
- ALL agents (it's the fallback brain)
- Rules/Knowledge Base
- Humans (staff input)

Critical system component - safety net for all other agents.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import json
import logging
from datetime import datetime

from langchain.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent

from ..domain.state_layer import state_layer
from ..config.settings import Settings
from ..monitoring.workflow_monitor import workflow_monitor

# Set up logging
logger = logging.getLogger(__name__)


@dataclass
class EscalationRequest:
    """Escalation request data model."""
    agent_id: str
    issue_type: str
    description: str
    severity: str = "medium"
    context: Optional[Dict[str, Any]] = None
    requires_human: bool = False


@dataclass
class DecisionResponse:
    """Decision response data model."""
    success: bool
    message: str
    decision_id: Optional[str] = None
    action_taken: str = "decision_made"
    escalated_to_human: bool = False
    policy_applied: Optional[str] = None


# Standalone tool functions for LangChain
@tool
def evaluate_edge_case_tool(agent_id: str, issue_type: str, description: str, context: Optional[Dict[str, Any]] = None) -> str:
    """Evaluate complex edge cases beyond standard agent capabilities."""
    try:
        # Analyze the edge case
        edge_analysis = {
            "agent_id": agent_id,
            "issue_type": issue_type,
            "description": description,
            "context": context or {},
            "complexity_score": _calculate_complexity(issue_type, description),
            "requires_human": _requires_human_intervention(issue_type, description),
            "recommended_action": _recommend_action(issue_type, description)
        }
        
        return json.dumps({
            "edge_case_id": f"EC{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "analysis": edge_analysis,
            "message": "Edge case analyzed successfully"
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def enforce_policy_tool(policy_type: str, agent_action: str, context: Optional[Dict[str, Any]] = None) -> str:
    """Enforce hotel policies and validate agent actions."""
    try:
        # Get relevant policy (placeholder for policy knowledge base)
        policy_rules = _get_policy_rules(policy_type)
        
        validation_result = {
            "policy_type": policy_type,
            "agent_action": agent_action,
            "context": context or {},
            "policy_rules": policy_rules,
            "compliance_check": _check_compliance(agent_action, policy_rules),
            "violations": _identify_violations(agent_action, policy_rules),
            "required_correction": _determine_correction(agent_action, policy_rules)
        }
        
        return json.dumps({
            "policy_enforcement_id": f"PE{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "validation_result": validation_result,
            "message": "Policy enforcement completed"
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def escalate_to_human_tool(escalation_request: str, severity: str, target_role: str, details: Optional[Dict[str, Any]] = None) -> str:
    """Escalate issues to appropriate human staff."""
    try:
        # Parse escalation request
        escalation_data = json.loads(escalation_request)
        
        # Determine escalation target based on severity and role
        escalation_target = _determine_escalation_target(severity, target_role)
        
        escalation_record = {
            "escalation_id": f"ES{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "source_agent": escalation_data.get("agent_id"),
            "issue_type": escalation_data.get("issue_type"),
            "severity": severity,
            "target_role": escalation_target,
            "target_department": _map_role_to_department(escalation_target),
            "details": details or escalation_data.get("context"),
            "escalated_at": datetime.now().isoformat(),
            "status": "escalated_to_human"
        }
        
        return json.dumps({
            "escalation_record": escalation_record,
            "message": f"Escalated to {escalation_target} - {escalation_target}",
            "target_contact_info": _get_contact_info(escalation_target)
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def get_policy_rules_tool(policy_type: Optional[str] = None) -> str:
    """Retrieve policy rules from knowledge base."""
    try:
        # Placeholder policy knowledge base (would be database in real system)
        policy_database = {
            "booking_policies": {
                "max_occupancy": 4,
                "cancellation_window": 24,  # hours
                "no_show_penalty": 0.5,
                "overbooking_policy": "strict"
            },
            "pricing_policies": {
                "rate_change_notice": 72,  # hours
                "discount_authority": ["manager", "revenue_team"],
                "max_discount_percentage": 15
            },
            "service_policies": {
                "response_time_sla": 30,  # minutes
                "escalation_threshold": 2,  # failed attempts
                "compensation_limits": {"room_issue": 50, "service_failure": 25}
            },
            "safety_policies": {
                "emergency_response_time": 5,  # minutes
                "safety_incident_escalation": "immediate",
                "guest_safety_priority": "highest"
            }
        }
        
        if policy_type:
            return json.dumps({
                "policy_type": policy_type,
                "rules": policy_database.get(policy_type, {}),
                "message": f"Policy rules retrieved for {policy_type}"
            })
        else:
            return json.dumps({
                "all_policies": policy_database,
                "message": "All policy rules retrieved"
            })
    except Exception as e:
        return json.dumps({"error": str(e)})


# Helper functions for decision logic
def _calculate_complexity(issue_type: str, description: str) -> float:
    """Calculate complexity score for edge case analysis."""
    complexity_keywords = {
        "safety": 10.0,
        "legal": 9.0,
        "multiple_guests": 7.0,
        "system_failure": 8.0,
        "policy_violation": 6.0,
        "financial_dispute": 8.5,
        "service_failure": 7.5
    }
    
    score = 3.0  # baseline complexity
    
    # Add complexity based on keywords
    for keyword, value in complexity_keywords.items():
        if keyword.lower() in description.lower():
            score = max(score, value)
    
    # Add length factor
    if len(description) > 200:
        score += 1.0
    
    return min(score, 10.0)


def _requires_human_intervention(issue_type: str, description: str) -> bool:
    """Determine if human intervention is required."""
    human_triggers = [
        "safety", "legal", "emergency", "police", "medical",
        "violence", "harassment", "theft", "security", "fraud"
    ]
    
    return any(trigger.lower() in description.lower() for trigger in human_triggers)


def _recommend_action(issue_type: str, description: str) -> str:
    """Recommend action for edge case resolution."""
    if "safety" in description.lower():
        return "immediate_escalation_to_management"
    elif "legal" in description.lower():
        return "escalate_to_legal_team"
    elif "system_failure" in issue_type.lower():
        return "escalate_to_technical_team"
    elif "policy_violation" in issue_type.lower():
        return "enforce_policy_and_notify_manager"
    else:
        return "attempt_automated_resolution_first"


def _get_policy_rules(policy_type: str) -> Dict[str, Any]:
    """Get policy rules for specific policy type."""
    # This would connect to a real policy database
    placeholder_rules = {
        "booking_policies": {
            "max_occupancy": 4,
            "cancellation_window": 24,
            "no_show_penalty": 0.5
        }
    }
    return placeholder_rules.get(policy_type, {})


def _check_compliance(agent_action: str, policy_rules: Dict[str, Any]) -> Dict[str, Any]:
    """Check if agent action complies with policies."""
    return {
        "compliant": True,  # Placeholder - would have actual logic
        "violations": [],
        "warnings": []
    }


def _identify_violations(agent_action: str, policy_rules: Dict[str, Any]) -> List[str]:
    """Identify policy violations in agent action."""
    return []  # Placeholder - would have actual violation detection


def _determine_correction(agent_action: str, policy_rules: Dict[str, Any]) -> str:
    """Determine required correction for policy violation."""
    return "no_correction_needed"  # Placeholder


def _determine_escalation_target(severity: str, target_role: str) -> str:
    """Determine appropriate escalation target."""
    if severity.lower() == "high":
        return "manager"
    elif severity.lower() == "critical":
        return "director"
    else:
        return target_role or "front_desk_supervisor"


def _map_role_to_department(role: str) -> str:
    """Map role to department for escalation."""
    role_mapping = {
        "manager": "operations",
        "director": "executive",
        "front_desk_supervisor": "front_desk",
        "revenue_team": "revenue"
    }
    return role_mapping.get(role.lower(), "general_management")


def _get_contact_info(role: str) -> Dict[str, str]:
    """Get contact information for escalation target."""
    contact_info = {
        "manager": {"phone": "ext-2001", "email": "manager@hotel.com"},
        "director": {"phone": "ext-3001", "email": "director@hotel.com"},
        "front_desk": {"phone": "ext-1001", "email": "frontdesk@hotel.com"},
        "revenue": {"phone": "ext-4001", "email": "revenue@hotel.com"}
    }
    return contact_info.get(role.lower(), {"phone": "ext-0", "email": "info@hotel.com"})


class DecisionAgent:
    """
    LLM-powered Decision Agent using LangChain.
    
    Handles edge cases, policy enforcement, and human escalation.
    Critical fallback brain for all other agents.
    """
    
    def __init__(self, llm: Optional[ChatOpenAI] = None, settings: Optional[Settings] = None):
        self.settings = settings or Settings.from_env()
        
        # Configure LLM from environment variables
        if llm:
            self.llm = llm
        else:
            self.llm = self._create_llm()
        
        # Initialize LangChain agent with tools
    
    def _create_llm(self) -> ChatOpenAI:
        """Create LLM instance from environment configuration."""
        logger.debug(f"Creating Decision Agent LLM with model: {self.settings.llm_model}")
        logger.debug(f"Base URL: {self.settings.llm_base_url}")
        logger.debug(f"Temperature: {self.settings.llm_temperature}")
        logger.debug(f"Max tokens: {self.settings.llm_max_tokens}")
        
        return ChatOpenAI(
            model=self.settings.llm_model,
            base_url=self.settings.llm_base_url,
            api_key=self.settings.llm_api_key,
            temperature=0.2,  # Decision Agent uses specific 0.2 temperature
            max_tokens=self.settings.llm_max_tokens,
            timeout=self.settings.llm_timeout_seconds,
            tool_choice="auto"  # Fix tool choice error for vLLM compatibility
        )
    
    def _create_agent(self):
        """Create LangChain agent with tools."""
        tools = [
            evaluate_edge_case_tool,
            enforce_policy_tool,
            escalate_to_human_tool,
            get_policy_rules_tool
        ]
        
        system_prompt = """
        You are a Decision Agent for a hospitality AI system. Your roles:
        
        1. Edge cases (D1) - Handle complex situations beyond standard rules
        2. Policy enforcement (D2) - Apply hotel policies consistently  
        3. Human escalation (D3) - Determine when human intervention needed
        
        Available tools:
        - evaluate_edge_case_tool: Analyze complex edge cases
        - enforce_policy_tool: Enforce hotel policies and rules
        - escalate_to_human_tool: Escalate issues to appropriate staff
        - get_policy_rules_tool: Retrieve policy knowledge base
        
        Rules:
        - Be the fallback brain for all other agents
        - Prioritize guest safety and system integrity
        - Apply policies fairly and consistently
        - Escalate when automation fails or human judgment needed
        - Document all decisions for learning and improvement
        
        You have final authority on complex issues and policy violations.
        Be thorough, fair, and document your reasoning.
        """
        
        return create_agent(
            model=self.llm,
            tools=tools,
            system_prompt=system_prompt
        )
    
    def process_escalation(self, request: EscalationRequest) -> DecisionResponse:
        """
        Process escalation request from other agents.
        
        Args:
            request: Escalation request with details
            
        Returns:
            DecisionResponse with resolution and action taken
        """
        try:
            # Prepare messages for LLM
            messages = [
                SystemMessage(content=f"""
                You are processing an escalation request.
                
                Source Agent: {request.agent_id}
                Issue Type: {request.issue_type}
                Description: {request.description}
                Severity: {request.severity}
                Context: {request.context or 'None'}
                Requires Human: {request.requires_human}
                
                Use tools to:
                1. Evaluate the edge case complexity
                2. Apply relevant policies
                3. Determine if human escalation is needed
                4. Route to appropriate staff if necessary
                
                Consider all factors: guest safety, system integrity, policy compliance.
                """),
                HumanMessage(content=f"Process escalation: {request}")
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
                output = result.get("output", "Escalation processing failed")
            
            # Parse result for response
            if "escalated" in output.lower():
                return DecisionResponse(
                    success=True,
                    message=output,
                    escalated_to_human=True,
                    action_taken="escalated_to_human"
                )
            elif "resolved" in output.lower():
                return DecisionResponse(
                    success=True,
                    message=output,
                    action_taken="resolved_automatically"
                )
            elif "policy" in output.lower():
                return DecisionResponse(
                    success=True,
                    message=output,
                    action_taken="policy_enforced"
                )
            else:
                return DecisionResponse(
                    success=True,
                    message=output,
                    action_taken="decision_processed"
                )
                
        except Exception as e:
            return DecisionResponse(
                success=False,
                message=f"Decision system error: {str(e)}",
                action_taken="decision_error"
            )
    
    def enforce_policy(self, agent_action: str, policy_type: str, context: Optional[Dict[str, Any]] = None) -> DecisionResponse:
        """
        Enforce specific policy on agent action.
        
        Args:
            agent_action: Action taken by another agent
            policy_type: Type of policy to enforce
            context: Additional context for decision
            
        Returns:
            DecisionResponse with policy enforcement result
        """
        try:
            # Prepare messages for LLM
            messages = [
                SystemMessage(content=f"""
                You are enforcing hotel policy.
                
                Agent Action: {agent_action}
                Policy Type: {policy_type}
                Context: {context or 'None'}
                
                Use tools to:
                1. Retrieve relevant policy rules
                2. Check compliance with policies
                3. Identify any violations
                4. Determine required corrections
                5. Apply enforcement actions
                
                Be fair, consistent, and document all enforcement actions.
                """),
                HumanMessage(content=f"Enforce policy: {policy_type} on {agent_action}")
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
                output = result.get("output", "Policy enforcement failed")
            
            # Parse result for response
            if "compliant" in output.lower():
                return DecisionResponse(
                    success=True,
                    message=output,
                    action_taken="policy_compliant"
                )
            elif "violation" in output.lower():
                return DecisionResponse(
                    success=True,
                    message=output,
                    action_taken="policy_violation_corrected"
                )
            else:
                return DecisionResponse(
                    success=True,
                    message=output,
                    action_taken="policy_enforced"
                )
                
        except Exception as e:
            return DecisionResponse(
                success=False,
                message=f"Policy enforcement error: {str(e)}",
                action_taken="policy_enforcement_error"
            )


# Global decision agent instance
decision_agent = DecisionAgent()
