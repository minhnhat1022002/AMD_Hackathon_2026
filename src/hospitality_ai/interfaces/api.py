"""Minimal API composition point.

FastAPI is optional for version one. The CLI is the primary runnable demo.
"""

from __future__ import annotations

from hospitality_ai.config.settings import Settings
from hospitality_ai.interfaces.cli import build_container
from hospitality_ai.interfaces.serialization import to_jsonable
from hospitality_ai.interfaces.trip_price_api import create_trip_price_router
from hospitality_ai.agents.guest_agent import guest_agent
from hospitality_ai.monitoring.workflow_monitor import workflow_monitor
from hospitality_ai.api.routes.workflow_visualization import router as workflow_router
import os
import logging
import sys
import markdown

# Configure logging to output to terminal
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

def create_app():
    """Create a FastAPI app if FastAPI is installed."""

    try:
        from fastapi import FastAPI
        from fastapi.staticfiles import StaticFiles
        from fastapi.responses import HTMLResponse
    except Exception as exc:  # pragma: no cover - optional dependency branch
        raise RuntimeError(
            "FastAPI is not installed. Install the api extra or use the CLI.",
        ) from exc

    app = FastAPI(title="Hospitality AI Optimization API")
    app.include_router(create_trip_price_router())
    app.include_router(workflow_router)
    
    # Mount static files for guest chat
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    
    # Add logging middleware
    @app.middleware("http")
    async def log_requests(request, call_next):
        logger.info(f"Request: {request.method} {request.url}")
        response = await call_next(request)
        logger.info(f"Response: {response.status_code}")
        return response

    def get_container() -> dict:
        return build_container(Settings.from_env())

    @app.get("/pricing-insight")
    def pricing_insight() -> dict:
        container = get_container()
        report = container["pricing_service"].generate_report()
        return to_jsonable(report)

    @app.get("/price-insight")
    def price_insight() -> dict:
        container = get_container()
        report = container["pricing_service"].generate_report()
        return to_jsonable(report)

    @app.get("/performance-monitoring")
    def performance_monitoring() -> dict:
        container = get_container()
        report = container["monitoring_service"].generate_report()
        return to_jsonable(report)

    @app.post("/guest/message")
    def guest_message(request: dict) -> dict:
        """Process guest message and return response."""
        try:
            guest_id = request.get("guest_id")
            message = request.get("message")
            
            if not guest_id or not message:
                return {
                    "reply": "Please provide both guest_id and message",
                    "action": "error"
                }
            
            # Use Guest Agent to process message
            from hospitality_ai.agents.guest_agent import GuestMessage, GuestResponse
            guest_request = GuestMessage(
                guest_id=guest_id,
                message=message,
                timestamp=None
            )
            
            response = guest_agent.process_message(guest_request)
            
            # Format reply with markdown - simple inline formatting
            formatted_reply = markdown.markdown(response.message, extensions=['extra'])
            
            return {
                "reply": formatted_reply,
                "action": response.action
            }
            
        except Exception as e:
            logger.error(f"API Error processing guest {guest_id}: {str(e)}", exc_info=True)
            return {
                "reply": f"Error processing message: {str(e)}",
                "action": "error"
            }

    @app.get("/workflow/summary")
    def get_workflow_summary() -> dict:
        """Get real-time workflow monitoring summary."""
        try:
            summary = workflow_monitor.get_workflow_summary()
            return summary
        except Exception as e:
            logger.error(f"Error getting workflow summary: {str(e)}", exc_info=True)
            return {"error": str(e)}

    @app.get("/", response_class=HTMLResponse)
    def guest_chat() -> HTMLResponse:
        """Serve the guest chat interface."""
        try:
            templates_dir = os.path.join(os.path.dirname(__file__), "templates", "guest-chat.html")
            with open(templates_dir, "r", encoding="utf-8") as f:
                html_content = f.read()
            return HTMLResponse(content=html_content)
        except FileNotFoundError:
            return HTMLResponse(content="<h1>Guest Chat Interface Not Found</h1>", status_code=404)

    @app.get("/frontdesk", response_class=HTMLResponse)
    def frontdesk_dashboard() -> HTMLResponse:
        """Serve the front desk dashboard interface."""
        try:
            templates_dir = os.path.join(os.path.dirname(__file__), "templates", "frontdesk-dashboard.html")
            with open(templates_dir, "r", encoding="utf-8") as f:
                html_content = f.read()
            return HTMLResponse(content=html_content)
        except FileNotFoundError:
            return HTMLResponse(content="<h1>Front Desk Dashboard Not Found</h1>", status_code=404)

    # Front Desk Dashboard API Endpoints
    @app.get("/booking/reservations")
    def get_reservations() -> dict:
        """Get all reservations for front desk dashboard."""
        try:
            from hospitality_ai.interfaces.dashboard_service import DashboardService
            container = get_container()
            dashboard_service = DashboardService(container)
            return dashboard_service.get_reservations()
        except Exception as e:
            logger.error(f"Error getting reservations: {str(e)}")
            return {"reservations": []}

    @app.post("/booking/override")
    def override_booking(request: dict) -> dict:
        """Override a booking reservation."""
        try:
            from hospitality_ai.interfaces.dashboard_service import DashboardService
            container = get_container()
            dashboard_service = DashboardService(container)
            result = dashboard_service.override_booking(request)
            return {"success": True, "message": "Booking updated successfully"}
        except Exception as e:
            logger.error(f"Error overriding booking: {str(e)}")
            return {"success": False, "message": f"Error: {str(e)}"}

    @app.get("/guest/activity")
    def get_guest_activity() -> dict:
        """Get guest activity for monitoring."""
        try:
            from hospitality_ai.interfaces.dashboard_service import DashboardService
            container = get_container()
            dashboard_service = DashboardService(container)
            return dashboard_service.get_guest_activity()
        except Exception as e:
            logger.error(f"Error getting guest activity: {str(e)}")
            return {"guests": []}

    @app.get("/decision/queue")
    def get_decision_queue() -> dict:
        """Get decision queue for front desk."""
        try:
            from hospitality_ai.interfaces.dashboard_service import DashboardService
            container = get_container()
            dashboard_service = DashboardService(container)
            return dashboard_service.get_decision_queue()
        except Exception as e:
            logger.error(f"Error getting decision queue: {str(e)}")
            return {"cases": []}

    @app.post("/decision/resolve")
    def resolve_case(request: dict) -> dict:
        """Resolve a decision case."""
        try:
            from hospitality_ai.interfaces.dashboard_service import DashboardService
            container = get_container()
            dashboard_service = DashboardService(container)
            result = dashboard_service.resolve_case(request)
            return {"success": True, "message": "Case resolved successfully"}
        except Exception as e:
            logger.error(f"Error resolving case: {str(e)}")
            return {"success": False, "message": f"Error: {str(e)}"}

    return app
