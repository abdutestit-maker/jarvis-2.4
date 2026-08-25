from __future__ import annotations

from core.actions import DEFAULT_REGISTRY
from core.agent import (
    Agent, AgentConfig, AgentOutcome, CapabilityDiscovery, GoalProgressDecision,
)
from core.actions.base import ActionResult
from core.capabilities import CAPABILITIES
from core.safety import assess_risk
from core.structured import ToolCallDecision
from core.verifier import VerificationResult


def test_every_implemented_computer_tool_is_registered():
    names = {tool.name for tool in DEFAULT_REGISTRY.list_tools()}
    assert {"computer_mouse", "computer_keyboard", "computer_screenshot"} <= names


def test_discovery_keeps_model_selected_live_capabilities():
    caps = CAPABILITIES.discover(
        "сделай действие через экран",
        ["computer_screenshot", "computer_mouse", "browser_automation"],
        top_k=8,
    )
    names = [cap.name for cap in caps]
    assert names[:3] == ["computer_screenshot", "computer_mouse", "browser_automation"]


def test_surface_summary_contains_full_capability_categories():
    surface = CAPABILITIES.surface_summary()
    assert "computer:" in surface
    assert "applications:" in surface
    assert "filesystem:" in surface
    assert "browser:" in surface
    assert "computer_keyboard:" in surface
    assert "browser_automation:" in surface


def test_discovery_uses_dialogue_history_for_follow_up(settings, monkeypatch):
    settings.deepseek_brain_mode = True
    agent = Agent(settings, config=AgentConfig(enable_skill_forge=False))
    agent._session.push("user", "поставь музыку")
    agent._session.push("assistant", "Какого исполнителя включить?")
    captured = {}
    agent._backend_for_routing = lambda routing: (object(), None)

    def stream(backend, messages, system, **kwargs):
        captured["messages"] = messages
        captured["system"] = system
        return '{"decision":"act","intent_clear":true,"capability_ids":["play_music"],"required_capability_ids":["play_music"],"clarification":""}'

    monkeypatch.setattr(agent, "_stream_consume", stream)
    discovery, error = agent._discover_capabilities(
        goal="Эминема", routing=None, memory_ctx="",
    )

    assert error == ""
    assert discovery == CapabilityDiscovery(
        "act", ("play_music",), True, "", ("play_music",),
    )
    assert any(item.get("content") == "поставь музыку" for item in captured["messages"])
    assert "Capability surface:" in captured["system"]


def test_ambiguous_turn_reaches_model_discovery_before_conversation(settings, monkeypatch):
    settings.deepseek_brain_mode = True
    agent = Agent(settings, config=AgentConfig(enable_skill_forge=False))
    seen = []

    def discover(**kwargs):
        seen.append(kwargs["goal"])
        return CapabilityDiscovery(
            "clarify", (), False, "Какой именно объект вы имеете в виду?", (),
        ), ""

    monkeypatch.setattr(agent, "_discover_capabilities", discover)
    outcome = agent.execute("что именно?")

    assert seen == ["что именно?"]
    assert outcome.tool_used is None
    assert outcome.text == "Какой именно объект вы имеете в виду?"
    assert outcome.verified is False
    assert outcome.mode == "clarification"


def test_inconsistent_discovery_is_retried_before_any_conversational_output(settings, monkeypatch):
    settings.deepseek_brain_mode = True
    agent = Agent(settings, config=AgentConfig(enable_skill_forge=False))
    agent._backend_for_routing = lambda routing: (object(), None)
    replies = iter([
        '{"decision":"clarify","intent_clear":false,"capability_ids":["search_files","open_app","read_file"],"required_capability_ids":[],"clarification":""}',
        '{"decision":"act","intent_clear":true,"capability_ids":["search_files","open_app","read_file"],"required_capability_ids":["search_files","open_app","read_file"],"clarification":""}',
    ])
    calls = []

    def stream(backend, messages, system, **kwargs):
        calls.append(messages)
        return next(replies)

    monkeypatch.setattr(agent, "_stream_consume", stream)
    discovery, error = agent._discover_capabilities(
        goal="найди файл, открой его и прочитай", routing=None, memory_ctx="",
    )

    assert error == ""
    assert discovery == CapabilityDiscovery(
        "act", ("search_files", "open_app", "read_file"), True, "",
        ("search_files", "open_app", "read_file"),
    )
    assert len(calls) == 2
    assert "rejected" in calls[1][-1]["content"]


