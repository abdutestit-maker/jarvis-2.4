from __future__ import annotations

from pathlib import Path

from config import Settings
from core.actions.base import ActionResult
from core.research import ResearchEngine


def test_search_failure_is_resumable_and_never_claims_success(monkeypatch, tmp_path: Path):
    settings = Settings()
    settings.paths.documents_dir = str(tmp_path)

    def fake_execute(registry, name, args, context):
        return ActionResult(tool=name, args=args, ok=False, error="offline fixture")

    monkeypatch.setattr("core.research.execute_tool", fake_execute)
    report = ResearchEngine(settings).run("найди книгу")
    assert report.verified is False
    assert report.status == "research_pending"
    assert report.resume_task_id.startswith("research-")
    assert "Возобновление" in report.to_text()
