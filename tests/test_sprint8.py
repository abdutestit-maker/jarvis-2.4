"""Sprint 8 — Shadow Engine: local pattern learning and guarded tool generation."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from core.actions.registry import ToolRegistry
from core.agent import Agent, AgentConfig
from config.settings import Settings
from core.shadow import (
    CheckResult,
    PatternWatcher,
    SandboxReport,
    SandboxTester,
    ShadowEngine,
    ToolGenerator,
    active_mode_message,
)


def test_pattern_watcher_detects_repeated_unfulfilled_request(tmp_path):
    watcher = PatternWatcher(tmp_path)
    for _ in range(3):
        watcher.record_command("конвертируй PDF в DOCX", outcome="unfulfilled")

    patterns = watcher.analyze()
    pattern = next(p for p in patterns if p.type == "unfulfilled_request")

    assert pattern.frequency == 3
    assert pattern.confidence > 0.8
    assert pattern.suggested_tool == "pdf_converter"
    assert (tmp_path / "patterns.json").is_file()


def test_tool_generator_wraps_valid_local_model_code(tmp_path):
    generator = ToolGenerator(
        tmp_path,
        generate=lambda prompt: "def execute_task(params):\n    return params.get('value', 'ok')\n",
    )
    source = generator.generate(
        name="echo_value",
        description="return a supplied value",
        confidence=0.91,
        params={"value": "text"},
        expected_output="the input value",
        examples="",
    )

    assert "def run(params: dict) -> dict:" in source
    assert "def execute_task(params):" in source
    assert SandboxTester().syntax_check(source).passed is True


def test_sandbox_rejects_dangerous_generated_code():
    source = "import os\ndef execute_task(params):\n    os.system('del C:\\\\Windows\\\\System32')\n"
    report = SandboxTester().test_source(source, {})

    assert report.safety.passed is False
    assert report.confidence == 0


def test_confidence_thresholds_auto_register_and_reject(tmp_path):
    engine = ShadowEngine(data_dir=tmp_path, registry=ToolRegistry(), enabled=True)
    safe = "def execute_task(params):\n    return 'ok'\n"

    registered = engine.prepare_tool(
        name="safe_echo", description="echo", source=safe, test_params={},
    )
    assert registered.status == "registered"
    assert registered.confidence >= 90
    assert engine.registry.get("safe_echo") is not None
    assert engine.registry.get("safe_echo").generated_by_shadow is True

    rejected = engine.prepare_tool(
        name="unsafe", description="unsafe",
        source="import subprocess\ndef execute_task(params):\n return 'x'\n",
        test_params={},
    )
    assert rejected.status == "rejected"
    assert rejected.confidence < 70


def test_exact_confidence_policy_registers_95_and_rejects_50(tmp_path):
    safe = "def execute_task(params):\n    return 'ok'\n"
    passed = CheckResult(True)
    failed = CheckResult(False, "functional failure")

    class FixedTester:
        def __init__(self, score): self.score = score
        def test_source(self, source, params):
            return SandboxReport(passed, passed, passed if self.score >= 90 else failed,
                                 passed, self.score)

    auto = ShadowEngine(data_dir=tmp_path / "auto", registry=ToolRegistry(), enabled=True,
                        tester=FixedTester(95))
    reject = ShadowEngine(data_dir=tmp_path / "reject", registry=ToolRegistry(), enabled=True,
                          tester=FixedTester(50))
    assert auto.prepare_tool(name="ninety_five", description="ok", source=safe,
                             test_params={}).status == "registered"
    assert reject.prepare_tool(name="fifty", description="bad", source=safe,
                               test_params={}).status == "rejected"


def test_shadow_can_prepare_a_safe_tool_on_demand(tmp_path):
    generator = ToolGenerator(
        tmp_path,
        generate=lambda prompt: "def execute_task(params):\n    return params['request']\n",
    )
    engine = ShadowEngine(data_dir=tmp_path, registry=ToolRegistry(), enabled=True, generator=generator)

    prepared = engine.prepare_on_demand("обработай новую локальную задачу")

    assert prepared is not None
    assert prepared.status == "registered"
    result = engine.registry.get(prepared.name).run({"request": "ok"}, None)
    assert result.ok is True
    assert result.output == "ok"


def test_active_mode_uses_learning_language_and_safety_warning():
    assert "сейчас разберусь" in active_mode_message("new task").lower()
    warning = active_mode_message("удали все файлы")
    assert "подтверждение" in warning.lower()
    assert "не умею" not in warning.lower()


def test_agent_unknown_path_says_it_will_investigate_not_cannot():
    agent = Agent(Settings(), config=AgentConfig(enable_skill_forge=False))
    outcome = agent._handle_unknown("сделай новый локальный формат", [], None, [], "no tool")

    assert "сейчас разберусь" in outcome.text.lower()
    assert "не умею" not in outcome.text.lower()


def test_time_pattern_requires_repeated_ritual(tmp_path):
    watcher = PatternWatcher(tmp_path)
    at_nine = datetime(2026, 8, 17, 9, 5, tzinfo=timezone.utc)
    for day in range(4):
        watcher.record_screen_context(
            active_window="Inbox - Mail", observed_at=at_nine + timedelta(days=day),
            permission=True,
        )

    patterns = watcher.analyze()
    assert any(p.type == "time_pattern" and p.frequency == 4 for p in patterns)


def test_manual_workaround_is_recorded_as_an_unfulfilled_need(tmp_path):
    watcher = PatternWatcher(tmp_path)
    for _ in range(3):
        watcher.record_manual_workaround("конвертируй PDF в DOCX")
    assert any(p.type == "unfulfilled_request" for p in watcher.analyze())
