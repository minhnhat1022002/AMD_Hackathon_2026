"""Fallback comparable-room matching for pricing insight.

The real LLM path returns comparable competitor record IDs. This module keeps
local development deterministic and provides a safe fallback when an LLM
returns invalid JSON or incomplete selections.
"""

from __future__ import annotations

import re
from typing import Sequence

from hospitality_ai.domain.models import (
    ComparableRoomSelection,
    CompetitorRoomPricingContext,
    OwnRoomPricingContext,
    PricingMarketContext,
)

MAX_COMPARABLE_RECORDS_PER_ROOM = 8


def select_comparable_rooms_deterministically(
    context: PricingMarketContext,
    limit_per_room: int = MAX_COMPARABLE_RECORDS_PER_ROOM,
) -> list[ComparableRoomSelection]:
    """Select comparable competitor room IDs without using an LLM.

    The matcher prefers exact room-name matches. If none exist, it selects
    same-date rooms by room category, keyword overlap, and price proximity.
    It intentionally does not use every competitor room on the same date.
    """

    selections: list[ComparableRoomSelection] = []
    for own_room in context.own_rooms:
        same_date_candidates = [
            room
            for room in context.competitor_rooms
            if room.check_in_date == own_room.check_in_date
        ]
        if not same_date_candidates:
            selections.append(
                ComparableRoomSelection(
                    room_key=own_room.room_key,
                    comparable_record_ids=[],
                    benchmark_basis="no_same_date_competitor_rooms",
                    reasoning=(
                        "No competitor room was available for the same "
                        "check-in date."
                    ),
                    confidence="low",
                )
            )
            continue

        exact_matches = [
            room
            for room in same_date_candidates
            if _normalize_room_type(room.room_type)
            == _normalize_room_type(own_room.room_type)
        ]
        if exact_matches:
            selected_rooms = exact_matches[:limit_per_room]
            selections.append(
                ComparableRoomSelection(
                    room_key=own_room.room_key,
                    comparable_record_ids=[
                        room.record_id for room in selected_rooms
                    ],
                    benchmark_basis="exact_room_type_match",
                    reasoning=(
                        "Matched competitor rooms with the same normalized "
                        "room type."
                    ),
                    confidence="high",
                )
            )
            continue

        selected_rooms = _rank_candidate_rooms(
            own_room,
            same_date_candidates,
        )[:limit_per_room]
        selections.append(
            ComparableRoomSelection(
                room_key=own_room.room_key,
                comparable_record_ids=[
                    room.record_id for room in selected_rooms
                ],
                benchmark_basis="room_category_price_tier_match",
                reasoning=(
                    "No exact room-type match was found. Matched by room "
                    "category keywords, shared room descriptors, and nearest "
                    "total-price tier."
                ),
                confidence="medium" if selected_rooms else "low",
            )
        )
    return selections


def _rank_candidate_rooms(
    own_room: OwnRoomPricingContext,
    candidates: Sequence[CompetitorRoomPricingContext],
) -> list[CompetitorRoomPricingContext]:
    own_category = _room_category_score(own_room.room_type)
    own_tokens = _room_tokens(own_room.room_type)
    current_price = own_room.current_price

    def sort_key(room: CompetitorRoomPricingContext) -> tuple:
        room_category = _room_category_score(room.room_type)
        category_distance = abs(room_category - own_category)
        shared_tokens = len(
            own_tokens.intersection(_room_tokens(room.room_type)),
        )
        price_distance = abs(room.total_price - current_price)
        return (
            category_distance,
            -shared_tokens,
            price_distance,
            room.total_price,
            room.hotel_id,
            room.room_type,
        )

    return sorted(candidates, key=sort_key)


def _normalize_room_type(value: str) -> str:
    return " ".join(sorted(_room_tokens(value)))


def _room_tokens(value: str) -> set[str]:
    tokens = {
        token
        for token in re.findall(r"[a-z0-9]+", value.lower())
        if token
        and token
        not in {
            "room",
            "rooms",
            "bed",
            "beds",
            "king",
            "queen",
            "double",
            "twin",
            "or",
            "and",
            "non",
            "smoking",
        }
    }
    return tokens


def _room_category_score(room_type: str) -> int:
    lowered = room_type.lower()
    score = 2
    if any(token in lowered for token in ("no window", "internal", "insider")):
        score -= 2
    if any(token in lowered for token in ("standard", "superior", "deluxe")):
        score = max(score, 2)
    if any(token in lowered for token in ("premium", "premier", "executive")):
        score = max(score, 4)
    if any(
        token in lowered
        for token in ("suite", "signature", "family")
    ):
        score = max(score, 6)
    if "grand" in lowered:
        score = max(score, 7)
    if "city view" in lowered or "outside view" in lowered:
        score += 1
    return max(score, 0)
