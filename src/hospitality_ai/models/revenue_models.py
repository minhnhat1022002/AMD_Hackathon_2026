"""
Revenue Dashboard Data Models
Data structures for pricing control, revenue optimization, and analytics
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum
from pydantic import BaseModel, Field


class PricingStatus(str, Enum):
    """Pricing override status"""
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    PENDING = "pending"


class StrategyStatus(str, Enum):
    """Pricing strategy status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    TESTING = "testing"
    ARCHIVED = "archived"


class PricingOverride(BaseModel):
    """Pricing override model for revenue dashboard"""
    override_id: str = Field(..., description="Unique override identifier")
    room_type: str = Field(..., description="Room type for pricing override")
    original_price: float = Field(..., description="Original room price")
    new_price: float = Field(..., description="New override price")
    reason: str = Field(..., description="Reason for price override")
    approved_by: str = Field(..., description="Manager who approved override")
    status: PricingStatus = Field(default=PricingStatus.ACTIVE, description="Override status")
    expires_at: Optional[datetime] = Field(None, description="Override expiration time")
    created_at: datetime = Field(default_factory=datetime.now, description="Override creation time")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional override data")

    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class PricingStrategy(BaseModel):
    """Pricing strategy model for revenue dashboard"""
    strategy_id: str = Field(..., description="Unique strategy identifier")
    name: str = Field(..., description="Strategy name")
    description: str = Field(..., description="Strategy description")
    conditions: Dict[str, Any] = Field(..., description="Strategy trigger conditions")
    actions: Dict[str, Any] = Field(..., description="Strategy pricing actions")
    status: StrategyStatus = Field(default=StrategyStatus.ACTIVE, description="Strategy status")
    performance_metrics: Dict[str, Any] = Field(default_factory=dict, description="Strategy performance data")
    created_by: str = Field(..., description="Revenue manager who created strategy")
    created_at: datetime = Field(default_factory=datetime.now, description="Strategy creation time")
    updated_at: Optional[datetime] = Field(None, description="Last update time")
    priority: int = Field(default=1, ge=1, le=10, description="Strategy priority")

    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class PricingUpdate(BaseModel):
    """Pricing update request model"""
    room_type: str = Field(..., description="Room type to update")
    new_price: float = Field(..., description="New price for room type")
    reason: str = Field(..., description="Reason for price update")
    expires_at: Optional[datetime] = Field(None, description="When price override expires")
    approved_by: str = Field(..., description="Manager approving the change")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class StrategyUpdate(BaseModel):
    """Strategy update request model"""
    strategy_id: str = Field(..., description="Strategy ID to update")
    name: Optional[str] = None
    description: Optional[str] = None
    conditions: Optional[Dict[str, Any]] = None
    actions: Optional[Dict[str, Any]] = None
    status: Optional[StrategyStatus] = None
    priority: Optional[int] = Field(None, ge=1, le=10)

    class Config:
        use_enum_values = True


class StrategyCreate(BaseModel):
    """Strategy creation request model"""
    name: str = Field(..., description="Strategy name")
    description: str = Field(..., description="Strategy description")
    conditions: Dict[str, Any] = Field(..., description="Strategy trigger conditions")
    actions: Dict[str, Any] = Field(..., description="Strategy pricing actions")
    priority: int = Field(default=1, ge=1, le=10, description="Strategy priority")
    created_by: str = Field(..., description="Revenue manager creating strategy")

    class Config:
        use_enum_values = True


class RoomPricing(BaseModel):
    """Current room pricing model"""
    room_type: str = Field(..., description="Room type")
    base_price: float = Field(..., description="Base room price")
    current_price: float = Field(..., description="Current effective price")
    last_updated: datetime = Field(..., description="Last price update time")
    override_active: bool = Field(default=False, description="Whether override is active")
    override_expires: Optional[datetime] = Field(None, description="Override expiration")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class RevenueAnalytics(BaseModel):
    """Revenue analytics model for dashboard"""
    total_revenue: float = Field(..., description="Total revenue for period")
    revenue_by_room_type: Dict[str, float] = Field(..., description="Revenue breakdown by room type")
    occupancy_rate: float = Field(..., description="Current occupancy rate")
    average_daily_rate: float = Field(..., description="Average daily room rate")
    revenue_per_available_room: float = Field(..., description="RevPAR metric")
    pricing_effectiveness: float = Field(..., description="Pricing strategy effectiveness score")
    active_overrides: int = Field(..., description="Number of active pricing overrides")
    active_strategies: int = Field(..., description="Number of active pricing strategies")
    period_start: datetime = Field(..., description="Analytics period start")
    period_end: datetime = Field(..., description="Analytics period end")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class PricingHistory(BaseModel):
    """Pricing history model"""
    room_type: str = Field(..., description="Room type")
    price_changes: List[Dict[str, Any]] = Field(..., description="List of price changes")
    current_price: float = Field(..., description="Current room price")
    average_price: float = Field(..., description="Average historical price")
    min_price: float = Field(..., description="Minimum historical price")
    max_price: float = Field(..., description="Maximum historical price")
    volatility_score: float = Field(..., description="Price volatility score")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class StrategyPerformance(BaseModel):
    """Strategy performance metrics"""
    strategy_id: str = Field(..., description="Strategy ID")
    strategy_name: str = Field(..., description="Strategy name")
    revenue_impact: float = Field(..., description="Revenue impact in dollars")
    occupancy_impact: float = Field(..., description="Occupancy rate impact")
    effectiveness_score: float = Field(..., description="Overall effectiveness score (0-100)")
    days_active: int = Field(..., description="Number of days strategy has been active")
    last_triggered: Optional[datetime] = Field(None, description="Last time strategy was triggered")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class PricingFilter(BaseModel):
    """Pricing analytics filter parameters"""
    start_date: Optional[datetime] = Field(None, description="Start date for analytics")
    end_date: Optional[datetime] = Field(None, description="End date for analytics")
    room_types: Optional[List[str]] = Field(None, description="Filter by room types")
    include_overrides: bool = Field(True, description="Include pricing overrides")
    include_strategies: bool = Field(True, description="Include strategy impacts")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }