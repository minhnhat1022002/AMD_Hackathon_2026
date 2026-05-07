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
        choices=["pricing-insight", "performance-monitoring", "trip-price"],
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
    elif args.command == "performance-monitoring":
        result = PerformanceMonitoringAgent(
            container["monitoring_service"],
        ).run()
    else:
        result = container["trip_price_service"].collect(
            container["trip_price_query"],
        )
        result = to_jsonable(result)

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
        OpenAICompatibleLLMClient,
    )
    from hospitality_ai.infrastructure.mcp.mock_crawler_client import (
        MockCrawlerClient,
    )
    from hospitality_ai.infrastructure.mcp.trip_mcp_crawler_client import (
        TripMcpCrawlerClient,
    )
    from hospitality_ai.infrastructure.mcp.trip_price_api_client import (
        MockTripPriceApiClient,
        TripOtaPriceApiClient,
    )
    from hospitality_ai.infrastructure.repositories import (
        InMemoryPricingRepository,
    )
    from hospitality_ai.application.trip_price_service import TripPriceService

    trip_api_client = (
        TripOtaPriceApiClient(
            base_url=settings.trip_price_api_base_url,
            timeout_seconds=settings.trip_price_api_timeout_seconds,
        )
        if settings.trip_price_api_mode == "http"
        else MockTripPriceApiClient()
    )
    trip_price_service = TripPriceService(trip_api_client)
    trip_price_query = settings.build_trip_price_query()
    crawler_client = (
        TripMcpCrawlerClient(
            trip_price_service=trip_price_service,
            query=trip_price_query,
        )
        if settings.crawler_source == "trip-api"
        else MockCrawlerClient()
    )
    pricing_repository = InMemoryPricingRepository()
    llm_client = (
        OpenAICompatibleLLMClient(
            api_key=settings.llm_api_key,
            model_name=settings.llm_model,
            base_url=settings.llm_base_url,
            timeout_seconds=settings.llm_timeout_seconds,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
        )
        if settings.use_real_llm
        else MockLLMClient(model_name=settings.llm_model)
    )
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
        "trip_price_service": trip_price_service,
        "trip_price_query": trip_price_query,
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

    if "normalized_records" in result:
        lines = [
            (
                "Trip Price API: {total_raw_records} raw records, "
                "{skipped_records} skipped"
            ).format(**result),
            "",
        ]
        for record in result["normalized_records"]:
            lines.append(
                "{hotel_id} {room_type} {check_in_date}: "
                "price={price}, tax={tax}, discount={discount}".format(
                    **record,
                ),
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
