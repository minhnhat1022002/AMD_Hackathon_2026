"""Future MCP crawler client adapter."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from hospitality_ai.domain.exceptions import CrawlerClientError
from hospitality_ai.domain.models import CrawlerRunMetric


class McpCrawlerClient:
    """Placeholder adapter for a real MCP crawler server.

    The class implements the application crawler port shape. Version one keeps
    this adapter explicit but unimplemented so local development can use
    ``MockCrawlerClient`` without touching application services.
    """

    def __init__(self, server_url: str) -> None:
        self._server_url = server_url

    def fetch_pricing_records(self) -> Sequence[Mapping[str, Any]]:
        """Fetch pricing records from the MCP crawler server."""

        raise CrawlerClientError(
            "Real MCP integration is not implemented yet. "
            f"Configured server URL: {self._server_url}",
        )

    def fetch_crawler_runs(self) -> Sequence[CrawlerRunMetric]:
        """Fetch crawler run telemetry from the MCP crawler server."""

        raise CrawlerClientError(
            "Real MCP integration is not implemented yet. "
            f"Configured server URL: {self._server_url}",
        )
