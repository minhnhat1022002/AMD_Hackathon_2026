"""Trip.com price collection routes.

This router is intentionally small because ``ota-crawl`` is now used only as
the local Trip Price API that feeds the hospitality AI service.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request

from common.constants import SOURCE_TRIP
from exceptions import ConnectorNotFoundError
from schemas.price import CollectPriceRequest
from services.prices.registry import price_provider_registry
from services.prices.service import PriceService

router = APIRouter(prefix="/v1/prices", tags=["prices"])
logger = logging.getLogger(__name__)


def _get_service(request: Request) -> PriceService:
    """Read the request-scoped price service from FastAPI app state."""
    return request.app.state.price_service


def _api_response(
    data=None,
    message: str = "SUCCESS",
    status: int = 200,
    success: bool = True,
) -> dict:
    """Return the API envelope expected by the hospitality AI client."""
    return {
        "status": status,
        "success": success,
        "message": message,
        "data": data,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/sources", response_model=list[str])
async def list_sources() -> list[str]:
    """List price sources available in this trimmed service."""
    return price_provider_registry.list_sources()


@router.post("/collect/trip")
async def collect_trip_prices(
    payload: CollectPriceRequest,
    request: Request,
):
    """Collect Trip.com prices and return normalized records inline."""
    try:
        logger.info(
            "Received Trip price collect request hotel_urls=%s",
            len(payload.hotel_urls or []),
        )
        if payload.background_job:
            raise ValueError(
                "background_job is not supported by the trimmed Trip API"
            )

        result = await _get_service(request).collect_by_source(
            SOURCE_TRIP,
            payload,
        )
        return _api_response(
            data={"result": result.model_dump(mode="json")},
            message="COLLECT_SUCCESS",
        )
    except ConnectorNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
