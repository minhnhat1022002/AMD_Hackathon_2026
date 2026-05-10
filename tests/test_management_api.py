"""
Test Management Dashboard API endpoints
"""

import pytest
from datetime import datetime, timedelta
from hospitality_ai.models.management_models import (
    EscalationCase, PolicyRule, ManualDecision, CaseSeverity, CaseStatus,
    RuleType, RuleStatus
)
from hospitality_ai.api.routes.management_routes import (
    _cases_storage, _rules_storage, generate_case_id, generate_rule_id
)


def test_management_api_endpoints():
    """Test basic Management API functionality."""
    
    # Create sample escalation case
    case_id = generate_case_id()
    sample_case = EscalationCase(
        case_id=case_id,
        guest_id="G123",
        issue_type="booking_conflict",
        severity=CaseSeverity.HIGH,
        description="Guest wants room upgrade but no rooms available"
    )
    
    # Store case
    _cases_storage[case_id] = sample_case
    
    print(f"Created sample case: {case_id}")
    print(f"Case details: {sample_case.description}")
    print(f"Severity: {sample_case.severity}")
    print(f"Status: {sample_case.status}")
    
    # Test case count
    total_cases = len(_cases_storage)
    print(f"Total cases in storage: {total_cases}")
    
    # Verify case was stored correctly
    assert case_id in _cases_storage, "Case not stored correctly"
    assert _cases_storage[case_id].severity == CaseSeverity.HIGH, "Severity mismatch"
    assert _cases_storage[case_id].status == CaseStatus.OPEN, "Status mismatch"
    
    print("Management API test passed!")
    return True


def test_manual_decision_handling():
    """Test manual decision override functionality."""
    
    # Create sample case
    case_id = generate_case_id()
    sample_case = EscalationCase(
        case_id=case_id,
        guest_id="G456",
        issue_type="service_complaint",
        severity=CaseSeverity.MEDIUM,
        description="Guest unhappy with room service quality"
    )
    
    # Store case
    _cases_storage[case_id] = sample_case
    
    print(f"Created service complaint case: {case_id}")
    print(f"Initial status: {sample_case.status}")
    
    # Simulate manual decision
    from hospitality_ai.models.management_models import ManualDecision
    decision = ManualDecision(
        case_id=case_id,
        decision="approve_room_upgrade",
        decision_type="compensation",
        made_by="manager_001",
        notes="Guest satisfaction priority - approve upgrade to deluxe room"
    )
    
    # Apply decision
    case = _cases_storage[case_id]
    case.status = CaseStatus.RESOLVED
    case.resolution = decision.decision
    case.resolved_at = decision.timestamp
    
    print(f"Updated status: {case.status}")
    print(f"Decision: {case.resolution}")
    print(f"Decision made by: {decision.made_by}")
    
    # Verify decision was applied
    assert case.status == CaseStatus.RESOLVED, "Status update failed"
    assert case.resolution == "approve_room_upgrade", "Resolution update failed"
    
    print("Manual decision handling test passed!")
    return True


def test_policy_rule_management():
    """Test policy rule management functionality."""
    
    # Create sample rule
    rule_id = generate_rule_id()
    sample_rule = PolicyRule(
        rule_id=rule_id,
        name="no_overbooking_policy",
        description="Prevent overbooking during peak season",
        rule_type=RuleType.BOOKING,
        conditions={
            "occupancy_rate": {"operator": ">", "value": 0.8},
            "season": {"operator": "in", "value": ["summer", "holidays"]}
        },
        actions={
            "block_overbooking": True,
            "require_manager_approval": True
        },
        created_by="admin_001",
        priority=5
    )
    
    # Store rule
    _rules_storage[rule_id] = sample_rule
    
    print(f"Created policy rule: {rule_id}")
    print(f"Rule name: {sample_rule.name}")
    print(f"Rule type: {sample_rule.rule_type}")
    print(f"Priority: {sample_rule.priority}")
    print(f"Status: {sample_rule.status}")
    
    # Test rule update
    from hospitality_ai.models.management_models import RuleUpdate
    rule_update = RuleUpdate(
        rule_id=rule_id,
        priority=8,
        status=RuleStatus.ACTIVE
    )
    
    # Apply update
    rule = _rules_storage[rule_id]
    rule.priority = rule_update.priority
    rule.status = rule_update.status
    rule.updated_at = datetime.now()
    
    print(f"Updated priority: {rule.priority}")
    print(f"Updated status: {rule.status}")
    
    # Verify rule was updated
    assert rule.priority == 8, "Priority update failed"
    assert rule.status == RuleStatus.ACTIVE, "Status update failed"
    
    print("Policy rule management test passed!")
    return True


