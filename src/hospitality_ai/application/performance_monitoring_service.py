"""Performance monitoring service."""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from statistics import median
from typing import Any, Mapping, Sequence

from hospitality_ai.application.interfaces import (
    CrawlerClient,
    LLMClient,
    PricingRepository,
)
from hospitality_ai.application.pricing_insight_service import (
    normalize_pricing_record,
    quantize_money,
)
from hospitality_ai.domain.enums import (
    AlertSeverity,
    CrawlerStatus,
    PipelineStatus,
)
from hospitality_ai.domain.exceptions import InvalidPricingRecordError
from hospitality_ai.domain.models import (
    CrawlerRunMetric,
    MonitoringAlert,
    MonitoringReport,
    PricingRecord,
)

logger = logging.getLogger(__name__)


class PerformanceMonitoringService:
    """Computes crawler and pricing pipeline health metrics."""

    def __init__(
        self,
        crawler_client: CrawlerClient,
        pricing_repository: PricingRepository,
        llm_client: LLMClient,
        min_success_rate_percent: Decimal,
        max_failed_crawl_count: int,
        data_freshness_threshold_hours: int,
    ) -> None:
        self._crawler_client = crawler_client
        self._pricing_repository = pricing_repository
        self._llm_client = llm_client
        self._min_success_rate_percent = min_success_rate_percent
        self._max_failed_crawl_count = max_failed_crawl_count
        self._data_freshness_threshold_hours = (
            data_freshness_threshold_hours
        )

    def generate_report(self) -> MonitoringReport:
        """Generate a monitoring report from crawler telemetry and prices."""

        runs = list(self._crawler_client.fetch_crawler_runs())
        raw_records = list(self._crawler_client.fetch_pricing_records())
        records = self._normalize_valid_records(raw_records)
        self._pricing_repository.save_many(records)

        success_rate = self._calculate_success_rate(runs)
        failed_count = self._count_failed_runs(runs)
        average_duration = self._calculate_average_duration(runs)
        data_freshness = self._calculate_data_freshness_minutes(records)
        missing_records = self._count_missing_price_records(raw_records)
        anomaly_count = self._count_price_anomalies(records)
        alerts = self._build_alerts(
            success_rate=success_rate,
            failed_count=failed_count,
            data_freshness_minutes=data_freshness,
            missing_records=missing_records,
            anomaly_count=anomaly_count,
        )
        status = self._derive_pipeline_status(alerts)

        report = MonitoringReport(
            generated_at=datetime.now(timezone.utc),
            status=status,
            crawl_success_rate_percent=quantize_money(success_rate),
            failed_crawl_count=failed_count,
            average_crawl_duration_seconds=quantize_money(average_duration),
            data_freshness_minutes=quantize_money(data_freshness),
            missing_price_records=missing_records,
            price_anomaly_count=anomaly_count,
            alerts=alerts,
            summary="",
        )
        summary = self._llm_client.summarize_monitoring(report)
        return MonitoringReport(
            generated_at=report.generated_at,
            status=report.status,
            crawl_success_rate_percent=report.crawl_success_rate_percent,
            failed_crawl_count=report.failed_crawl_count,
            average_crawl_duration_seconds=(
                report.average_crawl_duration_seconds
            ),
            data_freshness_minutes=report.data_freshness_minutes,
            missing_price_records=report.missing_price_records,
            price_anomaly_count=report.price_anomaly_count,
            alerts=report.alerts,
            summary=summary,
        )

    def _normalize_valid_records(
        self,
        raw_records: Sequence[Mapping[str, Any]],
    ) -> list[PricingRecord]:
        records: list[PricingRecord] = []
        for raw_record in raw_records:
            try:
                record = normalize_pricing_record(raw_record)
            except InvalidPricingRecordError:
                logger.info(
                    "Skipping invalid pricing record: %s",
                    raw_record,
                )
                continue

            if record.price <= Decimal("0"):
                logger.info(
                    "Skipping non-positive price for hotel_id=%s",
                    record.hotel_id,
                )
                continue
            records.append(record)
        return records

    def _calculate_success_rate(
        self,
        runs: Sequence[CrawlerRunMetric],
    ) -> Decimal:
        if not runs:
            return Decimal("0")
        success_count = sum(
            1 for run in runs if run.status == CrawlerStatus.SUCCESS
        )
        return Decimal(success_count) / Decimal(len(runs)) * Decimal("100")

    def _count_failed_runs(
        self,
        runs: Sequence[CrawlerRunMetric],
    ) -> int:
        return sum(1 for run in runs if run.status == CrawlerStatus.FAILED)

    def _calculate_average_duration(
        self,
        runs: Sequence[CrawlerRunMetric],
    ) -> Decimal:
        if not runs:
            return Decimal("0")
        total_duration = sum(
            Decimal(str(run.duration_seconds)) for run in runs
        )
        return total_duration / Decimal(len(runs))

    def _calculate_data_freshness_minutes(
        self,
        records: Sequence[PricingRecord],
    ) -> Decimal:
        if not records:
            return Decimal("999999")

        latest_crawled_at = max(record.crawled_at for record in records)
        freshness_seconds = (
            datetime.now(timezone.utc) - latest_crawled_at
        ).total_seconds()
        return Decimal(str(max(0.0, freshness_seconds / 60)))

    def _count_missing_price_records(
        self,
        raw_records: Sequence[Mapping[str, Any]],
    ) -> int:
        missing_count = 0
        for raw_record in raw_records:
            price = raw_record.get("price")
            if price is None:
                missing_count += 1
                continue
            try:
                if Decimal(str(price)) <= Decimal("0"):
                    missing_count += 1
            except Exception:
                missing_count += 1
        return missing_count

    def _count_price_anomalies(
        self,
        records: Sequence[PricingRecord],
    ) -> int:
        records_by_key: dict[tuple[str, object], list[PricingRecord]] = (
            defaultdict(list)
        )
        for record in records:
            key = (record.room_type, record.check_in_date)
            records_by_key[key].append(record)

        anomaly_count = 0
        for grouped_records in records_by_key.values():
            prices = [record.total_price for record in grouped_records]
            if len(prices) < 3:
                continue

            median_price = Decimal(str(median(prices)))
            if median_price <= Decimal("0"):
                continue

            for price in prices:
                deviation = abs(price - median_price) / median_price
                if deviation > Decimal("0.50"):
                    anomaly_count += 1
        return anomaly_count

    def _build_alerts(
        self,
        success_rate: Decimal,
        failed_count: int,
        data_freshness_minutes: Decimal,
        missing_records: int,
        anomaly_count: int,
    ) -> list[MonitoringAlert]:
        alerts: list[MonitoringAlert] = []

        if success_rate < self._min_success_rate_percent:
            severity = (
                AlertSeverity.CRITICAL
                if success_rate < Decimal("80")
                else AlertSeverity.WARNING
            )
            alerts.append(
                MonitoringAlert(
                    code="LOW_CRAWL_SUCCESS_RATE",
                    severity=severity,
                    message=(
                        "Crawl success rate is below the configured "
                        f"threshold: {quantize_money(success_rate)}%."
                    ),
                ),
            )

        if failed_count > self._max_failed_crawl_count:
            alerts.append(
                MonitoringAlert(
                    code="FAILED_CRAWL_COUNT_HIGH",
                    severity=AlertSeverity.WARNING,
                    message=(
                        "Failed crawl count is above the configured "
                        f"threshold: {failed_count}."
                    ),
                ),
            )

        freshness_threshold_minutes = Decimal(
            self._data_freshness_threshold_hours * 60,
        )
        if data_freshness_minutes > freshness_threshold_minutes:
            alerts.append(
                MonitoringAlert(
                    code="STALE_PRICING_DATA",
                    severity=AlertSeverity.CRITICAL,
                    message=(
                        "Pricing data is stale. Latest valid price record is "
                        f"{quantize_money(data_freshness_minutes)} minutes "
                        "old."
                    ),
                ),
            )

        if missing_records > 0:
            alerts.append(
                MonitoringAlert(
                    code="MISSING_PRICE_RECORDS",
                    severity=AlertSeverity.WARNING,
                    message=(
                        f"{missing_records} raw pricing record(s) have a "
                        "missing or invalid price."
                    ),
                ),
            )

        if anomaly_count > 0:
            alerts.append(
                MonitoringAlert(
                    code="PRICE_ANOMALY_DETECTED",
                    severity=AlertSeverity.WARNING,
                    message=(
                        f"{anomaly_count} pricing record(s) deviate more than "
                        "50% from the room/date median."
                    ),
                ),
            )

        if not alerts:
            alerts.append(
                MonitoringAlert(
                    code="PIPELINE_HEALTHY",
                    severity=AlertSeverity.INFO,
                    message=(
                        "Crawler and pricing pipeline metrics look healthy."
                    ),
                ),
            )

        return alerts

    def _derive_pipeline_status(
        self,
        alerts: Sequence[MonitoringAlert],
    ) -> PipelineStatus:
        if any(alert.severity == AlertSeverity.CRITICAL for alert in alerts):
            return PipelineStatus.CRITICAL
        if any(alert.severity == AlertSeverity.WARNING for alert in alerts):
            return PipelineStatus.DEGRADED
        return PipelineStatus.HEALTHY
