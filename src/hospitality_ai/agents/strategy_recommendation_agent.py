"""Strategy recommendation agent orchestration."""

from __future__ import annotations

from hospitality_ai.application.recommendation_service import (
    RecommendationService,
)
from hospitality_ai.domain.models import MonitoringReport, PricingInsightReport
from hospitality_ai.interfaces.serialization import to_jsonable

try:  # pragma: no cover - optional dependency branch
    from crewai import Agent
except Exception:  # pragma: no cover - optional dependency branch
    Agent = None  # type: ignore[assignment]


class StrategyRecommendationAgent:
    """Agent facade for combining pricing and monitoring outputs."""

    def __init__(self, service: RecommendationService) -> None:
        self._service = service

    def build_agent(self):
        """Build a CrewAI agent when CrewAI is installed."""

        if Agent is None:
            return None
        return Agent(
            role="Strategy Recommendation Agent",
            goal="Combine pricing insight and monitoring health into action.",
            backstory=(
                "You help business users decide when to adjust prices and "
                "when to first fix data quality issues."
            ),
            verbose=False,
        )

    def run(
        self,
        pricing_report: PricingInsightReport,
        monitoring_report: MonitoringReport,
    ) -> dict:
        """Run strategy recommendation orchestration."""

        recommendation = self._service.build_strategy_recommendation(
            pricing_report=pricing_report,
            monitoring_report=monitoring_report,
        )
        return to_jsonable(recommendation)
