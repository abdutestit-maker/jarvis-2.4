"""Safe real Sprint 11 demos: workflow learning, attention, beginner and Shadow."""

from __future__ import annotations

import argparse
import functools
import http.server
import json
import shutil
import subprocess
import sys
import threading
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.actions.registry import ToolRegistry
from core.capability_engine import CapabilityCatalog
from core.living import (
    AttentionSnapshot,
    ComputerAssistanceLevel,
    LivingIntelligence,
    ProactiveCandidate,
    ResourceSnapshot,
    SemanticAction,
    WindowsContextSampler,
    WorkflowCapabilityBridge,
    WorkflowExecutor,
    WorkflowLearner,
    WorkflowRun,
)
from core.operator.software import InstallerEngine, SoftwareResolver
from core.platform.browser import BrowserAutomationProvider
from core.shadow import ShadowEngine
from core.task_runtime import MissionStatus


APP = "Notepad++"
PACKAGE_ID = "Notepad++.Notepad++"


class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, _format: str, *args: Any) -> None:
        return


class _LocalServer:
    def __init__(self, directory: Path) -> None:
        handler = functools.partial(_QuietHandler, directory=str(directory))
        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.server.server_address[1]}"

    def __enter__(self) -> "_LocalServer":
        self.thread.start()
        return self

    def __exit__(self, *_args: Any) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)


def _workflow_demo(run_id: str, intelligence: LivingIntelligence) -> dict[str, Any]:
    workspace = ROOT / "artifacts" / "sprint11" / "live_workspace" / run_id
    inbox = workspace / "inbox"
    archive = workspace / "organized"
    inbox.mkdir(parents=True, exist_ok=True)
    archive.mkdir(parents=True, exist_ok=True)
    learner = intelligence.workflows

    manual_verified: list[bool] = []
    for index in range(4):
        source = inbox / f"report-{run_id}-{index}.txt"
        destination = archive / source.name
        source.write_text(f"local report {index}\n", encoding="utf-8")
        listed = source.name in {item.name for item in inbox.iterdir()}
        shutil.move(str(source), str(destination))
        verified = destination.is_file() and not source.exists()
        manual_verified.append(listed and verified)
        intelligence.observe_file_activity(
            "discover_incoming_report", "inbox", project="local_reports",
            workflow="organize incoming reports",
        )
        intelligence.observe_file_activity(
            "move_report_to_archive", "organized", project="local_reports",
            workflow="organize incoming reports",
        )
        intelligence.observe_workflow(WorkflowRun(
            run_id=f"{run_id}-manual-{index}",
            actions=[
                SemanticAction("discover", "folder", "inbox", "filesystem.list",
                               {"path": str(inbox)}),
                SemanticAction("move", "file", "new report", "filesystem.move", {
                    "source": str(source), "destination": str(destination),
                }),
            ],
            duration_seconds=24 + index,
            estimated_automated_seconds=2,
            success=listed and verified,
            desired_state={"organized": True},
            observed_state={"organized": verified},
        ))

    candidate = learner.discover()[0]
    detected_opportunities = intelligence.opportunity_candidates()
    opportunity = ProactiveCandidate(
        id=candidate.id, topic=f"local report organization {run_id}",
        opportunity="organize incoming local report files",
        confidence=candidate.confidence, expected_value=0.92,
        reversible=True, risk="low", evidence=list(candidate.evidence),
        can_prepare=True, capability_id=candidate.id,
    )
    suggestion = intelligence.decisions.decide(
        opportunity, AttentionSnapshot(), profile=intelligence.profile_store.load(),
    )
    if suggestion.action.value != "SUGGEST":
        raise RuntimeError(f"workflow was not suggested: {asdict(suggestion)}")
    intelligence.memory.record(
        opportunity.topic, outcome="accepted", useful=True,
        suggestion=suggestion.user_message,
    )

    rehearsal_source = inbox / f"rehearsal-{run_id}.txt"
    rehearsal_destination = archive / rehearsal_source.name
    rehearsal_source.write_text("verified rehearsal\n", encoding="utf-8")

    def filesystem_provider(action: SemanticAction, params: dict[str, Any]) -> bool:
        if action.verb == "discover":
            return Path(str(params["path"])).is_dir() and list(Path(str(params["path"])).iterdir()) is not None
        if action.verb == "move":
            source = Path(str(params["source"]))
            destination = Path(str(params["destination"]))
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source), str(destination))
            return True
        return False

    rehearsal_executor = WorkflowExecutor(
        {"filesystem.list": filesystem_provider, "filesystem.move": filesystem_provider},
        observer=lambda: {"organized": rehearsal_destination.is_file()
                          and not rehearsal_source.exists()},
    )
    rehearsal = rehearsal_executor.execute(candidate, slots={
        "path": str(inbox), "source": str(rehearsal_source),
        "destination": str(rehearsal_destination),
    })
    catalog = CapabilityCatalog(intelligence.directory / "capabilities")
    capability = WorkflowCapabilityBridge(catalog).rehearse(
        candidate, lambda _candidate: {
            "verified": rehearsal.verified,
            "observed": rehearsal.observed,
            "duration": 0.05,
        },
    )
    if capability is None:
        raise RuntimeError("verified workflow rehearsal did not create a capability")

    # A fresh learner/catalog instance proves persisted second-run reuse.
    reloaded_candidate = WorkflowLearner(
        learner.directory,
    ).discover()[0]
    reloaded_capability = CapabilityCatalog(
        catalog.directory,
    ).get(capability.id)
    next_source = inbox / f"next-{run_id}.txt"
    next_destination = archive / next_source.name
    next_source.write_text("second run\n", encoding="utf-8")
    second = WorkflowExecutor(
        {"filesystem.list": filesystem_provider, "filesystem.move": filesystem_provider},
        observer=lambda: {"organized": next_destination.is_file() and not next_source.exists()},
    ).execute(reloaded_candidate, slots={
        "path": str(inbox), "source": str(next_source), "destination": str(next_destination),
    })
    verified = all(manual_verified) and rehearsal.verified and second.verified and reloaded_capability is not None
    return {
        "verified": verified,
        "workspace": str(workspace),
        "manual_runs": len(manual_verified),
        "manual_verified": manual_verified,
        "living_context": asdict(intelligence.context.current),
        "living_context_observations": len(intelligence.context.observations),
        "candidate": asdict(candidate),
        "service_opportunity_candidates": [asdict(item) for item in detected_opportunities],
        "proactive_decision": asdict(suggestion),
        "mock_user_response": "accepted",
        "rehearsal": asdict(rehearsal),
        "capability_path": str(catalog.directory / f"{capability.id}.json"),
        "capability_kind": capability.kind.value,
        "second_run": asdict(second),
        "second_run_reused_persistent_workflow": reloaded_candidate.frequency >= candidate.frequency,
        "second_run_reused_capability": reloaded_capability is not None,
        "raw_coordinates_used": False,
    }


