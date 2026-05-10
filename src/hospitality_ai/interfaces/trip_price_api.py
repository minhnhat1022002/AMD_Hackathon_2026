"""Embedded Trip Price API routes.

This module intentionally exposes a small subset of the old ota-crawl price
API contract so the repository can remove the separate ``ota-crawl`` folder
without breaking callers that POST to ``/v1/prices/collect/trip``.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from hospitality_ai.application.trip_price_service import TripPriceService
from hospitality_ai.domain.enums import CrawlerStatus
from hospitality_ai.domain.models import TripPriceQuery
from hospitality_ai.infrastructure.mcp.trip_price_api_client import (
    MockTripPriceApiClient,
)
from hospitality_ai.interfaces.serialization import to_jsonable


def create_trip_price_router():
    """Create a FastAPI router for the embedded Trip Price API."""

    try:
        from fastapi import APIRouter, HTTPException
        from pydantic import BaseModel, Field, model_validator
    except Exception as exc:  # pragma: no cover - optional dependency branch
        raise RuntimeError(
            "FastAPI/Pydantic is not installed. Install the api extra.",
        ) from exc

    class CollectTripPriceRequest(BaseModel):
        """Request body compatible with ota-crawl Trip price collection."""

        hotel_urls: list[str] | None = None
        hotel_names: list[str] | None = None
        check_in_dates: list[date] | None = None
        check_in_date: date | None = None
        check_out_date: date | None = None
        adults: int = Field(default=2, ge=1)
        children: int = Field(default=0, ge=0)
        rooms: int = Field(default=1, ge=1)
        currency: str | None = "VND"
        include_raw: bool = True
        background_job: bool = False

        @model_validator(mode="after")
        def validate_sources(self) -> "CollectTripPriceRequest":
            if not self.hotel_urls and not self.hotel_names:
                raise ValueError(
                    "At least one of hotel_urls or hotel_names is required",
                )
            if (
                self.check_in_date
                and self.check_out_date
                and self.check_out_date <= self.check_in_date
            ):
                raise ValueError("check_out_date must be after check_in_date")
            return self

        def to_query(self) -> TripPriceQuery:
            check_in_dates = self.check_in_dates or []
            if self.check_in_date:
                check_in_dates = [self.check_in_date]
            return TripPriceQuery(
                hotel_urls=self.hotel_urls or [],
                hotel_names=self.hotel_names or [],
                check_in_dates=check_in_dates,
                check_out_date=self.check_out_date,
                adults=self.adults,
                children=self.children,
                rooms=self.rooms,
                currency=self.currency,
                include_raw=self.include_raw,
            )

    router = APIRouter(prefix="/v1/prices", tags=["trip-prices"])
    service = TripPriceService(MockTripPriceApiClient())

    @router.get("/sources", response_model=list[str])
    async def list_sources() -> list[str]:
        """Return supported embedded price sources."""

        return ["trip"]

    @router.post("/collect/trip")
    async def collect_trip_prices(payload: CollectTripPriceRequest) -> dict:
        """Collect Trip prices and return raw plus processed records."""

        if payload.background_job:
            raise HTTPException(
                status_code=400,
                detail="background_job is not supported by embedded API",
            )

        collection = await service.collect_async(payload.to_query())
        if collection.run_metric.status == CrawlerStatus.FAILED:
            raise HTTPException(
                status_code=502,
                detail=collection.run_metric.error_message,
            )

        response = dict(collection.raw_response)
        response["data"] = _build_response_data(
            raw_data=response.get("data"),
            collection=collection,
            include_raw=payload.include_raw,
        )
        response.setdefault("status", 200)
        response.setdefault("success", True)
        response.setdefault("message", "COLLECT_SUCCESS")
        response.setdefault(
            "timestamp",
            datetime.now(timezone.utc).isoformat(),
        )
        return response

    return router


def _build_response_data(
    raw_data: Any,
    collection,
    include_raw: bool,
) -> dict[str, Any]:
    data = dict(raw_data) if isinstance(raw_data, dict) else {}
    if not include_raw:
        data.pop("result", None)
    data["normalized_records"] = to_jsonable(collection.normalized_records)
    data["processing"] = {
        "source": collection.source,
        "total_raw_records": collection.total_raw_records,
        "normalized_record_count": len(collection.normalized_records),
        "skipped_records": collection.skipped_records,
        "run_metric": to_jsonable(collection.run_metric),
    }
    return data
