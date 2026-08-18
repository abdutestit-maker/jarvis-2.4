from __future__ import annotations

from datetime import datetime

from core.agent import Agent, AgentConfig
from core.living.models import ReturnContext
from core.living.service import LivingIntelligence
from core.memory.relationship import PreferenceLearner, RelationshipMemoryStore
from core.personality import PersonalityEngine
from core.voice.greeting import build_startup_greeting
from core.voice.tts_sanitizer import sanitize_for_tts


def _isolate(settings, tmp_path):
    settings.paths.data_dir = str(tmp_path / "data")
    settings.paths.graph_dir = str(tmp_path / "graph")
    settings.paths.profile_dir = str(tmp_path / "profile")


def test_agent_retrieves_relationship_style_before_conversation(settings, fake_backend, tmp_path):
    _isolate(settings, tmp_path)
    agent = Agent(settings, config=AgentConfig(enable_skill_forge=False))
    agent.preference_learner.observe_user_message("Отвечай кратко")

    prompt = agent._build_conversation_prompt("", "Расскажи, как идут дела", fake_backend)

    assert "Identity: JARVIS" in prompt
    assert "verbosity=short" in prompt
    assert "Пользователь предпочитает стиль ответов: short" in prompt


def test_agent_updates_and_persists_explicit_preference(settings, fake_backend, tmp_path):
    _isolate(settings, tmp_path)
    first = Agent(settings, config=AgentConfig(enable_skill_forge=False))
    first.execute("Пожалуйста, отвечай кратко")
    second = Agent(settings, config=AgentConfig(enable_skill_forge=False))

    assert second.preference_learner.profile().communication_style == "short"


def test_busy_living_context_reaches_communication_adapter(settings, fake_backend, tmp_path):
    _isolate(settings, tmp_path)
    agent = Agent(settings, config=AgentConfig(enable_skill_forge=False))
    agent.set_user_context({"busy": True, "typing_active": True})

    prompt = agent._build_conversation_prompt("", "Как дела?", fake_backend)

    assert "verbosity=short" in prompt
    assert "max_sentences=2" in prompt


def test_adaptive_detailed_style_is_not_overridden_by_legacy_fixed_brevity(settings, fake_backend, tmp_path):
    _isolate(settings, tmp_path)
    agent = Agent(settings, config=AgentConfig(enable_skill_forge=False))
    agent.preference_learner.observe_user_message("Теперь объясняй подробно и по шагам")

    prompt = agent._build_conversation_prompt("", "Объясни как работает роутинг", fake_backend)

    assert "verbosity=detailed" in prompt
    assert "Правила: 1-3 предложения" not in prompt


def test_sprint11_feedback_updates_both_proactive_and_relationship_memory(tmp_path):
    learner = PreferenceLearner(RelationshipMemoryStore(tmp_path / "relationship"))
    living = LivingIntelligence(tmp_path / "living", relationship_learner=learner)

    confidence = living.record_suggestion_feedback(
        "weekly_report", outcome="accepted", useful=True,
        suggestion="Автоматизировать еженедельный отчёт?",
    )

    assert confidence > 0.5
    assert living.memory.affinity("weekly_report") > 0
    assert learner.delegation_confidence("weekly_report") == confidence


def test_contextual_greeting_uses_unfinished_task_only_when_confident(settings):
    returned = ReturnContext(
        message="Вы остановились на проверке сборки.", confidence=0.91,
        evidence=("episode:build",), episode_id="build-1",
    )

    contextual = build_startup_greeting(
        settings, now=datetime(2026, 8, 17, 10, 0), return_context=returned,
    )
    ordinary = build_startup_greeting(
        settings, now=datetime(2026, 8, 17, 10, 0), return_context=None,
    )

    assert contextual == "Сэр, продолжим: проверку сборки?"
    assert contextual != ordinary


def test_contextual_greeting_understands_sprint11_return_context_shape(settings):
    returned = ReturnContext(
        message="Продолжим catalog assets? Остановились на export_image.",
        confidence=0.88, evidence=("unfinished episode e-1",), episode_id="e-1",
    )

    contextual = build_startup_greeting(settings, return_context=returned)

    assert contextual == "Сэр, продолжим catalog assets?"


def test_personality_output_remains_voice_safe_and_not_theatrical():
    engine = PersonalityEngine()
    original = "Отчёт сохранён в E:\\reports\\result.json. Проверка: 18 записей."

    adapted = engine.naturalize(original, verified=True, task_type="report")

    assert adapted == original
    assert sanitize_for_tts(adapted)
    assert adapted.casefold().count("сэр") == 0
