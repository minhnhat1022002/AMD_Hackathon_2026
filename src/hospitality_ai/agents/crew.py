"""CrewAI composition for hospitality optimization workflows."""

from __future__ import annotations

from hospitality_ai.agents.performance_monitoring_agent import (
    PerformanceMonitoringAgent,
)
from hospitality_ai.agents.pricing_insight_agent import PricingInsightAgent
from hospitality_ai.agents.strategy_recommendation_agent import (
    StrategyRecommendationAgent,
)
from hospitality_ai.application.performance_monitoring_service import (
    PerformanceMonitoringService,
)
from hospitality_ai.application.pricing_insight_service import (
    PricingInsightService,
)
from hospitality_ai.application.recommendation_service import (
    RecommendationService,
)
from hospitality_ai.interfaces.serialization import to_jsonable

try:  # pragma: no cover - optional dependency branch
    from crewai import Crew
except Exception:  # pragma: no cover - optional dependency branch
    Crew = None  # type: ignore[assignment]


class HospitalityOptimizationCrew:
    """Coordinates pricing insight, monitoring, and strategy agents."""

    def __init__(
        self,
        pricing_service: PricingInsightService,
        monitoring_service: PerformanceMonitoringService,
        recommendation_service: RecommendationService,
    ) -> None:
        self.pricing_agent = PricingInsightAgent(pricing_service)
        self.monitoring_agent = PerformanceMonitoringAgent(monitoring_service)
        self.strategy_agent = StrategyRecommendationAgent(
            recommendation_service,
        )
        self._pricing_service = pricing_service
        self._monitoring_service = monitoring_service

    def build_crew(self):
        """Build a CrewAI crew shell when CrewAI is installed."""

        if Crew is None:
            return None

        agents = [
            agent
            for agent in [
                self.pricing_agent.build_agent(),
                self.monitoring_agent.build_agent(),
                self.strategy_agent.build_agent(),
            ]
            if agent is not None
        ]
        return Crew(agents=agents, tasks=[], verbose=False)

    def run_full_strategy(self) -> dict:
        """Run the full workflow without requiring external LLM calls."""

        pricing_report = self._pricing_service.generate_report()
        monitoring_report = self._monitoring_service.generate_report()
        strategy = self.strategy_agent.run(
            pricing_report=pricing_report,
            monitoring_report=monitoring_report,
        )
        return {
            "pricing": to_jsonable(pricing_report),
            "monitoring": to_jsonable(monitoring_report),
            "strategy": strategy,
        }
