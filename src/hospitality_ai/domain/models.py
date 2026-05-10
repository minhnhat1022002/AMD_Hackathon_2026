"""Domain models for pricing insight and performance monitoring."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Mapping, Optional

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
    recommended_price: Decimal = Decimal("0.00")
    benchmark_basis: str = ""
    benchmark_reasoning: str = ""
    confidence: str = "medium"
    competitor_room_types: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class PricingInsightReport:
    """Pricing insight report for a hotel."""

    own_hotel_id: str
    generated_at: datetime
    insights: list[PricingInsight]
    summary: str
    pricing_records: list[PricingRecord] = field(default_factory=list)


@dataclass(frozen=True)
class OwnRoomPricingContext:
    """LLM-facing context for one own room/date benchmark target."""

    room_key: str
    room_type: str
    check_in_date: date
    current_price: Decimal


@dataclass(frozen=True)
class CompetitorRoomPricingContext:
    """LLM-facing context for one competitor room candidate."""

    record_id: str
    hotel_id: str
    hotel_name: str
    room_type: str
    check_in_date: date
    total_price: Decimal


@dataclass(frozen=True)
class PricingMarketContext:
    """Structured market context used to select comparable rooms."""

    own_hotel_id: str
    own_rooms: list[OwnRoomPricingContext]
    competitor_rooms: list[CompetitorRoomPricingContext]


@dataclass(frozen=True)
class ComparableRoomSelection:
    """LLM-selected competitor records for one own room benchmark."""

    room_key: str
    comparable_record_ids: list[str]
    benchmark_basis: str
    reasoning: str
    confidence: str = "medium"


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


@dataclass(frozen=True)
class TripPriceQuery:
    """Trip.com price collection query."""

    hotel_urls: list[str] = field(default_factory=list)
    hotel_names: list[str] = field(default_factory=list)
    check_in_dates: list[date] = field(default_factory=list)
    check_out_date: Optional[date] = None
    adults: int = 2
    children: int = 0
    rooms: int = 1
    currency: Optional[str] = None
    include_raw: bool = True


@dataclass(frozen=True)
class TripPriceCollection:
    """Processed Trip.com price collection result."""

    source: str
    run_at: datetime
    total_raw_records: int
    normalized_records: list[PricingRecord]
    skipped_records: int
    run_metric: CrawlerRunMetric
    raw_response: Mapping[str, Any]
