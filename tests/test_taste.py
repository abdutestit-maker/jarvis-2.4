"""Тесты профиля вкусов (TasteProfile) — Фаза памяти/вкусов.

Цель: музыкальный сценарий «бро, поставь музыку, скучна» — движок вынимает
настроение/жанр, копит профиль и ранжирует кандидатов по вкусу.
"""

import json
import sys
import tempfile

import pytest

sys.path.insert(0, ".")

from core.memory.taste import (  # noqa: E402
    DEFAULT_TASTE,
    TasteProfile,
    extract_taste_signals,
)


@pytest.fixture
def profile(tmp_path):
    return TasteProfile(tmp_path)


# --------------------------------------------------------------------------- #
#  Извлечение сигналов
# --------------------------------------------------------------------------- #


def test_extract_mood_from_scuchna():
    sig = extract_taste_signals("бро, поставь музыку, скучна")
    assert sig["media_request"] is True
    assert sig["mood"] == "calm"


def test_extract_genre():
    sig = extract_taste_signals("включи рок потяжелее")
    assert sig["genre"] == "rock"


def test_extract_artist_hint():
    sig = extract_taste_signals("что-нибудь в духе Queen")
    assert sig["artist_hint"] == "queen"


def test_no_signal_for_random_text():
    sig = extract_taste_signals("какая погода завтра")
    assert sig["media_request"] is False
    assert sig["mood"] == ""
    assert sig["genre"] == ""


# --------------------------------------------------------------------------- #
#  Обучение из реплик
# --------------------------------------------------------------------------- #


def test_observe_writes_mood(profile):
    profile.observe("скучно, поставь что-нибудь спокойное")
    data = profile.load()
    assert data["moods"].get("calm", 0.0) > 0


def test_observe_writes_genre(profile):
    profile.observe("поставь джаз")
    data = profile.load()
    assert data["genres"].get("jazz", 0.0) > 0


def test_observe_ignores_nonmedia(profile):
    changes = profile.observe("привет, как дела")
    data = profile.load()
    assert data["genres"] == {}
    assert data["moods"] == {}


# --------------------------------------------------------------------------- #
#  Обратная связь
# --------------------------------------------------------------------------- #


def test_accepted_boosts_genre(profile):
    profile.observe("поставь рок")
    c = profile.record_suggestion_outcome(genre="rock", outcome="accepted")
    assert c > 0.5
    data = profile.load()
    assert data["genres"].get("rock", 0.0) > 0.15


def test_rejected_decays(profile):
    profile.observe("поставь рок")
    data = profile.load()
    before = data["genres"].get("rock", 0.0)
    profile.record_suggestion_outcome(genre="rock", outcome="rejected")
    data = profile.load()
    assert data["genres"].get("rock", 0.0) < before


def test_signal_counts(profile):
    profile.record_suggestion_outcome(outcome="accepted")
    profile.record_suggestion_outcome(outcome="rejected")
    data = profile.load()
    assert data["signals"]["accepted"] == 1
    assert data["signals"]["rejected"] == 1
    assert data["signals"]["count"] == 2


# --------------------------------------------------------------------------- #
#  Ранжирование
# --------------------------------------------------------------------------- #


def test_score_ranks_by_taste(profile):
    profile.observe("поставь джаз")
    profile.record_suggestion_outcome(genre="jazz", outcome="accepted")
    cands = [
        {"id": "1", "title": "Jazz Standard", "genre": "jazz"},
        {"id": "2", "title": "Rock Anthem", "genre": "rock"},
    ]
    ranked = profile.score(cands)
    assert ranked[0]["id"] == "1"
    assert ranked[0]["_taste"] > ranked[1]["_taste"]


def test_negative_space_penalizes(profile):
    profile.load()
    profile._data["negative_space"] = ["opera"]
    profile._save()
    cands = [
        {"id": "op", "title": "Opera", "genre": "opera"},
        {"id": "rock", "title": "Rock", "genre": "rock"},
    ]
    ranked = profile.score(cands)
    assert ranked[0]["id"] == "rock"
    assert ranked[-1]["id"] == "op"


# --------------------------------------------------------------------------- #
#  Контекст и сериализация
# --------------------------------------------------------------------------- #


def test_context_smoke(profile):
    profile.observe("поставь джаз под фокус")
    ctx = profile.context()
    assert isinstance(ctx, str)
    assert len(ctx) <= 400


def test_reload_from_disk(tmp_path):
    p1 = TasteProfile(tmp_path)
    p1.observe("поставь рок")
    p2 = TasteProfile(tmp_path)
    data = p2.load()
    assert data["genres"].get("rock", 0.0) > 0


def test_default_shape():
    assert "genres" in DEFAULT_TASTE
    assert "moods" in DEFAULT_TASTE
    assert "signals" in DEFAULT_TASTE
