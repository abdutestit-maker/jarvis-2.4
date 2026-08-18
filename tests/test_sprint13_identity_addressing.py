from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from core.cognitive import AddressFormStore, AddressRecognizer, AtlasIdentityCore
from core.personality import IdentityProfile, PersonalityEngine, PersonalityProfile


def test_atlas_is_canonical_runtime_identity_with_legacy_aliases():
    identity = AtlasIdentityCore()

    assert identity.canonical_name == "ATLAS"
    assert identity.canonical_name_ru == "АТЛАС"
    assert identity.internal_role == "digital intelligence"
    assert "JARVIS" in identity.compatibility_aliases
    assert identity.matches_legacy("Джарвис") is True


def test_personality_defaults_load_canonical_atlas_identity():
    engine = PersonalityEngine()

    assert engine.identity == IdentityProfile()
    assert engine.profile == PersonalityProfile()
    assert engine.identity.name == "ATLAS"
    assert engine.identity.role == "digital intelligence"
    assert "Identity: ATLAS" in engine.prompt_fragment(engine.style_for())


@pytest.mark.parametrize("utterance", [
    "Атлас, открой проект",
    "Атла, открой проект",
    "Атласик, ты тут?",
    "Атласшо, глянь сюда",
    "эй Атлас",
    "слушай Атлас",
    "Атлас?",
])
def test_contextual_fuzzy_address_variants_activate(utterance, tmp_path):
    result = AddressRecognizer(AddressFormStore(tmp_path)).recognize(utterance)

    assert result.addressed_to_atlas is True
    assert result.confidence >= 0.7
    assert result.candidate
    assert result.evidence


@pytest.mark.parametrize("utterance", [
    "открой атлас мира на нужной странице",
    "мне нравится атласный переплёт",
    "этот географический атлас дорог",
    "классный проект получился",
    "атласная ткань лежит на столе",
    "покажи статистику класса",
])
def test_similar_random_words_do_not_false_wake(utterance, tmp_path):
    result = AddressRecognizer(AddressFormStore(tmp_path)).recognize(utterance)

    assert result.addressed_to_atlas is False
    assert result.confidence < 0.7


def test_legacy_jarvis_address_still_routes_to_atlas(tmp_path):
    result = AddressRecognizer(AddressFormStore(tmp_path)).recognize("Джарвис, открой проект")

    assert result.addressed_to_atlas is True
    assert "legacy_alias" in result.evidence


def test_recent_confirmed_address_supports_continuing_command(tmp_path):
    recognizer = AddressRecognizer(AddressFormStore(tmp_path), conversation_window_seconds=90)
    now = datetime(2026, 8, 17, 12, 0, tzinfo=timezone.utc)
    first = recognizer.recognize("Атлас?", now=now)
    recognizer.confirm(first, accepted=True, now=now)

    continued = recognizer.recognize(
        "открой проект", conversational_context=True, now=now + timedelta(seconds=20),
    )

    assert continued.addressed_to_atlas is True
    assert "recent_address_state" in continued.evidence


def test_recurring_custom_form_is_learned_only_after_three_confirmations(tmp_path):
    store = AddressFormStore(tmp_path)
    recognizer = AddressRecognizer(store)

    for _ in range(2):
        match = recognizer.recognize("Атлос, посмотри сюда")
        recognizer.confirm(match, accepted=True)
    assert store.learned_forms() == ()

    match = recognizer.recognize("Атлос, посмотри сюда")
    recognizer.confirm(match, accepted=True)

    assert "атлос" in AddressFormStore(tmp_path).learned_forms()


def test_unconfirmed_accidental_word_is_never_persisted(tmp_path):
    store = AddressFormStore(tmp_path)
    recognizer = AddressRecognizer(store)
    accidental = recognizer.recognize("атласная ткань")

    recognizer.confirm(accidental, accepted=False)

    assert store.learned_forms() == ()
