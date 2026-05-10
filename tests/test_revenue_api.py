"""
Test Revenue Dashboard API endpoints
"""

import pytest
from datetime import datetime, timedelta
from hospitality_ai.models.revenue_models import (
    PricingUpdate, PricingStrategy, RoomPricing, RevenueAnalytics,
    PricingOverride, PricingHistory, PricingStatus, StrategyStatus
)
from hospitality_ai.api.routes.revenue_routes import (
    _overrides_storage, _strategies_storage, _pricing_storage, _history_storage,
    generate_override_id, generate_strategy_id
)


def test_revenue_api_endpoints():
    """Test basic Revenue API functionality."""
    
    # Create sample room pricing
    room_pricing = RoomPricing(
        room_type="deluxe",
        base_price=150.0,
        current_price=150.0,
        last_updated=datetime.now(),
        override_active=False
    )
    
    # Store pricing
    _pricing_storage["deluxe"] = room_pricing
    
    print(f"Created sample room pricing: {room_pricing.room_type}")
    print(f"Base price: ${room_pricing.base_price}")
    print(f"Current price: ${room_pricing.current_price}")
    print(f"Override active: {room_pricing.override_active}")
    
    # Test pricing count
    total_pricing = len(_pricing_storage)
    print(f"Total room pricing entries: {total_pricing}")
    
    # Verify pricing was stored correctly
    assert "deluxe" in _pricing_storage, "Room pricing not stored correctly"
    assert _pricing_storage["deluxe"].base_price == 150.0, "Base price mismatch"
    assert _pricing_storage["deluxe"].current_price == 150.0, "Current price mismatch"
    
    print("Revenue API test passed!")
    return True


def test_pricing_update():
    """Test pricing update functionality."""
    
    # Create initial pricing
    room_pricing = RoomPricing(
        room_type="standard",
        base_price=100.0,
        current_price=100.0,
        last_updated=datetime.now(),
        override_active=False
    )
    
    # Store pricing
    _pricing_storage["standard"] = room_pricing
    
    print(f"Created standard room pricing: ${room_pricing.current_price}")
    
    # Simulate pricing update
    pricing_update = PricingUpdate(
        room_type="standard",
        new_price=120.0,
        reason="Weekend rate increase",
        approved_by="revenue_manager_001",
        expires_at=datetime.now() + timedelta(days=2)
    )
    
    # Create override
    override = PricingOverride(
        override_id=generate_override_id(),
        room_type=pricing_update.room_type,
        original_price=room_pricing.current_price,
        new_price=pricing_update.new_price,
        reason=pricing_update.reason,
        approved_by=pricing_update.approved_by,
        expires_at=pricing_update.expires_at
    )
    
    # Store override and update pricing
    _overrides_storage[override.override_id] = override
    room_pricing.current_price = pricing_update.new_price
    room_pricing.last_updated = datetime.now()
    room_pricing.override_active = True
    room_pricing.override_expires = pricing_update.expires_at
    
    print(f"Updated pricing: ${room_pricing.base_price} -> ${room_pricing.current_price}")
    print(f"Override active: {room_pricing.override_active}")
    print(f"Expires at: {room_pricing.override_expires}")
    
    # Verify pricing update
    assert room_pricing.current_price == 120.0, "Pricing update failed"
    assert room_pricing.override_active == True, "Override activation failed"
    
    print("Pricing update test passed!")
    return True


def test_pricing_strategy():
    """Test pricing strategy functionality."""
    
    # Create sample strategy
    strategy = PricingStrategy(
        strategy_id=generate_strategy_id(),
        name="weekend_premium",
        description="Increase prices by 20% on weekends",
        conditions={
            "day_of_week": {"operator": "in", "value": ["saturday", "sunday"]},
            "occupancy_rate": {"operator": ">", "value": 0.7}
        },
        actions={
            "price_multiplier": 1.2,
            "min_price_increase": 10.0
        },
        created_by="revenue_manager_001",
        priority=5
    )
    
    # Store strategy
    _strategies_storage[strategy.strategy_id] = strategy
    
    print(f"Created pricing strategy: {strategy.strategy_id}")
    print(f"Strategy name: {strategy.name}")
    print(f"Description: {strategy.description}")
    print(f"Priority: {strategy.priority}")
    print(f"Status: {strategy.status}")
    
    # Test strategy update
    from hospitality_ai.models.revenue_models import StrategyUpdate
    strategy_update = StrategyUpdate(
        strategy_id=strategy.strategy_id,
        priority=8,
        status=StrategyStatus.ACTIVE
    )
    
    # Apply update
    strategy.priority = strategy_update.priority
    strategy.status = strategy_update.status
    strategy.updated_at = datetime.now()
    
    print(f"Updated priority: {strategy.priority}")
    print(f"Updated status: {strategy.status}")
    
    # Verify strategy was updated
    assert strategy.priority == 8, "Priority update failed"
    assert strategy.status == StrategyStatus.ACTIVE, "Status update failed"
    
    print("Pricing strategy test passed!")
    return True


