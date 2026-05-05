"""Unit tests for pricing insight service."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from hospitality_ai.application.pricing_insight_service import (
    PricingInsightService,
)
from hospitality_ai.application.recommendation_service import (
    RecommendationService,
)
from hospitality_ai.domain.enums import RecommendationAction
from hospitality_ai.infrastructure.llm.langchain_client import MockLLMClient
from hospitality_ai.infrastructure.mcp.mock_crawler_client import (
    MockCrawlerClient,
)
from hospitality_ai.infrastructure.repositories import (
    InMemoryPricingRepository,
)


def test_generate_pricing_insight_report() -> None:
    """Service computes competitor benchmark and recommendation."""

    service = PricingInsightService(
        crawler_client=MockCrawlerClient(
            now=datetime(2026, 5, 6, tzinfo=timezone.utc),
        ),
        pricing_repository=InMemoryPricingRepository(),
        llm_client=MockLLMClient(),
        recommendation_service=RecommendationService(
            threshold_percent=Decimal("5"),
        ),
        own_hotel_id="hotel_own",
    )

    report = service.generate_report()

    assert len(report.insights) == 2
    standard = report.insights[0]
    deluxe = report.insights[1]

    assert standard.room_type == "standard"
    assert standard.current_price == Decimal("128.50")
    assert standard.average_competitor_price == Decimal("133.67")
    assert standard.recommendation == RecommendationAction.KEEP_PRICE

    assert deluxe.room_type == "deluxe"
    assert deluxe.price_gap_percentage == Decimal("8.00")
    assert deluxe.recommendation == RecommendationAction.DECREASE_PRICE
    assert "pricing" in report.summary.lower()
