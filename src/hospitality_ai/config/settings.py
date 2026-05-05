"""Application settings loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from decimal import Decimal


def _get_decimal(name: str, default: str) -> Decimal:
    return Decimal(os.getenv(name, default))


def _get_int(name: str, default: str) -> int:
    return int(os.getenv(name, default))


def _get_bool(name: str, default: str = "false") -> bool:
    value = os.getenv(name, default).strip().lower()
    return value in {"1", "true", "yes", "on"}


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
    mcp_server_url: str

    @classmethod
    def from_env(cls) -> "Settings":
        """Create settings from environment variables with local defaults."""

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
            llm_model=os.getenv("HOSPITALITY_LLM_MODEL", "mock-llm"),
            mcp_server_url=os.getenv(
                "HOSPITALITY_MCP_SERVER_URL",
                "http://localhost:8765",
            ),
        )
