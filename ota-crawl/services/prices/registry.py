from exceptions import ConnectorNotFoundError
from services.prices.base import BasePriceProvider


class PriceProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, BasePriceProvider] = {}

    def register(self, name: str, provider: BasePriceProvider) -> None:
        self._providers[name] = provider

    def get(self, name: str) -> BasePriceProvider:
        if name not in self._providers:
            raise ConnectorNotFoundError(f"Connector '{name}' is not registered")
        return self._providers[name]

    def list_sources(self) -> list[str]:
        return sorted(self._providers.keys())


price_provider_registry = PriceProviderRegistry()
