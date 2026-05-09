from datetime import date, timedelta
from abc import ABC, abstractmethod
from typing import Any

from schemas.price import CollectPriceRequest


def resolve_checkin_dates(payload: CollectPriceRequest) -> list[date]:
    if payload.check_in_dates:
        return payload.check_in_dates
    if payload.check_in_date:
        return [payload.check_in_date]
    return [date.today()]


def resolve_checkout_date(
    payload: CollectPriceRequest,
    checkin_date: date,
) -> date:
    return payload.check_out_date or checkin_date + timedelta(days=1)


class BasePriceProvider(ABC):
    source: str

    @abstractmethod
    async def collect(self, payload: CollectPriceRequest) -> list[dict[str, Any]]:
        raise NotImplementedError
