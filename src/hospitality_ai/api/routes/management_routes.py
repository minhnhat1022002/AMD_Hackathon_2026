"""
Management Dashboard API Routes
API endpoints for escalation handling, policy management, and performance analytics
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional
import logging
from datetime import datetime, timedelta

from hospitality_ai.models.management_models import (
    EscalationCase, ManualDecision, EscalationAction, CaseSummary,
    PolicyRule, RuleUpdate, RuleCreate, PerformanceMetrics,
    CaseSeverity, CaseStatus, RuleType, RuleStatus, AnalyticsFilter
)
from hospitality_ai.monitoring.workflow_monitor import workflow_monitor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/management", tags=["management"])


# In-memory storage for demo (replace with actual database in production)
_cases_storage: dict[str, EscalationCase] = {}
_rules_storage: dict[str, PolicyRule] = {}
_decisions_storage: dict[str, ManualDecision] = {}
_actions_storage: dict[str, EscalationAction] = {}


def generate_case_id() -> str:
    """Generate unique case ID"""
    import uuid
    return f"C{datetime.now().strftime('%Y%m%d')}{str(uuid.uuid4())[:8].upper()}"


def generate_rule_id() -> str:
    """Generate unique rule ID"""
    import uuid
    return f"R{datetime.now().strftime('%Y%m%d')}{str(uuid.uuid4())[:8].upper()}"


@router.post("/decision/manual", response_model=dict)
async def handle_manual_decision(decision: ManualDecision) -> dict:
    """
    Handle manual decision override for complex guest cases.
    
    Args:
        decision: Manual decision details
        
    Returns:
        Success message with decision details
    """
    try:
        logger.info(f"Processing manual decision for case {decision.case_id}")
        
        # Check if case exists
        if decision.case_id not in _cases_storage:
            raise HTTPException(status_code=404, detail="Case not found")
        
        # Store decision
        _decisions_storage[decision.case_id] = decision
        
        # Update case status
        case = _cases_storage[decision.case_id]
        old_status = case.status
        case.status = CaseStatus.RESOLVED
        case.resolution = decision.decision
        case.resolved_at = decision.timestamp
        
        # Log decision
        logger.info(f"Case {decision.case_id} resolved with decision: {decision.decision}")
        
        # Add to workflow monitor
        workflow_monitor.workflow_events.append({
            "timestamp": datetime.now().isoformat(),
            "event_type": "manual_decision",
            "case_id": decision.case_id,
            "decision": decision.decision,
            "decision_type": decision.decision_type,
            "made_by": decision.made_by,
            "from": "management_dashboard",
            "to": "decision_agent",
            "details": f"Manual decision {decision.decision_type} made for case {decision.case_id}"
        })
        
        return {
            "success": True,
            "message": "Decision processed successfully",
            "case_id": decision.case_id,
            "decision": decision.decision,
            "decision_type": decision.decision_type,
            "made_by": decision.made_by,
            "timestamp": decision.timestamp.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing manual decision for case {decision.case_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to process decision")


@router.post("/decision/escalation", response_model=dict)
async def handle_escalation(
    case_id: str = Query(..., description="Case ID"),
    action: str = Query(..., description="Escalation action"),
    performed_by: str = Query(..., description="Manager performing escalation"),
    notes: Optional[str] = Query(None, description="Escalation notes")
) -> dict:
    """
    Handle escalation cases for management resolution.
    
    Args:
        case_id: Case identifier
        action: Escalation action taken
        performed_by: Manager performing the action
        notes: Additional notes about the escalation
        
    Returns:
        Success message with escalation details
    """
    try:
        logger.info(f"Handling escalation for case {case_id}")
        
        # Check if case exists
        if case_id not in _cases_storage:
            raise HTTPException(status_code=404, detail="Case not found")
        
        # Create escalation action
        escalation_action = EscalationAction(
            case_id=case_id,
            action=action,
            action_type="escalation",
            performed_by=performed_by,
            notes=notes
        )
        
        # Store action
        _actions_storage[case_id] = escalation_action
        
        # Update case status
        case = _cases_storage[case_id]
        old_status = case.status
        case.status = CaseStatus.ESCALATED
        case.assigned_to = performed_by
        
        # Log escalation
        logger.info(f"Case {case_id} escalated with action: {action}")
        
        # Add to workflow monitor
        workflow_monitor.workflow_events.append({
            "timestamp": datetime.now().isoformat(),
            "event_type": "case_escalation",
            "case_id": case_id,
            "action": action,
            "performed_by": performed_by,
            "from": "management_dashboard",
            "to": "decision_agent",
            "details": f"Case {case_id} escalated: {action}"
        })
        
        return {
            "success": True,
            "message": "Escalation handled successfully",
            "case_id": case_id,
            "action": action,
            "performed_by": performed_by,
            "status": case.status.value,
            "timestamp": escalation_action.timestamp.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error handling escalation for case {case_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to handle escalation")


@router.post("/rules/update", response_model=dict)
async def update_policy_rule(rule_update: RuleUpdate) -> dict:
    """
    Update existing policy rules.
    
    Args:
        rule_update: Rule update details
        
    Returns:
        Success message with updated rule details
    """
    try:
        logger.info(f"Updating policy rule {rule_update.rule_id}")
        
        # Check if rule exists
        if rule_update.rule_id not in _rules_storage:
            raise HTTPException(status_code=404, detail="Rule not found")
        
        # Update rule
        rule = _rules_storage[rule_update.rule_id]
        
        if rule_update.name:
            rule.name = rule_update.name
        if rule_update.description:
            rule.description = rule_update.description
        if rule_update.conditions:
            rule.conditions = rule_update.conditions
        if rule_update.actions:
            rule.actions = rule_update.actions
        if rule_update.status:
            rule.status = rule_update.status
        if rule_update.priority:
            rule.priority = rule_update.priority
        
        rule.updated_at = datetime.now()
        
        # Log rule update
        logger.info(f"Rule {rule_update.rule_id} updated successfully")
        
        # Add to workflow monitor
        workflow_monitor.workflow_events.append({
            "timestamp": datetime.now().isoformat(),
            "event_type": "rule_update",
            "rule_id": rule_update.rule_id,
            "rule_name": rule.name,
            "rule_type": rule.rule_type.value,
            "status": rule.status.value,
            "from": "management_dashboard",
            "to": "state_layer",
            "details": f"Policy rule {rule.name} updated"
        })
        
        return {
            "success": True,
            "message": "Rule updated successfully",
            "rule_id": rule_update.rule_id,
            "rule_name": rule.name,
            "status": rule.status.value,
            "updated_at": rule.updated_at.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating rule {rule_update.rule_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update rule")


@router.get("/rules/active", response_model=List[PolicyRule])
async def get_active_rules(
    rule_type: Optional[RuleType] = Query(None, description="Filter by rule type")
) -> List[PolicyRule]:
    """
    Get all active policy rules.
    
    Args:
        rule_type: Optional filter by rule type
        
    Returns:
        List of active policy rules
    """
    try:
        logger.info("Getting active policy rules")
        
        # Filter active rules
        active_rules = []
        for rule in _rules_storage.values():
            if rule.status == RuleStatus.ACTIVE:
                if rule_type is None or rule.rule_type == rule_type:
                    active_rules.append(rule)
        
        # Sort by priority and name
        active_rules.sort(key=lambda r: (-r.priority, r.name))
        
        return active_rules
        
    except Exception as e:
        logger.error(f"Error getting active rules: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve active rules")


@router.get("/analytics/performance", response_model=PerformanceMetrics)
async def get_performance_analytics(
    start_date: Optional[datetime] = Query(None, description="Start date for analytics"),
    end_date: Optional[datetime] = Query(None, description="End date for analytics")
) -> PerformanceMetrics:
    """
    Get performance analytics for management dashboard.
    
    Args:
        start_date: Optional start date for analytics period
        end_date: Optional end date for analytics period
        
    Returns:
        Performance metrics summary
    """
    try:
        logger.info("Getting performance analytics")
        
        # Set default date range if not provided
        if not end_date:
            end_date = datetime.now()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        # Calculate metrics
        total_cases = len(_cases_storage)
        
        # Cases by status
        cases_by_status = {}
        for status in CaseStatus:
            cases_by_status[status.value] = sum(
                1 for case in _cases_storage.values() 
                if case.status == status
            )
        
        # Cases by severity
        cases_by_severity = {}
        for severity in CaseSeverity:
            cases_by_severity[severity.value] = sum(
                1 for case in _cases_storage.values() 
                if case.severity == severity
            )
        
        # Calculate resolution metrics
        resolved_cases = [
            case for case in _cases_storage.values()
            if case.status == CaseStatus.RESOLVED and case.resolved_at
        ]
        
        average_resolution_time = None
        if resolved_cases:
            total_resolution_time = sum(
                (case.resolved_at - case.created_at).total_seconds() / 3600
                for case in resolved_cases
            )
            average_resolution_time = total_resolution_time / len(resolved_cases)
        
        resolution_rate = (len(resolved_cases) / total_cases * 100) if total_cases > 0 else 0
        
        # Escalation rate
        escalated_cases = sum(
            1 for case in _cases_storage.values()
            if case.status == CaseStatus.ESCALATED
        )
        escalation_rate = (escalated_cases / total_cases * 100) if total_cases > 0 else 0
        
        # Active rules count
        active_rules = sum(
            1 for rule in _rules_storage.values()
            if rule.status == RuleStatus.ACTIVE
        )
        
        # Mock staff performance and satisfaction score
        staff_performance = {
            "manager_001": {
                "cases_resolved": 15,
                "average_resolution_time": 2.5,
                "satisfaction_score": 4.2
            },
            "manager_002": {
                "cases_resolved": 12,
                "average_resolution_time": 3.1,
                "satisfaction_score": 4.0
            }
        }
        
        guest_satisfaction_score = 4.1
        
        metrics = PerformanceMetrics(
            total_cases=total_cases,
            cases_by_status=cases_by_status,
            cases_by_severity=cases_by_severity,
            average_resolution_time=average_resolution_time,
            resolution_rate=resolution_rate,
            escalation_rate=escalation_rate,
            active_rules=active_rules,
            staff_performance=staff_performance,
            guest_satisfaction_score=guest_satisfaction_score
        )
        
        return metrics
        
    except Exception as e:
        logger.error(f"Error getting performance analytics: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve performance analytics")


@router.get("/escalations/queue", response_model=List[CaseSummary])
async def get_escalation_queue(
    severity: Optional[CaseSeverity] = Query(None, description="Filter by severity"),
    assigned_to: Optional[str] = Query(None, description="Filter by assigned manager"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of cases")
) -> List[CaseSummary]:
    """
    Get escalation queue for management dashboard.
    
    Args:
        severity: Optional filter by severity
        assigned_to: Optional filter by assigned manager
        limit: Maximum number of cases to return
        
    Returns:
        List of escalation case summaries
    """
    try:
        logger.info("Getting escalation queue")
        
        # Filter cases
        queue_cases = []
        for case in _cases_storage.values():
            if case.status in [CaseStatus.OPEN, CaseStatus.INVESTIGATING, CaseStatus.ESCALATED]:
                if severity is None or case.severity == severity:
                    if assigned_to is None or case.assigned_to == assigned_to:
                        case_summary = CaseSummary(
                            case_id=case.case_id,
                            issue_type=case.issue_type,
                            severity=case.severity,
                            status=case.status,
                            description=case.description,
                            assigned_to=case.assigned_to,
                            created_at=case.created_at,
                            guest_id=case.guest_id
                        )
                        queue_cases.append(case_summary)
        
        # Sort by severity and creation time
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        queue_cases.sort(
            key=lambda c: (severity_order.get(c.severity.value, 4), c.created_at),
            reverse=False
        )
        
        # Apply limit
        return queue_cases[:limit]
        
    except Exception as e:
        logger.error(f"Error getting escalation queue: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve escalation queue")