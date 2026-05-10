"""
Operations Agent - Handles task assignment, scheduling, and execution tracking.

Solves:
O1: Task assignment
O2: Scheduling
O3: Execution tracking

Dependencies:
- Booking Agent (new reservations, room prep tasks)
- Decision Agent (resource conflicts, failures)
- State Layer (task data, staff availability)

Primary interface for housekeeping/ops staff with mobile app/task dashboard.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import json
import logging
from datetime import datetime, timedelta

from langchain.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent

from ..domain.state_layer import state_layer, TaskStatus, Priority
from ..config.settings import Settings
from ..monitoring.workflow_monitor import workflow_monitor

# Set up logging
logger = logging.getLogger(__name__)


@dataclass
class ServiceRequest:
    """Service request data model."""
    guest_id: str
    service_type: str
    description: str
    priority: str = "medium"
    room_id: Optional[str] = None
    special_instructions: Optional[str] = None


@dataclass
class TaskResponse:
    """Task response data model."""
    success: bool
    message: str
    task_id: Optional[str] = None
    assigned_to: Optional[str] = None
    estimated_completion: Optional[str] = None
    action: str = "task_processed"


# Standalone tool functions for LangChain
@tool
def create_task_tool(guest_id: str, room_id: Optional[str], task_type: str, description: str, priority: str = "medium") -> str:
    """Create new task for staff assignment."""
    try:
        from ..domain.state_layer import Task
        task_id = f"TSK{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Convert priority string to enum
        priority_enum = Priority.MEDIUM
        if priority.lower() == "high":
            priority_enum = Priority.HIGH
        elif priority.lower() == "low":
            priority_enum = Priority.LOW
        
        task = Task(
            task_id=task_id,
            task_type=task_type,
            assigned_to="unassigned",  # Will be assigned by scheduling
            room_id=room_id,
            priority=priority_enum,
            status=TaskStatus.PENDING,
            description=description
        )
        
        created_task = state_layer.create_task(task)
        
        return json.dumps({
            "task_id": task_id,
            "guest_id": guest_id,
            "room_id": room_id,
            "task_type": task_type,
            "description": description,
            "priority": priority,
            "status": "created",
            "message": "Task created successfully"
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def assign_task_tool(task_id: str, staff_id: str, estimated_time: Optional[str] = None) -> str:
    """Assign task to specific staff member."""
    try:
        task = state_layer.get_task(task_id)
        if not task:
            return json.dumps({"error": "Task not found"})
        
        if task.status != TaskStatus.PENDING:
            return json.dumps({"error": "Task already assigned or completed"})
        
        # Update task assignment
        updated_task = state_layer.update_task(task_id, TaskStatus.IN_PROGRESS)
        if updated_task:
            # Update assigned staff (this would normally update staff record)
            updated_task.assigned_to = staff_id
            
            return json.dumps({
                "task_id": task_id,
                "assigned_to": staff_id,
                "estimated_completion": estimated_time,
                "status": "assigned",
                "message": f"Task assigned to {staff_id}"
            })
        
        return json.dumps({"error": "Failed to assign task"})
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def update_task_status_tool(task_id: str, status: str, notes: Optional[str] = None) -> str:
    """Update task status and add completion notes."""
    try:
        # Convert status string to enum
        status_enum = TaskStatus.PENDING
        if status.lower() == "in_progress":
            status_enum = TaskStatus.IN_PROGRESS
        elif status.lower() == "completed":
            status_enum = TaskStatus.COMPLETED
        elif status.lower() == "cancelled":
            status_enum = TaskStatus.CANCELLED
        
        updated_task = state_layer.update_task(task_id, status_enum)
        if updated_task:
            response_data = {
                "task_id": task_id,
                "status": status,
                "message": f"Task status updated to {status}"
            }
            
            if notes:
                response_data["notes"] = notes
            
            if status_enum == TaskStatus.COMPLETED:
                response_data["completed_at"] = datetime.now().isoformat()
            
            return json.dumps(response_data)
        
        return json.dumps({"error": "Failed to update task status"})
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def get_staff_workload_tool(staff_id: Optional[str] = None) -> str:
    """Get current workload for staff or all staff."""
    try:
        all_tasks = state_layer._tasks  # Access internal task storage
        
        workload_data = {}
        
        for task in all_tasks.values():
            if task.assigned_to:
                if task.assigned_to not in workload_data:
                    workload_data[task.assigned_to] = {
                        "total_tasks": 0,
                        "pending_tasks": 0,
                        "in_progress_tasks": 0,
                        "high_priority_tasks": 0
                    }
                
                workload = workload_data[task.assigned_to]
                workload["total_tasks"] += 1
                
                if task.status == TaskStatus.PENDING:
                    workload["pending_tasks"] += 1
                elif task.status == TaskStatus.IN_PROGRESS:
                    workload["in_progress_tasks"] += 1
                
                if task.priority == Priority.HIGH:
                    workload["high_priority_tasks"] += 1
        
        if staff_id:
            return json.dumps({
                "staff_id": staff_id,
                "workload": workload_data.get(staff_id, {})
            })
        else:
            return json.dumps({
                "all_staff_workload": workload_data
            })
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def schedule_task_tool(task_id: str, scheduled_time: str, estimated_duration: Optional[str] = None) -> str:
    """Schedule task for optimal timing based on staff availability."""
    try:
        task = state_layer.get_task(task_id)
        if not task:
            return json.dumps({"error": "Task not found"})
        
        # Parse scheduled time
        schedule_dt = datetime.fromisoformat(scheduled_time)
        
        # Simple scheduling logic (would be more sophisticated with real staff data)
        current_time = datetime.now()
        
        if schedule_dt < current_time:
            return json.dumps({"error": "Cannot schedule task in the past"})
        
        # Calculate optimal assignment based on current workload
        workload_result = json.loads(get_staff_workload_tool())
        all_workload = workload_result.get("all_staff_workload", {})
        
        # Find least loaded staff member (placeholder logic)
        best_staff = None
        min_tasks = float('inf')
        
        for staff_id, workload in all_workload.items():
            total_tasks = workload.get("total_tasks", 0)
            high_priority = workload.get("high_priority_tasks", 0)
            
            # Prioritize staff with fewer high-priority tasks
            if high_priority < min_tasks or (high_priority == min_tasks and total_tasks < all_workload[best_staff]["total_tasks"] if best_staff else float('inf')):
                min_tasks = high_priority
                best_staff = staff_id
        
        if best_staff:
            # Assign and schedule task
            assign_result = json.loads(assign_task_tool(task_id, best_staff, scheduled_time))
            
            return json.dumps({
                "task_id": task_id,
                "scheduled_for": scheduled_time,
                "estimated_duration": estimated_duration,
                "assigned_to": best_staff,
                "scheduling_reason": f"Optimal assignment based on workload",
                "assignment_result": assign_result
            })
        else:
            return json.dumps({"error": "No available staff for assignment"})
            
    except Exception as e:
        return json.dumps({"error": str(e)})


class OperationsAgent:
    """
    LLM-powered Operations Agent using LangChain.
    
    Handles task assignment, scheduling, and execution tracking.
    Primary interface for housekeeping/ops staff.
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
        logger.debug(f"Creating Operations Agent LLM with model: {self.settings.llm_model}")
        logger.debug(f"Base URL: {self.settings.llm_base_url}")
        logger.debug(f"Temperature: {self.settings.llm_temperature}")
        logger.debug(f"Max tokens: {self.settings.llm_max_tokens}")
        
        return ChatOpenAI(
            model=self.settings.llm_model,
            base_url=self.settings.llm_base_url,
            api_key=self.settings.llm_api_key,
            temperature=self.settings.llm_temperature,  # Operations Agent uses 0.3
            max_tokens=self.settings.llm_max_tokens,
            timeout=self.settings.llm_timeout_seconds,
            tool_choice="auto"  # Fix tool choice error for vLLM compatibility
        )
    
    def _create_agent(self):
        """Create LangChain agent with tools."""
        tools = [
            create_task_tool,
            assign_task_tool,
            update_task_status_tool,
            get_staff_workload_tool,
            schedule_task_tool
        ]
        
        system_prompt = """
        You are an Operations Agent for a hospitality AI system. Your roles:
        
        1. Task assignment (O1) - Assign tasks to appropriate staff
        2. Scheduling (O2) - Optimize task timing and workload
        3. Execution tracking (O3) - Monitor task progress and completion
        
        Available tools:
        - create_task_tool: Create new tasks for staff
        - assign_task_tool: Assign tasks to specific staff members
        - update_task_status_tool: Update task progress and completion
        - get_staff_workload_tool: Check current staff workload
        - schedule_task_tool: Schedule tasks for optimal timing
        
        Rules:
        - Prioritize guest-facing tasks (room prep, service requests)
        - Balance workload across available staff
        - Track task completion and status updates
        - Escalate resource conflicts to Decision Agent
        - Coordinate with Booking Agent for room preparation
        
        Be efficient, fair in task distribution, and track everything carefully.
        """
        
        return create_agent(
            model=self.llm,
            tools=tools,
            system_prompt=system_prompt
        )
    
    def process_service_request(self, request: ServiceRequest) -> TaskResponse:
        """
        Process service request from Guest Agent or other sources.
        
        Args:
            request: Service request with details
            
        Returns:
            TaskResponse with result and task details
        """
        try:
            # Prepare messages for LLM
            messages = [
                SystemMessage(content=f"""
                You are processing a service request.
                
                Guest ID: {request.guest_id}
                Room ID: {request.room_id}
                Service Type: {request.service_type}
                Description: {request.description}
                Priority: {request.priority}
                Special Instructions: {request.special_instructions or 'None'}
                
                Use tools to:
                1. Create appropriate task
                2. Assign to best available staff
                3. Schedule for optimal timing
                4. Track execution progress
                
                Consider staff workload and task urgency.
                """),
                HumanMessage(content=f"Process service request: {request}")
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
                output = result.get("output", "Service request processing failed")
            
            # Parse result for response
            if "created" in output.lower() and "assigned" in output.lower():
                return TaskResponse(
                    success=True,
                    message=output,
                    action="task_created_assigned"
                )
            elif "error" in output.lower():
                return TaskResponse(
                    success=False,
                    message=output,
                    action="task_failed"
                )
            else:
                return TaskResponse(
                    success=True,
                    message=output,
                    action="task_processed"
                )
                
        except Exception as e:
            return TaskResponse(
                success=False,
                message=f"Operations system error: {str(e)}",
                action="task_error"
            )
    
    def process_booking_prep(self, booking_data: dict) -> TaskResponse:
        """
        Process room preparation tasks from Booking Agent.
        
        Args:
            booking_data: Booking details with prep requirements
            
        Returns:
            TaskResponse with prep task details
        """
        try:
            # Prepare messages for LLM
            messages = [
                SystemMessage(content=f"""
                You are processing room preparation from a new booking.
                
                Booking Data: {booking_data}
                
                Use tools to:
                1. Create room preparation tasks
                2. Assign to appropriate staff
                3. Schedule for timely completion before check-in
                4. Set high priority for guest-facing tasks
                
                Room prep tasks may include:
                - Clean room
                - Check amenities
                - Prepare keycard
                - Handle special requests
                
                Ensure all tasks complete before guest arrival.
                """),
                HumanMessage(content=f"Process room prep for booking: {booking_data}")
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
                output = result.get("output", "Room prep processing failed")
            
            # Parse result for response
            if "created" in output.lower():
                return TaskResponse(
                    success=True,
                    message=output,
                    action="room_prep_initiated"
                )
            elif "error" in output.lower():
                return TaskResponse(
                    success=False,
                    message=output,
                    action="room_prep_failed"
                )
            else:
                return TaskResponse(
                    success=True,
                    message=output,
                    action="room_prep_processed"
                )
                
        except Exception as e:
            return TaskResponse(
                success=False,
                message=f"Room prep system error: {str(e)}",
                action="room_prep_error"
            )


# Global operations agent instance
operations_agent = OperationsAgent()
