"""
Revenue Dashboard API Routes
API endpoints for pricing control, revenue optimization, and analytics
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional
import logging
from datetime import datetime, timedelta

from hospitality_ai.models.revenue_models import (
    PricingUpdate, PricingOverride, RoomPricing, RevenueAnalytics,
    StrategyCreate, StrategyUpdate, PricingStrategy, PricingHistory,
    StrategyPerformance, PricingFilter, PricingStatus, StrategyStatus
)
from hospitality_ai.monitoring.workflow_monitor import workflow_monitor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/revenue", tags=["revenue"])


# In-memory storage for demo (replace with actual database in production)
_overrides_storage: dict[str, PricingOverride] = {}
_strategies_storage: dict[str, PricingStrategy] = {}
_pricing_storage: dict[str, RoomPricing] = {}
_history_storage: dict[str, PricingHistory] = {}


def generate_override_id() -> str:
    """Generate unique override ID"""
    import uuid
    return f"O{datetime.now().strftime('%Y%m%d')}{str(uuid.uuid4())[:8].upper()}"


def generate_strategy_id() -> str:
    """Generate unique strategy ID"""
    import uuid
    return f"S{datetime.now().strftime('%Y%m%d')}{str(uuid.uuid4())[:8].upper()}"


@router.post("/pricing/update", response_model=dict)
async def update_pricing(pricing_update: PricingUpdate) -> dict:
    """
    Override pricing for specific room types.
    
    Args:
        pricing_update: Pricing update details
        
    Returns:
        Success message with override details
    """
    try:
        logger.info(f"Updating pricing for room type: {pricing_update.room_type}")
        
        # Get current pricing
        current_pricing = _pricing_storage.get(pricing_update.room_type)
        if not current_pricing:
            # Create default pricing if not exists
            current_pricing = RoomPricing(
                room_type=pricing_update.room_type,
                base_price=100.0,  # Default base price
                current_price=100.0,
                last_updated=datetime.now(),
                override_active=False
            )
            _pricing_storage[pricing_update.room_type] = current_pricing
        
        # Create pricing override
        override = PricingOverride(
            override_id=generate_override_id(),
            room_type=pricing_update.room_type,
            original_price=current_pricing.current_price,
            new_price=pricing_update.new_price,
            reason=pricing_update.reason,
            approved_by=pricing_update.approved_by,
            expires_at=pricing_update.expires_at
        )
        
        # Store override
        _overrides_storage[override.override_id] = override
        
        # Update current pricing
        current_pricing.current_price = pricing_update.new_price
        current_pricing.last_updated = datetime.now()
        current_pricing.override_active = True
        current_pricing.override_expires = pricing_update.expires_at
        
        # Add to pricing history
        if pricing_update.room_type not in _history_storage:
            _history_storage[pricing_update.room_type] = PricingHistory(
                room_type=pricing_update.room_type,
                price_changes=[],
                current_price=pricing_update.new_price,
                average_price=pricing_update.new_price,
                min_price=pricing_update.new_price,
                max_price=pricing_update.new_price,
                volatility_score=0.0
            )
        
        history = _history_storage[pricing_update.room_type]
        history.price_changes.append({
            "timestamp": datetime.now().isoformat(),
            "old_price": current_pricing.base_price,
            "new_price": pricing_update.new_price,
            "reason": pricing_update.reason,
            "approved_by": pricing_update.approved_by,
            "override_id": override.override_id
        })
        
        # Recalculate history metrics
        prices = [change["new_price"] for change in history.price_changes]
        if prices:
            history.average_price = sum(prices) / len(prices)
            history.min_price = min(prices)
            history.max_price = max(prices)
            if len(prices) > 1:
                history.volatility_score = (history.max_price - history.min_price) / history.average_price
        
        # Log pricing update
        logger.info(f"Pricing updated for {pricing_update.room_type}: ${current_pricing.base_price} -> ${pricing_update.new_price}")
        
        # Add to workflow monitor
        workflow_monitor.workflow_events.append({
            "timestamp": datetime.now().isoformat(),
            "event_type": "pricing_update",
            "room_type": pricing_update.room_type,
            "old_price": current_pricing.base_price,
            "new_price": pricing_update.new_price,
            "approved_by": pricing_update.approved_by,
            "from": "revenue_dashboard",
            "to": "revenue_agent",
            "details": f"Pricing updated for {pricing_update.room_type} by {pricing_update.approved_by}"
        })
        
        return {
            "success": True,
            "message": "Pricing updated successfully",
            "override_id": override.override_id,
            "room_type": pricing_update.room_type,
            "old_price": current_pricing.base_price,
            "new_price": pricing_update.new_price,
            "approved_by": pricing_update.approved_by,
            "expires_at": pricing_update.expires_at.isoformat() if pricing_update.expires_at else None
        }
        
    except Exception as e:
        logger.error(f"Error updating pricing for {pricing_update.room_type}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update pricing")


@router.post("/pricing/strategy", response_model=dict)
async def create_pricing_strategy(strategy: StrategyCreate) -> dict:
    """
    Set pricing strategy for automated pricing rules.
    
    Args:
        strategy: Strategy creation details
        
    Returns:
        Success message with strategy details
    """
    try:
        logger.info(f"Creating pricing strategy: {strategy.name}")
        
        # Create strategy
        new_strategy = PricingStrategy(
            strategy_id=generate_strategy_id(),
            name=strategy.name,
            description=strategy.description,
            conditions=strategy.conditions,
            actions=strategy.actions,
            created_by=strategy.created_by,
            priority=strategy.priority
        )
        
        # Store strategy
        _strategies_storage[new_strategy.strategy_id] = new_strategy
        
        # Log strategy creation
        logger.info(f"Pricing strategy created: {new_strategy.strategy_id} - {new_strategy.name}")
        
        # Add to workflow monitor
        workflow_monitor.workflow_events.append({
            "timestamp": datetime.now().isoformat(),
            "event_type": "strategy_created",
            "strategy_id": new_strategy.strategy_id,
            "strategy_name": new_strategy.name,
            "created_by": strategy.created_by,
            "from": "revenue_dashboard",
            "to": "revenue_agent",
            "details": f"Pricing strategy {new_strategy.name} created by {strategy.created_by}"
        })
        
        return {
            "success": True,
            "message": "Strategy created successfully",
            "strategy_id": new_strategy.strategy_id,
            "strategy_name": new_strategy.name,
            "status": new_strategy.status.value,
            "priority": new_strategy.priority,
            "created_by": strategy.created_by
        }
        
    except Exception as e:
        logger.error(f"Error creating pricing strategy: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create strategy")


@router.get("/pricing/current", response_model=List[RoomPricing])
async def get_current_pricing(
    room_types: Optional[List[str]] = Query(None, description="Filter by room types")
) -> List[RoomPricing]:
    """
    Get current pricing for all room types.
    
    Args:
        room_types: Optional filter by room types
        
    Returns:
        List of current room pricing
    """
    try:
        logger.info("Getting current pricing")
        
        # Filter pricing
        current_pricing = []
        for room_type, pricing in _pricing_storage.items():
            if room_types is None or room_type in room_types:
                current_pricing.append(pricing)
        
        # Sort by room type
        current_pricing.sort(key=lambda p: p.room_type)
        
        return current_pricing
        
    except Exception as e:
        logger.error(f"Error getting current pricing: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve current pricing")


@router.get("/pricing/analytics", response_model=RevenueAnalytics)
async def get_pricing_analytics(
    start_date: Optional[datetime] = Query(None, description="Start date for analytics"),
    end_date: Optional[datetime] = Query(None, description="End date for analytics")
) -> RevenueAnalytics:
    """
    Get revenue analytics and pricing metrics.
    
    Args:
        start_date: Optional start date for analytics period
        end_date: Optional end date for analytics period
        
    Returns:
        Revenue analytics summary
    """
    try:
        logger.info("Getting pricing analytics")
        
        # Set default date range if not provided
        if not end_date:
            end_date = datetime.now()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        # Calculate metrics (mock data for demo)
        total_revenue = 125000.50
        revenue_by_room_type = {
            "standard": 45000.00,
            "deluxe": 55000.00,
            "suite": 25500.50
        }
        occupancy_rate = 0.78
        average_daily_rate = 145.50
        revenue_per_available_room = 113.49
        pricing_effectiveness = 0.85
        
        active_overrides = len([
            o for o in _overrides_storage.values()
            if o.status == PricingStatus.ACTIVE
        ])
        
        active_strategies = len([
            s for s in _strategies_storage.values()
            if s.status == StrategyStatus.ACTIVE
        ])
        
        analytics = RevenueAnalytics(
            total_revenue=total_revenue,
            revenue_by_room_type=revenue_by_room_type,
            occupancy_rate=occupancy_rate,
            average_daily_rate=average_daily_rate,
            revenue_per_available_room=revenue_per_available_room,
            pricing_effectiveness=pricing_effectiveness,
            active_overrides=active_overrides,
            active_strategies=active_strategies,
            period_start=start_date,
            period_end=end_date
        )
        
        return analytics
        
    except Exception as e:
        logger.error(f"Error getting pricing analytics: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve pricing analytics")


@router.get("/pricing/history", response_model=List[PricingHistory])
async def get_pricing_history(
    room_types: Optional[List[str]] = Query(None, description="Filter by room types"),
    days: int = Query(30, ge=1, le=365, description="Number of days to look back")
) -> List[PricingHistory]:
    """
    Get pricing history for room types.
    
    Args:
        room_types: Optional filter by room types
        days: Number of days to look back
        
    Returns:
        List of pricing history
    """
    try:
        logger.info(f"Getting pricing history for last {days} days")
        
        # Filter history
        pricing_history = []
        for room_type, history in _history_storage.items():
            if room_types is None or room_type in room_types:
                pricing_history.append(history)
        
        # Sort by room type
        pricing_history.sort(key=lambda h: h.room_type)
        
        return pricing_history
        
    except Exception as e:
        logger.error(f"Error getting pricing history: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve pricing history")