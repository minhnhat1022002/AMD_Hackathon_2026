"""LLM summary adapters.

Version one provides deterministic local summaries while keeping a LangChain
prompt boundary that can be swapped for a real chat model later.
"""

from __future__ import annotations

from hospitality_ai.domain.enums import RecommendationAction
from hospitality_ai.domain.models import MonitoringReport, PricingInsightReport

try:  # pragma: no cover - optional dependency branch
    from langchain_core.prompts import PromptTemplate
except Exception:  # pragma: no cover - optional dependency branch
    PromptTemplate = None  # type: ignore[assignment]


class LangChainLLMClient:
    """Business summary client with an optional LangChain prompt layer."""

    def __init__(self, model_name: str = "mock-llm") -> None:
        self._model_name = model_name

    def summarize_pricing_insight(
        self,
        report: PricingInsightReport,
    ) -> str:
        """Create a concise business summary for pricing insight."""

        if not report.insights:
            return "No pricing insight is available for the selected filters."

        increase_count = sum(
            1
            for insight in report.insights
            if insight.recommendation == RecommendationAction.INCREASE_PRICE
        )
        decrease_count = sum(
            1
            for insight in report.insights
            if insight.recommendation == RecommendationAction.DECREASE_PRICE
        )
        keep_count = len(report.insights) - increase_count - decrease_count
        largest_gap = max(
            report.insights,
            key=lambda insight: abs(insight.price_gap_percentage),
        )

        context = (
            f"{len(report.insights)} room/date combinations analyzed. "
            f"Increase: {increase_count}, decrease: {decrease_count}, "
            f"keep: {keep_count}. Largest gap: {largest_gap.room_type} on "
            f"{largest_gap.check_in_date.isoformat()} at "
            f"{largest_gap.price_gap_percentage}%."
        )

        if PromptTemplate is not None:
            prompt = PromptTemplate.from_template(
                "Pricing summary: {context}",
            )
            return prompt.format(context=context)
        return f"Pricing summary: {context}"

    def summarize_monitoring(self, report: MonitoringReport) -> str:
        """Create a concise business summary for monitoring."""

        alert_codes = ", ".join(alert.code for alert in report.alerts)
        context = (
            f"Pipeline status is {report.status.value}. "
            f"Crawl success rate is {report.crawl_success_rate_percent}%, "
            f"failed crawls: {report.failed_crawl_count}, "
            f"freshness: {report.data_freshness_minutes} minutes, "
            f"alerts: {alert_codes}."
        )

        if PromptTemplate is not None:
            prompt = PromptTemplate.from_template(
                "Monitoring summary: {context}",
            )
            return prompt.format(context=context)
        return f"Monitoring summary: {context}"


class MockLLMClient(LangChainLLMClient):
    """Explicit local mock summary client."""
