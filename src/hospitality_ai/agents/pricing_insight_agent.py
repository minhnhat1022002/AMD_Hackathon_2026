"""Pricing insight agent orchestration."""

from __future__ import annotations

from hospitality_ai.application.pricing_insight_service import (
    PricingInsightService,
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


class PricingInsightAgent:
    """Agent facade for pricing insight workflow orchestration."""

    def __init__(self, service: PricingInsightService) -> None:
        self._service = service

    def build_agent(self):
        """Build a CrewAI agent when CrewAI is installed."""

        if Agent is None:
            return None
        return Agent(
            role="Pricing Insight Agent",
            goal="Analyze OTA pricing and explain hotel price positioning.",
            backstory=(
                "You help revenue managers compare hotel prices against "
                "competitors using normalized OTA crawler data."
            ),
            verbose=False,
        )

    def build_tool(self):
        """Build a LangChain tool wrapper when LangChain is installed."""

        if StructuredTool is None:
            return None
        return StructuredTool.from_function(
            func=self.run,
            name="generate_pricing_insight",
            description=(
                "Generate pricing insight for the configured hotel using "
                "crawler pricing data."
            ),
        )

    def run(self) -> dict:
        """Run pricing insight orchestration."""

        report = self._service.generate_report()
        return to_jsonable(report)
