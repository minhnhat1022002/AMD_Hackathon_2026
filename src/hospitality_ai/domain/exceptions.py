"""Domain and application exceptions."""

from __future__ import annotations


class HospitalityAIError(Exception):
    """Base exception for the hospitality AI package."""


class InvalidPricingRecordError(HospitalityAIError):
    """Raised when a raw pricing record cannot be normalized."""


class CrawlerClientError(HospitalityAIError):
    """Raised when a crawler client cannot fetch required data."""


class LLMClientError(HospitalityAIError):
    """Raised when an LLM client cannot generate a summary."""
