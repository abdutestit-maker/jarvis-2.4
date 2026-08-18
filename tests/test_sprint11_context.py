"""Sprint 11 living context, episodes, inference, privacy and summaries."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from core.living.context import LivingContextEngine
from core.living.inference import FrictionDetector, GoalTracker
from core.living.models import ContextObservation


BASE = datetime(2026, 8, 17, 9, 0, tzinfo=timezone.utc)


def _event(offset: int, **kwargs) -> ContextObservation:
    defaults = {
        "observed_at": BASE + timedelta(seconds=offset),
        "application": "Editor",
        "process": "editor.exe",
        "action": "edit_file",
        "target": "catalog/item.txt",
        "outcome": "success",
        "metadata": {"project": "catalog", "goal_hint": "prepare catalog assets"},
    }
    defaults.update(kwargs)
    return ContextObservation(**defaults)


def test_living_context_updates_structured_state_without_pixels_or_keystrokes(tmp_path: Path) -> None:
    engine = LivingContextEngine(tmp_path)

    context = engine.update(_event(
        0, window_title="catalog - Editor", metadata={
            "project": "catalog", "goal_hint": "prepare catalog assets",
            "screen_pixels": "raw", "keystrokes": "secret typing",
        },
    ))

    assert context.active_application == "Editor"
    assert context.current_project == "catalog"
    assert context.recent_actions == ["edit_file"]
    assert "screen_pixels" not in str(engine.observations)
    assert "secret typing" not in str(engine.observations)
    assert not list(tmp_path.glob("*screenshot*"))


def test_sensitive_window_is_reduced_to_category_and_private_values_are_removed(tmp_path: Path) -> None:
    engine = LivingContextEngine(tmp_path, sensitive_app_patterns=["password manager"])

    engine.update(_event(
        0, application="Password Manager", window_title="ACCOUNT — vault",
        target="ROLE password", clipboard_metadata={"type": "text", "value": "TOKEN"},
    ))
    stored = engine.observations[-1]

    assert stored.application == "sensitive_application"
    assert stored.window_title == ""
    assert stored.target == ""
    assert stored.clipboard_metadata == {"type": "text"}


def test_activity_episode_segmentation_uses_gap_and_meaningful_context_boundary(tmp_path: Path) -> None:
    engine = LivingContextEngine(tmp_path, minimum_episode_gap_seconds=120)
    engine.update(_event(0))
    engine.update(_event(20, action="export_file"))
    engine.update(_event(
        400, application="Browser", process="browser.exe", action="research",
        metadata={"goal_hint": "research product", "activity": "research"},
    ))

    episodes = engine.episodes(include_active=True)

    assert len(episodes) == 2
    assert episodes[0].high_level_actions == ["edit_file", "export_file"]
    assert episodes[0].end is not None
    assert episodes[1].applications == ["Browser"]


def test_goal_inference_requires_multiple_evidence_sources_and_reports_confidence() -> None:
    tracker = GoalTracker()
    observations = [
        _event(0, user_language="prepare catalog assets"),
        _event(10, action="resize_image"),
        _event(20, action="export_image"),
    ]

    goal = tracker.infer(observations, recent_missions=["prepare catalog assets"])

    assert goal.goal == "prepare catalog assets"
    assert goal.confidence >= 0.75
    assert len(goal.evidence) >= 2


def test_low_evidence_goal_does_not_claim_certainty() -> None:
    goal = GoalTracker().infer([_event(0, metadata={})])

    assert goal.confidence < 0.5
    assert goal.goal == ""


def test_friction_detector_uses_repeated_failures_and_workaround_not_emotion() -> None:
    events = [
        _event(0, action="export_pdf", outcome="failure", error_signature="E_EXPORT"),
        _event(15, action="export_pdf", outcome="failure", error_signature="E_EXPORT"),
        _event(30, action="export_pdf", outcome="workaround", error_signature="E_EXPORT"),
    ]

    signals = FrictionDetector().detect(events)

    assert signals[0].type == "repeated_failure"
    assert signals[0].confidence >= 0.8
    assert "angry" not in str(signals).lower()
    assert "зл" not in str(signals).lower()


def test_session_summary_and_return_context_are_evidence_based(tmp_path: Path) -> None:
    engine = LivingContextEngine(tmp_path)
    engine.update(_event(0, action="open_image"))
    engine.update(_event(10, action="export_image", outcome="failure", error_signature="E_EXPORT"))
    summary = engine.close_episode(outcome="unfinished")

    returned = engine.return_context(now=BASE + timedelta(hours=12), min_confidence=0.7)

    assert summary is not None
    assert summary["goal"] == "prepare catalog assets"
    assert summary["unfinished_work"] is True
    assert returned is not None
    assert "catalog" in returned.message
    assert returned.evidence


def test_natural_context_questions_never_invent_missing_activity(tmp_path: Path) -> None:
    engine = LivingContextEngine(tmp_path)

    assert engine.answer("что я сейчас делал?")["known"] is False
    engine.update(_event(0, action="export_image"))
    answer = engine.answer("на чем мы остановились?")
    assert answer["known"] is True
    assert "export_image" in answer["answer"]


class _FakeWindowProvider:
    def window_active(self):
        from core.platform.windows import ProviderResult
        return ProviderResult(True, {"title": "catalog - Editor", "process_id": 42}, provider="native_windows")


def test_context_monitor_collects_native_metadata_without_screen_content(tmp_path: Path) -> None:
    from core.living.monitor import LivingContextMonitor, WindowsContextSampler

    sampler = WindowsContextSampler(
        provider=_FakeWindowProvider(),
        process_lookup=lambda pid: "editor.exe",
        idle_lookup=lambda: 12.5,
        fullscreen_lookup=lambda handle: False,
    )
    engine = LivingContextEngine(tmp_path)
    monitor = LivingContextMonitor(engine, sampler=sampler, interval_seconds=0.05)

    context = monitor.tick()

    assert context.active_application == "Editor"
    assert context.active_process == "editor.exe"
    assert context.window_title == "catalog - Editor"
    assert engine.observations[-1].idle_seconds == 12.5
    assert "screen_pixels" not in str(engine.observations).casefold()
    assert "screenshot" not in str(engine.observations).casefold()
    assert "keystroke" not in str(engine.observations).casefold()


def test_learned_workflow_and_background_questions_use_structured_traces(tmp_path: Path) -> None:
    engine = LivingContextEngine(tmp_path)
    engine.update(_event(0, metadata={"workflow": "organize reports", "goal_hint": "organize reports"}))
    engine.update(_event(5, source="shadow_engine", action="sandbox_capability",
                         metadata={"goal_hint": "organize reports"}))

    learned = engine.answer("чему ты научился?")
    background = engine.answer("что ты делал пока меня не было?")

    assert learned["known"] is True
    assert "organize reports" in learned["answer"]
    assert background["known"] is True
    assert "sandbox_capability" in background["answer"]


def test_session_summary_contains_learned_workflows(tmp_path: Path) -> None:
    engine = LivingContextEngine(tmp_path)
    engine.update(_event(0, metadata={
        "project": "catalog", "goal_hint": "prepare catalog assets",
        "workflow": "export catalog image",
    }))

    summary = engine.close_episode(outcome="unfinished")

    assert summary is not None
    assert summary["learned_workflows"] == ["export catalog image"]

def test_context_redacts_secret_values_and_rejects_unstructured_metadata(tmp_path: Path) -> None:
    engine = LivingContextEngine(tmp_path)
    engine.update(_event(
        0, user_language="prepare catalog token=TOPSECRET",
        window_title="Editor",
        target="item secret=VAULT",
        metadata={"project": "catalog", "note": "TOKEN", "goal_hint": "prepare catalog"},
    ))

    stored = engine.observations[-1]

    assert stored.metadata["project"] == "catalog"
    assert "note" not in stored.metadata
    assert "TOPSECRET" not in str(stored)
    assert "VAULT" not in str(stored)
    assert "[redacted]" in stored.user_language
