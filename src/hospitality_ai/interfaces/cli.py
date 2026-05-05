"""Command line interface for local demos."""

from __future__ import annotations

import argparse
import json
import logging
from typing import Any

from hospitality_ai.agents.performance_monitoring_agent import (
    PerformanceMonitoringAgent,
)
from hospitality_ai.agents.pricing_insight_agent import PricingInsightAgent
from hospitality_ai.config.settings import Settings
from hospitality_ai.interfaces.serialization import to_jsonable


def main() -> None:
    """Run the CLI."""

    parser = argparse.ArgumentParser(
        description="AI Hospitality Optimization & Strategy demo CLI.",
    )
    parser.add_argument(
        "command",
        choices=["pricing-insight", "performance-monitoring"],
    )
    parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="json",
        help="Output format.",
    )
    parser.add_argument(
        "--log-level",
        default="WARNING",
        help="Python logging level.",
    )
    args = parser.parse_args()

    logging.basicConfig(level=getattr(logging, args.log_level.upper()))

    container = build_container(Settings.from_env())
    if args.command == "pricing-insight":
        result = PricingInsightAgent(
            container["pricing_service"],
        ).run()
    else:
        result = PerformanceMonitoringAgent(
            container["monitoring_service"],
        ).run()

    if args.format == "json":
        print(json.dumps(to_jsonable(result), indent=2))
    else:
        print(_format_text(result))


def build_container(settings: Settings) -> dict[str, Any]:
    """Build local demo dependencies."""

    from hospitality_ai.application.performance_monitoring_service import (
        PerformanceMonitoringService,
    )
    from hospitality_ai.application.pricing_insight_service import (
        PricingInsightService,
    )
    from hospitality_ai.application.recommendation_service import (
        RecommendationService,
    )
    from hospitality_ai.infrastructure.llm.langchain_client import (
        MockLLMClient,
    )
    from hospitality_ai.infrastructure.mcp.mock_crawler_client import (
        MockCrawlerClient,
    )
    from hospitality_ai.infrastructure.repositories import (
        InMemoryPricingRepository,
    )

    crawler_client = MockCrawlerClient()
    pricing_repository = InMemoryPricingRepository()
    llm_client = MockLLMClient(model_name=settings.llm_model)
    recommendation_service = RecommendationService(
        threshold_percent=settings.recommendation_threshold_percent,
    )
    pricing_service = PricingInsightService(
        crawler_client=crawler_client,
        pricing_repository=pricing_repository,
        llm_client=llm_client,
        recommendation_service=recommendation_service,
        own_hotel_id=settings.own_hotel_id,
    )
    monitoring_service = PerformanceMonitoringService(
        crawler_client=crawler_client,
        pricing_repository=pricing_repository,
        llm_client=llm_client,
        min_success_rate_percent=settings.min_success_rate_percent,
        max_failed_crawl_count=settings.max_failed_crawl_count,
        data_freshness_threshold_hours=(
            settings.data_freshness_threshold_hours
        ),
    )
    return {
        "crawler_client": crawler_client,
        "pricing_repository": pricing_repository,
        "llm_client": llm_client,
        "recommendation_service": recommendation_service,
        "pricing_service": pricing_service,
        "monitoring_service": monitoring_service,
    }


def _format_text(result: dict[str, Any]) -> str:
    summary = result.get("summary", "")
    if "insights" in result:
        lines = [summary, ""]
        for insight in result["insights"]:
            lines.append(
                "{room_type} {check_in_date}: current={current_price}, "
                "competitor_avg={average_competitor_price}, "
                "gap={price_gap_percentage}%, recommendation={recommendation}"
                .format(**insight),
            )
        return "\n".join(lines).strip()

    lines = [summary, ""]
    for alert in result.get("alerts", []):
        lines.append(
            "[{severity}] {code}: {message}".format(**alert),
        )
    return "\n".join(lines).strip()


if __name__ == "__main__":
    main()
