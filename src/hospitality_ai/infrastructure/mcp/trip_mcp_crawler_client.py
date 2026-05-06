"""Crawler client adapter backed by Trip Price MCP/API service."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from hospitality_ai.application.trip_price_service import (
    TripPriceService,
    to_crawler_payloads,
)
from hospitality_ai.domain.models import CrawlerRunMetric, TripPriceQuery


class TripMcpCrawlerClient:
    """Expose processed Trip Price API data through the crawler port."""

    def __init__(
        self,
        trip_price_service: TripPriceService,
        query: TripPriceQuery,
    ) -> None:
        self._trip_price_service = trip_price_service
        self._query = query
        self._cached_payloads: list[dict[str, Any]] | None = None
        self._cached_run_metric: CrawlerRunMetric | None = None

    def fetch_pricing_records(self) -> Sequence[Mapping[str, Any]]:
        """Return Trip.com prices in normalized crawler payload shape."""

        self._ensure_collection()
        return list(self._cached_payloads or [])

    def fetch_crawler_runs(self) -> Sequence[CrawlerRunMetric]:
        """Return the latest Trip.com collection run metric."""

        self._ensure_collection()
        if self._cached_run_metric is None:
            return []
        return [self._cached_run_metric]

    def _ensure_collection(self) -> None:
        if self._cached_payloads is not None:
            return
        collection = self._trip_price_service.collect(self._query)
        self._cached_payloads = to_crawler_payloads(collection)
        self._cached_run_metric = collection.run_metric