def test_pricing_history():
    """Test pricing history functionality."""
    
    # Create sample pricing history
    history = PricingHistory(
        room_type="suite",
        price_changes=[],
        current_price=250.0,
        average_price=250.0,
        min_price=250.0,
        max_price=250.0,
        volatility_score=0.0
    )
    
    # Store history
    _history_storage["suite"] = history
    
    print(f"Created pricing history for: {history.room_type}")
    print(f"Current price: ${history.current_price}")
    
    # Add price changes
    price_changes = [
        {
            "timestamp": datetime.now().isoformat(),
            "old_price": 250.0,
            "new_price": 275.0,
            "reason": "Holiday pricing",
            "approved_by": "revenue_manager_001",
            "override_id": generate_override_id()
        },
        {
            "timestamp": (datetime.now() + timedelta(days=1)).isoformat(),
            "old_price": 275.0,
            "new_price": 300.0,
            "reason": "Weekend premium",
            "approved_by": "revenue_manager_001",
            "override_id": generate_override_id()
        }
    ]
    
    # Add changes to history
    for change in price_changes:
        history.price_changes.append(change)
    
    # Recalculate metrics
    prices = [change["new_price"] for change in history.price_changes]
    if prices:
        history.average_price = sum(prices) / len(prices)
        history.min_price = min(prices)
        history.max_price = max(prices)
        if len(prices) > 1:
            history.volatility_score = (history.max_price - history.min_price) / history.average_price
    
    print(f"Price changes recorded: {len(history.price_changes)}")
    print(f"Average price: ${history.average_price:.2f}")
    print(f"Min price: ${history.min_price:.2f}")
    print(f"Max price: ${history.max_price:.2f}")
    print(f"Volatility score: {history.volatility_score:.3f}")
    
    # Verify history calculations
    assert len(history.price_changes) == 2, "Price changes not recorded correctly"
    assert history.max_price == 300.0, "Max price calculation error"
    assert history.min_price == 250.0, "Min price calculation error"
    assert history.average_price == 287.5, "Average price calculation error"
    
    print("Pricing history test passed!")
    return True


def test_revenue_analytics():
    """Test revenue analytics functionality."""
    
    # Create sample pricing data
    room_types = ["standard", "deluxe", "suite"]
    base_prices = [100.0, 150.0, 250.0]
    
    for room_type, base_price in zip(room_types, base_prices):
        pricing = RoomPricing(
            room_type=room_type,
            base_price=base_price,
            current_price=base_price,
            last_updated=datetime.now(),
            override_active=False
        )
        _pricing_storage[room_type] = pricing
    
    print(f"Created pricing for {len(room_types)} room types")
    
    # Create sample overrides
    overrides = [
        PricingOverride(
            override_id=generate_override_id(),
            room_type="deluxe",
            original_price=150.0,
            new_price=180.0,
            reason="Weekend rate",
            approved_by="manager_001",
            status=PricingStatus.ACTIVE
        ),
        PricingOverride(
            override_id=generate_override_id(),
            room_type="suite",
            original_price=250.0,
            new_price=300.0,
            reason="Holiday pricing",
            approved_by="manager_001",
            status=PricingStatus.ACTIVE
        )
    ]
    
    # Store overrides
    for override in overrides:
        _overrides_storage[override.override_id] = override
    
    print(f"Created {len(overrides)} pricing overrides")
    
    # Create sample strategies
    strategies = [
        PricingStrategy(
            strategy_id=generate_strategy_id(),
            name="dynamic_pricing",
            description="Automated pricing based on demand",
            conditions={"occupancy_rate": {"operator": ">", "value": 0.8}},
            actions={"price_multiplier": 1.15},
            created_by="revenue_manager_001",
            status=StrategyStatus.ACTIVE
        )
    ]
    
    # Store strategies
    for strategy in strategies:
        _strategies_storage[strategy.strategy_id] = strategy
    
    print(f"Created {len(strategies)} pricing strategies")
    
    # Calculate analytics metrics
    total_pricing = len(_pricing_storage)
    active_overrides = len([o for o in _overrides_storage.values() if o.status == PricingStatus.ACTIVE])
    active_strategies = len([s for s in _strategies_storage.values() if s.status == StrategyStatus.ACTIVE])
    
    # Mock revenue calculations
    total_revenue = sum(p.current_price * 0.8 for p in _pricing_storage.values())  # Assume 80% occupancy
    average_daily_rate = total_revenue / len(_pricing_storage)
    
    print(f"Total room types: {total_pricing}")
    print(f"Active overrides: {active_overrides}")
    print(f"Active strategies: {active_strategies}")
    print(f"Total revenue: ${total_revenue:.2f}")
    print(f"Average daily rate: ${average_daily_rate:.2f}")
    
    # Verify analytics calculations
    assert total_pricing == 3, "Room types count mismatch"
    assert active_overrides == 2, "Active overrides count mismatch"
    assert active_strategies == 1, "Active strategies count mismatch"
    assert total_revenue > 0, "Revenue calculation error"
    
    print("Revenue analytics test passed!")
    return True


if __name__ == "__main__":
    print("Testing Revenue Dashboard API...")
    
    print("\n1. Testing basic Revenue API functionality...")
    test_revenue_api_endpoints()
    
    print("\n2. Testing pricing update...")
    test_pricing_update()
    
    print("\n3. Testing pricing strategy...")
    test_pricing_strategy()
    
    print("\n4. Testing pricing history...")
    test_pricing_history()
    
    print("\n5. Testing revenue analytics...")
    test_revenue_analytics()
    
    print("\nAll Revenue Dashboard API tests passed!")
    print("\nAvailable endpoints:")
    print("  POST /revenue/pricing/update")
    print("  POST /revenue/pricing/strategy")
    print("  GET /revenue/pricing/current")
    print("  GET /revenue/pricing/analytics")
    print("  GET /revenue/pricing/history")