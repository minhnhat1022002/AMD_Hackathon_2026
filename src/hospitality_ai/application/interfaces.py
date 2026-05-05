"""Application ports used by services.

The application layer depends on these protocols instead of concrete
infrastructure classes. This keeps crawler, storage, and LLM providers
replaceable in local tests and production deployments.
"""

from __future__ import annotations

from typing import Any, Mapping, Protocol, Sequence

from hospitality_ai.domain.models import (
    CrawlerRunMetric,
    MonitoringReport,
    PricingInsightReport,
    PricingRecord,
)


class CrawlerClient(Protocol):
    """Port for reading OTA pricing and crawler telemetry."""

    def fetch_pricing_records(self) -> Sequence[Mapping[str, Any]]:
        """Fetch raw pricing records from a crawler or MCP tool."""

    def fetch_crawler_runs(self) -> Sequence[CrawlerRunMetric]:
        """Fetch crawler execution metrics."""


class PricingRepository(Protocol):
    """Port for pricing persistence."""

    def save_many(self, records: Sequence[PricingRecord]) -> None:
        """Persist normalized pricing records."""

    def list_pricing_records(self) -> Sequence[PricingRecord]:
        """Return normalized pricing records."""


class LLMClient(Protocol):
    """Port for creating business-friendly text summaries."""

    def summarize_pricing_insight(
        self,
        report: PricingInsightReport,
    ) -> str:
        """Summarize a pricing insight report."""

    def summarize_monitoring(self, report: MonitoringReport) -> str:
        """Summarize a monitoring report."""
