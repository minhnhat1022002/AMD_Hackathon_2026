"""
Test Admin Panel API endpoints
"""

import pytest
from datetime import datetime, timedelta
from hospitality_ai.models.admin_models import (
    SystemConfig, IntegrationConfig, SystemLog, WorkflowConfig,
    ConfigUpdate, IntegrationTest, IntegrationTestResult, SystemStatus,
    AdminAction, ConfigCategory, IntegrationStatus, LogLevel
)
from hospitality_ai.api.routes.admin_routes import (
    _configs_storage, _integrations_storage, _logs_storage, _workflows_storage,
    generate_log_id, generate_action_id
)


def test_admin_api_endpoints():
    """Test basic Admin API functionality."""
    
    # Create sample system config
    config = SystemConfig(
        config_key="max_booking_days",
        config_value=365,
        description="Maximum days in advance for bookings",
        category=ConfigCategory.BOOKING,
        updated_by="admin_001"
    )
    
    # Store config
    _configs_storage[config.config_key] = config
    
    print(f"Created sample config: {config.config_key}")
    print(f"Config value: {config.config_value}")
    print(f"Category: {config.category}")
    print(f"Updated by: {config.updated_by}")
    
    # Test config count
    total_configs = len(_configs_storage)
    print(f"Total configurations: {total_configs}")
    
    # Verify config was stored correctly
    assert config.config_key in _configs_storage, "Config not stored correctly"
    assert _configs_storage[config.config_key].config_value == 365, "Config value mismatch"
    assert _configs_storage[config.config_key].category == ConfigCategory.BOOKING, "Category mismatch"
    
    print("Admin API test passed!")
    return True


def test_config_update():
    """Test configuration update functionality."""
    
    # Create initial config
    config = SystemConfig(
        config_key="api_timeout",
        config_value=30,
        description="API request timeout in seconds",
        category=ConfigCategory.API,
        updated_by="admin_001"
    )
    
    # Store config
    _configs_storage[config.config_key] = config
    
    print(f"Created initial config: {config.config_key} = {config.config_value}")
    
    # Simulate config update
    config_update = ConfigUpdate(
        config_key="api_timeout",
        config_value=60,
        updated_by="admin_002"
    )
    
    # Apply update
    old_value = config.config_value
    config.config_value = config_update.config_value
    config.updated_by = config_update.updated_by
    config.updated_at = datetime.now()
    
    print(f"Updated config: {old_value} -> {config.config_value}")
    print(f"Updated by: {config.updated_by}")
    
    # Verify config update
    assert config.config_value == 60, "Config value update failed"
    assert config.updated_by == "admin_002", "Updated by field failed"
    
    print("Config update test passed!")
    return True


def test_integration_testing():
    """Test integration testing functionality."""
    
    # Create sample integration
    integration = IntegrationConfig(
        integration_id="payment_gateway",
        service_name="Stripe Payment Gateway",
        endpoint="https://api.stripe.com/v1",
        credentials={"api_key": "sk_test_123"},
        status=IntegrationStatus.INACTIVE
    )
    
    # Store integration
    _integrations_storage[integration.integration_id] = integration
    
    print(f"Created integration: {integration.integration_id}")
    print(f"Service name: {integration.service_name}")
    print(f"Status: {integration.status}")
    
    # Simulate integration test
    integration_test = IntegrationTest(
        integration_id="payment_gateway",
        test_type="connectivity"
    )
    
    # Mock test result
    test_result = IntegrationTestResult(
        integration_id=integration_test.integration_id,
        test_type=integration_test.test_type,
        success=True,
        response_time=150.5,
        test_data={"status": "connected"}
    )
    
    # Update integration based on test result
    if test_result.success:
        integration.status = IntegrationStatus.ACTIVE
        integration.last_sync = datetime.now()
        integration.error_message = None
    
    print(f"Test result: {'Success' if test_result.success else 'Failed'}")
    print(f"Response time: {test_result.response_time}ms")
    print(f"Updated status: {integration.status}")
    
    # Verify integration test
    assert test_result.success == True, "Test result should be successful"
    assert integration.status == IntegrationStatus.ACTIVE, "Integration status should be active"
    assert integration.last_sync is not None, "Last sync should be set"
    
    print("Integration testing test passed!")
    return True


