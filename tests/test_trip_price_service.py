"""Unit tests for Trip Price API processing."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Mapping

from hospitality_ai.application.trip_price_service import (
    TripPriceService,
    to_crawler_payloads,
    to_llm_ready_trip_payload,
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


class FakeRawTripPriceApiClient:
    """Fake client returning raw Trip fields from ota-crawl."""

    async def collect_prices(
        self,
        query: TripPriceQuery,
    ) -> Mapping[str, Any]:
        return {
            "source": "trip",
            "total": 1,
            "run_at": "2026-05-08T05:13:18.505371Z",
            "data": [
                {
                    "is_found": True,
                    "hotel_name": "Nhat Ha L'Opera Hotel",
                    "property_id": "2192602",
                    "room_type": "Business (Without Window)",
                    "price_before_tax": 1596552.0,
                    "price_after_tax": 3407012.0,
                    "tax_and_fee": 1810460.0,
                    "check_in_date": "2026-05-08",
                    "raw": {
                        "price_info": {"price": 1596552},
                        "total_price_info": {
                            "totalNoApprox": {
                                "content": "VND 1,810,460",
                            },
                            "payTax": {"price": 213908},
                        },
                    },
                },
            ],
        }


def test_trip_price_service_prefers_nested_raw_price_fields() -> None:
    """Service avoids double-counted top-level raw price fields."""

    service = TripPriceService(FakeRawTripPriceApiClient())

    collection = service.collect(
        TripPriceQuery(
            hotel_urls=[
                (
                    "https://vn.trip.com/hotels/ho-chi-minh-city-hotel-"
                    "detail-2192602/nhat-ha-3-hotel/"
                ),
            ],
            check_in_dates=[date(2026, 5, 8)],
            currency="VND",
        ),
    )

    record = collection.normalized_records[0]
    assert record.price == Decimal("1596552.00")
    assert record.tax == Decimal("213908.00")
    assert record.total_price == Decimal("1810460.00")

    llm_payload = to_llm_ready_trip_payload(collection)
    assert "raw_response" not in llm_payload
    assert llm_payload["records"][0]["total_price"] == "1810460.00"
