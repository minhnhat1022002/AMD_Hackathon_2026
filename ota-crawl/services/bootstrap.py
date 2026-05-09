"""Provider registration for the trimmed Trip Price API."""

from common.constants import SOURCE_TRIP
from services.prices.providers.trip import TripPriceProvider
from services.prices.registry import price_provider_registry


def register_default_providers() -> None:
    """Register the only provider kept in this local crawl service."""
    if SOURCE_TRIP not in price_provider_registry.list_sources():
        price_provider_registry.register(SOURCE_TRIP, TripPriceProvider())
