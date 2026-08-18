from __future__ import annotations

from datetime import datetime, timedelta, timezone

from core.memory.relationship import (
    MemoryHierarchy,
    PreferenceLearner,
    RelationshipMemoryStore,
)
from core.memory.short_term import SessionManager


def test_relationship_memory_creation_persists_quality_fields(tmp_path):
    store = RelationshipMemoryStore(tmp_path)

    saved = store.remember(
        "Пользователь предпочитает короткие ответы",
        source="user_explicit", confidence=0.9, importance=0.8,
        category="preference", key="communication_style",
    )
    reloaded = RelationshipMemoryStore(tmp_path).all_memories()

    assert saved is not None
    assert reloaded[0].fact == saved.fact
    assert reloaded[0].source == "user_explicit"
    assert reloaded[0].confidence == 0.9
    assert reloaded[0].last_confirmed
    assert reloaded[0].importance == 0.8


def test_reconfirming_memory_increases_confidence_without_duplicates(tmp_path):
    store = RelationshipMemoryStore(tmp_path)
    first = store.remember(
        "Пользователь предпочитает короткие ответы", source="observed",
        confidence=0.55, importance=0.7, key="communication_style",
    )
    second = store.remember(
        "Пользователь предпочитает короткие ответы", source="user_explicit",
        confidence=0.9, importance=0.8, key="communication_style",
    )

    assert first is not None and second is not None
    assert second.confidence > first.confidence
    assert len(store.all_memories()) == 1


def test_expired_memories_are_pruned_and_not_retrieved(tmp_path):
    now = datetime(2026, 8, 17, tzinfo=timezone.utc)
    store = RelationshipMemoryStore(tmp_path)
    store.remember(
        "Временная настройка отчётов", source="observed", confidence=0.7,
        importance=0.2, ttl_days=1, now=now - timedelta(days=3), key="temporary_report_style",
    )

    assert store.retrieve("отчёты", now=now) == []
    assert store.prune(now=now) == 1
    assert store.all_memories(now=now) == []


def test_privacy_filter_does_not_store_secrets_or_sensitive_profile_data(tmp_path):
    store = RelationshipMemoryStore(tmp_path)

    secret = store.remember(
        "password=super-secret", source="user_explicit", confidence=1,
        importance=1, category="preference",
    )
    sensitive = store.remember(
        "Мой медицинский диагноз важен", source="user_explicit", confidence=1,
        importance=1, category="preference",
    )

    assert secret is None
    assert sensitive is None
    assert store.all_memories() == []


def test_privacy_filter_discards_direct_identifiers(tmp_path):
    store = RelationshipMemoryStore(tmp_path)

    email = store.remember(
        "Почта user@example.test", source="user_explicit", confidence=1,
        importance=1, category="preference",
    )
    phone = store.remember(
        "Телефон +7 777 123 45 67", source="user_explicit", confidence=1,
        importance=1, category="preference",
    )

    assert email is None
    assert phone is None


def test_retrieval_returns_only_relevant_bounded_memories(tmp_path):
    store = RelationshipMemoryStore(tmp_path)
    store.remember("Предпочитает короткие технические отчёты", source="observed",
                   confidence=0.8, importance=0.8, key="report_style")
    store.remember("Любит подробные учебные объяснения", source="observed",
                   confidence=0.8, importance=0.8, key="learning_style")
    store.remember("Обычно делегирует установку приложений", source="observed",
                   confidence=0.8, importance=0.7, key="delegation:installation")

    found = store.retrieve("сделай технический отчёт", limit=1)

    assert len(found) == 1
    assert "отчёт" in found[0].fact


def test_explicit_preference_learning_updates_user_profile(tmp_path):
    learner = PreferenceLearner(RelationshipMemoryStore(tmp_path))

    changes = learner.observe_user_message("Отвечай кратко, без длинных объяснений")
    profile = learner.profile()

    assert changes["communication_style"] == "short"
    assert profile.communication_style == "short"


def test_explicit_technical_level_is_a_style_preference_not_freeform_profile(tmp_path):
    learner = PreferenceLearner(RelationshipMemoryStore(tmp_path))

    changes = learner.observe_user_message("Объясняй как для разработчика, технически")

    assert changes["technical_level"] == "advanced"
    assert learner.profile().technical_level == "advanced"


def test_new_explicit_preference_supersedes_old_preference(tmp_path):
    learner = PreferenceLearner(RelationshipMemoryStore(tmp_path))
    learner.observe_user_message("Отвечай кратко")
    learner.observe_user_message("Теперь объясняй подробно и по шагам")

    assert learner.profile().communication_style == "detailed"
    assert len(learner.store.all_memories()) == 1


def test_acceptance_and_rejection_learning_adjust_delegation_confidence(tmp_path):
    learner = PreferenceLearner(RelationshipMemoryStore(tmp_path))

    initial = learner.delegation_confidence("file_cleanup")
    accepted = learner.record_suggestion_outcome("file_cleanup", "accepted")
    accepted_again = learner.record_suggestion_outcome("file_cleanup", "accepted")
    rejected = learner.record_suggestion_outcome("file_cleanup", "rejected")

    assert accepted > initial
    assert accepted_again > accepted
    assert rejected < accepted_again


def test_repeated_rejections_prevent_proactive_offer(tmp_path):
    learner = PreferenceLearner(RelationshipMemoryStore(tmp_path))
    learner.record_suggestion_outcome("email_summary", "rejected")
    learner.record_suggestion_outcome("email_summary", "rejected")

    assert learner.should_offer("email_summary") is False


def test_suggestion_topic_never_persists_embedded_secret(tmp_path):
    learner = PreferenceLearner(RelationshipMemoryStore(tmp_path))

    learner.record_suggestion_outcome("report password=top-secret", "accepted")
    raw = learner.path.read_text(encoding="utf-8")

    assert "top-secret" not in raw


def test_memory_hierarchy_keeps_layers_separate_and_context_bounded(tmp_path):
    relationship = RelationshipMemoryStore(tmp_path / "relationship")
    relationship.remember("Предпочитает краткий отчёт", source="observed",
                          confidence=0.9, importance=0.8, key="report_style")
    session = SessionManager(max_size=4)
    session.push("user", "Продолжи отчёт")
    session.push("assistant", "Проверяю данные")
    hierarchy = MemoryHierarchy(relationship, session=session)
    hierarchy.working.set("active_application", "Editor")

    context = hierarchy.retrieve("отчёт", max_chars=360)

    assert context.working["active_application"] == "Editor"
    assert len(context.session) == 2
    assert context.relationship[0].fact == "Предпочитает краткий отчёт"
    assert len(context.to_prompt(max_chars=360)) <= 360


def test_malformed_persisted_profile_falls_back_to_bounded_defaults(tmp_path):
    learner = PreferenceLearner(RelationshipMemoryStore(tmp_path))
    learner.path.write_text(
        '{"communication_style":"extreme","humor_preference":"loud",'
        '"delegation_affinity":{"report":"invalid"}}',
        encoding="utf-8",
    )

    profile = learner.profile()

    assert profile.communication_style == "adaptive"
    assert profile.humor_preference is None
    assert profile.delegation_affinity == {}
