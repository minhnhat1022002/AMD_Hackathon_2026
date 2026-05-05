"""Unit tests for performance monitoring service."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from hospitality_ai.application.performance_monitoring_service import (
    PerformanceMonitoringService,
)
from hospitality_ai.domain.enums import PipelineStatus
from hospitality_ai.infrastructure.llm.langchain_client import MockLLMClient
from hospitality_ai.infrastructure.mcp.mock_crawler_client import (
    MockCrawlerClient,
)
from hospitality_ai.infrastructure.repositories import (
    InMemoryPricingRepository,
)


def test_generate_monitoring_report_with_mock_data() -> None:
    """Service computes crawler health metrics and alerts."""

    service = PerformanceMonitoringService(
        crawler_client=MockCrawlerClient(
            now=datetime(2026, 5, 6, tzinfo=timezone.utc),
        ),
        pricing_repository=InMemoryPricingRepository(),
        llm_client=MockLLMClient(),
        min_success_rate_percent=Decimal("95"),
        max_failed_crawl_count=0,
        data_freshness_threshold_hours=24,
    )

    report = service.generate_report()

    assert report.status == PipelineStatus.CRITICAL
    assert report.crawl_success_rate_percent == Decimal("75.00")
    assert report.failed_crawl_count == 1
    assert report.missing_price_records == 1
    assert {alert.code for alert in report.alerts} == {
        "LOW_CRAWL_SUCCESS_RATE",
        "FAILED_CRAWL_COUNT_HIGH",
        "MISSING_PRICE_RECORDS",
    }
    assert "pipeline status" in report.summary.lower()
