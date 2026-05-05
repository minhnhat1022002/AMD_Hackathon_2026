"""In-memory pricing repository."""

from __future__ import annotations

from typing import Sequence

from hospitality_ai.domain.models import PricingRecord


class InMemoryPricingRepository:
    """Simple repository useful for local demos and unit tests."""

    def __init__(self) -> None:
        self._records: list[PricingRecord] = []

    def save_many(self, records: Sequence[PricingRecord]) -> None:
        """Persist records in memory."""

        self._records.extend(records)

    def list_pricing_records(self) -> Sequence[PricingRecord]:
        """Return all in-memory pricing records."""

        return list(self._records)
