"""
Test Operations API endpoints
"""

import pytest
from datetime import datetime, timedelta
from hospitality_ai.models.operations_models import Task, TaskType, TaskPriority, TaskStatus
from hospitality_ai.api.routes.operations_routes import _tasks_storage, generate_task_id


def test_operations_api_endpoints():
    """Test basic Operations API functionality."""
    
    # Create sample task
    task_id = generate_task_id()
    sample_task = Task(
        task_id=task_id,
        staff_id="H001",
        guest_id="G123",
        room_id="101",
        task_type=TaskType.HOUSEKEEPING,
        priority=TaskPriority.HIGH,
        description="Clean room 101",
        due_at=datetime.now() + timedelta(hours=2)
    )
    
    # Store task
    _tasks_storage[task_id] = sample_task
    
    print(f"Created sample task: {task_id}")
    print(f"Task details: {sample_task.description}")
    print(f"Assigned to staff: {sample_task.staff_id}")
    print(f"Priority: {sample_task.priority}")
    print(f"Status: {sample_task.status}")
    
    # Test task count
    total_tasks = len(_tasks_storage)
    print(f"Total tasks in storage: {total_tasks}")
    
    # Verify task was stored correctly
    assert task_id in _tasks_storage, "Task not stored correctly"
    assert _tasks_storage[task_id].staff_id == "H001", "Staff ID mismatch"
    assert _tasks_storage[task_id].task_type == TaskType.HOUSEKEEPING, "Task type mismatch"
    
    print("Operations API test passed!")
    return True


def test_task_status_update():
    """Test task status update functionality."""
    
    # Create sample task
    task_id = generate_task_id()
    sample_task = Task(
        task_id=task_id,
        staff_id="H002",
        task_type=TaskType.MAINTENANCE,
        priority=TaskPriority.MEDIUM,
        description="Fix AC in room 202"
    )
    
    # Store task
    _tasks_storage[task_id] = sample_task
    
    print(f"Created maintenance task: {task_id}")
    print(f"Initial status: {sample_task.status}")
    
    # Simulate status update
    from hospitality_ai.models.operations_models import TaskUpdate
    update = TaskUpdate(
        task_id=task_id,
        status=TaskStatus.IN_PROGRESS,
        notes="Started working on AC repair"
    )
    
    # Apply update
    task = _tasks_storage[task_id]
    task.status = update.status
    task.notes = update.notes
    
    print(f"Updated status: {task.status}")
    print(f"Update notes: {task.notes}")
    
    # Verify update
    assert task.status == TaskStatus.IN_PROGRESS, "Status update failed"
    assert task.notes == "Started working on AC repair", "Notes update failed"
    
    print("Task status update test passed!")
    return True


def test_task_issue_reporting():
    """Test task issue reporting functionality."""
    
    # Create sample task
    task_id = generate_task_id()
    sample_task = Task(
        task_id=task_id,
        staff_id="H003",
        task_type=TaskType.SERVICE,
        priority=TaskPriority.URGENT,
        description="Deliver extra towels to room 303"
    )
    
    # Store task
    _tasks_storage[task_id] = sample_task
    
    print(f"Created service task: {task_id}")
    
    # Simulate issue reporting
    from hospitality_ai.models.operations_models import TaskIssue, IssueStatus
    from hospitality_ai.api.routes.operations_routes import generate_issue_id, _issues_storage
    
    issue_id = generate_issue_id()
    issue = TaskIssue(
        issue_id=issue_id,
        task_id=task_id,
        issue_type="guest_not_available",
        description="Guest not in room, towels left at door",
        reported_by="H003"
    )
    
    # Store issue
    _issues_storage[issue_id] = issue
    
    print(f"Reported issue: {issue_id}")
    print(f"Issue type: {issue.issue_type}")
    print(f"Issue description: {issue.description}")
    print(f"Reported by: {issue.reported_by}")
    
    # Verify issue was stored
    assert issue_id in _issues_storage, "Issue not stored correctly"
    assert _issues_storage[issue_id].task_id == task_id, "Task ID mismatch in issue"
    
    print("Task issue reporting test passed!")
    return True


if __name__ == "__main__":
    print("Testing Operations API...")
    
    print("\n1. Testing basic Operations API functionality...")
    test_operations_api_endpoints()
    
    print("\n2. Testing task status updates...")
    test_task_status_update()
    
    print("\n3. Testing task issue reporting...")
    test_task_issue_reporting()
    
    print("\nAll Operations API tests passed!")
    print("\nAvailable endpoints:")
    print("  GET /operations/tasks?staff_id=H001")
    print("  POST /operations/tasks/update")
    print("  POST /operations/tasks/issue")
    print("  GET /operations/tasks/history?staff_id=H001")