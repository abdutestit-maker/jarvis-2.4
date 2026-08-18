"""Safe real-files Sprint 13 continuity/composition/restart demonstration."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import Settings  # noqa: E402
from core.actions import DEFAULT_REGISTRY, ToolContext  # noqa: E402
from core.capabilities import CAPABILITIES  # noqa: E402
from core.capability_engine import CapabilityCatalog, CapabilityEngine, CapabilityPlanner  # noqa: E402
from core.cognitive import CognitiveOrchestrator  # noqa: E402
from core.task_runtime import TaskRuntime  # noqa: E402


ADDRESS_VARIANTS = (
    "Атлас, открой проект", "Атла, открой проект", "Атласик, ты тут?",
    "Атласшо, глянь сюда", "эй Атлас", "слушай Атлас", "Атлас?",
)
FALSE_WAKE_SAMPLES = (
    "В книге есть географический атлас мира",
    "Атласная ткань лежит на столе",
    "Катлас выглядит как случайное слово",
    "Обсудим план проекта завтра",
)


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def run_demo(root: Path | str, *, reset: bool = True) -> dict[str, Any]:
    output_root = Path(root).resolve()
    if reset and output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    workspace = output_root / "workspace"
    workspace.mkdir()
    for name, content in (
        ("alpha.txt", "alpha"), ("beta.md", "beta"), ("gamma.txt", "gamma"),
    ):
        (workspace / name).write_text(content, encoding="utf-8")

    settings = Settings()
    settings.paths.documents_dir = str(workspace)
    settings.paths.data_dir = str(output_root / "runtime_data")
    catalog = CapabilityCatalog(output_root / "capabilities")
    planner = CapabilityPlanner(catalog, DEFAULT_REGISTRY)
    engine = CapabilityEngine(
        catalog, DEFAULT_REGISTRY,
        context=ToolContext(settings=settings),
    )
    runtime = TaskRuntime(persistence_dir=output_root / "missions")
    cognitive_dir = output_root / "cognitive"
    coordinator = CognitiveOrchestrator(
        cognitive_dir, registry=DEFAULT_REGISTRY,
        capability_registry=CAPABILITIES, task_runtime=runtime,
        capability_planner=planner, capability_engine=engine,
    )

    address_results = []
    for utterance in ADDRESS_VARIANTS:
        result = coordinator.addressing.recognize(utterance)
        address_results.append({
            "text": utterance, "addressed": result.addressed_to_atlas,
            "confidence": result.confidence, "evidence": list(result.evidence),
        })
    false_wakes = []
    for utterance in FALSE_WAKE_SAMPLES:
        result = coordinator.addressing.recognize(utterance)
        false_wakes.append({
            "text": utterance, "addressed": result.addressed_to_atlas,
            "confidence": result.confidence,
        })
    _assert(all(item["addressed"] for item in address_results), "address variant missed")
    _assert(not any(item["addressed"] for item in false_wakes), "false wake detected")

    initial = coordinator.begin_interaction(
        "Атласшо, организуй локальные файлы по расширению", channel="voice",
    )
    _assert(initial.addressed and initial.action == "execute", "composable goal was not prepared")
    _assert(initial.plan.acquisition == "composed", "unknown requirement was not composed")

    suspended = coordinator.suspend_current()
    unrelated = coordinator.begin_interaction("Как настроение?", implicit_address=True)
    resumed = coordinator.begin_interaction("ладно, продолжай", implicit_address=True)
    _assert(suspended is not None, "goal was not suspended")
    _assert(unrelated.action == "conversation", "interruption was not handled as conversation")
    _assert(resumed.action == "continue" and resumed.goal == initial.goal,
            "suspended goal was not restored")

    executable = coordinator.begin_interaction(resumed.goal, implicit_address=True)
    _assert(executable.action == "execute", "restored goal was not replanned")
    final_text, report = coordinator.execute(executable)
    _assert(report.completed and report.verification.verified, "desired state not verified")
    _assert(final_text == "Готово. Проверил — работает.", "success wording mismatch")
    actual_files = sorted(
        str(path.relative_to(workspace)).replace("\\", "/")
        for path in workspace.rglob("*") if path.is_file()
        and ".capabilities" not in path.parts
    )
    expected_files = ["md/beta.md", "txt/alpha.txt", "txt/gamma.txt"]
    _assert(actual_files == expected_files, "observed filesystem differs from desired state")
    _assert(report.episode is not None, "verified capability episode missing")
    cognitive_episodes = coordinator.store.recent_verified(limit=5)
    _assert(bool(cognitive_episodes), "verified cognitive episode missing")

    second_plan = CapabilityPlanner(catalog, DEFAULT_REGISTRY).plan(
        "снова организуй файлы по расширению"
    )
    _assert(second_plan.acquisition == "learned", "second run did not reuse learned capability")

    # Simulate process reopen: no shared Python objects, only persisted state/catalog.
    reopened = CognitiveOrchestrator(
        cognitive_dir, registry=DEFAULT_REGISTRY,
        capability_registry=CAPABILITIES,
        capability_planner=CapabilityPlanner(
            CapabilityCatalog(output_root / "capabilities"), DEFAULT_REGISTRY,
        ),
    )
    followup = reopened.begin_interaction("Чем всё закончилось?", implicit_address=True)
    _assert(followup.action == "self_knowledge" and "результат проверен" in followup.response,
            "restart follow-up did not use reconstructed state")

    result = {
        "scenario": "address -> compose -> interrupt -> resume -> execute -> observe -> verify -> learn -> restart",
        "address_recognition": address_results,
        "false_wakes": false_wakes,
        "initial_action": initial.action,
        "acquisition": initial.plan.acquisition,
        "interruption_action": unrelated.action,
        "resume_action": resumed.action,
        "resumed_goal": resumed.goal,
        "execution_trace": list(report.action_trace),
        "observed": report.verification.observed,
        "verified": report.verification.verified,
        "actual_files": actual_files,
        "capability_episode": report.episode.episode_id,
        "cognitive_episode_count": len(cognitive_episodes),
        "second_run_acquisition": second_plan.acquisition,
        "restart_goal": reopened.state.current_goal,
        "restart_last_verified": bool(reopened.state.last_verified_result),
        "followup": followup.response,
        "final_response": final_text,
    }
    report_path = output_root / "live_demo_report.json"
    report_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    result["report_path"] = str(report_path)
    runtime.shutdown()
    return result


if __name__ == "__main__":
    destination = Path(sys.argv[1]) if len(sys.argv) > 1 else (
        PROJECT_ROOT / "artifacts" / "sprint13" / "live_demo"
    )
    try:
        demo = run_demo(destination)
        print(json.dumps(demo, ensure_ascii=False, indent=2))
    except Exception as exc:
        print(json.dumps({"verified": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        raise SystemExit(1)