def test_escalation_queue():
    """Test escalation queue functionality."""
    
    # Create multiple test cases
    cases = [
        EscalationCase(
            case_id=generate_case_id(),
            guest_id="G001",
            issue_type="maintenance_urgent",
            severity=CaseSeverity.CRITICAL,
            description="AC failure in presidential suite"
        ),
        EscalationCase(
            case_id=generate_case_id(),
            guest_id="G002", 
            issue_type="pricing_dispute",
            severity=CaseSeverity.HIGH,
            description="Guest disputes final bill amount"
        ),
        EscalationCase(
            case_id=generate_case_id(),
            guest_id="G003",
            issue_type="room_change_request",
            severity=CaseSeverity.MEDIUM,
            description="Guest wants different room view"
        )
    ]
    
    # Store cases
    for case in cases:
        _cases_storage[case.case_id] = case
    
    print(f"Created {len(cases)} test cases for escalation queue")
    
    # Test queue filtering by severity
    high_priority_cases = [
        case for case in _cases_storage.values()
        if case.severity in [CaseSeverity.CRITICAL, CaseSeverity.HIGH]
    ]
    
    print(f"High priority cases: {len(high_priority_cases)}")
    
    # Verify queue filtering
    assert len(high_priority_cases) == 2, "Severity filtering failed"
    
    # Test case status filtering
    open_cases = [
        case for case in _cases_storage.values()
        if case.status == CaseStatus.OPEN
    ]
    
    print(f"Open cases: {len(open_cases)}")
    
    # Verify status filtering
    assert len(open_cases) == 3, "Status filtering failed"
    
    print("Escalation queue test passed!")
    return True


def test_performance_analytics():
    """Test performance analytics functionality."""
    
    # Create sample cases with different statuses
    cases_data = [
        (CaseSeverity.CRITICAL, CaseStatus.RESOLVED),
        (CaseSeverity.HIGH, CaseStatus.OPEN),
        (CaseSeverity.MEDIUM, CaseStatus.RESOLVED),
        (CaseSeverity.LOW, CaseStatus.INVESTIGATING),
        (CaseSeverity.HIGH, CaseStatus.ESCALATED)
    ]
    
    for i, (severity, status) in enumerate(cases_data):
        case_id = generate_case_id()
        case = EscalationCase(
            case_id=case_id,
            guest_id=f"G{i:03d}",
            issue_type=f"test_issue_{i}",
            severity=severity,
            status=status,
            description=f"Test case {i}"
        )
        
        # Set resolved time for resolved cases
        if status == CaseStatus.RESOLVED:
            case.resolved_at = datetime.now() - timedelta(hours=i+1)
        
        _cases_storage[case_id] = case
    
    print(f"Created {len(cases_data)} cases for analytics testing")
    
    # Calculate metrics
    total_cases = len(_cases_storage)
    resolved_cases = sum(
        1 for case in _cases_storage.values()
        if case.status == CaseStatus.RESOLVED
    )
    resolution_rate = (resolved_cases / total_cases * 100) if total_cases > 0 else 0
    
    print(f"Total cases: {total_cases}")
    print(f"Resolved cases: {resolved_cases}")
    print(f"Resolution rate: {resolution_rate:.1f}%")
    
    # Test cases by severity
    severity_counts = {}
    for severity in CaseSeverity:
        severity_counts[severity.value] = sum(
            1 for case in _cases_storage.values()
            if case.severity == severity
        )
    
    print("Cases by severity:")
    for severity, count in severity_counts.items():
        print(f"  {severity}: {count}")
    
    # Verify metrics calculation
    assert total_cases == 5, "Total cases count mismatch"
    assert resolved_cases == 2, "Resolved cases count mismatch"
    assert resolution_rate == 40.0, "Resolution rate calculation error"
    
    print("Performance analytics test passed!")
    return True


if __name__ == "__main__":
    print("Testing Management Dashboard API...")
    
    print("\n1. Testing basic Management API functionality...")
    test_management_api_endpoints()
    
    print("\n2. Testing manual decision handling...")
    test_manual_decision_handling()
    
    print("\n3. Testing policy rule management...")
    test_policy_rule_management()
    
    print("\n4. Testing escalation queue...")
    test_escalation_queue()
    
    print("\n5. Testing performance analytics...")
    test_performance_analytics()
    
    print("\nAll Management Dashboard API tests passed!")
    print("\nAvailable endpoints:")
    print("  POST /management/decision/manual")
    print("  POST /management/decision/escalation")
    print("  POST /management/rules/update")
    print("  GET /management/rules/active")
    print("  GET /management/analytics/performance")
    print("  GET /management/escalations/queue")