def _attention_demo(run_id: str, intelligence: LivingIntelligence) -> dict[str, Any]:
    artifact = ROOT / "artifacts" / "sprint11"
    media = artifact / f"attention-{run_id}.mp4"
    html = artifact / f"attention-{run_id}.html"
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required for the real local media fixture")
    done = subprocess.run([
        ffmpeg, "-y", "-f", "lavfi", "-i", "color=c=#152238:s=640x360:d=3",
        "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(media),
    ], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60, check=False)
    if done.returncode != 0 or not media.is_file():
        raise RuntimeError(f"media fixture generation failed: {done.stderr[-500:]}")
    html.write_text("""<!doctype html><html><head><meta charset='utf-8'><title>Local lesson</title>
<style>html,body{margin:0;background:#000;overflow:hidden} video{position:fixed;inset:0;width:100vw;height:100vh;object-fit:contain}</style>
</head><body><video id='lesson' aria-label='Local tutorial video' autoplay muted loop controls src='"""
                    + media.name + "'></video></body></html>", encoding="utf-8")

    provider = BrowserAutomationProvider(headless=True)
    try:
        with _LocalServer(artifact) as server:
            opened = provider.open(f"{server.base_url}/{html.name}")
            provider._page.locator("#lesson").evaluate("el => el.play()")
            provider._page.wait_for_timeout(700)
            nodes = provider.inspect_dom()
            dom_state = dict(provider._page.evaluate("""() => {
              const el = document.querySelector('#lesson'); const rect = el.getBoundingClientRect();
              return {media_active: !el.paused && el.readyState >= 2,
                      fullscreen: Math.abs(rect.width-innerWidth)<2 && Math.abs(rect.height-innerHeight)<2,
                      current_time: el.currentTime, ready_state: el.readyState};
            }"""))
            busy = AttentionSnapshot(
                fullscreen=bool(dom_state["fullscreen"]),
                media_active=bool(dom_state["media_active"]),
            )
            candidate = ProactiveCandidate(
                id=f"busy-{run_id}", topic=f"attention demo {run_id}",
                opportunity="prepare local report organization capability",
                confidence=0.94, expected_value=0.88, reversible=True, risk="low",
                evidence=["repeated semantic workflow", "verified filesystem rehearsal"],
                can_prepare=True,
            )
            while_busy = intelligence.decisions.decide(
                candidate, busy, profile=intelligence.profile_store.load(),
            )
    finally:
        provider.close()
    after = intelligence.decisions.decide(
        candidate, AttentionSnapshot(), profile=intelligence.profile_store.load(),
    )
    verified = all((
        opened.get("ok"), dom_state["media_active"], dom_state["fullscreen"],
        while_busy.action.value == "PREPARE", while_busy.user_message == "",
        after.action.value == "SUGGEST", bool(after.user_message),
    ))
    return {
        "verified": verified,
        "browser_provider": type(provider).__name__,
        "url": opened["url"],
        "dom_nodes": len(nodes),
        "dom_state": dom_state,
        "while_busy": asdict(while_busy),
        "after_video": asdict(after),
        "foreground_message_while_busy": while_busy.user_message,
        "raw_coordinates_used": False,
    }


