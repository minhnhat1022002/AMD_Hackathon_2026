"""
Management Dashboard Data Models
Data structures for escalation handling, policy management, and performance analytics
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum
from pydantic import BaseModel, Field


class CaseSeverity(str, Enum):
    """Escalation case severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class CaseStatus(str, Enum):
    """Escalation case status tracking"""
    OPEN = "open"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    CLOSED = "closed"
    ESCALATED = "escalated"


class RuleType(str, Enum):
    """Policy rule categories"""
    PRICING = "pricing"
    BOOKING = "booking"
    SERVICE = "service"
    OPERATIONS = "operations"


class RuleStatus(str, Enum):
    """Policy rule status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    DRAFT = "draft"
    ARCHIVED = "archived"


class EscalationCase(BaseModel):
    """Escalation case model for management dashboard"""
    case_id: str = Field(..., description="Unique case identifier")
    guest_id: Optional[str] = Field(None, description="Related guest ID")
    issue_type: str = Field(..., description="Type of issue requiring escalation")
    severity: CaseSeverity = Field(..., description="Case severity level")
    status: CaseStatus = Field(default=CaseStatus.OPEN, description="Current case status")
    assigned_to: Optional[str] = Field(None, description="Manager assigned to case")
    description: str = Field(..., description="Detailed case description")
    resolution: Optional[str] = Field(None, description="Case resolution details")
    created_at: datetime = Field(default_factory=datetime.now, description="Case creation time")
    resolved_at: Optional[datetime] = Field(None, description="Case resolution time")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional case data")

    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class PolicyRule(BaseModel):
    """Policy rule model for management dashboard"""
    rule_id: str = Field(..., description="Unique rule identifier")
    name: str = Field(..., description="Rule name")
    description: str = Field(..., description="Rule description")
    rule_type: RuleType = Field(..., description="Type of policy rule")
    conditions: Dict[str, Any] = Field(..., description="Rule conditions")
    actions: Dict[str, Any] = Field(..., description="Rule actions")
    status: RuleStatus = Field(default=RuleStatus.ACTIVE, description="Rule status")
    created_by: str = Field(..., description="Manager who created rule")
    created_at: datetime = Field(default_factory=datetime.now, description="Rule creation time")
    updated_at: Optional[datetime] = Field(None, description="Last update time")
    priority: int = Field(default=1, ge=1, le=10, description="Rule priority (1-10)")

    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ManualDecision(BaseModel):
    """Manual decision override model"""
    case_id: str = Field(..., description="Case ID for decision")
    decision: str = Field(..., description="Decision made")
    decision_type: str = Field(..., description="Type of decision")
    made_by: str = Field(..., description="Manager making decision")
    notes: Optional[str] = Field(None, description="Decision notes")
    timestamp: datetime = Field(default_factory=datetime.now, description="Decision time")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class EscalationAction(BaseModel):
    """Escalation action model"""
    case_id: str = Field(..., description="Case ID")
    action: str = Field(..., description="Action taken")
    action_type: str = Field(..., description="Type of action")
    performed_by: str = Field(..., description="Manager performing action")
    notes: Optional[str] = Field(None, description="Action notes")
    timestamp: datetime = Field(default_factory=datetime.now, description="Action time")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class CaseSummary(BaseModel):
    """Case summary for dashboard display"""
    case_id: str
    issue_type: str
    severity: CaseSeverity
    status: CaseStatus
    description: str
    assigned_to: Optional[str]
    created_at: datetime
    guest_id: Optional[str]

    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class PerformanceMetrics(BaseModel):
    """Performance metrics for management dashboard"""
    total_cases: int
    cases_by_status: Dict[str, int]
    cases_by_severity: Dict[str, int]
    average_resolution_time: Optional[float]  # in hours
    resolution_rate: float  # percentage
    escalation_rate: float  # percentage
    active_rules: int
    staff_performance: Dict[str, Dict[str, Any]]
    guest_satisfaction_score: Optional[float]


class ManagerWorkload(BaseModel):
    """Manager workload summary"""
    manager_id: str
    manager_name: Optional[str]
    active_cases: int
    resolved_today: int
    average_resolution_time: Optional[float]
    escalation_success_rate: float


class RuleUpdate(BaseModel):
    """Rule update request model"""
    rule_id: str
    name: Optional[str] = None
    description: Optional[str] = None
    conditions: Optional[Dict[str, Any]] = None
    actions: Optional[Dict[str, Any]] = None
    status: Optional[RuleStatus] = None
    priority: Optional[int] = Field(None, ge=1, le=10)

    class Config:
        use_enum_values = True


class RuleCreate(BaseModel):
    """Rule creation request model"""
    name: str = Field(..., description="Rule name")
    description: str = Field(..., description="Rule description")
    rule_type: RuleType = Field(..., description="Type of policy rule")
    conditions: Dict[str, Any] = Field(..., description="Rule conditions")
    actions: Dict[str, Any] = Field(..., description="Rule actions")
    priority: int = Field(default=1, ge=1, le=10, description="Rule priority")
    created_by: str = Field(..., description="Manager creating rule")

    class Config:
        use_enum_values = True


class AnalyticsFilter(BaseModel):
    """Analytics filter parameters"""
    start_date: Optional[datetime] = Field(None, description="Start date for analytics")
    end_date: Optional[datetime] = Field(None, description="End date for analytics")
    severity_filter: Optional[List[CaseSeverity]] = Field(None, description="Severity filter")
    status_filter: Optional[List[CaseStatus]] = Field(None, description="Status filter")
    manager_filter: Optional[List[str]] = Field(None, description="Manager filter")

    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }