"""
Admin Panel Data Models
Data structures for system configuration, debugging, and integration management
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum
from pydantic import BaseModel, Field


class ConfigCategory(str, Enum):
    """System configuration categories"""
    AGENT = "agent"
    WORKFLOW = "workflow"
    API = "api"
    DATABASE = "database"
    LOGGING = "logging"
    SECURITY = "security"


class IntegrationStatus(str, Enum):
    """Integration status tracking"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    TESTING = "testing"
    DISABLED = "disabled"


class LogLevel(str, Enum):
    """Logging levels"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class SystemConfig(BaseModel):
    """System configuration model for admin panel"""
    config_key: str = Field(..., description="Configuration key")
    config_value: Any = Field(..., description="Configuration value")
    description: str = Field(..., description="Configuration description")
    category: ConfigCategory = Field(..., description="Configuration category")
    updated_by: str = Field(..., description="Admin who updated configuration")
    updated_at: datetime = Field(default_factory=datetime.now, description="Last update time")
    is_sensitive: bool = Field(default=False, description="Whether config contains sensitive data")

    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class IntegrationConfig(BaseModel):
    """Integration configuration model"""
    integration_id: str = Field(..., description="Integration identifier")
    service_name: str = Field(..., description="Service name")
    endpoint: str = Field(..., description="Service endpoint URL")
    credentials: Dict[str, Any] = Field(default_factory=dict, description="Encrypted credentials")
    status: IntegrationStatus = Field(default=IntegrationStatus.INACTIVE, description="Integration status")
    last_sync: Optional[datetime] = Field(None, description="Last successful sync time")
    error_message: Optional[str] = Field(None, description="Last error message")
    retry_count: int = Field(default=0, description="Number of retry attempts")
    config: Dict[str, Any] = Field(default_factory=dict, description="Additional integration config")

    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class SystemLog(BaseModel):
    """System log entry model"""
    log_id: str = Field(..., description="Log entry ID")
    timestamp: datetime = Field(..., description="Log timestamp")
    level: LogLevel = Field(..., description="Log level")
    source: str = Field(..., description="Log source component")
    message: str = Field(..., description="Log message")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional log metadata")
    user_id: Optional[str] = Field(None, description="User ID if applicable")

    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class WorkflowConfig(BaseModel):
    """Workflow configuration model"""
    workflow_id: str = Field(..., description="Workflow identifier")
    workflow_name: str = Field(..., description="Workflow name")
    description: str = Field(..., description="Workflow description")
    agent_sequence: List[str] = Field(..., description="Sequence of agents in workflow")
    conditions: Dict[str, Any] = Field(..., description="Workflow trigger conditions")
    actions: Dict[str, Any] = Field(..., description="Workflow actions")
    is_active: bool = Field(default=True, description="Whether workflow is active")
    created_by: str = Field(..., description="Admin who created workflow")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation time")
    updated_at: Optional[datetime] = Field(None, description="Last update time")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ConfigUpdate(BaseModel):
    """Configuration update request model"""
    config_key: str = Field(..., description="Configuration key")
    config_value: Any = Field(..., description="New configuration value")
    updated_by: str = Field(..., description="Admin updating configuration")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class IntegrationTest(BaseModel):
    """Integration test request model"""
    integration_id: str = Field(..., description="Integration ID to test")
    test_type: str = Field(default="connectivity", description="Type of test to perform")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Test parameters")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class IntegrationTestResult(BaseModel):
    """Integration test result model"""
    integration_id: str = Field(..., description="Integration ID")
    test_type: str = Field(..., description="Type of test performed")
    success: bool = Field(..., description="Whether test passed")
    response_time: Optional[float] = Field(None, description="Response time in milliseconds")
    error_message: Optional[str] = Field(None, description="Error message if test failed")
    test_data: Optional[Dict[str, Any]] = Field(None, description="Test response data")
    timestamp: datetime = Field(default_factory=datetime.now, description="Test timestamp")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class SystemStatus(BaseModel):
    """System status summary model"""
    api_status: str = Field(..., description="API server status")
    database_status: str = Field(..., description="Database connection status")
    agent_status: Dict[str, str] = Field(..., description="Individual agent statuses")
    integration_status: Dict[str, IntegrationStatus] = Field(..., description="Integration statuses")
    active_workflows: int = Field(..., description="Number of active workflows")
    total_requests: int = Field(..., description="Total API requests")
    error_rate: float = Field(..., description="Current error rate")
    uptime: float = Field(..., description="System uptime in hours")
    last_restart: datetime = Field(..., description="Last system restart time")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class AdminAction(BaseModel):
    """Admin action tracking model"""
    action_id: str = Field(..., description="Action identifier")
    admin_id: str = Field(..., description="Admin performing action")
    action_type: str = Field(..., description="Type of admin action")
    target: str = Field(..., description="Action target (config, integration, etc.)")
    details: Dict[str, Any] = Field(..., description="Action details")
    timestamp: datetime = Field(default_factory=datetime.now, description="Action timestamp")
    ip_address: Optional[str] = Field(None, description="Admin IP address")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class LogFilter(BaseModel):
    """Log filtering parameters"""
    start_time: Optional[datetime] = Field(None, description="Filter logs from this time")
    end_time: Optional[datetime] = Field(None, description="Filter logs until this time")
    level: Optional[LogLevel] = Field(None, description="Filter by log level")
    source: Optional[str] = Field(None, description="Filter by log source")
    user_id: Optional[str] = Field(None, description="Filter by user ID")
    search: Optional[str] = Field(None, description="Search in log messages")
    limit: int = Field(default=100, ge=1, le=1000, description="Maximum log entries")

    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }