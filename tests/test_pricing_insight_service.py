"""Unit tests for pricing insight service."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Mapping, Sequence

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


class DifferentRoomTypeCrawlerClient:
    """Crawler fixture where competitor room names do not exactly match."""

    def fetch_pricing_records(self) -> Sequence[Mapping[str, Any]]:
        crawled_at = datetime(2026, 5, 10, tzinfo=timezone.utc).isoformat()
        check_in_date = "2026-05-10"
        competitor_rooms = [
            ("hotel_comp_a", "Comp A", "Premier Room", "900"),
            ("hotel_comp_a", "Comp A", "Executive Room", "950"),
            ("hotel_comp_b", "Comp B", "Premium Twin", "1000"),
            ("hotel_comp_b", "Comp B", "Premium Double", "1050"),
            ("hotel_comp_c", "Comp C", "Executive City View", "1100"),
            ("hotel_comp_c", "Comp C", "Premier City View", "1150"),
            ("hotel_comp_d", "Comp D", "Grand Suite", "5000"),
            ("hotel_comp_d", "Comp D", "Signature Suite", "5100"),
            ("hotel_comp_e", "Comp E", "Junior Suite", "5200"),
            ("hotel_comp_e", "Comp E", "Family Suite", "5300"),
            ("hotel_comp_f", "Comp F", "Grand Family Room", "5400"),
            ("hotel_comp_f", "Comp F", "Presidential Suite", "5500"),
        ]
        records: list[Mapping[str, Any]] = [
            {
                "hotel_id": "hotel_own",
                "hotel_name": "Own Hotel",
                "platform": "trip.com",
                "room_type": "Premium Double City View",
                "check_in_date": check_in_date,
                "price": "1000",
                "tax": "0",
                "discount": "0",
                "crawled_at": crawled_at,
            }
        ]
        for hotel_id, hotel_name, room_type, price in competitor_rooms:
            records.append(
                {
                    "hotel_id": hotel_id,
                    "hotel_name": hotel_name,
                    "platform": "trip.com",
                    "room_type": room_type,
                    "check_in_date": check_in_date,
                    "price": price,
                    "tax": "0",
                    "discount": "0",
                    "crawled_at": crawled_at,
                }
            )
        return records

    def fetch_crawler_runs(self) -> Sequence:
        return []


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


def test_generate_pricing_insight_uses_comparable_room_selection() -> None:
    """Service should not benchmark each room against all competitor rooms."""

    service = PricingInsightService(
        crawler_client=DifferentRoomTypeCrawlerClient(),
        pricing_repository=InMemoryPricingRepository(),
        llm_client=MockLLMClient(),
        recommendation_service=RecommendationService(
            threshold_percent=Decimal("5"),
        ),
        own_hotel_id="hotel_own",
    )

    report = service.generate_report()

    assert len(report.insights) == 1
    insight = report.insights[0]

    assert insight.room_type == "Premium Double City View"
    assert insight.competitor_count == 8
    assert insight.competitor_count < 12
    assert insight.benchmark_basis == "room_category_price_tier_match"
    assert insight.average_competitor_price < Decimal("3000")
    assert insight.recommended_price > Decimal("0")
    assert "Matched by room category" in insight.benchmark_reasoning
