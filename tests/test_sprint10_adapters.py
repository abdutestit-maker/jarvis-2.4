"""Config/registry-first adapters used after semantic application discovery."""

from __future__ import annotations

from pathlib import Path

from core.operator.adapters import XmlConfigAdapter, XmlSetting
from core.operator.software import CheckpointManager


def _config(path: Path) -> None:
    path.write_text(
        """<?xml version="1.0" encoding="UTF-8" ?>
<NotepadPlus><GUIConfigs>
  <GUIConfig name="RememberLastSession">yes</GUIConfig>
  <GUIConfig name="ScintillaPrimaryView" Wrap="no" zoom="0" />
</GUIConfigs></NotepadPlus>""",
        encoding="utf-8",
    )


def test_xml_adapter_observes_applies_and_rolls_back_minimal_fields(tmp_path: Path) -> None:
    path = tmp_path / "config.xml"
    _config(path)
    closed: list[bool] = []
    launched: list[bool] = []
    adapter = XmlConfigAdapter(
        config_path=path,
        settings={
            "remember_last_session": XmlSetting(
                ".//GUIConfig[@name='RememberLastSession']", kind="text", value_type="bool",
            ),
            "word_wrap": XmlSetting(
                ".//GUIConfig[@name='ScintillaPrimaryView']", kind="attribute",
                attribute="Wrap", value_type="bool",
            ),
        },
        checkpoints=CheckpointManager(tmp_path / "checkpoints"),
        close_application=lambda: closed.append(True),
        launch_application=lambda: launched.append(True),
    )

    assert adapter.observe() == {"remember_last_session": True, "word_wrap": False}
    checkpoint = adapter.checkpoint(["remember_last_session", "word_wrap"])
    assert closed == [True]
    assert adapter.apply_setting("remember_last_session", False).ok
    assert adapter.apply_setting("word_wrap", True).ok
    assert adapter.observe() == {"remember_last_session": False, "word_wrap": True}
    assert launched == [True]
    text = path.read_text(encoding="utf-8")
    assert 'zoom="0"' in text

    assert adapter.rollback(checkpoint)["restored"] is True
    assert adapter.observe() == {"remember_last_session": True, "word_wrap": False}


def test_xml_adapter_unknown_path_is_failed_action_result(tmp_path: Path) -> None:
    path = tmp_path / "config.xml"
    _config(path)
    adapter = XmlConfigAdapter(
        config_path=path,
        settings={},
        checkpoints=CheckpointManager(tmp_path / "checkpoints"),
    )

    result = adapter.apply_setting("not_known", True)

    assert result.ok is False
    assert "unknown setting" in (result.error or "")


def test_xml_adapter_materializes_first_run_config_by_clean_close(tmp_path: Path) -> None:
    path = tmp_path / "config.xml"

    def close_and_write() -> None:
        _config(path)

    adapter = XmlConfigAdapter(
        config_path=path,
        settings={
            "word_wrap": XmlSetting(
                ".//GUIConfig[@name='ScintillaPrimaryView']", kind="attribute",
                attribute="Wrap", value_type="bool",
            ),
        },
        checkpoints=CheckpointManager(tmp_path / "checkpoints"),
        close_application=close_and_write,
    )

    assert adapter.observe() == {"word_wrap": False}