def test_action_intent_rejects_discovery_answer(settings, monkeypatch):
    settings.deepseek_brain_mode = True
    agent = Agent(settings, config=AgentConfig(enable_skill_forge=False))
    agent._backend_for_routing = lambda routing: (object(), None)
    replies = iter([
        '{"decision":"answer","intent_clear":true,"capability_ids":[],"required_capability_ids":[],"clarification":""}',
        '{"decision":"act","intent_clear":true,"capability_ids":["search_files","read_file"],"required_capability_ids":["search_files","read_file"],"clarification":""}',
    ])
    monkeypatch.setattr(agent, "_stream_consume", lambda *args, **kwargs: next(replies))

    discovery, error = agent._discover_capabilities(
        goal="найди последний PDF и прочитай", routing=None, memory_ctx="",
        action_expected=True,
    )

    assert error == ""
    assert discovery.decision == "act"
    assert discovery.required_capability_ids == ("search_files", "read_file")


def test_capability_loop_uses_verified_observation_before_next_tool(settings, monkeypatch):
    settings.deepseek_brain_mode = True
    agent = Agent(settings, config=AgentConfig(enable_skill_forge=False, max_plan_steps=3))
    results = {
        "search_files": ActionResult("search_files", {"query": "report"}, True, output="report.txt"),
        "read_file": ActionResult("read_file", {"path": "report.txt"}, True, output="содержимое отчёта"),
    }
    observed_contexts = []

    def execute_verified(*, tool, args, risk, **kwargs):
        result = results[tool]
        verification = VerificationResult(True, "fixture", "verified fixture")
        return AgentOutcome(
            "", verified=True, verification=verification, tool_used=tool,
            risk=risk, mode="tool", action_result=result,
        )

    progress_decisions = iter([
        GoalProgressDecision(
            "continue",
            ToolCallDecision("read_file", {"path": "report.txt"}, "read result"),
            "file still needs reading",
        ),
        GoalProgressDecision("complete", reason="file content observed", evidence_steps=(1, 2)),
    ])

    def evaluate(*, observations, **kwargs):
        observed_contexts.append(__import__("json").dumps(observations, ensure_ascii=False))
        return next(progress_decisions), ""

    monkeypatch.setattr(agent, "_execute_verified", execute_verified)
    monkeypatch.setattr(agent, "_evaluate_goal_progress", evaluate)
    monkeypatch.setattr(agent, "_finalize_tool_response", lambda **kwargs: "Готово, сэр. Отчёт прочитан.")
    monkeypatch.setattr(agent, "_store_fact", lambda **kwargs: None)

    outcome = agent._execute_capability_loop(
        goal="найди отчёт и прочитай его",
        first_decision=ToolCallDecision("search_files", {"query": "report"}, "search"),
        mission=None,
        cancel=__import__("threading").Event(),
        trace=[],
        risk=assess_risk("найди отчёт"),
        caps=[CAPABILITIES.get("search_files"), CAPABILITIES.get("read_file")],
        routing=None,
        memory_ctx="",
    )

    assert outcome.verified is True
    assert outcome.text == "Готово, сэр. Отчёт прочитан."
    assert '"tool": "search_files"' in observed_contexts[0]
    assert '"tool": "read_file"' in observed_contexts[1]


def test_goal_evidence_rejects_unobserved_tool_claim(settings):
    agent = Agent(settings, config=AgentConfig(enable_skill_forge=False))
    observations = [{
        "step": 1,
        "tool": "search_files",
        "arguments": {"query": ".pdf"},
        "output": "report.pdf",
        "error": None,
        "verification": VerificationResult(True, "file_search", "found").to_dict(),
    }]

    steps, error = agent._validate_goal_evidence(
        [{"step": 1, "tool": "search_files"}],
        observations,
        reason="Файл прочитан через read_file.",
    )

    assert steps == ()
    assert "read_file" in error


def test_goal_evidence_requires_every_model_selected_capability(settings):
    agent = Agent(settings, config=AgentConfig(enable_skill_forge=False))
    observations = [{
        "step": 1,
        "tool": "search_files",
        "arguments": {"query": "report"},
        "output": "report.txt",
        "error": None,
        "verification": VerificationResult(True, "file_search", "found").to_dict(),
    }]

    steps, error = agent._validate_goal_evidence(
        [{"step": 1, "tool": "search_files"}],
        observations,
        required_capability_ids=("search_files", "open_app"),
    )

    assert steps == ()
    assert "open_app" in error


