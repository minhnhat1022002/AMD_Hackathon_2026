"""Domain enums."""

from __future__ import annotations

from enum import Enum


class Platform(str, Enum):
    """Supported OTA platforms."""

    BOOKING = "booking"
    EXPEDIA = "expedia"
    TRIP = "trip.com"


class RecommendationAction(str, Enum):
    """Pricing recommendation actions."""

    INCREASE_PRICE = "increase_price"
    DECREASE_PRICE = "decrease_price"
    KEEP_PRICE = "keep_price"


class AlertSeverity(str, Enum):
    """Monitoring alert severity."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class CrawlerStatus(str, Enum):
    """Crawler run status."""

    SUCCESS = "success"
    FAILED = "failed"


class PipelineStatus(str, Enum):
    """Aggregated pricing pipeline health."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