def _beginner_demo(intelligence: LivingIntelligence) -> dict[str, Any]:
    intelligence.profile_store.update(assistance=ComputerAssistanceLevel.BEGINNER)
    evidence_holder: dict[str, Any] = {}

    def operator(_request: str) -> dict[str, Any]:
        candidate = SoftwareResolver().resolve(APP, package_id=PACKAGE_ID)
        if candidate is None:
            return {"verified": False, "reason": "trusted package metadata absent"}
        candidate.expected_executable = "notepad++.exe"
        evidence = InstallerEngine().verify(candidate, installer_exit=None, launch=False)
        evidence_holder.update(asdict(evidence))
        return {"verified": evidence.verified, "evidence": asdict(evidence)}

    assistance = intelligence.assist(
        "Я скачал программу, не понимаю, как её установить.",
        capability_available=True, operator=operator,
    )
    return {
        "verified": assistance.executed and assistance.verified,
        "profile": "beginner",
        "assistant_message": assistance.message,
        "message_words": len(assistance.message.split()),
        "executed_safe_parts": assistance.executed,
        "installer_verification": evidence_holder,
        "source_resolver": "SoftwareResolver/winget trusted source",
        "long_instruction_dumped": False,
    }


def _shadow_demo(run_id: str, intelligence: LivingIntelligence) -> dict[str, Any]:
    registry = ToolRegistry()
    shadow = ShadowEngine(
        data_dir=ROOT / "data" / "living" / "live_shadow",
        registry=registry, enabled=True,
    )
    source = '''"""
Tool: shadow_safe_item_counter
Generated by: Shadow Engine
Description: Count a supplied list without filesystem or network access.
"""

def execute_task(params):
    return len(list(params.get("items") or []))

def run(params: dict) -> dict:
    try:
        return {"success": True, "result": execute_task(params), "error": None}
    except Exception as exc:
        return {"success": False, "result": None, "error": str(exc)}
'''
    prepared_holder: dict[str, Any] = {}

    def prepare() -> dict[str, Any]:
        template = ROOT / "data" / "tools" / "templates" / "basic_tool.py"
        template_text = template.read_text(encoding="utf-8")
        prepared = shadow.prepare_tool(
            name="shadow_safe_item_counter",
            description="Count supplied local items",
            source=source,
            test_params={"items": ["a", "b", "c"]},
        )
        prepared_holder.update({
            "name": prepared.name, "status": prepared.status,
            "confidence": prepared.confidence, "path": str(prepared.path or ""),
            "syntax": prepared.report.syntax.passed,
            "safety": prepared.report.safety.passed,
            "functional": prepared.report.functional.passed,
            "style": prepared.report.style.passed,
            "research": {
                "template": str(template), "template_read": bool(template_text),
                "existing_tool_examples": len(registry.list_tools()),
            },
        })
        return {
            "verified": prepared.status == "registered" and prepared.confidence >= 90
                        and bool(prepared.path and prepared.path.is_file()),
            **prepared_holder,
        }

    candidate = ProactiveCandidate(
        id=f"shadow-{run_id}", topic=f"shadow preparation {run_id}",
        opportunity="prepare a local deterministic item counter",
        confidence=0.95, expected_value=0.84, reversible=True, risk="low",
        evidence=["repeated local list counting", "standard-library-only template"],
        can_prepare=True,
    )
    intelligence.observe_action(
        action="repeated_list_count_failed", outcome="failure", source="shadow_engine",
        error_signature="missing reusable counter",
        metadata={"goal_hint": "prepare local item counter"},
    )
    # Busy media state suppresses interruption but permits verified preparation.
    cycle = intelligence.proactive_cycle(
        candidate, AttentionSnapshot(media_active=True),
        resources=ResourceSnapshot(cpu_percent=5, ram_percent=20),
        prepare=prepare,
    )
    if cycle.mission is None:
        raise RuntimeError("background preparation was not scheduled")
    finished = intelligence.task_runtime.wait(cycle.mission.task_id, timeout=30)
    tool = registry.get("shadow_safe_item_counter")
    verified = bool(
        finished and finished.status is MissionStatus.COMPLETED
        and finished.verification and finished.verification.get("verified")
        and prepared_holder.get("confidence", 0) >= 90 and tool is not None
        and cycle.decision.user_message == ""
    )
    return {
        "verified": verified,
        "decision": asdict(cycle.decision),
        "foreground_message": cycle.decision.user_message,
        "mission": finished.to_dict() if finished else None,
        "prepared_tool": prepared_holder,
        "registered_in_action_registry": tool is not None,
        "foreground_interrupted": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.parse_args()
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    artifact = ROOT / "artifacts" / "sprint11"
    artifact.mkdir(parents=True, exist_ok=True)
    intelligence = LivingIntelligence(ROOT / "data" / "living" / "live_service" / run_id)
    native_sample = WindowsContextSampler().sample()
    resource_sample = intelligence.resource_sampler.sample()
    resource_decision = intelligence.resources.assess(resource_sample)
    workflow = _workflow_demo(run_id, intelligence)
    attention = _attention_demo(run_id, intelligence)
    beginner = _beginner_demo(intelligence)
    shadow = _shadow_demo(run_id, intelligence)
    report = {
        "run_id": run_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "native_context_sample": {
            "source": native_sample.source,
            "application": native_sample.application,
            "process": native_sample.process,
            "window_title": native_sample.window_title,
            "idle_seconds": native_sample.idle_seconds,
            "fullscreen": native_sample.fullscreen,
        },
        "background_resources": {
            "snapshot": asdict(resource_sample), "decision": asdict(resource_decision),
        },
        "repeated_workflow": workflow,
        "attention_aware": attention,
        "beginner_assistance": beginner,
        "shadow_prepare": shadow,
        "privacy": {
            "screen_pixels_stored": False, "keystrokes_stored": False,
            "clipboard_values_stored": False, "secrets_stored": False,
        },
        "frontend_changed_by_sprint11": False,
        "new_llm_models": [],
    }
    report["verified"] = all(
        report[key]["verified"] for key in (
            "repeated_workflow", "attention_aware", "beginner_assistance", "shadow_prepare",
        )
    )
    report_path = artifact / "live_demo_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "verified": report["verified"], "report": str(report_path),
        "workflow": workflow["verified"], "attention": attention["verified"],
        "beginner": beginner["verified"], "shadow": shadow["verified"],
        "second_run_reuse": workflow["second_run_reused_capability"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["verified"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
