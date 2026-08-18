from __future__ import annotations

import json
import struct
from dataclasses import dataclass

import pytest

from core.brain import (
    BrainBenchmark,
    AutoRoleSuggester,
    BrainRequest,
    BrainRole,
    ContextBudgetError,
    ContextComposer,
    Critic,
    CriticVerdict,
    LocalModelLifecycle,
    LocalModelManager,
    ModelCapabilityProfile,
    StructuredOutputError,
    StructuredOutputValidator,
)


def test_context_budget_preserves_identity_request_and_mission():
    composer = ContextComposer(role_budgets={BrainRole.FAST: 80})
    result = composer.compose(
        role=BrainRole.FAST,
        identity="ATLAS identity accuracy privacy reliability",
        user_request="critical current user request",
        mission="install and verify the selected application",
        current_mind_state="stage planning",
        verified_memory=("preferred concise answers",),
        recent_messages=("old message " * 40,),
        unverified_memory=("uncertain memory " * 40,),
    )

    assert "ATLAS identity" in result.text
    assert "critical current user request" in result.text
    assert "install and verify" in result.text
    assert result.estimated_tokens <= 80
    assert "unverified_memory" in result.omitted_sections


def test_context_budget_never_silently_drops_critical_state():
    composer = ContextComposer(role_budgets={BrainRole.FAST: 5})
    with pytest.raises(ContextBudgetError, match="critical context"):
        composer.compose(
            role=BrainRole.FAST,
            identity="identity contract is mandatory",
            user_request="current request is mandatory",
            mission="mission state is mandatory",
        )


@dataclass(frozen=True)
class PlanSchema:
    action: str
    confidence: float


def test_structured_output_uses_json_decoder_and_bounded_repair():
    calls = []

    def repair(raw: str, error: str) -> str:
        calls.append((raw, error))
        return json.dumps({"action": "inspect", "confidence": 0.8})

    validator = StructuredOutputValidator(max_repairs=2)
    result = validator.validate("not-json", PlanSchema, repair=repair)

    assert result == PlanSchema(action="inspect", confidence=0.8)
    assert len(calls) == 1

    with pytest.raises(StructuredOutputError):
        validator.validate("```json\n{}\n```", PlanSchema)


def test_structured_output_never_executes_tool_shaped_data():
    validator = StructuredOutputValidator()
    payload = validator.validate(
        '{"tool":"delete_file","arguments":{"path":"C:/sample"}}', dict,
    )
    assert payload == {"tool": "delete_file", "arguments": {"path": "C:/sample"}}


def test_critic_returns_only_structured_verdicts():
    critic = Critic()
    missing = critic.review(goal="change system", plan=("step",), evidence=(), risk="high")
    assert missing.verdict is CriticVerdict.INSUFFICIENT_EVIDENCE

    revised = critic.review(
        goal="change system", plan=(), evidence=("verified source",), risk="high",
    )
    assert revised.verdict is CriticVerdict.REVISE

    approved = critic.review(
        goal="read status", plan=("inspect",), evidence=("local observation",), risk="low",
    )
    assert approved.verdict is CriticVerdict.APPROVE


def test_local_gguf_discovery_reads_metadata_without_loading_or_copying(tmp_path):
    model = tmp_path / "Qwen3-1.7B-Q6_K.gguf"
    model.write_bytes(b"GGUF" + struct.pack("<IQQ", 3, 123, 0) + b"payload")
    manager = LocalModelManager((tmp_path,))

    found = manager.discover()

    assert len(found) == 1
    assert found[0].path == model
    assert found[0].size_bytes == model.stat().st_size
    assert found[0].architecture == "qwen"
    assert found[0].version == 3
    assert found[0].tensor_count == 123
    assert found[0].compatible is True
    assert found[0].loaded is False


def test_local_lifecycle_loads_only_selected_model_and_unloads(tmp_path):
    first = tmp_path / "first.gguf"
    second = tmp_path / "second.gguf"
    first.write_bytes(b"GGUF" + struct.pack("<IQQ", 3, 1, 0))
    second.write_bytes(b"GGUF" + struct.pack("<IQQ", 3, 1, 0))
    events = []
    lifecycle = LocalModelLifecycle(
        loader=lambda path: events.append(("load", path.name)) or {"path": path},
        warmer=lambda handle: events.append(("warm", handle["path"].name)),
        unloader=lambda handle: events.append(("unload", handle["path"].name)),
        max_loaded=1,
    )

    lifecycle.load(first)
    lifecycle.warm(first)
    lifecycle.load(second)

    assert lifecycle.loaded_paths() == (second,)
    assert events == [
        ("load", "first.gguf"), ("warm", "first.gguf"),
        ("unload", "first.gguf"), ("load", "second.gguf"),
    ]


def test_local_manager_applies_ram_and_background_resource_budget(tmp_path):
    model = tmp_path / "model.gguf"
    model.write_bytes(b"GGUF" + struct.pack("<IQQ", 3, 1, 0) + b"x" * 1000)
    info = LocalModelManager.inspect(model)

    assert LocalModelManager.can_load(info, available_ram_bytes=100_000_000, background=False)
    assert not LocalModelManager.can_load(
        info, available_ram_bytes=200_000_000, background=True, background_fraction=0.25,
    )


class _BenchProvider:
    name = "bench"
    external = False

    def stream(self, request, *, model=None):
        yield "ATLAS"
        yield " ready"


def test_benchmark_reports_measurements_not_subjective_score():
    report = BrainBenchmark().run_stream(
        _BenchProvider(), "model", BrainRequest("hello", BrainRole.CHAT),
        schema_check=lambda text: text.startswith("ATLAS"),
    )

    assert report.success is True
    assert report.ttft_ms >= 0
    assert report.total_latency_ms >= report.ttft_ms
    assert report.tokens_per_second > 0
    assert report.schema_compliance is True
    assert "intelligence" not in report.to_dict()


def test_auto_role_suggestion_uses_capability_and_measurement_with_override():
    profile = ModelCapabilityProfile(
        model="model", roles=frozenset({BrainRole.FAST, BrainRole.CHAT}), local=True,
    )
    report = BrainBenchmark().run_stream(
        _BenchProvider(), "model", BrainRequest("hello", BrainRole.FAST),
    )
    suggestions = AutoRoleSuggester().suggest(
        {"bench:model": profile}, (report,), overrides={BrainRole.CHAT: "user:choice"},
    )

    assert suggestions[BrainRole.FAST] == "bench:model"
    assert suggestions[BrainRole.CHAT] == "user:choice"
