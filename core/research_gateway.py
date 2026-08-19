"""Structured local research gateway for the Universal Mind loop.

The gateway deliberately delegates network access to the existing
``ResearchEngine`` and action registry.  It adds a small stable API so the
cognitive kernel can persist ``research_pending`` without treating an empty
search page as a successful answer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from config.settings import Settings
from core.research import ResearchEngine, ResearchReport


@dataclass
class ResearchResult:
    query: str
    status: str = "research_pending"
    sources: list[dict[str, Any]] = field(default_factory=list)
    source_errors: list[str] = field(default_factory=list)
    cached_results: list[dict[str, Any]] = field(default_factory=list)
    local_fallback: list[dict[str, Any]] = field(default_factory=list)
    resume_task_id: str = ""
    report: dict[str, Any] = field(default_factory=dict)

    @property
    def verified(self) -> bool:
        return self.status == "completed" and bool(self.sources)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "query": self.query,
            "sources": list(self.sources),
            "source_errors": list(self.source_errors),
            "cached_results": list(self.cached_results),
            "local_fallback": list(self.local_fallback),
            "resume_task_id": self.resume_task_id,
            "report": dict(self.report),
        }


class ResearchGateway:
    """One local-only boundary for online/offline research missions."""

    def __init__(self, settings: Settings, *, engine: ResearchEngine | None = None) -> None:
        self.settings = settings
        self.engine = engine or ResearchEngine(settings)
        self._pending: dict[str, str] = {}

    def search(self, query: str, constraints: Mapping[str, Any] | None = None) -> ResearchResult:
        query = " ".join(str(query or "").split())
        report = self.engine.run(query)
        result = self._from_report(report)
        if result.resume_task_id:
            self._pending[result.resume_task_id] = query
        return result

    def fetch(self, source_url: str) -> dict[str, Any]:
        """Fetch one source through the existing verified action registry."""
        from core.actions import DEFAULT_REGISTRY
        from core.actions.base import ToolContext
        from core.actions.executor import execute_tool

        url = str(source_url or "").strip()
        if not url:
            return {"ok": False, "error": "source_url is required"}
        tool = DEFAULT_REGISTRY.get("web_fetch")
        if tool is None:
            return {"ok": False, "error": "web_fetch capability unavailable"}
        outcome = execute_tool(DEFAULT_REGISTRY, "web_fetch", {"url": url}, ToolContext(settings=self.settings))
        return {"ok": bool(outcome.ok), "url": url, "content": outcome.output if outcome.ok else "", "error": outcome.error}

    def verify_sources(self, result: ResearchResult | ResearchReport | Mapping[str, Any]) -> dict[str, Any]:
        data = result.to_dict() if hasattr(result, "to_dict") else dict(result)
        sources = data.get("sources") or data.get("sources_read") or []
        findings = data.get("findings") or []
        return {
            "verified": bool(data.get("status") == "completed" and sources and findings),
            "source_count": len(sources),
            "evidence": findings,
        }

    def resume(self, task_id: str) -> ResearchResult:
        query = self._pending.get(str(task_id), "")
        if not query:
            return ResearchResult(query="", resume_task_id=str(task_id), source_errors=["unknown resume task"])
        return self.search(query)

    @staticmethod
    def _from_report(report: ResearchReport) -> ResearchResult:
        data = report.to_dict()
        return ResearchResult(
            query=report.query,
            status=report.status,
            sources=[{"url": url} for url in report.sources_read],
            source_errors=list(report.sources_failed),
            local_fallback=list(report.local_fallback),
            resume_task_id=report.resume_task_id,
            report=data,
        )


__all__ = ["ResearchGateway", "ResearchResult"]
