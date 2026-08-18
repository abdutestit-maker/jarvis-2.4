"""Real local Sprint 14 metacognition, correction and restart demo."""

from __future__ import annotations

import json
import os
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.actions import DEFAULT_REGISTRY  # noqa: E402
from core.cognitive import CognitiveOrchestrator  # noqa: E402
from core.metacognition import (  # noqa: E402
    EpistemicStatus,
    EvidenceRef,
    Expectation,
    Freshness,
    SourceType,
    Strategy,
)


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporary, path)


def run_demo(root: Path | str, *, reset: bool = True) -> dict[str, Any]:
    destination = Path(root).resolve()
    if reset and destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True, exist_ok=True)
    fixture = destination / "fixture_app.json"
    _write_json_atomic(fixture, {"version": "2.0", "feature_enabled": False})

    cognitive_dir = destination / "cognitive"
    coordinator = CognitiveOrchestrator(cognitive_dir, registry=DEFAULT_REGISTRY)
    now = datetime(2026, 8, 17, 17, 0, tzinfo=timezone.utc)

    # Deliberately stale and incorrect prior memory.
    coordinator.metacognition.record(
        key="fixture.version", claim="Installed fixture version", value="1.0",
        status=EpistemicStatus.INFERRED,
        evidence=[EvidenceRef(
            "memory:old-version", SourceType.MEMORY, "memory:fixture-version",
            reliability=0.65, observed_at=(now - timedelta(days=5)).isoformat(),
            verified=False, direct=False, memory_confidence=0.7,
        )],
        freshness=Freshness.volatile(now - timedelta(days=5), ttl_seconds=86_400),
        now=now,
    )

    def inspect_version() -> dict[str, Any]:
        current = json.loads(fixture.read_text(encoding="utf-8"))
        return {
            "value": current["version"], "source_id": "disk:fixture_app.json:version",
            "origin_id": "local_file:fixture_app.json", "reliability": 1.0,
        }

    knowledge = coordinator.resolve_knowledge(
        key="fixture.version", claim="Installed fixture version",
        observer=inspect_version, now=now,
    )
    _assert(knowledge.belief.value == "2.0", "direct observation did not correct memory")
    _assert(bool(knowledge.belief.contradictions), "contradiction evidence was lost")
    _assert("Раньше" in knowledge.response, "natural contradiction notice missing")

    action_calls: list[str] = []

    def misleading_provider_success():
        action_calls.append("cached_provider")
        return SimpleNamespace(ok=True, message="reported success")

    def atomic_config_write():
        action_calls.append("atomic_config")
        current = json.loads(fixture.read_text(encoding="utf-8"))
        current["feature_enabled"] = True
        _write_json_atomic(fixture, current)
        return SimpleNamespace(ok=True)

    def observe_feature() -> dict[str, Any]:
        current = json.loads(fixture.read_text(encoding="utf-8"))
        return {"feature_enabled": current["feature_enabled"]}

    environment = {"app": "fixture", "version": "2.0", "platform": "windows-local"}
    expectation = Expectation(
        "enable-feature", "enable fixture feature", "",
        {"feature_enabled": True}, "read fixture JSON independently",
        ["feature_enabled remains false"],
    )
    first_response, first = coordinator.execute_with_correction(
        goal="enable fixture feature", task_class="fixture_config",
        strategies=[
            Strategy("cached_provider", misleading_provider_success),
            Strategy("atomic_config", atomic_config_write),
        ], expectation=expectation, observer=observe_feature,
        evidence_provider=lambda: ["disk:fixture_app.json:feature_enabled"],
        environment=environment,
    )
    _assert(first.verified, "repair did not reach verified desired state")
    _assert(action_calls == ["cached_provider", "atomic_config"], "strategy change missing")
    _assert(first.attempts[0].reported_success and not first.attempts[0].verified,
            "provider success was trusted without observation")
    _assert(first.failure_episodes and first.failure_episodes[0].successful_repair == "atomic_config",
            "failure and repair episode not learned")
    observed_after = observe_feature()
    _assert(observed_after == {"feature_enabled": True}, "independent final verification failed")

    # Process restart plus similar task in the same environment.
    _write_json_atomic(fixture, {"version": "2.0", "feature_enabled": False})
    reopened = CognitiveOrchestrator(cognitive_dir, registry=DEFAULT_REGISTRY)
    second_calls: list[str] = []

    def should_be_avoided():
        second_calls.append("cached_provider")
        return SimpleNamespace(ok=True)

    def reused_repair():
        second_calls.append("atomic_config")
        current = json.loads(fixture.read_text(encoding="utf-8"))
        current["feature_enabled"] = True
        _write_json_atomic(fixture, current)
        return SimpleNamespace(ok=True)

    second_response, second = reopened.execute_with_correction(
        goal="enable fixture feature again", task_class="fixture_config",
        strategies=[
            Strategy("cached_provider", should_be_avoided),
            Strategy("atomic_config", reused_repair),
        ], expectation=expectation, observer=observe_feature,
        evidence_provider=lambda: ["disk:fixture_app.json:feature_enabled"],
        environment=environment,
    )
    _assert(second.verified, "second run did not verify")
    _assert(second_calls == ["atomic_config"], "known contextual failure was repeated")
    _assert(second.skipped_strategies == ["cached_provider"], "failed strategy not skipped")

    reopened.state.active_epistemic_key = "fixture.version"
    provenance = reopened.begin_interaction("Откуда ты это знаешь?", implicit_address=True)
    _assert(provenance.response == "Я проверил это в локальной системе.",
            "provenance answer did not use actual evidence")

    audit_path = reopened.audit.export_bundle(
        destination / "sprint14_audit_bundle.json",
        beliefs=reopened.belief_store.all(), failures=reopened.failure_store.all(),
    )
    audit_payload = json.loads(audit_path.read_text(encoding="utf-8"))
    event_types = sorted({item["type"] for item in audit_payload["events"]})
    required_events = {
        "belief_transition", "expectation", "action", "observation", "surprise",
        "strategy_change", "verification", "provenance",
    }
    _assert(required_events <= set(event_types), "audit bundle lacks required transitions")

    result = {
        "scenario": "stale belief -> observe -> contradict -> expect -> misleading success -> surprise -> repair -> verify -> learn -> restart -> avoid failure -> provenance",
        "stale_value": "1.0",
        "observed_value": knowledge.belief.value,
        "belief_status": knowledge.belief.status.value,
        "belief_confidence": knowledge.belief.confidence,
        "contradictions": knowledge.belief.contradictions,
        "belief_correction_message": knowledge.response,
        "first_action_calls": action_calls,
        "misleading_action_reported_success": first.attempts[0].reported_success,
        "misleading_action_verified": first.attempts[0].verified,
        "surprise": first.surprises[0].to_dict(),
        "selected_repair": first.selected_strategy,
        "first_response": first_response,
        "final_observed": observed_after,
        "final_verified": first.verified,
        "failure_episode": first.failure_episodes[0].to_dict(),
        "second_run_calls": second_calls,
        "second_run_skipped": second.skipped_strategies,
        "second_run_verified": second.verified,
        "second_response": second_response,
        "provenance_response": provenance.response,
        "audit_event_types": event_types,
        "audit_bundle": str(audit_path),
    }
    report_path = destination / "live_demo_report.json"
    report_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    result["report_path"] = str(report_path)
    return result


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else (
        PROJECT_ROOT / "artifacts" / "sprint14" / "live_demo"
    )
    try:
        print(json.dumps(run_demo(target), ensure_ascii=False, indent=2))
    except Exception as exc:
        print(json.dumps({"verified": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        raise SystemExit(1)
