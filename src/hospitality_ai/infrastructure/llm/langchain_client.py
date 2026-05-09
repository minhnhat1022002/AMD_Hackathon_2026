"""LLM summary adapters."""

from __future__ import annotations

import json
import re
from typing import Any

from hospitality_ai.application.pricing_market_matcher import (
    select_comparable_rooms_deterministically,
)
from hospitality_ai.domain.enums import RecommendationAction
from hospitality_ai.domain.exceptions import LLMClientError
from hospitality_ai.domain.models import (
    ComparableRoomSelection,
    MonitoringReport,
    PricingInsightReport,
    PricingMarketContext,
)

try:  # pragma: no cover - optional dependency branch
    from langchain_core.prompts import PromptTemplate
except Exception:  # pragma: no cover - optional dependency branch
    PromptTemplate = None  # type: ignore[assignment]


class LangChainLLMClient:
    """Deterministic local summary client with optional LangChain templates."""

    def __init__(self, model_name: str = "mock-llm") -> None:
        self._model_name = model_name

    def select_comparable_rooms(
        self,
        context: PricingMarketContext,
    ) -> list[ComparableRoomSelection]:
        """Select comparable rooms deterministically for local mode."""

        return select_comparable_rooms_deterministically(context)

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
                    "Mention the key recommendation, price guidance by room "
                    "type, and the reason behind the guidance.\n\n"
                    f"Context:\n{context}"
                ),
            ),
        ]
        return self._chat(messages)

    def select_comparable_rooms(
        self,
        context: PricingMarketContext,
    ) -> list[ComparableRoomSelection]:
        """Use an LLM to choose comparable competitor rooms by record ID."""

        payload = _pricing_market_context_to_payload(context)
        messages = [
            _build_system_message(
                (
                    "You are a hotel revenue management analyst. Your task "
                    "is to choose comparable competitor room records for "
                    "each own hotel room. Return JSON only. Do not invent "
                    "room keys or competitor record IDs."
                ),
            ),
            _build_human_message(
                (
                    "Select 3 to 8 comparable competitor rooms for each "
                    "own room when possible. Compare room category, view, "
                    "suite/family/premium keywords, and price tier. Only use "
                    "competitor records with the same check-in date. Return "
                    "this JSON shape exactly:\n"
                    "{"
                    '"selections":[{'
                    '"room_key":"own_001",'
                    '"comparable_record_ids":["cmp_001"],'
                    '"benchmark_basis":"short label",'
                    '"reasoning":"short business reason",'
                    '"confidence":"high|medium|low"'
                    "}]}\n\n"
                    f"Market context JSON:\n{json.dumps(payload)}"
                ),
            ),
        ]
        response_text = self._chat(messages)
        return _parse_comparable_room_selections(response_text, context)

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
            f"recommendation={insight.recommendation.value}, "
            f"recommended_price={insight.recommended_price}, "
            f"benchmark_basis={insight.benchmark_basis}, "
            f"confidence={insight.confidence}, "
            f"competitor_room_types={insight.competitor_room_types}, "
            f"benchmark_reasoning={insight.benchmark_reasoning}"
        )
        for insight in report.insights
    ]
    record_lines = [
        (
            f"- {record.hotel_id} | {record.hotel_name} | "
            f"{record.room_type} | {record.check_in_date.isoformat()} | "
            f"price_before_tax={record.price} | tax={record.tax} | "
            f"discount={record.discount} | total={record.total_price}"
        )
        for record in report.pricing_records[:80]
    ]

    context = [
        f"Own hotel ID: {report.own_hotel_id}.",
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
        "Computed pricing insights:",
        *insight_lines,
    ]
    if record_lines:
        context.extend(["Normalized PricingRecord rows:", *record_lines])
    return "\n".join(context)


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


def _pricing_market_context_to_payload(
    context: PricingMarketContext,
) -> dict[str, Any]:
    return {
        "own_hotel_id": context.own_hotel_id,
        "own_rooms": [
            {
                "room_key": room.room_key,
                "room_type": room.room_type,
                "check_in_date": room.check_in_date.isoformat(),
                "current_price": str(room.current_price),
            }
            for room in context.own_rooms
        ],
        "competitor_rooms": [
            {
                "record_id": room.record_id,
                "hotel_id": room.hotel_id,
                "hotel_name": room.hotel_name,
                "room_type": room.room_type,
                "check_in_date": room.check_in_date.isoformat(),
                "total_price": str(room.total_price),
            }
            for room in context.competitor_rooms
        ],
    }


def _parse_comparable_room_selections(
    response_text: str,
    context: PricingMarketContext,
) -> list[ComparableRoomSelection]:
    payload = _load_json_object(response_text)
    raw_selections = payload.get("selections")
    if not isinstance(raw_selections, list):
        raise LLMClientError("Comparable-room LLM response has no selections.")

    valid_room_keys = {room.room_key for room in context.own_rooms}
    valid_record_ids = {room.record_id for room in context.competitor_rooms}
    selections: list[ComparableRoomSelection] = []
    for raw_selection in raw_selections:
        if not isinstance(raw_selection, dict):
            continue
        room_key = str(raw_selection.get("room_key") or "").strip()
        if room_key not in valid_room_keys:
            continue
        raw_record_ids = raw_selection.get("comparable_record_ids")
        record_ids = [
            str(record_id)
            for record_id in raw_record_ids
            if str(record_id) in valid_record_ids
        ] if isinstance(raw_record_ids, list) else []
        selections.append(
            ComparableRoomSelection(
                room_key=room_key,
                comparable_record_ids=record_ids,
                benchmark_basis=str(
                    raw_selection.get("benchmark_basis")
                    or "llm_comparable_room_selection",
                ),
                reasoning=str(raw_selection.get("reasoning") or "").strip(),
                confidence=_normalize_confidence(
                    raw_selection.get("confidence"),
                ),
            )
        )

    if not selections:
        raise LLMClientError("Comparable-room LLM response was empty.")
    return selections


def _load_json_object(response_text: str) -> dict[str, Any]:
    cleaned = response_text.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", cleaned, re.DOTALL)
    if fenced:
        cleaned = fenced.group(1).strip()

    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise LLMClientError(
            f"Comparable-room LLM response is not valid JSON: {exc}",
        ) from exc

    if not isinstance(payload, dict):
        raise LLMClientError(
            "Comparable-room LLM response must be a JSON object.",
        )
    return payload


def _normalize_confidence(value: Any) -> str:
    confidence = str(value or "medium").strip().lower()
    if confidence not in {"high", "medium", "low"}:
        return "medium"
    return confidence
