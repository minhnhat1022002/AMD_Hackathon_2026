"""Unit tests for Trip Price API processing."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Mapping

from hospitality_ai.application.trip_price_service import (
    TripPriceService,
    to_crawler_payloads,
)
from hospitality_ai.domain.enums import CrawlerStatus, Platform
from hospitality_ai.domain.models import TripPriceQuery


class FakeTripPriceApiClient:
    """Fake Trip Price API client returning ota-crawl style data."""

    async def collect_prices(
        self,
        query: TripPriceQuery,
    ) -> Mapping[str, Any]:
        return {
            "status": 200,
            "success": True,
            "data": {
                "result": {
                    "source": "trip",
                    "total": 2,
                    "run_at": "2026-05-07T02:00:00+00:00",
                    "data": [
                        {
                            "is_found": True,
                            "hotel_name": "Sunrise Central Hotel",
                            "property_id": "hotel_own",
                            "room_type": "standard",
                            "price_before_tax": "100",
                            "price_after_tax": "112",
                            "discount": "5",
                            "checkin_date": "2026-06-01",
                        },
                        {
                            "is_found": False,
                            "error": "No Trip.com room payload captured",
                        },
                    ],
                },
            },
        }


def test_trip_price_service_normalizes_ota_crawl_response() -> None:
    """Trip service maps Trip API records into domain pricing records."""

    service = TripPriceService(FakeTripPriceApiClient())

    collection = service.collect(
        TripPriceQuery(
            hotel_urls=[
                "https://www.trip.com/hotels/detail?hotelId=hotel_own",
            ],
            check_in_dates=[date(2026, 6, 1)],
            currency="VND",
        ),
    )

    assert collection.source == "trip"
    assert collection.total_raw_records == 2
    assert collection.skipped_records == 1
    assert collection.run_metric.status == CrawlerStatus.SUCCESS

    record = collection.normalized_records[0]
    assert record.hotel_id == "hotel_own"
    assert record.hotel_name == "Sunrise Central Hotel"
    assert record.platform == Platform.TRIP
    assert record.price == Decimal("100.00")
    assert record.tax == Decimal("12.00")
    assert record.discount == Decimal("5.00")
    assert record.crawled_at == datetime(
        2026,
        5,
        7,
        2,
        0,
        tzinfo=timezone.utc,
    )

    crawler_payloads = to_crawler_payloads(collection)
    assert crawler_payloads == [
        {
            "hotel_id": "hotel_own",
            "hotel_name": "Sunrise Central Hotel",
            "platform": "trip.com",
            "room_type": "standard",
            "check_in_date": "2026-06-01",
            "price": "100.00",
            "tax": "12.00",
            "discount": "5.00",
            "crawled_at": "2026-05-07T02:00:00+00:00",
        }
    ]
