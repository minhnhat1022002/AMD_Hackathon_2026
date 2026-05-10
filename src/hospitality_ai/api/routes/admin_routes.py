"""
Admin Panel API Routes
API endpoints for system configuration, debugging, and integration management
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional
import logging
from datetime import datetime, timedelta
import uuid

from hospitality_ai.models.admin_models import (
    SystemConfig, IntegrationConfig, SystemLog, WorkflowConfig,
    ConfigUpdate, IntegrationTest, IntegrationTestResult, SystemStatus,
    AdminAction, LogFilter, ConfigCategory, IntegrationStatus, LogLevel
)
from hospitality_ai.monitoring.workflow_monitor import workflow_monitor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


# In-memory storage for demo (replace with actual database in production)
_configs_storage: dict[str, SystemConfig] = {}
_integrations_storage: dict[str, IntegrationConfig] = {}
_logs_storage: List[SystemLog] = []
_workflows_storage: dict[str, WorkflowConfig] = {}
_actions_storage: List[AdminAction] = []


def generate_log_id() -> str:
    """Generate unique log ID"""
    return f"L{datetime.now().strftime('%Y%m%d%H%M%S')}{str(uuid.uuid4())[:8].upper()}"


def generate_action_id() -> str:
    """Generate unique action ID"""
    return f"A{datetime.now().strftime('%Y%m%d%H%M%S')}{str(uuid.uuid4())[:8].upper()}"


@router.post("/config/update", response_model=dict)
async def update_system_config(config_update: ConfigUpdate) -> dict:
    """
    Update system configuration parameters.
    
    Args:
        config_update: Configuration update details
        
    Returns:
        Success message with configuration details
    """
    try:
        logger.info(f"Updating system config: {config_update.config_key}")
        
        # Check if config exists
        if config_update.config_key in _configs_storage:
            # Update existing config
            config = _configs_storage[config_update.config_key]
            old_value = config.config_value
            config.config_value = config_update.config_value
            config.updated_by = config_update.updated_by
            config.updated_at = datetime.now()
        else:
            # Create new config (with default description)
            config = SystemConfig(
                config_key=config_update.config_key,
                config_value=config_update.config_value,
                description=f"Configuration for {config_update.config_key}",
                category=ConfigCategory.API,  # Default category
                updated_by=config_update.updated_by
            )
            _configs_storage[config_update.config_key] = config
            old_value = None
        
        # Log admin action
        action = AdminAction(
            action_id=generate_action_id(),
            admin_id=config_update.updated_by,
            action_type="config_update",
            target=config_update.config_key,
            details={
                "old_value": old_value,
                "new_value": config_update.config_value
            }
        )
        _actions_storage.append(action)
        
        # Add to workflow monitor
        workflow_monitor.workflow_events.append({
            "timestamp": datetime.now().isoformat(),
            "event_type": "config_update",
            "config_key": config_update.config_key,
            "updated_by": config_update.updated_by,
            "from": "admin_panel",
            "to": "state_layer",
            "details": f"Configuration {config_update.config_key} updated by {config_update.updated_by}"
        })
        
        return {
            "success": True,
            "message": "Configuration updated successfully",
            "config_key": config_update.config_key,
            "old_value": old_value,
            "new_value": config_update.config_value,
            "updated_by": config_update.updated_by,
            "updated_at": config.updated_at.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error updating config {config_update.config_key}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update configuration")


@router.get("/config/all", response_model=List[SystemConfig])
async def get_all_configurations(
    category: Optional[ConfigCategory] = Query(None, description="Filter by category")
) -> List[SystemConfig]:
    """
    Get all system configurations.
    
    Args:
        category: Optional filter by category
        
    Returns:
        List of system configurations
    """
    try:
        logger.info("Getting all system configurations")
        
        # Filter configurations
        configs = []
        for config in _configs_storage.values():
            if category is None or config.category == category:
                configs.append(config)
        
        # Sort by category and config key
        configs.sort(key=lambda c: (c.category.value, c.config_key))
        
        return configs
        
    except Exception as e:
        logger.error(f"Error getting configurations: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve configurations")


@router.post("/integration/test", response_model=IntegrationTestResult)
async def test_integration(integration_test: IntegrationTest) -> IntegrationTestResult:
    """
    Test external integration connectivity.
    
    Args:
        integration_test: Integration test details
        
    Returns:
        Integration test result
    """
    try:
        logger.info(f"Testing integration: {integration_test.integration_id}")
        
        # Check if integration exists
        if integration_test.integration_id not in _integrations_storage:
            raise HTTPException(status_code=404, detail="Integration not found")
        
        integration = _integrations_storage[integration_test.integration_id]
        
        # Simulate integration test
        import time
        start_time = time.time()
        
        # Mock test logic
        success = True
        error_message = None
        test_data = {"status": "connected", "version": "1.0.0"}
        
        # Simulate network delay
        time.sleep(0.1)
        
        response_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        
        # Update integration status based on test result
        if success:
            integration.status = IntegrationStatus.ACTIVE
            integration.last_sync = datetime.now()
            integration.error_message = None
            integration.retry_count = 0
        else:
            integration.status = IntegrationStatus.ERROR
            integration.error_message = error_message
            integration.retry_count += 1
        
        # Create test result
        result = IntegrationTestResult(
            integration_id=integration_test.integration_id,
            test_type=integration_test.test_type,
            success=success,
            response_time=response_time,
            error_message=error_message,
            test_data=test_data
        )
        
        # Log admin action
        action = AdminAction(
            action_id=generate_action_id(),
            admin_id="system",  # In real implementation, get from auth
            action_type="integration_test",
            target=integration_test.integration_id,
            details={
                "test_type": integration_test.test_type,
                "success": success,
                "response_time": response_time
            }
        )
        _actions_storage.append(action)
        
        # Add to workflow monitor
        workflow_monitor.workflow_events.append({
            "timestamp": datetime.now().isoformat(),
            "event_type": "integration_test",
            "integration_id": integration_test.integration_id,
            "test_result": "success" if success else "failed",
            "response_time": response_time,
            "from": "admin_panel",
            "to": integration.service_name,
            "details": f"Integration test for {integration.service_name}"
        })
        
        logger.info(f"Integration test completed: {integration_test.integration_id} - {'Success' if success else 'Failed'}")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing integration {integration_test.integration_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to test integration")


@router.get("/logs/system", response_model=List[SystemLog])
async def get_system_logs(log_filter: LogFilter = Depends()) -> List[SystemLog]:
    """
    Get system logs with filtering options.
    
    Args:
        log_filter: Log filtering parameters
        
    Returns:
        List of system log entries
    """
    try:
        logger.info("Getting system logs")
        
        # Filter logs
        filtered_logs = []
        for log in _logs_storage:
            # Apply filters
            if log_filter.start_time and log.timestamp < log_filter.start_time:
                continue
            if log_filter.end_time and log.timestamp > log_filter.end_time:
                continue
            if log_filter.level and log.level != log_filter.level:
                continue
            if log_filter.source and log.source != log_filter.source:
                continue
            if log_filter.user_id and log.user_id != log_filter.user_id:
                continue
            if log_filter.search and log_filter.search.lower() not in log.message.lower():
                continue
            
            filtered_logs.append(log)
        
        # Sort by timestamp (most recent first)
        filtered_logs.sort(key=lambda l: l.timestamp, reverse=True)
        
        # Apply limit
        return filtered_logs[:log_filter.limit]
        
    except Exception as e:
        logger.error(f"Error getting system logs: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve system logs")


@router.post("/workflow/reload", response_model=dict)
async def reload_workflows(admin_id: str = Query(..., description="Admin ID performing reload")) -> dict:
    """
    Reload workflow configurations.
    
    Args:
        admin_id: Admin performing the reload
        
    Returns:
        Success message with reload details
    """
    try:
        logger.info(f"Reloading workflows by admin: {admin_id}")
        
        # Count active workflows before reload
        active_before = sum(1 for w in _workflows_storage.values() if w.is_active)
        
        # Simulate workflow reload (in real implementation, would reload from config files)
        for workflow in _workflows_storage.values():
            workflow.updated_at = datetime.now()
        
        # Count active workflows after reload
        active_after = sum(1 for w in _workflows_storage.values() if w.is_active)
        
        # Log admin action
        action = AdminAction(
            action_id=generate_action_id(),
            admin_id=admin_id,
            action_type="workflow_reload",
            target="all_workflows",
            details={
                "active_before": active_before,
                "active_after": active_after,
                "total_workflows": len(_workflows_storage)
            }
        )
        _actions_storage.append(action)
        
        # Add to workflow monitor
        workflow_monitor.workflow_events.append({
            "timestamp": datetime.now().isoformat(),
            "event_type": "workflow_reload",
            "admin_id": admin_id,
            "workflows_reloaded": len(_workflows_storage),
            "from": "admin_panel",
            "to": "orchestrator",
            "details": f"Workflows reloaded by {admin_id}"
        })
        
        return {
            "success": True,
            "message": "Workflows reloaded successfully",
            "total_workflows": len(_workflows_storage),
            "active_workflows": active_after,
            "reloaded_by": admin_id,
            "reload_time": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error reloading workflows: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to reload workflows")


@router.get("/status", response_model=SystemStatus)
async def get_system_status() -> SystemStatus:
    """
    Get overall system status.
    
    Returns:
        System status summary
    """
    try:
        logger.info("Getting system status")
        
        # Calculate system metrics
        api_status = "healthy"
        database_status = "connected"
        
        # Agent statuses
        agent_status = {
            "guest_agent": "active",
            "booking_agent": "active", 
            "operations_agent": "active",
            "decision_agent": "active",
            "revenue_agent": "active",
            "orchestrator": "active"
        }
        
        # Integration statuses
        integration_status = {
            integration_id: integration.status
            for integration_id, integration in _integrations_storage.items()
        }
        
        # Calculate metrics
        active_workflows = sum(1 for w in _workflows_storage.values() if w.is_active)
        total_requests = len(workflow_monitor.workflow_events)
        
        # Calculate error rate (mock data)
        error_events = sum(1 for event in workflow_monitor.workflow_events if "error" in str(event).lower())
        error_rate = (error_events / total_requests * 100) if total_requests > 0 else 0
        
        # System uptime (mock - would calculate from actual start time)
        uptime = 24.5  # hours
        last_restart = datetime.now() - timedelta(hours=uptime)
        
        status = SystemStatus(
            api_status=api_status,
            database_status=database_status,
            agent_status=agent_status,
            integration_status=integration_status,
            active_workflows=active_workflows,
            total_requests=total_requests,
            error_rate=error_rate,
            uptime=uptime,
            last_restart=last_restart
        )
        
        return status
        
    except Exception as e:
        logger.error(f"Error getting system status: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve system status")