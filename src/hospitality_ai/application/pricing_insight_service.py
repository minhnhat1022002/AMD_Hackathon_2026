"""Pricing insight service."""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import date, datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Iterable, Mapping, Optional, Sequence

from hospitality_ai.application.interfaces import (
    CrawlerClient,
    LLMClient,
    PricingRepository,
)
from hospitality_ai.application.pricing_market_matcher import (
    select_comparable_rooms_deterministically,
)
from hospitality_ai.application.recommendation_service import (
    RecommendationService,
)
from hospitality_ai.domain.enums import Platform
from hospitality_ai.domain.exceptions import (
    InvalidPricingRecordError,
    LLMClientError,
)
from hospitality_ai.domain.models import (
    ComparableRoomSelection,
    CompetitorRoomPricingContext,
    OwnRoomPricingContext,
    PricingInsight,
    PricingInsightReport,
    PricingMarketContext,
    PricingRecord,
)

logger = logging.getLogger(__name__)

TWOPLACES = Decimal("0.01")


def quantize_money(value: Decimal) -> Decimal:
    """Round money values to two decimal places."""

    return value.quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def normalize_pricing_record(raw: Mapping[str, Any]) -> PricingRecord:
    """Normalize a raw crawler payload into a domain pricing record."""

    try:
        return PricingRecord(
            hotel_id=str(raw["hotel_id"]),
            hotel_name=str(raw["hotel_name"]),
            platform=_parse_platform(raw["platform"]),
            room_type=str(raw["room_type"]),
            check_in_date=_parse_date(raw["check_in_date"]),
            price=_parse_decimal(raw["price"]),
            tax=_parse_decimal(raw.get("tax", "0")),
            discount=_parse_decimal(raw.get("discount", "0")),
            crawled_at=_parse_datetime(raw["crawled_at"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise InvalidPricingRecordError(
            f"Invalid pricing record: {raw}",
        ) from exc


class PricingInsightService:
    """Computes pricing insights from OTA crawler data."""

    def __init__(
        self,
        crawler_client: CrawlerClient,
        pricing_repository: PricingRepository,
        llm_client: LLMClient,
        recommendation_service: RecommendationService,
        own_hotel_id: str,
    ) -> None:
        self._crawler_client = crawler_client
        self._pricing_repository = pricing_repository
        self._llm_client = llm_client
        self._recommendation_service = recommendation_service
        self._own_hotel_id = own_hotel_id

    def generate_report(
        self,
        room_type: Optional[str] = None,
        check_in_date: Optional[date] = None,
    ) -> PricingInsightReport:
        """Generate a pricing insight report for the configured hotel."""

        raw_records = self._crawler_client.fetch_pricing_records()
        records = self._normalize_valid_records(raw_records)
        self._pricing_repository.save_many(records)

        filtered_records = self._filter_records(
            records,
            room_type=room_type,
            check_in_date=check_in_date,
        )
        insights = self._build_insights(filtered_records)
        report = PricingInsightReport(
            own_hotel_id=self._own_hotel_id,
            generated_at=datetime.now(timezone.utc),
            insights=insights,
            summary="",
            pricing_records=filtered_records,
        )
        summary = self._llm_client.summarize_pricing_insight(report)
        return PricingInsightReport(
            own_hotel_id=report.own_hotel_id,
            generated_at=report.generated_at,
            insights=report.insights,
            summary=summary,
            pricing_records=report.pricing_records,
        )

    def _normalize_valid_records(
        self,
        raw_records: Sequence[Mapping[str, Any]],
    ) -> list[PricingRecord]:
        records: list[PricingRecord] = []
        for raw_record in raw_records:
            try:
                record = normalize_pricing_record(raw_record)
            except InvalidPricingRecordError:
                logger.info(
                    "Skipping invalid pricing record: %s",
                    raw_record,
                )
                continue

            if record.price <= Decimal("0"):
                logger.info(
                    "Skipping non-positive price for hotel_id=%s",
                    record.hotel_id,
                )
                continue
            records.append(record)
        return records

    def _filter_records(
        self,
        records: Iterable[PricingRecord],
        room_type: Optional[str],
        check_in_date: Optional[date],
    ) -> list[PricingRecord]:
        filtered_records = list(records)
        if room_type is not None:
            filtered_records = [
                record
                for record in filtered_records
                if record.room_type.lower() == room_type.lower()
            ]
        if check_in_date is not None:
            filtered_records = [
                record
                for record in filtered_records
                if record.check_in_date == check_in_date
            ]
        return filtered_records

    def _build_insights(
        self,
        records: Sequence[PricingRecord],
    ) -> list[PricingInsight]:
        own_records_by_key: dict[tuple[str, date], list[PricingRecord]] = (
            defaultdict(list)
        )
        competitor_records: list[PricingRecord] = []

        for record in records:
            key = (record.room_type, record.check_in_date)
            if record.hotel_id == self._own_hotel_id:
                own_records_by_key[key].append(record)
            else:
                competitor_records.append(record)

        market_context, competitor_records_by_id = self._build_market_context(
            own_records_by_key=own_records_by_key,
            competitor_records=competitor_records,
        )
        selections = self._select_comparable_rooms(market_context)
        selections_by_key = {
            selection.room_key: selection for selection in selections
        }

        own_room_contexts_by_key = {
            room.room_key: room for room in market_context.own_rooms
        }
        insights: list[PricingInsight] = []
        grouped_own_records = sorted(
            own_records_by_key.items(),
            key=lambda item: (item[0][1], item[0][0].lower()),
        )
        for index, (key, own_records) in enumerate(grouped_own_records, 1):
            room_key = _build_room_key(index)
            own_room_context = own_room_contexts_by_key[room_key]
            selection = selections_by_key.get(room_key)
            if selection is None:
                selection = self._fallback_selection(
                    market_context,
                    own_room_context,
                )
            selected_competitor_records = [
                competitor_records_by_id[record_id]
                for record_id in selection.comparable_record_ids
                if record_id in competitor_records_by_id
            ]
            if (
                not selected_competitor_records
                and _has_same_date_competitors(
                    market_context,
                    own_room_context.check_in_date,
                )
            ):
                selection = self._fallback_selection(
                    market_context,
                    own_room_context,
                )
                selected_competitor_records = [
                    competitor_records_by_id[record_id]
                    for record_id in selection.comparable_record_ids
                    if record_id in competitor_records_by_id
                ]
            insight = self._build_single_insight(
                key=key,
                own_records=own_records,
                competitor_records=selected_competitor_records,
                selection=selection,
            )
            insights.append(insight)
        return insights

    def _build_market_context(
        self,
        own_records_by_key: Mapping[tuple[str, date], list[PricingRecord]],
        competitor_records: Sequence[PricingRecord],
    ) -> tuple[PricingMarketContext, dict[str, PricingRecord]]:
        grouped_own_records = sorted(
            own_records_by_key.items(),
            key=lambda item: (item[0][1], item[0][0].lower()),
        )
        own_rooms: list[OwnRoomPricingContext] = []
        own_dates: set[date] = set()
        for index, (key, own_records) in enumerate(grouped_own_records, 1):
            current_price = quantize_money(
                _average([record.total_price for record in own_records]),
            )
            own_dates.add(key[1])
            own_rooms.append(
                OwnRoomPricingContext(
                    room_key=_build_room_key(index),
                    room_type=key[0],
                    check_in_date=key[1],
                    current_price=current_price,
                )
            )

        competitor_rooms: list[CompetitorRoomPricingContext] = []
        competitor_records_by_id: dict[str, PricingRecord] = {}
        relevant_competitors = [
            record
            for record in competitor_records
            if record.check_in_date in own_dates
        ]
        sorted_competitors = sorted(
            relevant_competitors,
            key=lambda record: (
                record.check_in_date,
                record.hotel_id,
                record.room_type.lower(),
                record.total_price,
            ),
        )
        for index, record in enumerate(sorted_competitors, 1):
            record_id = f"cmp_{index:03d}"
            competitor_records_by_id[record_id] = record
            competitor_rooms.append(
                CompetitorRoomPricingContext(
                    record_id=record_id,
                    hotel_id=record.hotel_id,
                    hotel_name=record.hotel_name,
                    room_type=record.room_type,
                    check_in_date=record.check_in_date,
                    total_price=quantize_money(record.total_price),
                )
            )

        return (
            PricingMarketContext(
                own_hotel_id=self._own_hotel_id,
                own_rooms=own_rooms,
                competitor_rooms=competitor_rooms,
            ),
            competitor_records_by_id,
        )

    def _select_comparable_rooms(
        self,
        market_context: PricingMarketContext,
    ) -> list[ComparableRoomSelection]:
        if not market_context.own_rooms:
            return []

        try:
            selections = list(
                self._llm_client.select_comparable_rooms(market_context),
            )
        except LLMClientError as exc:
            logger.warning(
                "LLM comparable-room selection failed, using fallback: %s",
                exc,
            )
            return select_comparable_rooms_deterministically(market_context)

        if not selections:
            return select_comparable_rooms_deterministically(market_context)
        return selections

    def _fallback_selection(
        self,
        market_context: PricingMarketContext,
        own_room_context: OwnRoomPricingContext,
    ) -> ComparableRoomSelection:
        fallback_context = PricingMarketContext(
            own_hotel_id=market_context.own_hotel_id,
            own_rooms=[own_room_context],
            competitor_rooms=market_context.competitor_rooms,
        )
        selections = select_comparable_rooms_deterministically(
            fallback_context,
        )
        return selections[0]

    def _build_single_insight(
        self,
        key: tuple[str, date],
        own_records: Sequence[PricingRecord],
        competitor_records: Sequence[PricingRecord],
        selection: ComparableRoomSelection,
    ) -> PricingInsight:
        own_prices = [record.total_price for record in own_records]
        current_price = quantize_money(_average(own_prices))

        competitor_prices = [
            record.total_price for record in competitor_records
        ]
        if competitor_prices:
            average_competitor_price = quantize_money(
                _average(competitor_prices),
            )
            min_competitor_price = quantize_money(min(competitor_prices))
            max_competitor_price = quantize_money(max(competitor_prices))
            price_gap = quantize_money(
                current_price - average_competitor_price,
            )
            price_gap_percentage = quantize_money(
                price_gap / average_competitor_price * Decimal("100"),
            )
        else:
            average_competitor_price = Decimal("0.00")
            min_competitor_price = Decimal("0.00")
            max_competitor_price = Decimal("0.00")
            price_gap = Decimal("0.00")
            price_gap_percentage = Decimal("0.00")

        recommendation = self._recommendation_service.recommend_price(
            current_price=current_price,
            average_competitor_price=average_competitor_price,
        )
        recommended_price = quantize_money(
            self._recommendation_service.recommend_target_price(
                current_price=current_price,
                average_competitor_price=average_competitor_price,
            )
        )

        return PricingInsight(
            room_type=key[0],
            check_in_date=key[1],
            current_price=current_price,
            average_competitor_price=average_competitor_price,
            min_competitor_price=min_competitor_price,
            max_competitor_price=max_competitor_price,
            price_gap=price_gap,
            price_gap_percentage=price_gap_percentage,
            recommendation=recommendation,
            competitor_count=len(competitor_records),
            recommended_price=recommended_price,
            benchmark_basis=selection.benchmark_basis,
            benchmark_reasoning=selection.reasoning,
            confidence=selection.confidence,
            competitor_room_types=sorted(
                {record.room_type for record in competitor_records},
            ),
        )


def _average(values: Sequence[Decimal]) -> Decimal:
    if not values:
        return Decimal("0")
    return sum(values, Decimal("0")) / Decimal(len(values))


def _build_room_key(index: int) -> str:
    return f"own_{index:03d}"


def _has_same_date_competitors(
    market_context: PricingMarketContext,
    check_in_date: date,
) -> bool:
    return any(
        room.check_in_date == check_in_date
        for room in market_context.competitor_rooms
    )


def _parse_platform(value: Any) -> Platform:
    value_as_text = str(value).strip().lower()
    for platform in Platform:
        if platform.value == value_as_text:
            return platform
    raise ValueError(f"Unsupported platform: {value}")


def _parse_date(value: Any) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    return date.fromisoformat(str(value))


def _parse_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _parse_decimal(value: Any) -> Decimal:
    if value is None:
        raise ValueError("Decimal value cannot be None")
    return Decimal(str(value))