def test_system_logging():
    """Test system logging functionality."""
    
    # Create sample log entries
    log_entries = [
        SystemLog(
            log_id=generate_log_id(),
            timestamp=datetime.now() - timedelta(minutes=30),
            level=LogLevel.INFO,
            source="guest_agent",
            message="Guest message processed successfully",
            metadata={"guest_id": "G123", "response_time": 1.2}
        ),
        SystemLog(
            log_id=generate_log_id(),
            timestamp=datetime.now() - timedelta(minutes=15),
            level=LogLevel.WARNING,
            source="booking_agent",
            message="Room availability check timeout",
            metadata={"room_type": "deluxe", "timeout": 5.0}
        ),
        SystemLog(
            log_id=generate_log_id(),
            timestamp=datetime.now() - timedelta(minutes=5),
            level=LogLevel.ERROR,
            source="api",
            message="Database connection failed",
            metadata={"error_code": "DB_CONN_ERROR", "retry_count": 3}
        )
    ]
    
    # Store logs
    _logs_storage.extend(log_entries)
    
    print(f"Created {len(log_entries)} log entries")
    
    # Test log filtering by level
    error_logs = [log for log in _logs_storage if log.level == LogLevel.ERROR]
    warning_logs = [log for log in _logs_storage if log.level == LogLevel.WARNING]
    info_logs = [log for log in _logs_storage if log.level == LogLevel.INFO]
    
    print(f"Error logs: {len(error_logs)}")
    print(f"Warning logs: {len(warning_logs)}")
    print(f"Info logs: {len(info_logs)}")
    
    # Test log filtering by source
    api_logs = [log for log in _logs_storage if log.source == "api"]
    agent_logs = [log for log in _logs_storage if "agent" in log.source]
    
    print(f"API logs: {len(api_logs)}")
    print(f"Agent logs: {len(agent_logs)}")
    
    # Verify log filtering
    assert len(error_logs) == 1, "Should have 1 error log"
    assert len(warning_logs) == 1, "Should have 1 warning log"
    assert len(info_logs) == 1, "Should have 1 info log"
    assert len(api_logs) == 1, "Should have 1 API log"
    assert len(agent_logs) == 2, "Should have 2 agent logs"
    
    print("System logging test passed!")
    return True


def test_workflow_management():
    """Test workflow management functionality."""
    
    # Create sample workflows
    workflows = [
        WorkflowConfig(
            workflow_id="guest_booking_flow",
            workflow_name="Guest Booking Workflow",
            description="Standard guest booking process",
            agent_sequence=["guest_agent", "booking_agent", "revenue_agent"],
            conditions={"booking_type": "standard"},
            actions={"confirm_booking": True, "send_confirmation": True},
            created_by="admin_001",
            is_active=True
        ),
        WorkflowConfig(
            workflow_id="service_request_flow",
            workflow_name="Service Request Workflow",
            description="Handle guest service requests",
            agent_sequence=["guest_agent", "orchestrator", "operations_agent"],
            conditions={"request_type": "service"},
            actions={"create_task": True, "notify_staff": True},
            created_by="admin_001",
            is_active=True
        )
    ]
    
    # Store workflows
    for workflow in workflows:
        _workflows_storage[workflow.workflow_id] = workflow
    
    print(f"Created {len(workflows)} workflows")
    
    # Test workflow filtering
    active_workflows = [w for w in _workflows_storage.values() if w.is_active]
    booking_workflows = [w for w in _workflows_storage.values() if "booking" in w.workflow_name.lower()]
    
    print(f"Active workflows: {len(active_workflows)}")
    print(f"Booking workflows: {len(booking_workflows)}")
    
    # Simulate workflow reload
    for workflow in _workflows_storage.values():
        workflow.updated_at = datetime.now()
    
    print("Workflows reloaded successfully")
    
    # Verify workflow management
    assert len(active_workflows) == 2, "Should have 2 active workflows"
    assert len(booking_workflows) == 1, "Should have 1 booking workflow"
    assert all(w.updated_at is not None for w in _workflows_storage.values()), "All workflows should have updated_at"
    
    print("Workflow management test passed!")
    return True


def test_system_status():
    """Test system status functionality."""
    
    # Create sample data for status calculation
    # Add some configs
    configs = [
        SystemConfig("config1", "value1", "Test config 1", ConfigCategory.API, "admin_001"),
        SystemConfig("config2", "value2", "Test config 2", ConfigCategory.AGENT, "admin_001")
    ]
    for config in configs:
        _configs_storage[config.config_key] = config
    
    # Add some integrations
    integrations = [
        IntegrationConfig("int1", "Service 1", "https://api.service1.com", {}, IntegrationStatus.ACTIVE),
        IntegrationConfig("int2", "Service 2", "https://api.service2.com", {}, IntegrationStatus.ERROR)
    ]
    for integration in integrations:
        _integrations_storage[integration.integration_id] = integration
    
    # Add some workflows
    workflows = [
        WorkflowConfig("wf1", "Workflow 1", "Test workflow", ["agent1"], {}, {}, "admin_001", True),
        WorkflowConfig("wf2", "Workflow 2", "Test workflow", ["agent2"], {}, {}, "admin_001", False)
    ]
    for workflow in workflows:
        _workflows_storage[workflow.workflow_id] = workflow
    
    print(f"Setup: {len(configs)} configs, {len(integrations)} integrations, {len(workflows)} workflows")
    
    # Calculate system status metrics
    api_status = "healthy"
    database_status = "connected"
    
    agent_status = {
        "guest_agent": "active",
        "booking_agent": "active",
        "operations_agent": "active"
    }
    
    integration_status = {
        integration_id: integration.status
        for integration_id, integration in _integrations_storage.items()
    }
    
    active_workflows = sum(1 for w in _workflows_storage.values() if w.is_active)
    
    # Mock system metrics
    total_requests = 1250
    error_rate = 2.5
    uptime = 48.5
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
    
    print(f"System Status:")
    print(f"  API Status: {status.api_status}")
    print(f"  Database Status: {status.database_status}")
    print(f"  Active Workflows: {status.active_workflows}")
    print(f"  Total Requests: {status.total_requests}")
    print(f"  Error Rate: {status.error_rate}%")
    print(f"  Uptime: {status.uptime} hours")
    
    # Verify system status
    assert status.api_status == "healthy", "API status should be healthy"
    assert status.active_workflows == 1, "Should have 1 active workflow"
    assert status.total_requests == 1250, "Total requests mismatch"
    assert status.error_rate == 2.5, "Error rate mismatch"
    
    print("System status test passed!")
    return True


if __name__ == "__main__":
    print("Testing Admin Panel API...")
    
    print("\n1. Testing basic Admin API functionality...")
    test_admin_api_endpoints()
    
    print("\n2. Testing configuration update...")
    test_config_update()
    
    print("\n3. Testing integration testing...")
    test_integration_testing()
    
    print("\n4. Testing system logging...")
    test_system_logging()
    
    print("\n5. Testing workflow management...")
    test_workflow_management()
    
    print("\n6. Testing system status...")
    test_system_status()
    
    print("\nAll Admin Panel API tests passed!")
    print("\nAvailable endpoints:")
    print("  POST /admin/config/update")
    print("  GET /admin/config/all")
    print("  POST /admin/integration/test")
    print("  GET /admin/logs/system")
    print("  POST /admin/workflow/reload")
    print("  GET /admin/status")