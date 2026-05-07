"""LLM summary adapters."""

from __future__ import annotations

from typing import Any

from hospitality_ai.domain.enums import RecommendationAction
from hospitality_ai.domain.exceptions import LLMClientError
from hospitality_ai.domain.models import MonitoringReport, PricingInsightReport

try:  # pragma: no cover - optional dependency branch
    from langchain_core.prompts import PromptTemplate
except Exception:  # pragma: no cover - optional dependency branch
    PromptTemplate = None  # type: ignore[assignment]


class LangChainLLMClient:
    """Deterministic local summary client with optional LangChain templates."""

    def __init__(self, model_name: str = "mock-llm") -> None:
        self._model_name = model_name

    def summarize_pricing_insight(
        self,
        report: PricingInsightReport,
    ) -> str:
        """Create a concise local summary for pricing insight."""

        context = build_pricing_summary_context(report)
        if PromptTemplate is not None:
            prompt = PromptTemplate.from_template(
                "Pricing summary: {context}",
            )
            return prompt.format(context=context)
        return f"Pricing summary: {context}"

    def summarize_monitoring(self, report: MonitoringReport) -> str:
        """Create a concise local summary for monitoring."""

        context = build_monitoring_summary_context(report)
        if PromptTemplate is not None:
            prompt = PromptTemplate.from_template(
                "Monitoring summary: {context}",
            )
            return prompt.format(context=context)
        return f"Monitoring summary: {context}"


class MockLLMClient(LangChainLLMClient):
    """Explicit local mock summary client."""


class OpenAICompatibleLLMClient:
    """LLM client for OpenAI-compatible chat completion APIs."""

    def __init__(
        self,
        api_key: str | None,
        model_name: str,
        base_url: str = "https://api.openai.com/v1",
        timeout_seconds: float = 60.0,
        temperature: float = 0.2,
        max_tokens: int = 500,
    ) -> None:
        if not api_key:
            raise LLMClientError(
                "Missing LLM API key. Set HOSPITALITY_LLM_API_KEY or "
                "OPENAI_API_KEY.",
            )

        self._client = _build_chat_openai_client(
            api_key=api_key,
            model_name=model_name,
            base_url=base_url,
            timeout_seconds=timeout_seconds,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    def summarize_pricing_insight(
        self,
        report: PricingInsightReport,
    ) -> str:
        """Generate a business summary for a pricing insight report."""

        context = build_pricing_summary_context(report)
        messages = [
            _build_system_message(
                (
                    "You are a senior revenue management assistant for a "
                    "hotel business user. Explain pricing insight clearly, "
                    "avoid technical jargon, and keep the response concise."
                ),
            ),
            _build_human_message(
                (
                    "Write a short pricing insight summary in Vietnamese. "
                    "Mention the key recommendation and the biggest gap.\n\n"
                    f"Context:\n{context}"
                ),
            ),
        ]
        return self._chat(messages)

    def summarize_monitoring(self, report: MonitoringReport) -> str:
        """Generate a business summary for a monitoring report."""

        context = build_monitoring_summary_context(report)
        messages = [
            _build_system_message(
                (
                    "You are an AI operations monitoring assistant for a "
                    "hotel pricing pipeline. Explain health, alerts, and "
                    "next action clearly."
                ),
            ),
            _build_human_message(
                (
                    "Write a short monitoring summary in Vietnamese. "
                    "Prioritize critical alerts and recommended next action."
                    f"\n\nContext:\n{context}"
                ),
            ),
        ]
        return self._chat(messages)

    def _chat(self, messages: list[Any]) -> str:
        try:
            response = self._client.invoke(messages)
        except Exception as exc:
            raise LLMClientError(
                f"LangChain OpenAI request failed: {exc}",
            ) from exc

        return _extract_langchain_message_text(response)


def build_pricing_summary_context(report: PricingInsightReport) -> str:
    """Build deterministic pricing context before calling an LLM."""

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

    insight_lines = [
        (
            f"- {insight.room_type} {insight.check_in_date.isoformat()}: "
            f"current={insight.current_price}, "
            f"competitor_avg={insight.average_competitor_price}, "
            f"gap={insight.price_gap_percentage}%, "
            f"recommendation={insight.recommendation.value}"
        )
        for insight in report.insights
    ]

    return "\n".join(
        [
            f"Hotel ID: {report.own_hotel_id}.",
            f"{len(report.insights)} room/date combinations analyzed.",
            (
                f"Recommendation counts: increase={increase_count}, "
                f"decrease={decrease_count}, keep={keep_count}."
            ),
            (
                f"Largest gap: {largest_gap.room_type} on "
                f"{largest_gap.check_in_date.isoformat()} at "
                f"{largest_gap.price_gap_percentage}%."
            ),
            "Details:",
            *insight_lines,
        ],
    )


def build_monitoring_summary_context(report: MonitoringReport) -> str:
    """Build deterministic monitoring context before calling an LLM."""

    alert_lines = [
        (
            f"- [{alert.severity.value}] {alert.code}: "
            f"{alert.message}"
        )
        for alert in report.alerts
    ]
    return "\n".join(
        [
            f"Pipeline status: {report.status.value}.",
            f"Crawl success rate: {report.crawl_success_rate_percent}%.",
            f"Failed crawls: {report.failed_crawl_count}.",
            (
                "Average crawl duration seconds: "
                f"{report.average_crawl_duration_seconds}."
            ),
            f"Data freshness minutes: {report.data_freshness_minutes}.",
            f"Missing price records: {report.missing_price_records}.",
            f"Price anomaly count: {report.price_anomaly_count}.",
            "Alerts:",
            *alert_lines,
        ],
    )


def _build_chat_openai_client(
    api_key: str,
    model_name: str,
    base_url: str,
    timeout_seconds: float,
    temperature: float,
    max_tokens: int,
) -> Any:
    try:
        from langchain_openai import ChatOpenAI
    except Exception as exc:
        raise LLMClientError(
            "langchain-openai is not installed. Run "
            '`pip install -e ".[dev]"` after updating dependencies, or run '
            "`pip install langchain-openai`.",
        ) from exc

    return ChatOpenAI(
        model=model_name,
        api_key=api_key,
        base_url=base_url.rstrip("/"),
        timeout=timeout_seconds,
        temperature=temperature,
        max_tokens=max_tokens,
    )


def _build_system_message(content: str) -> Any:
    try:
        from langchain_core.messages import SystemMessage
    except Exception as exc:
        raise LLMClientError(
            "langchain-core is not installed. Run `pip install -e .`.",
        ) from exc

    return SystemMessage(content=content)


def _build_human_message(content: str) -> Any:
    try:
        from langchain_core.messages import HumanMessage
    except Exception as exc:
        raise LLMClientError(
            "langchain-core is not installed. Run `pip install -e .`.",
        ) from exc

    return HumanMessage(content=content)


def _extract_langchain_message_text(response: Any) -> str:
    content = getattr(response, "content", None)

    if not isinstance(content, str) or not content.strip():
        if isinstance(content, list):
            text = _extract_text_from_content_blocks(content)
            if text:
                return text
        raise LLMClientError("LLM response message is empty.")

    return content.strip()


def _extract_text_from_content_blocks(content: list[Any]) -> str:
    parts: list[str] = []
    for block in content:
        if isinstance(block, str):
            parts.append(block)
            continue
        if isinstance(block, dict):
            text = block.get("text")
            if isinstance(text, str):
                parts.append(text)
    return "\n".join(part.strip() for part in parts if part.strip())
