"""Performance monitoring agent orchestration."""

from __future__ import annotations

from hospitality_ai.application.performance_monitoring_service import (
    PerformanceMonitoringService,
)
from hospitality_ai.interfaces.serialization import to_jsonable

try:  # pragma: no cover - optional dependency branch
    from crewai import Agent
except Exception:  # pragma: no cover - optional dependency branch
    Agent = None  # type: ignore[assignment]

try:  # pragma: no cover - optional dependency branch
    from langchain_core.tools import StructuredTool
except Exception:  # pragma: no cover - optional dependency branch
    StructuredTool = None  # type: ignore[assignment]


class PerformanceMonitoringAgent:
    """Agent facade for monitoring workflow orchestration."""

    def __init__(self, service: PerformanceMonitoringService) -> None:
        self._service = service

    def build_agent(self):
        """Build a CrewAI agent when CrewAI is installed."""

        if Agent is None:
            return None
        return Agent(
            role="Performance Monitoring Agent",
            goal="Monitor crawler and pricing pipeline health.",
            backstory=(
                "You watch crawler success, data freshness, missing prices, "
                "and pricing anomalies for hotel operators."
            ),
            verbose=False,
        )

    def build_tool(self):
        """Build a LangChain tool wrapper when LangChain is installed."""

        if StructuredTool is None:
            return None
        return StructuredTool.from_function(
            func=self.run,
            name="generate_performance_monitoring_report",
            description=(
                "Generate crawler and pricing pipeline monitoring report."
            ),
        )

    def run(self) -> dict:
        """Run monitoring orchestration."""

        report = self._service.generate_report()
        return to_jsonable(report)
