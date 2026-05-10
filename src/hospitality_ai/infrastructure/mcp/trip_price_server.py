"""MCP server exposing processed Trip Price API tools."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from hospitality_ai.application.trip_price_service import TripPriceService
from hospitality_ai.config.settings import Settings
from hospitality_ai.domain.models import TripPriceQuery
from hospitality_ai.infrastructure.mcp.trip_price_api_client import (
    MockTripPriceApiClient,
    TripOtaPriceApiClient,
)
from hospitality_ai.interfaces.serialization import to_jsonable


def create_trip_price_mcp_server(settings: Optional[Settings] = None):
    """Create a FastMCP server for Trip price tools."""

    try:
        from mcp.server.fastmcp import FastMCP
    except Exception as exc:  # pragma: no cover - optional dependency branch
        raise RuntimeError(
            "The 'mcp' package is not installed. Install the mcp extra before "
            "running this server.",
        ) from exc

    settings = settings or Settings.from_env()
    service = TripPriceService(_build_trip_api_client(settings))
    server = FastMCP("hospitality-trip-price")

    @server.tool()
    async def collect_trip_prices(
        hotel_urls: list[str],
        check_in_dates: Optional[list[str]] = None,
        check_out_date: Optional[str] = None,
        adults: int = 2,
        children: int = 0,
        rooms: int = 1,
        currency: Optional[str] = "VND",
    ) -> dict:
        """Collect Trip.com prices and return processed pricing records."""

        query = _build_query(
            hotel_urls=hotel_urls,
            check_in_dates=check_in_dates,
            check_out_date=check_out_date,
            adults=adults,
            children=children,
            rooms=rooms,
            currency=currency,
        )
        collection = await service.collect_async(query)
        return to_jsonable(collection)

    @server.tool()
    async def collect_trip_pricing_records(
        hotel_urls: list[str],
        check_in_dates: Optional[list[str]] = None,
        check_out_date: Optional[str] = None,
        adults: int = 2,
        children: int = 0,
        rooms: int = 1,
        currency: Optional[str] = "VND",
    ) -> list[dict]:
        """Collect Trip.com prices and return only normalized records."""

        query = _build_query(
            hotel_urls=hotel_urls,
            check_in_dates=check_in_dates,
            check_out_date=check_out_date,
            adults=adults,
            children=children,
            rooms=rooms,
            currency=currency,
        )
        collection = await service.collect_async(query)
        return to_jsonable(collection.normalized_records)

    return server


def main() -> None:
    """Run the Trip Price MCP server."""

    create_trip_price_mcp_server().run()


def _build_trip_api_client(settings: Settings):
    if settings.trip_price_api_mode == "http":
        return TripOtaPriceApiClient(
            base_url=settings.trip_price_api_base_url,
            timeout_seconds=settings.trip_price_api_timeout_seconds,
        )
    return MockTripPriceApiClient()


def _build_query(
    hotel_urls: list[str],
    check_in_dates: Optional[list[str]],
    check_out_date: Optional[str],
    adults: int,
    children: int,
    rooms: int,
    currency: Optional[str],
) -> TripPriceQuery:
    parsed_check_in_dates = [
        date.fromisoformat(value) for value in (check_in_dates or [])
    ]
    if not parsed_check_in_dates:
        parsed_check_in_dates = [date.today() + timedelta(days=30)]
    return TripPriceQuery(
        hotel_urls=hotel_urls,
        check_in_dates=parsed_check_in_dates,
        check_out_date=(
            date.fromisoformat(check_out_date) if check_out_date else None
        ),
        adults=adults,
        children=children,
        rooms=rooms,
        currency=currency,
        include_raw=True,
    )


if __name__ == "__main__":
    main()
