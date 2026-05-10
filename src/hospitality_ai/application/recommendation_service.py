"""Recommendation business rules."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from hospitality_ai.domain.enums import PipelineStatus, RecommendationAction
from hospitality_ai.domain.models import (
    MonitoringReport,
    PricingInsightReport,
    StrategyRecommendation,
)


class RecommendationService:
    """Encapsulates pricing and strategy recommendation rules."""

    def __init__(self, threshold_percent: Decimal) -> None:
        self._threshold_percent = threshold_percent

    def recommend_price(
        self,
        current_price: Decimal,
        average_competitor_price: Decimal,
    ) -> RecommendationAction:
        """Recommend a pricing action from current and competitor prices."""

        if average_competitor_price <= Decimal("0"):
            return RecommendationAction.KEEP_PRICE

        gap_percentage = (
            (current_price - average_competitor_price)
            / average_competitor_price
            * Decimal("100")
        )

        if gap_percentage < -self._threshold_percent:
            return RecommendationAction.INCREASE_PRICE
        if gap_percentage > self._threshold_percent:
            return RecommendationAction.DECREASE_PRICE
        return RecommendationAction.KEEP_PRICE

    def recommend_target_price(
        self,
        current_price: Decimal,
        average_competitor_price: Decimal,
    ) -> Decimal:
        """Recommend a concrete target price from a market benchmark.

        The target closes half of the gap to the comparable competitor
        benchmark. This avoids recommending abrupt jumps while still providing
        an actionable number.
        """

        if average_competitor_price <= Decimal("0"):
            return current_price

        action = self.recommend_price(
            current_price=current_price,
            average_competitor_price=average_competitor_price,
        )
        if action == RecommendationAction.KEEP_PRICE:
            return current_price

        return current_price + (
            average_competitor_price - current_price
        ) / Decimal("2")

    def build_strategy_recommendation(
        self,
        pricing_report: PricingInsightReport,
        monitoring_report: MonitoringReport,
    ) -> StrategyRecommendation:
        """Build a concise strategy recommendation from two reports."""

        pricing_actions = [
            insight.recommendation for insight in pricing_report.insights
        ]
        decrease_count = pricing_actions.count(
            RecommendationAction.DECREASE_PRICE,
        )
        increase_count = pricing_actions.count(
            RecommendationAction.INCREASE_PRICE,
        )

        if monitoring_report.status == PipelineStatus.CRITICAL:
            summary = (
                "Pricing data quality is critical. Fix crawler or pipeline "
                "issues before making price changes."
            )
        elif decrease_count > increase_count:
            summary = (
                "Several room/date combinations are above the competitor "
                "benchmark. Consider targeted price decreases."
            )
        elif increase_count > decrease_count:
            summary = (
                "Several room/date combinations are below the competitor "
                "benchmark. Consider targeted price increases."
            )
        else:
            summary = (
                "Pricing is broadly aligned with competitors. Keep monitoring "
                "freshness and anomaly signals."
            )

        return StrategyRecommendation(
            generated_at=datetime.now(timezone.utc),
            pricing_actions=pricing_actions,
            monitoring_status=monitoring_report.status,
            summary=summary,
        )
