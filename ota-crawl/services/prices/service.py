import re
from datetime import date, datetime, timezone
from typing import Any

from schemas.price import CollectPriceRequest, CollectPriceResponse
from services.prices.registry import price_provider_registry


def _normalized_hotel_urls(payload: CollectPriceRequest) -> list[str]:
    return [item for item in (payload.hotel_urls or []) if item]


def _extract_record_hotel_url(
    record: dict[str, Any],
    hotel_urls: list[str],
) -> str | None:
    if len(hotel_urls) == 1:
        return hotel_urls[0]

    input_urls = set(hotel_urls)
    for field in ("input_url", "hotel_url", "url"):
        value = record.get(field)
        if isinstance(value, str) and value in input_urls:
            return value
    return None


def _attach_hotel_urls(
    records: list[dict[str, Any]],
    hotel_urls: list[str],
) -> list[dict[str, Any]]:
    if not hotel_urls:
        return records

    enriched_records: list[dict[str, Any]] = []
    for record in records:
        enriched_record = dict(record)
        hotel_url = _extract_record_hotel_url(enriched_record, hotel_urls)
        if hotel_url:
            enriched_record["hotel_url"] = hotel_url
        enriched_records.append(enriched_record)
    return enriched_records


def _first_present(record: dict[str, Any], keys: list[str]) -> Any:
    for key in keys:
        value = record.get(key)
        if value not in (None, "", [], {}):
            return value
    return None


def _to_number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str):
        return None

    matches = re.findall(r"\d[\d\s.,]*", value)
    if not matches:
        return None

    candidate = max(matches, key=lambda item: len(re.sub(r"\D", "", item)))
    digits = re.sub(r"\D", "", candidate)
    if not digits:
        return None

    compact = candidate.replace(" ", "")
    separators = re.findall(r"[.,]", compact)
    if not separators:
        return float(digits)
    if len(separators) > 1:
        return float(re.sub(r"[.,]", "", compact))

    whole, fractional = compact.rsplit(separators[0], 1)
    whole_digits = re.sub(r"\D", "", whole)
    fractional_digits = re.sub(r"\D", "", fractional)
    if whole_digits and len(fractional_digits) in (1, 2):
        try:
            return float(f"{whole_digits}.{fractional_digits}")
        except ValueError:
            return None
    return float(re.sub(r"[.,]", "", compact))


def _to_int(value: Any) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if not isinstance(value, str):
        return None
    match = re.search(r"\d+", value)
    if not match:
        return None
    return int(match.group(0))


def _to_iso_date(value: Any) -> str | None:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str) and value:
        return value
    return None


def _normalize_services(record: dict[str, Any]) -> dict[str, Any]:
    existing = record.get("services")
    if isinstance(existing, dict):
        return {
            key: value
            for key, value in existing.items()
            if value not in (None, "", [], {})
        }
    if isinstance(existing, list):
        return {"items": existing}
    if isinstance(existing, str) and existing:
        return {"description": existing}

    services = {
        "rate": _first_present(record, ["rate_name", "rate_text"]),
        "occupancy": _first_present(record, ["occupancy_text", "occupancy"]),
        "tax": _first_present(record, ["tax_text", "tax_and_fee_text"]),
        "bed": _first_present(record, ["bed_text", "number_of_beds"]),
        "meal": _first_present(record, ["meal_text", "board_type"]),
        "cancellation": _first_present(record, ["cancellation_text", "refund_text"]),
        "facilities": _first_present(record, ["facilities", "amenities"]),
    }
    return {
        key: value
        for key, value in services.items()
        if value not in (None, "", [], {})
    }


def _normalize_discount(record: dict[str, Any], sale_price: float | None) -> Any:
    explicit_discount = _first_present(
        record,
        ["discount", "discount_amount", "discount_text"],
    )
    parsed_discount = _to_number(explicit_discount)
    if parsed_discount is not None:
        return parsed_discount
    if explicit_discount not in (None, "", [], {}):
        return explicit_discount

    original_price = _to_number(
        _first_present(
            record,
            [
                "original_price",
                "strike_price",
                "strike_price_value",
                "before_discount_price",
                "crossed_out_price",
                "was_price",
            ],
        )
    )
    if original_price is None or sale_price is None or original_price <= sale_price:
        return None
    return original_price - sale_price


def _normalize_price_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized_records: list[dict[str, Any]] = []
    for record in records:
        normalized = dict(record)

        tax_and_fee = _to_number(
            _first_present(normalized, ["tax_and_fee", "tax", "fee"])
        )
        price_before_tax = _to_number(
            _first_present(
                normalized,
                [
                    "price_before_tax",
                    "before_tax_price",
                    "price_excluding_tax",
                    "exclusive_price",
                    "base_price",
                    "nightly_price",
                ],
            )
        )
        price_after_tax = _to_number(
            _first_present(
                normalized,
                [
                    "price_after_tax",
                    "after_tax_price",
                    "price_including_tax",
                    "inclusive_price",
                    "total_price",
                ],
            )
        )

        if (
            price_before_tax is None
            and price_after_tax is not None
            and tax_and_fee is not None
        ):
            price_before_tax = max(price_after_tax - tax_and_fee, 0)
        if price_before_tax is None:
            price_before_tax = price_after_tax
        if (
            price_after_tax is None
            and price_before_tax is not None
            and tax_and_fee is not None
        ):
            price_after_tax = price_before_tax + tax_and_fee
        if price_after_tax is None:
            price_after_tax = price_before_tax

        sale_price = price_before_tax if price_before_tax is not None else price_after_tax
        normalized["hotel_name"] = _first_present(
            normalized,
            ["hotel_name", "property_name"],
        )
        normalized["hotel_url"] = _first_present(
            normalized,
            ["hotel_url", "input_url", "property_url", "url"],
        )
        normalized["price_before_tax"] = price_before_tax
        normalized["price_after_tax"] = price_after_tax
        normalized["discount"] = _normalize_discount(normalized, sale_price)
        normalized["remaining_room"] = _to_int(
            _first_present(
                normalized,
                [
                    "remaining_room",
                    "rooms_left",
                    "room_left",
                    "available_rooms",
                    "first_room_availability",
                ],
            )
        )
        normalized["services"] = _normalize_services(normalized)
        normalized["check_in_date"] = _to_iso_date(
            _first_present(
                normalized,
                ["check_in_date", "checkin_date", "start_date"],
            )
        )
        normalized["room_type"] = _first_present(
            normalized,
            ["room_type", "room_name", "unit_name", "roomName"],
        )
        normalized_records.append(normalized)
    return normalized_records


class PriceService:
    async def collect_by_source(
        self,
        source: str,
        payload: CollectPriceRequest,
    ) -> CollectPriceResponse:
        provider = price_provider_registry.get(source)
        hotel_urls = _normalized_hotel_urls(payload)
        hotel_url = hotel_urls[0] if len(hotel_urls) == 1 else None
        provider_records = await provider.collect(payload)
        records = _attach_hotel_urls(provider_records, hotel_urls)
        prices = _normalize_price_records(records)
        return CollectPriceResponse(
            source=source,
            total=len(prices),
            run_at=datetime.now(timezone.utc),
            hotel_url=hotel_url,
            hotel_urls=hotel_urls or None,
            data=prices,
        )