def test_goal_evidence_requires_targeted_open_after_file_search(settings):
    agent = Agent(settings, config=AgentConfig(enable_skill_forge=False))
    verified = VerificationResult(True, "fixture", "verified").to_dict()
    observations = [
        {"step": 1, "tool": "search_files", "arguments": {"query": "notes"},
         "output": "C:/Downloads/notes.txt", "verification": verified},
        {"step": 2, "tool": "open_app", "arguments": {"name": "блокнот"},
         "output": "started", "verification": verified},
    ]

    steps, error = agent._validate_goal_evidence(
        [{"step": 1, "tool": "search_files"}, {"step": 2, "tool": "open_app"}],
        observations,
        required_capability_ids=("search_files", "open_app"),
    )

    assert steps == ()
    assert "target_path" in error


def test_folder_goal_requires_explorer_location_verification(settings):
    agent = Agent(settings, config=AgentConfig(enable_skill_forge=False))
    verified = VerificationResult(True, "fixture", "verified").to_dict()
    observations = [
        {"step": 1, "tool": "search_files", "arguments": {"query": "notes"},
         "output": "C:/Downloads/notes.txt", "verification": verified},
        {"step": 2, "tool": "open_app",
         "arguments": {"name": "Блокнот", "target_path": "C:/Downloads/notes.txt"},
         "output": "started",
         "verification": VerificationResult(True, "process_running", "notepad").to_dict()},
    ]

    steps, error = agent._validate_goal_evidence(
        [{"step": 1, "tool": "search_files"}, {"step": 2, "tool": "open_app"}],
        observations,
        required_capability_ids=("search_files", "open_app"),
        goal="найди notes.txt и открой папку, где он лежит",
    )

    assert steps == ()
    assert "explorer_location" in error


def test_goal_progress_fallback_never_maps_text_to_complete(settings, monkeypatch):
    settings.deepseek_brain_mode = True
    agent = Agent(settings, config=AgentConfig(enable_skill_forge=False, max_plan_steps=2))
    result = ActionResult("search_files", {"query": "report"}, True, output="report.txt")
    verification = VerificationResult(True, "file_search", "found")

    monkeypatch.setattr(agent, "_execute_verified", lambda **kwargs: AgentOutcome(
        "", verified=True, verification=verification, tool_used="search_files",
        risk=kwargs["risk"], mode="tool", action_result=result,
    ))
    monkeypatch.setattr(
        agent, "_evaluate_goal_progress",
        lambda **kwargs: (None, "invalid evidence"),
    )
    monkeypatch.setattr(
        agent, "_decide_with_model",
        lambda *args, **kwargs: (
            ToolCallDecision(None, {}, "native text response", answer="Сейчас прочитаю."), ""
        ),
    )
    monkeypatch.setattr(agent, "_store_fact", lambda **kwargs: None)

    outcome = agent._execute_capability_loop(
        goal="найди и прочитай отчёт",
        first_decision=ToolCallDecision("search_files", {"query": "report"}, "search"),
        mission=None,
        cancel=__import__("threading").Event(),
        trace=[],
        risk=assess_risk("найди отчёт"),
        caps=[CAPABILITIES.get("search_files"), CAPABILITIES.get("read_file")],
        routing=None,
        memory_ctx="",
    )

    assert outcome.verified is False
    assert outcome.mode == "goal_unverified"


def test_capability_requirement_is_metadata_driven(settings):
    agent = Agent(settings, config=AgentConfig(enable_skill_forge=False))
    assert agent._missing_capability_requirement("play_music", {})
    assert not agent._missing_capability_requirement("play_music", {"query": "Eminem"})


def test_generic_computer_hands_are_recovery_when_specialized_tools_exist(settings):
    agent = Agent(settings, config=AgentConfig(enable_skill_forge=False))

    assert agent._required_capability_contract([
        "search_files", "open_app", "computer_keyboard", "read_file",
    ]) == ("search_files", "open_app", "read_file")
    assert agent._required_capability_contract([
        "computer_screenshot", "computer_mouse", "computer_keyboard",
    ]) == ("computer_screenshot", "computer_mouse", "computer_keyboard")
