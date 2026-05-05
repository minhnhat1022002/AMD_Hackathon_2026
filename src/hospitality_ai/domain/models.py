"""Domain models for pricing insight and performance monitoring."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from hospitality_ai.domain.enums import (
    AlertSeverity,
    CrawlerStatus,
    PipelineStatus,
    Platform,
    RecommendationAction,
)


@dataclass(frozen=True)
class PricingRecord:
    """Normalized OTA pricing record."""

    hotel_id: str
    hotel_name: str
    platform: Platform
    room_type: str
    check_in_date: date
    price: Decimal
    tax: Decimal
    discount: Decimal
    crawled_at: datetime

    @property
    def total_price(self) -> Decimal:
        """Return net price paid by a guest after tax and discount."""

        return self.price + self.tax - self.discount


@dataclass(frozen=True)
class PricingInsight:
    """Computed pricing comparison for one room type and check-in date."""

    room_type: str
    check_in_date: date
    current_price: Decimal
    average_competitor_price: Decimal
    min_competitor_price: Decimal
    max_competitor_price: Decimal
    price_gap: Decimal
    price_gap_percentage: Decimal
    recommendation: RecommendationAction
    competitor_count: int


@dataclass(frozen=True)
class PricingInsightReport:
    """Pricing insight report for a hotel."""

    own_hotel_id: str
    generated_at: datetime
    insights: list[PricingInsight]
    summary: str


@dataclass(frozen=True)
class CrawlerRunMetric:
    """Telemetry from one crawler execution."""

    run_id: str
    platform: Platform
    status: CrawlerStatus
    started_at: datetime
    finished_at: datetime
    records_found: int
    error_message: Optional[str] = None

    @property
    def duration_seconds(self) -> float:
        """Return crawl duration in seconds."""

        return max(
            0.0,
            (self.finished_at - self.started_at).total_seconds(),
        )


@dataclass(frozen=True)
class MonitoringAlert:
    """Actionable monitoring alert."""

    code: str
    severity: AlertSeverity
    message: str


@dataclass(frozen=True)
class MonitoringReport:
    """Aggregated monitoring report for crawler and pricing pipeline."""

    generated_at: datetime
    status: PipelineStatus
    crawl_success_rate_percent: Decimal
    failed_crawl_count: int
    average_crawl_duration_seconds: Decimal
    data_freshness_minutes: Decimal
    missing_price_records: int
    price_anomaly_count: int
    alerts: list[MonitoringAlert] = field(default_factory=list)
    summary: str = ""


@dataclass(frozen=True)
class StrategyRecommendation:
    """High-level strategy output combining pricing and monitoring signals."""

    generated_at: datetime
    pricing_actions: list[RecommendationAction]
    monitoring_status: PipelineStatus
    summary: str
