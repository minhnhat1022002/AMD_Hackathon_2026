from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field, model_validator


class CollectPriceRequest(BaseModel):
    hotel_urls: list[str] | None = None
    hotel_names: list[str] | None = None
    check_in_dates: list[date] | None = None
    check_in_date: date | None = None
    check_out_date: date | None = None
    adults: int = Field(default=2, ge=1)
    children: int = Field(default=0, ge=0)
    rooms: int = Field(default=1, ge=1)
    currency: str | None = None
    include_raw: bool = True
    background_job: bool = False

    @model_validator(mode="after")
    def validate_sources(self) -> "CollectPriceRequest":
        has_urls = bool(self.hotel_urls)
        has_names = bool(self.hotel_names)
        if not has_urls and not has_names:
            raise ValueError("At least one of hotel_urls or hotel_names must be provided")
        check_in_dates = self.check_in_dates or []
        if (
            self.check_in_date
            and self.check_out_date
            and self.check_out_date <= self.check_in_date
        ):
            raise ValueError("check_out_date must be after check_in_date")
        if self.check_out_date and any(
            self.check_out_date <= check_in_date for check_in_date in check_in_dates
        ):
            raise ValueError("check_out_date must be after every check_in_dates value")
        return self


class PriceRecord(BaseModel):
    data: dict[str, Any]


class CollectPriceResponse(BaseModel):
    source: str
    total: int
    run_at: datetime
    hotel_url: str | None = None
    hotel_urls: list[str] | None = None
    data: list[dict[str, Any]]
