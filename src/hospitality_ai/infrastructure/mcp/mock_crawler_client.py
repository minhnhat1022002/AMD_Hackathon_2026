"""Mock MCP crawler client for local development and tests."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any, Mapping, Sequence

from hospitality_ai.domain.enums import CrawlerStatus, Platform
from hospitality_ai.domain.models import CrawlerRunMetric


class MockCrawlerClient:
    """Returns deterministic sample pricing and crawler metrics."""

    def __init__(self, now: datetime | None = None) -> None:
        self._now = now or datetime.now(timezone.utc)

    def fetch_pricing_records(self) -> Sequence[Mapping[str, Any]]:
        """Return raw records shaped like a future MCP crawler response."""

        crawled_at = self._now - timedelta(hours=2)
        check_in_standard = date(2026, 6, 1)
        check_in_deluxe = date(2026, 6, 2)
        return [
            {
                "hotel_id": "hotel_own",
                "hotel_name": "Sunrise Central Hotel",
                "platform": "booking",
                "room_type": "standard",
                "check_in_date": check_in_standard.isoformat(),
                "price": "120",
                "tax": "12",
                "discount": "10",
                "crawled_at": crawled_at.isoformat(),
            },
            {
                "hotel_id": "hotel_own",
                "hotel_name": "Sunrise Central Hotel",
                "platform": "expedia",
                "room_type": "standard",
                "check_in_date": check_in_standard.isoformat(),
                "price": "123",
                "tax": "12",
                "discount": "0",
                "crawled_at": crawled_at.isoformat(),
            },
            {
                "hotel_id": "hotel_comp_a",
                "hotel_name": "River Gate Hotel",
                "platform": "booking",
                "room_type": "standard",
                "check_in_date": check_in_standard.isoformat(),
                "price": "130",
                "tax": "13",
                "discount": "0",
                "crawled_at": crawled_at.isoformat(),
            },
            {
                "hotel_id": "hotel_comp_b",
                "hotel_name": "Lotus Boutique Hotel",
                "platform": "expedia",
                "room_type": "standard",
                "check_in_date": check_in_standard.isoformat(),
                "price": "115",
                "tax": "11",
                "discount": "5",
                "crawled_at": crawled_at.isoformat(),
            },
            {
                "hotel_id": "hotel_comp_c",
                "hotel_name": "Market View Hotel",
                "platform": "trip.com",
                "room_type": "standard",
                "check_in_date": check_in_standard.isoformat(),
                "price": "125",
                "tax": "12",
                "discount": "0",
                "crawled_at": crawled_at.isoformat(),
            },
            {
                "hotel_id": "hotel_own",
                "hotel_name": "Sunrise Central Hotel",
                "platform": "booking",
                "room_type": "deluxe",
                "check_in_date": check_in_deluxe.isoformat(),
                "price": "190",
                "tax": "19",
                "discount": "0",
                "crawled_at": crawled_at.isoformat(),
            },
            {
                "hotel_id": "hotel_own",
                "hotel_name": "Sunrise Central Hotel",
                "platform": "expedia",
                "room_type": "deluxe",
                "check_in_date": check_in_deluxe.isoformat(),
                "price": "188",
                "tax": "18",
                "discount": "10",
                "crawled_at": crawled_at.isoformat(),
            },
            {
                "hotel_id": "hotel_comp_a",
                "hotel_name": "River Gate Hotel",
                "platform": "booking",
                "room_type": "deluxe",
                "check_in_date": check_in_deluxe.isoformat(),
                "price": "170",
                "tax": "17",
                "discount": "0",
                "crawled_at": crawled_at.isoformat(),
            },
            {
                "hotel_id": "hotel_comp_b",
                "hotel_name": "Lotus Boutique Hotel",
                "platform": "expedia",
                "room_type": "deluxe",
                "check_in_date": check_in_deluxe.isoformat(),
                "price": "172",
                "tax": "16",
                "discount": "0",
                "crawled_at": crawled_at.isoformat(),
            },
            {
                "hotel_id": "hotel_comp_c",
                "hotel_name": "Market View Hotel",
                "platform": "trip.com",
                "room_type": "deluxe",
                "check_in_date": check_in_deluxe.isoformat(),
                "price": None,
                "tax": "0",
                "discount": "0",
                "crawled_at": crawled_at.isoformat(),
            },
        ]

    def fetch_crawler_runs(self) -> Sequence[CrawlerRunMetric]:
        """Return sample crawler run telemetry."""

        base = self._now - timedelta(hours=3)
        return [
            CrawlerRunMetric(
                run_id="run_booking_001",
                platform=Platform.BOOKING,
                status=CrawlerStatus.SUCCESS,
                started_at=base,
                finished_at=base + timedelta(seconds=34),
                records_found=4,
            ),
            CrawlerRunMetric(
                run_id="run_expedia_001",
                platform=Platform.EXPEDIA,
                status=CrawlerStatus.SUCCESS,
                started_at=base + timedelta(minutes=5),
                finished_at=base + timedelta(minutes=5, seconds=41),
                records_found=4,
            ),
            CrawlerRunMetric(
                run_id="run_trip_001",
                platform=Platform.TRIP,
                status=CrawlerStatus.FAILED,
                started_at=base + timedelta(minutes=10),
                finished_at=base + timedelta(minutes=10, seconds=18),
                records_found=1,
                error_message="Trip.com returned partial room inventory.",
            ),
            CrawlerRunMetric(
                run_id="run_booking_002",
                platform=Platform.BOOKING,
                status=CrawlerStatus.SUCCESS,
                started_at=base + timedelta(minutes=15),
                finished_at=base + timedelta(minutes=15, seconds=29),
                records_found=4,
            ),
        ]
