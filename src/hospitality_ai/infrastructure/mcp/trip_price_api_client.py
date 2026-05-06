"""Trip Price API clients."""

from __future__ import annotations

import asyncio
import json
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone
from typing import Any, Mapping

from hospitality_ai.domain.exceptions import CrawlerClientError
from hospitality_ai.domain.models import TripPriceQuery


class TripOtaPriceApiClient:
    """HTTP adapter for the ota-crawl Trip price endpoint."""

    def __init__(self, base_url: str, timeout_seconds: float = 90.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds

    async def collect_prices(
        self,
        query: TripPriceQuery,
    ) -> Mapping[str, Any]:
        """POST to ``/v1/prices/collect/trip`` and return decoded JSON."""

        return await asyncio.to_thread(self._post_collect_prices, query)

    def _post_collect_prices(
        self,
        query: TripPriceQuery,
    ) -> Mapping[str, Any]:
        payload = _to_api_payload(query)
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url=f"{self._base_url}/v1/prices/collect/trip",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(
                request,
                timeout=self._timeout_seconds,
            ) as response:
                response_body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            raise CrawlerClientError(
                f"Trip Price API returned HTTP {exc.code}: {error_body}",
            ) from exc
        except urllib.error.URLError as exc:
            raise CrawlerClientError(
                f"Cannot connect to Trip Price API: {exc.reason}",
            ) from exc

        return json.loads(response_body)


class MockTripPriceApiClient:
    """Local Trip Price API mock with an ota-crawl-compatible envelope."""

    async def collect_prices(
        self,
        query: TripPriceQuery,
    ) -> Mapping[str, Any]:
        """Return deterministic Trip.com records for local development."""

        run_at = datetime.now(timezone.utc) - timedelta(minutes=20)
        check_in_date = (
            query.check_in_dates[0]
            if query.check_in_dates
            else date(2026, 6, 1)
        )
        urls = query.hotel_urls or [
            "https://www.trip.com/hotels/detail?hotelId=hotel_own",
            "https://www.trip.com/hotels/detail?hotelId=hotel_comp_a",
            "https://www.trip.com/hotels/detail?hotelId=hotel_comp_b",
        ]
        records = _build_mock_records(urls, check_in_date, run_at)
        return {
            "status": 200,
            "success": True,
            "message": "COLLECT_SUCCESS",
            "data": {
                "object_keys": [],
                "result": {
                    "source": "trip",
                    "total": len(records),
                    "run_at": run_at.isoformat(),
                    "hotel_urls": urls,
                    "data": records,
                },
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


def _to_api_payload(query: TripPriceQuery) -> dict[str, Any]:
    return {
        "hotel_urls": query.hotel_urls or None,
        "hotel_names": query.hotel_names or None,
        "check_in_dates": [
            value.isoformat() for value in query.check_in_dates
        ] or None,
        "check_out_date": (
            query.check_out_date.isoformat()
            if query.check_out_date
            else None
        ),
        "adults": query.adults,
        "children": query.children,
        "rooms": query.rooms,
        "currency": query.currency,
        "include_raw": query.include_raw,
        "background_job": False,
    }


def _build_mock_records(
    hotel_urls: list[str],
    check_in_date: date,
    run_at: datetime,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    price_matrix = [
        ("hotel_own", "Sunrise Central Hotel", "standard", 126, 13, 4),
        ("hotel_own", "Sunrise Central Hotel", "deluxe", 198, 20, 0),
        ("hotel_comp_a", "River Gate Hotel", "standard", 132, 14, 0),
        ("hotel_comp_a", "River Gate Hotel", "deluxe", 174, 18, 0),
        ("hotel_comp_b", "Lotus Boutique Hotel", "standard", 118, 12, 3),
        ("hotel_comp_b", "Lotus Boutique Hotel", "deluxe", 176, 17, 0),
    ]
    for (
        property_id,
        name,
        room_type,
        before_tax,
        tax,
        discount,
    ) in price_matrix:
        input_url = _pick_url_for_property(hotel_urls, property_id)
        if input_url is None:
            continue
        records.append(
            {
                "query_name": input_url,
                "input_url": input_url,
                "hotel_url": input_url,
                "is_found": True,
                "hotel_name": name,
                "property_id": property_id,
                "room_type": room_type,
                "currency": "VND",
                "price_before_tax": before_tax,
                "price_after_tax": before_tax + tax,
                "discount": discount,
                "tax_and_fee": tax,
                "remaining_room": 3,
                "checkin_date": check_in_date.isoformat(),
                "raw": {"mocked_at": run_at.isoformat()},
            }
        )
    return records


def _pick_url_for_property(
    hotel_urls: list[str],
    property_id: str,
) -> str | None:
    for hotel_url in hotel_urls:
        if property_id in hotel_url:
            return hotel_url
    if property_id == "hotel_own" and hotel_urls:
        return hotel_urls[0]
    return None
