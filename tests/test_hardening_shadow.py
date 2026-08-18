from __future__ import annotations

from core.actions.registry import ToolRegistry
from core.shadow import SandboxTester, ShadowEngine
from core.shadow.sandbox import SecurityDecision


def test_shadow_security_decision_is_not_quality_score() -> None:
    source = "def execute_task(params):\n    return 'ok'\n"
    report = SandboxTester().test_source(source, {})
    assert report.quality_score >= 90
    assert report.security_decision is SecurityDecision.SAFE_TO_EVALUATE
    assert report.registration_allowed is True


def test_shadow_blocks_reflection_process_socket_and_environment_escape() -> None:
    for source in (
        "def execute_task(params):\n    return __import__('os').environ\n",
        "import subprocess\ndef execute_task(params):\n    return subprocess.Popen(['cmd'])\n",
        "import socket\ndef execute_task(params):\n    return socket.socket()\n",
        "def execute_task(params):\n    return open('outside.txt', 'w')\n",
    ):
        report = SandboxTester().test_source(source, {})
        assert report.security_decision is SecurityDecision.BLOCKED
        assert report.registration_allowed is False


def test_generated_shadow_tool_executes_only_through_isolated_evaluator(tmp_path) -> None:
    engine = ShadowEngine(data_dir=tmp_path, registry=ToolRegistry(), enabled=True)
    prepared = engine.prepare_tool(
        name="safe_echo", description="echo", source="def execute_task(params):\n    return 'ok'\n", test_params={}
    )
    assert prepared.report.security_decision is SecurityDecision.SAFE_TO_EVALUATE
    assert prepared.path is not None
    assert engine.registry.get("safe_echo") is not None
    assert engine.registry.get("safe_echo").run({}, None).output == "ok"
