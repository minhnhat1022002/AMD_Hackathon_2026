"""Application ports used by services.

The application layer depends on these protocols instead of concrete
infrastructure classes. This keeps crawler, storage, and LLM providers
replaceable in local tests and production deployments.
"""

from __future__ import annotations

from typing import Any, Mapping, Protocol, Sequence

from hospitality_ai.domain.models import (
    ComparableRoomSelection,
    CrawlerRunMetric,
    MonitoringReport,
    PricingInsightReport,
    PricingMarketContext,
    PricingRecord,
    TripPriceQuery,
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

    def select_comparable_rooms(
        self,
        context: PricingMarketContext,
    ) -> Sequence[ComparableRoomSelection]:
        """Select competitor rooms comparable to each own room/date."""

    def summarize_pricing_insight(
        self,
        report: PricingInsightReport,
    ) -> str:
        """Summarize a pricing insight report."""

    def summarize_monitoring(self, report: MonitoringReport) -> str:
        """Summarize a monitoring report."""


class TripPriceApiClient(Protocol):
    """Port for collecting Trip.com price data."""

    async def collect_prices(
        self,
        query: TripPriceQuery,
    ) -> Mapping[str, Any]:
        """Collect Trip.com price data from API, MCP, or mock adapter."""
