"""Trip.com price collection and normalization service."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import re
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping, Optional, Sequence

from hospitality_ai.application.interfaces import TripPriceApiClient
from hospitality_ai.application.pricing_insight_service import quantize_money
from hospitality_ai.domain.enums import CrawlerStatus, Platform
from hospitality_ai.domain.exceptions import CrawlerClientError
from hospitality_ai.domain.models import (
    CrawlerRunMetric,
    PricingRecord,
    TripPriceCollection,
    TripPriceQuery,
)

logger = logging.getLogger(__name__)


class TripPriceService:
    """Collects Trip.com prices and converts OTA records to domain records."""

    def __init__(self, api_client: TripPriceApiClient) -> None:
        self._api_client = api_client

    def collect(self, query: TripPriceQuery) -> TripPriceCollection:
        """Synchronously collect and normalize Trip.com pricing."""

        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.collect_async(query))

        raise CrawlerClientError(
            "TripPriceService.collect() cannot run inside an active event "
            "loop. Use collect_async() instead.",
        )

    async def collect_async(
        self,
        query: TripPriceQuery,
    ) -> TripPriceCollection:
        """Collect and normalize Trip.com pricing."""

        started_at = datetime.now(timezone.utc)
        try:
            raw_response = await self._api_client.collect_prices(query)
            result_document = _extract_result_document(raw_response)
            raw_records = _extract_price_records(result_document)
            run_at = _parse_datetime(
                result_document.get("run_at"),
                default=datetime.now(timezone.utc),
            )

            normalized_records: list[PricingRecord] = []
            skipped_records = 0
            for raw_record in raw_records:
                record = _normalize_trip_record(
                    raw_record,
                    run_at=run_at,
                    fallback_query=query,
                )
                if record is None:
                    skipped_records += 1
                    continue
                normalized_records.append(record)

            finished_at = datetime.now(timezone.utc)
            run_metric = CrawlerRunMetric(
                run_id=_build_run_id("trip", started_at),
                platform=Platform.TRIP,
                status=CrawlerStatus.SUCCESS,
                started_at=started_at,
                finished_at=finished_at,
                records_found=len(normalized_records),
            )
            return TripPriceCollection(
                source=str(result_document.get("source") or "trip"),
                run_at=run_at,
                total_raw_records=len(raw_records),
                normalized_records=normalized_records,
                skipped_records=skipped_records,
                run_metric=run_metric,
                raw_response=raw_response,
            )
        except Exception as exc:
            finished_at = datetime.now(timezone.utc)
            run_metric = CrawlerRunMetric(
                run_id=_build_run_id("trip", started_at),
                platform=Platform.TRIP,
                status=CrawlerStatus.FAILED,
                started_at=started_at,
                finished_at=finished_at,
                records_found=0,
                error_message=str(exc),
            )
            logger.error("Trip price collection failed: %s", exc)
            return TripPriceCollection(
                source="trip",
                run_at=finished_at,
                total_raw_records=0,
                normalized_records=[],
                skipped_records=0,
                run_metric=run_metric,
                raw_response={"error": str(exc)},
            )


def to_crawler_payloads(
    collection: TripPriceCollection,
) -> list[dict[str, Any]]:
    """Convert Trip.com domain records to crawler payload dictionaries."""

    return [
        {
            "hotel_id": record.hotel_id,
            "hotel_name": record.hotel_name,
            "platform": record.platform.value,
            "room_type": record.room_type,
            "check_in_date": record.check_in_date.isoformat(),
            "price": str(record.price),
            "tax": str(record.tax),
            "discount": str(record.discount),
            "crawled_at": record.crawled_at.isoformat(),
        }
        for record in collection.normalized_records
    ]


def to_llm_ready_trip_payload(
    collection: TripPriceCollection,
) -> dict[str, Any]:
    """Build compact Trip price data suitable for LLM prompts."""

    return {
        "source": collection.source,
        "run_at": collection.run_at.isoformat(),
        "total_raw_records": collection.total_raw_records,
        "normalized_record_count": len(collection.normalized_records),
        "skipped_records": collection.skipped_records,
        "records": [
            {
                "hotel_id": record.hotel_id,
                "hotel_name": record.hotel_name,
                "platform": record.platform.value,
                "room_type": record.room_type,
                "check_in_date": record.check_in_date.isoformat(),
                "price_before_tax": str(record.price),
                "tax": str(record.tax),
                "discount": str(record.discount),
                "total_price": str(record.total_price),
                "crawled_at": record.crawled_at.isoformat(),
            }
            for record in collection.normalized_records
        ],
    }


def _extract_result_document(
    raw_response: Mapping[str, Any],
) -> Mapping[str, Any]:
    data = raw_response.get("data")
    if isinstance(data, Mapping):
        result = data.get("result")
        if isinstance(result, Mapping):
            return result
    if "source" in raw_response and isinstance(raw_response.get("data"), list):
        return raw_response
    return raw_response


def _extract_price_records(
    result_document: Mapping[str, Any],
) -> list[Mapping[str, Any]]:
    records = result_document.get("data")
    if not isinstance(records, list):
        return []
    return [record for record in records if isinstance(record, Mapping)]


def _normalize_trip_record(
    raw_record: Mapping[str, Any],
    run_at: datetime,
    fallback_query: TripPriceQuery,
) -> Optional[PricingRecord]:
    if raw_record.get("is_found") is False:
        return None

    price_components = _extract_price_components(raw_record)
    price_before_tax = price_components["price_before_tax"]
    price_after_tax = price_components["price_after_tax"]
    tax = price_components["tax"]

    if price_before_tax is None and price_after_tax is None:
        return None
    if price_before_tax is None:
        price_before_tax = price_after_tax
    if price_after_tax is None:
        price_after_tax = price_before_tax
    if tax is None:
        tax = max(price_after_tax - price_before_tax, Decimal("0"))

    discount = (
        price_components["discount"]
        if price_components["discount"] is not None
        else Decimal("0")
    )

    check_in_date = _parse_date(
        _first_present(
            raw_record,
            ["check_in_date", "checkin_date", "start_date"],
        ),
        fallback=_first_query_date(fallback_query.check_in_dates),
    )

    hotel_url = _first_present(
        raw_record,
        ["hotel_url", "input_url", "property_url", "url"],
    )
    hotel_id = _first_present(
        raw_record,
        ["hotel_id", "property_id"],
    ) or _stable_hotel_id(hotel_url or raw_record.get("query_name"))
    hotel_name = _first_present(
        raw_record,
        ["hotel_name", "property_name", "query_name"],
    ) or hotel_id
    room_type = _first_present(
        raw_record,
        ["room_type", "room_name", "unit_name", "roomName"],
    ) or "unknown"

    return PricingRecord(
        hotel_id=str(hotel_id),
        hotel_name=str(hotel_name),
        platform=Platform.TRIP,
        room_type=str(room_type),
        check_in_date=check_in_date,
        price=quantize_money(price_before_tax),
        tax=quantize_money(tax),
        discount=quantize_money(discount),
        crawled_at=run_at,
    )


def _extract_price_components(
    raw_record: Mapping[str, Any],
) -> dict[str, Optional[Decimal]]:
    raw = raw_record.get("raw")
    raw_payload = raw if isinstance(raw, Mapping) else {}
    raw_price_info = raw_payload.get("price_info")
    price_info = raw_price_info if isinstance(raw_price_info, Mapping) else {}
    raw_total_price_info = raw_payload.get("total_price_info")
    total_price_info = (
        raw_total_price_info
        if isinstance(raw_total_price_info, Mapping)
        else {}
    )

    price_before_tax = _first_decimal(
        price_info,
        ["price", "displayPrice", "basePrice", "salePrice", "roomPrice"],
    ) or _first_decimal(
        raw_record,
        [
            "price_before_tax",
            "before_tax_price",
            "price_excluding_tax",
            "nightly_price",
            "base_price",
        ],
    )

    price_after_tax = _extract_total_price(total_price_info) or _first_decimal(
        raw_record,
        [
            "price_after_tax",
            "after_tax_price",
            "price_including_tax",
            "total_price",
        ],
    )
    tax = _extract_tax(total_price_info)
    if tax is None and price_before_tax is not None and price_after_tax:
        tax = max(price_after_tax - price_before_tax, Decimal("0"))
    if tax is None:
        tax = _first_decimal(raw_record, ["tax", "fee", "tax_and_fee"])

    discount = _first_decimal(
        raw_record,
        ["discount", "discount_amount"],
    )

    return {
        "price_before_tax": price_before_tax,
        "price_after_tax": price_after_tax,
        "tax": tax,
        "discount": discount,
    }


def _extract_total_price(
    total_price_info: Mapping[str, Any],
) -> Optional[Decimal]:
    total_no_approx = total_price_info.get("totalNoApprox")
    if isinstance(total_no_approx, Mapping):
        total = _to_decimal(total_no_approx.get("content"))
        if total is not None:
            return total

    total = total_price_info.get("total")
    if isinstance(total, Mapping):
        parsed_total = _to_decimal(total.get("content"))
        if parsed_total is not None:
            return parsed_total

    quantity_days = total_price_info.get("quantityDays")
    if isinstance(quantity_days, Mapping):
        return _to_decimal(quantity_days.get("content"))

    return _first_decimal(
        total_price_info,
        ["price", "totalPrice", "amount", "payAmount"],
    )


def _extract_tax(
    total_price_info: Mapping[str, Any],
) -> Optional[Decimal]:
    pay_tax = total_price_info.get("payTax")
    if isinstance(pay_tax, Mapping):
        tax = _first_decimal(pay_tax, ["price", "content"])
        if tax is not None:
            return tax

        items = pay_tax.get("items")
        if isinstance(items, list):
            item_values = [
                _to_decimal(item.get("content"))
                for item in items
                if isinstance(item, Mapping)
            ]
            item_values = [item for item in item_values if item is not None]
            if item_values:
                return sum(item_values, Decimal("0"))

    return _first_decimal(
        total_price_info,
        ["tax", "tax_and_fee", "fee"],
    )


def _first_present(
    record: Mapping[str, Any],
    keys: Sequence[str],
) -> Any:
    for key in keys:
        value = record.get(key)
        if value not in (None, "", [], {}):
            return value
    return None


def _first_decimal(
    record: Mapping[str, Any],
    keys: Sequence[str],
) -> Optional[Decimal]:
    value = _first_present(record, keys)
    return _to_decimal(value)


def _to_decimal(value: Any) -> Optional[Decimal]:
    if value in (None, "", [], {}):
        return None
    if isinstance(value, str):
        text = value.strip()
        direct_text = text.replace(",", "")
        try:
            return Decimal(direct_text)
        except (InvalidOperation, ValueError):
            matches = re.findall(r"\d[\d\s,.]*", text)
            if not matches:
                return None
            candidate = max(
                matches,
                key=lambda item: len(re.sub(r"\D", "", item)),
            )
            digits = re.sub(r"\D", "", candidate)
            if not digits:
                return None
            return Decimal(digits)
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _parse_date(value: Any, fallback: date) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str) and value:
        return date.fromisoformat(value[:10])
    return fallback


def _parse_datetime(value: Any, default: datetime) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str) and value:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    else:
        parsed = default

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _first_query_date(values: Sequence[date]) -> date:
    if values:
        return values[0]
    return datetime.now(timezone.utc).date()


def _stable_hotel_id(value: Any) -> str:
    text = str(value or "unknown")
    digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]
    return f"trip_{digest}"


def _build_run_id(source: str, started_at: datetime) -> str:
    timestamp = started_at.strftime("%Y%m%d%H%M%S%f")
    return f"{source}_{timestamp}"
