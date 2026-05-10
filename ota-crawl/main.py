"""Trip.com price crawl API service."""

import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from config.settings import settings
from routers.prices_routers import router as prices_router
from services.bootstrap import register_default_providers
from services.prices.service import PriceService

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize the Trip price provider registry and request services."""
    register_default_providers()
    app.state.price_service = PriceService()

    logger.info("Trip Price API service initialized successfully")
    try:
        yield
    finally:
        logger.info("Trip Price API service shutting down")


app = FastAPI(
    title=settings.app_name,
    description="Minimal Trip.com price crawler API.",
    version="1.0.0",
    lifespan=lifespan,
)
app.include_router(prices_router)


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.app_debug,
    )
