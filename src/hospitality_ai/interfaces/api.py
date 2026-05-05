"""Minimal API composition point.

FastAPI is optional for version one. The CLI is the primary runnable demo.
"""

from __future__ import annotations

from hospitality_ai.config.settings import Settings
from hospitality_ai.interfaces.cli import build_container
from hospitality_ai.interfaces.serialization import to_jsonable


def create_app():
    """Create a FastAPI app if FastAPI is installed."""

    try:
        from fastapi import FastAPI
    except Exception as exc:  # pragma: no cover - optional dependency branch
        raise RuntimeError(
            "FastAPI is not installed. Install the api extra or use the CLI.",
        ) from exc

    app = FastAPI(title="Hospitality AI Optimization API")
    container = build_container(Settings.from_env())

    @app.get("/pricing-insight")
    def pricing_insight() -> dict:
        report = container["pricing_service"].generate_report()
        return to_jsonable(report)

    @app.get("/performance-monitoring")
    def performance_monitoring() -> dict:
        report = container["monitoring_service"].generate_report()
        return to_jsonable(report)

    return app
