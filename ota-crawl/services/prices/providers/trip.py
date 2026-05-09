from clients.trip.price_client import TripPriceClient
from common.constants import SOURCE_TRIP
from schemas.price import CollectPriceRequest
from services.prices.base import (
    BasePriceProvider,
    resolve_checkin_dates,
    resolve_checkout_date,
)


class TripPriceProvider(BasePriceProvider):
    source = SOURCE_TRIP

    def __init__(self) -> None:
        self.client = TripPriceClient()

    async def collect(self, payload: CollectPriceRequest) -> list[dict]:
        outputs: list[dict] = []
        for checkin_date in resolve_checkin_dates(payload):
            checkout_date = resolve_checkout_date(payload, checkin_date)
            outputs.extend(
                await self.client.fetch_prices(
                    hotel_urls=payload.hotel_urls or [],
                    hotel_names=payload.hotel_names or [],
                    checkin_date=checkin_date,
                    checkout_date=checkout_date,
                    adults=payload.adults,
                    children=payload.children,
                    rooms=payload.rooms,
                    currency=payload.currency,
                    include_raw=payload.include_raw,
                )
            )
        return outputs
