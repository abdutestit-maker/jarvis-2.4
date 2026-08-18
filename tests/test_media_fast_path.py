from __future__ import annotations

from unittest.mock import patch

from core.agent import Agent, AgentConfig
from core.actions.media import play_music


def test_bare_music_command_uses_media_fast_path(settings, fake_backend):
    agent = Agent(settings, config=AgentConfig(enable_skill_forge=False))
    with patch("core.actions.media._open_target", return_value=True):
        outcome = agent.execute("поставь музыку")

    assert outcome.mode == "fast_path"
    assert outcome.tool_used == "play_music"
    assert outcome.verified is True
    assert "музыкальный плеер" in outcome.text.lower()
    assert not fake_backend.calls


def test_bare_music_opens_default_player_without_network():
    with patch("core.actions.media._open_target", return_value=True) as opener:
        result = play_music()

    assert result.ok is True
    assert "музыкальный плеер" in result.output.lower()
    opener.assert_called_once()
