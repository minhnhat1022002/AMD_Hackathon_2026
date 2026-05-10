"""
Operations App Data Models
Data structures for task management and staff operations
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum
from pydantic import BaseModel, Field


class TaskType(str, Enum):
    """Task types for operations"""
    HOUSEKEEPING = "housekeeping"
    MAINTENANCE = "maintenance"
    SERVICE = "service"
    CLEANING = "cleaning"
    REPAIR = "repair"


class TaskPriority(str, Enum):
    """Task priority levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TaskStatus(str, Enum):
    """Task status tracking"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ON_HOLD = "on_hold"


class IssueStatus(str, Enum):
    """Issue reporting status"""
    REPORTED = "reported"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    ESCALATED = "escalated"


class Task(BaseModel):
    """Task model for operations management"""
    task_id: str = Field(..., description="Unique task identifier")
    staff_id: str = Field(..., description="Assigned staff member ID")
    guest_id: Optional[str] = Field(None, description="Related guest ID if applicable")
    room_id: Optional[str] = Field(None, description="Room ID if room-specific task")
    task_type: TaskType = Field(..., description="Type of task")
    priority: TaskPriority = Field(..., description="Task priority level")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="Current task status")
    description: str = Field(..., description="Task description")
    created_at: datetime = Field(default_factory=datetime.now, description="Task creation time")
    due_at: Optional[datetime] = Field(None, description="Task due time")
    completed_at: Optional[datetime] = Field(None, description="Task completion time")
    notes: Optional[str] = Field(None, description="Additional notes")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")

    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class TaskIssue(BaseModel):
    """Task issue reporting model"""
    issue_id: str = Field(..., description="Unique issue identifier")
    task_id: str = Field(..., description="Related task ID")
    issue_type: str = Field(..., description="Type of issue")
    description: str = Field(..., description="Issue description")
    reported_by: str = Field(..., description="Staff member who reported the issue")
    timestamp: datetime = Field(default_factory=datetime.now, description="Issue report time")
    status: IssueStatus = Field(default=IssueStatus.REPORTED, description="Issue resolution status")
    resolution_notes: Optional[str] = Field(None, description="Notes about issue resolution")
    escalated_to: Optional[str] = Field(None, description="Who the issue was escalated to")

    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class TaskUpdate(BaseModel):
    """Task update request model"""
    task_id: str = Field(..., description="Task ID to update")
    status: Optional[TaskStatus] = Field(None, description="New status if updating")
    notes: Optional[str] = Field(None, description="Update notes")
    completed_at: Optional[datetime] = Field(None, description="Completion time if completed")

    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class TaskCreate(BaseModel):
    """Task creation request model"""
    staff_id: str = Field(..., description="Staff member to assign task to")
    guest_id: Optional[str] = Field(None, description="Related guest ID")
    room_id: Optional[str] = Field(None, description="Room ID if applicable")
    task_type: TaskType = Field(..., description="Type of task")
    priority: TaskPriority = Field(..., description="Task priority")
    description: str = Field(..., description="Task description")
    due_at: Optional[datetime] = Field(None, description="Due time for task")
    notes: Optional[str] = Field(None, description="Additional notes")

    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class TaskSummary(BaseModel):
    """Task summary for dashboard display"""
    task_id: str
    task_type: TaskType
    priority: TaskPriority
    status: TaskStatus
    description: str
    room_id: Optional[str]
    created_at: datetime
    due_at: Optional[datetime]

    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class StaffWorkload(BaseModel):
    """Staff workload summary"""
    staff_id: str
    staff_name: Optional[str]
    total_tasks: int
    pending_tasks: int
    in_progress_tasks: int
    completed_today: int
    overdue_tasks: int


class OperationsStats(BaseModel):
    """Operations statistics summary"""
    total_tasks: int
    tasks_by_status: Dict[str, int]
    tasks_by_priority: Dict[str, int]
    tasks_by_type: Dict[str, int]
    average_completion_time: Optional[float]  # in minutes
    staff_workload: List[StaffWorkload]
    recent_issues: List[TaskIssue]