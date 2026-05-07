"""Application settings loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from hospitality_ai.domain.models import TripPriceQuery


def _load_dotenv_if_available() -> None:
    try:
        from dotenv import load_dotenv
    except Exception:
        return
    load_dotenv()


def _get_decimal(name: str, default: str) -> Decimal:
    return Decimal(os.getenv(name, default))


def _get_int(name: str, default: str) -> int:
    return int(os.getenv(name, default))


def _get_bool(name: str, default: str = "false") -> bool:
    value = os.getenv(name, default).strip().lower()
    return value in {"1", "true", "yes", "on"}


def _get_csv(name: str, default: str = "") -> list[str]:
    value = os.getenv(name, default)
    return [item.strip() for item in value.split(",") if item.strip()]


def _get_float(name: str, default: str) -> float:
    return float(os.getenv(name, default))


def _get_date_list(name: str, default: list[date]) -> list[date]:
    values = _get_csv(name)
    if not values:
        return default
    return [date.fromisoformat(value) for value in values]


def _get_optional_date(name: str) -> date | None:
    value = os.getenv(name)
    if not value:
        return None
    return date.fromisoformat(value)


@dataclass(frozen=True)
class Settings:
    """Runtime configuration for the optimization module."""

    own_hotel_id: str
    recommendation_threshold_percent: Decimal
    data_freshness_threshold_hours: int
    min_success_rate_percent: Decimal
    max_failed_crawl_count: int
    use_real_llm: bool
    llm_model: str
    llm_base_url: str
    llm_api_key: str | None
    llm_timeout_seconds: float
    llm_temperature: float
    llm_max_tokens: int
    mcp_server_url: str
    crawler_source: str
    trip_price_api_mode: str
    trip_price_api_base_url: str
    trip_price_api_timeout_seconds: float
    trip_hotel_urls: list[str]
    trip_hotel_names: list[str]
    trip_check_in_dates: list[date]
    trip_check_out_date: date | None
    trip_adults: int
    trip_children: int
    trip_rooms: int
    trip_currency: str | None

    @classmethod
    def from_env(cls) -> "Settings":
        """Create settings from environment variables with local defaults."""

        _load_dotenv_if_available()
        return cls(
            own_hotel_id=os.getenv("HOSPITALITY_OWN_HOTEL_ID", "hotel_own"),
            recommendation_threshold_percent=_get_decimal(
                "HOSPITALITY_RECOMMENDATION_THRESHOLD_PERCENT",
                "5",
            ),
            data_freshness_threshold_hours=_get_int(
                "HOSPITALITY_DATA_FRESHNESS_HOURS",
                "24",
            ),
            min_success_rate_percent=_get_decimal(
                "HOSPITALITY_MIN_SUCCESS_RATE_PERCENT",
                "95",
            ),
            max_failed_crawl_count=_get_int(
                "HOSPITALITY_MAX_FAILED_CRAWL_COUNT",
                "2",
            ),
            use_real_llm=_get_bool("HOSPITALITY_USE_REAL_LLM", "false"),
            llm_model=os.getenv("HOSPITALITY_LLM_MODEL", "gpt-4o-mini"),
            llm_base_url=os.getenv(
                "HOSPITALITY_LLM_BASE_URL",
                "https://api.openai.com/v1",
            ),
            llm_api_key=(
                os.getenv("HOSPITALITY_LLM_API_KEY")
                or os.getenv("OPENAI_API_KEY")
            ),
            llm_timeout_seconds=_get_float(
                "HOSPITALITY_LLM_TIMEOUT_SECONDS",
                "60",
            ),
            llm_temperature=_get_float("HOSPITALITY_LLM_TEMPERATURE", "0.2"),
            llm_max_tokens=_get_int("HOSPITALITY_LLM_MAX_TOKENS", "500"),
            mcp_server_url=os.getenv(
                "HOSPITALITY_MCP_SERVER_URL",
                "http://localhost:8765",
            ),
            crawler_source=os.getenv(
                "HOSPITALITY_CRAWLER_SOURCE",
                "mock",
            ).strip().lower(),
            trip_price_api_mode=os.getenv(
                "HOSPITALITY_TRIP_PRICE_API_MODE",
                "mock",
            ).strip().lower(),
            trip_price_api_base_url=os.getenv(
                "HOSPITALITY_TRIP_PRICE_API_BASE_URL",
                "http://localhost:8000",
            ),
            trip_price_api_timeout_seconds=_get_float(
                "HOSPITALITY_TRIP_PRICE_API_TIMEOUT_SECONDS",
                "90",
            ),
            trip_hotel_urls=_get_csv(
                "HOSPITALITY_TRIP_HOTEL_URLS",
                (
                    "https://www.trip.com/hotels/detail?hotelId=hotel_own,"
                    "https://www.trip.com/hotels/detail?hotelId=hotel_comp_a,"
                    "https://www.trip.com/hotels/detail?hotelId=hotel_comp_b"
                ),
            ),
            trip_hotel_names=_get_csv("HOSPITALITY_TRIP_HOTEL_NAMES"),
            trip_check_in_dates=_get_date_list(
                "HOSPITALITY_TRIP_CHECK_IN_DATES",
                [date.today() + timedelta(days=30)],
            ),
            trip_check_out_date=_get_optional_date(
                "HOSPITALITY_TRIP_CHECK_OUT_DATE",
            ),
            trip_adults=_get_int("HOSPITALITY_TRIP_ADULTS", "2"),
            trip_children=_get_int("HOSPITALITY_TRIP_CHILDREN", "0"),
            trip_rooms=_get_int("HOSPITALITY_TRIP_ROOMS", "1"),
            trip_currency=os.getenv("HOSPITALITY_TRIP_CURRENCY", "VND"),
        )

    def build_trip_price_query(self) -> TripPriceQuery:
        """Build the default Trip.com price query for local demos."""

        return TripPriceQuery(
            hotel_urls=self.trip_hotel_urls,
            hotel_names=self.trip_hotel_names,
            check_in_dates=self.trip_check_in_dates,
            check_out_date=self.trip_check_out_date,
            adults=self.trip_adults,
            children=self.trip_children,
            rooms=self.trip_rooms,
            currency=self.trip_currency,
            include_raw=True,
        )
