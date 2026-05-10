"""
Operations App API Routes
API endpoints for staff task management and operations
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional
import logging
from datetime import datetime

from hospitality_ai.models.operations_models import (
    Task, TaskUpdate, TaskCreate, TaskSummary, TaskIssue,
    StaffWorkload, OperationsStats, TaskStatus, TaskPriority
)
from hospitality_ai.state.state_manager import state_manager
from hospitality_ai.monitoring.workflow_monitor import workflow_monitor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/operations", tags=["operations"])


# In-memory storage for demo (replace with actual database in production)
_tasks_storage: dict[str, Task] = {}
_issues_storage: dict[str, TaskIssue] = {}


def generate_task_id() -> str:
    """Generate unique task ID"""
    import uuid
    return f"T{datetime.now().strftime('%Y%m%d')}{str(uuid.uuid4())[:8].upper()}"


def generate_issue_id() -> str:
    """Generate unique issue ID"""
    import uuid
    return f"I{datetime.now().strftime('%Y%m%d')}{str(uuid.uuid4())[:8].upper()}"


@router.get("/tasks", response_model=List[TaskSummary])
async def get_staff_tasks(
    staff_id: str = Query(..., description="Staff member ID"),
    status: Optional[TaskStatus] = Query(None, description="Filter by task status"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of tasks to return")
) -> List[TaskSummary]:
    """
    Get tasks assigned to a specific staff member.
    
    Args:
        staff_id: Staff member identifier
        status: Optional status filter
        limit: Maximum number of tasks to return
        
    Returns:
        List of task summaries for the staff member
    """
    try:
        logger.info(f"Getting tasks for staff {staff_id}")
        
        # Filter tasks by staff_id and optional status
        staff_tasks = []
        for task in _tasks_storage.values():
            if task.staff_id == staff_id:
                if status is None or task.status == status:
                    task_summary = TaskSummary(
                        task_id=task.task_id,
                        task_type=task.task_type,
                        priority=task.priority,
                        status=task.status,
                        description=task.description,
                        room_id=task.room_id,
                        created_at=task.created_at,
                        due_at=task.due_at
                    )
                    staff_tasks.append(task_summary)
        
        # Sort by priority and creation time
        priority_order = {"urgent": 0, "high": 1, "medium": 2, "low": 3}
        staff_tasks.sort(
            key=lambda t: (priority_order.get(t.priority.value, 4), t.created_at),
            reverse=False
        )
        
        # Apply limit
        return staff_tasks[:limit]
        
    except Exception as e:
        logger.error(f"Error getting tasks for staff {staff_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve tasks")


@router.post("/tasks/update", response_model=dict)
async def update_task_status(task_update: TaskUpdate) -> dict:
    """
    Update task status and details.
    
    Args:
        task_update: Task update details
        
    Returns:
        Success message with updated task details
    """
    try:
        logger.info(f"Updating task {task_update.task_id}")
        
        # Check if task exists
        if task_update.task_id not in _tasks_storage:
            raise HTTPException(status_code=404, detail="Task not found")
        
        # Update task
        task = _tasks_storage[task_update.task_id]
        
        if task_update.status:
            old_status = task.status
            task.status = task_update.status
            
            # Set completion time if completed
            if task_update.status == TaskStatus.COMPLETED and not task.completed_at:
                task.completed_at = datetime.now()
            
            # Log status change
            logger.info(f"Task {task_update.task_id} status changed from {old_status} to {task_update.status}")
            
            # Add to workflow monitor
            workflow_monitor.workflow_events.append({
                "timestamp": datetime.now().isoformat(),
                "event_type": "task_status_update",
                "task_id": task_update.task_id,
                "staff_id": task.staff_id,
                "old_status": old_status.value,
                "new_status": task_update.status.value,
                "from": "operations_app",
                "to": "state_layer",
                "details": f"Task {task_update.task_id} updated to {task_update.status.value}"
            })
        
        if task_update.notes:
            task.notes = task_update.notes
        
        if task_update.completed_at:
            task.completed_at = task_update.completed_at
        
        return {
            "success": True,
            "message": "Task updated successfully",
            "task_id": task_update.task_id,
            "status": task.status.value,
            "updated_at": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating task {task_update.task_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update task")


@router.post("/tasks/issue", response_model=dict)
async def report_task_issue(
    task_id: str = Query(..., description="Task ID"),
    issue_type: str = Query(..., description="Type of issue"),
    description: str = Query(..., description="Issue description"),
    reported_by: str = Query(..., description="Staff member reporting the issue")
) -> dict:
    """
    Report an issue with a task.
    
    Args:
        task_id: Task identifier
        issue_type: Type of issue encountered
        description: Detailed issue description
        reported_by: Staff member reporting the issue
        
    Returns:
        Success message with issue details
    """
    try:
        logger.info(f"Reporting issue for task {task_id}")
        
        # Check if task exists
        if task_id not in _tasks_storage:
            raise HTTPException(status_code=404, detail="Task not found")
        
        # Create issue
        issue = TaskIssue(
            issue_id=generate_issue_id(),
            task_id=task_id,
            issue_type=issue_type,
            description=description,
            reported_by=reported_by
        )
        
        # Store issue
        _issues_storage[issue.issue_id] = issue
        
        # Update task status if needed
        task = _tasks_storage[task_id]
        if task.status == TaskStatus.IN_PROGRESS:
            task.status = TaskStatus.ON_HOLD
            task.notes = f"Issue reported: {description[:100]}..."
        
        # Add to workflow monitor
        workflow_monitor.workflow_events.append({
            "timestamp": datetime.now().isoformat(),
            "event_type": "task_issue_reported",
            "task_id": task_id,
            "issue_id": issue.issue_id,
            "staff_id": reported_by,
            "from": "operations_app",
            "to": "decision_agent",
            "details": f"Issue {issue_type} reported for task {task_id}"
        })
        
        logger.info(f"Issue {issue.issue_id} reported for task {task_id}")
        
        return {
            "success": True,
            "message": "Issue reported successfully",
            "issue_id": issue.issue_id,
            "task_id": task_id,
            "status": issue.status.value,
            "reported_at": issue.timestamp.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reporting issue for task {task_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to report issue")


@router.get("/tasks/history", response_model=List[TaskSummary])
async def get_task_history(
    staff_id: str = Query(..., description="Staff member ID"),
    days: int = Query(7, ge=1, le=30, description="Number of days to look back")
) -> List[TaskSummary]:
    """
    Get completed task history for a staff member.
    
    Args:
        staff_id: Staff member identifier
        days: Number of days to look back
        
    Returns:
        List of completed task summaries
    """
    try:
        logger.info(f"Getting task history for staff {staff_id}")
        
        # Calculate date threshold
        threshold_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        threshold_date = threshold_date.replace(day=threshold_date.day - days)
        
        # Get completed tasks
        completed_tasks = []
        for task in _tasks_storage.values():
            if (task.staff_id == staff_id and 
                task.status == TaskStatus.COMPLETED and 
                task.completed_at and 
                task.completed_at >= threshold_date):
                
                task_summary = TaskSummary(
                    task_id=task.task_id,
                    task_type=task.task_type,
                    priority=task.priority,
                    status=task.status,
                    description=task.description,
                    room_id=task.room_id,
                    created_at=task.created_at,
                    due_at=task.due_at
                )
                completed_tasks.append(task_summary)
        
        # Sort by completion time (most recent first)
        completed_tasks.sort(key=lambda t: t.completed_at or datetime.min, reverse=True)
        
        return completed_tasks
        
    except Exception as e:
        logger.error(f"Error getting task history for staff {staff_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve task history")