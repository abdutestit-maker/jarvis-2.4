"""Trusted software resolution, installer proof and rollback tests."""

from __future__ import annotations

from pathlib import Path

from core.operator.software import (
    CheckpointManager,
    InstallerEngine,
    SoftwareCandidate,
    SoftwareResolver,
)


def _candidate(**overrides) -> SoftwareCandidate:
    data = {
        "name": "Fixture App",
        "package_id": "Fixture.App",
        "official_source": "winget://Fixture.App",
        "source_kind": "package_manager",
        "package_manager": "winget",
        "installer_type": "exe",
        "architecture": "x64",
        "version": "1.2.3",
        "publisher": "Fixture Org",
        "signature_expected": True,
        "trusted": True,
        "expected_executable": "fixture.exe",
    }
    data.update(overrides)
    return SoftwareCandidate(**data)


def test_software_resolver_ranks_trusted_sources_and_excludes_random_downloads() -> None:
    candidates = [
        _candidate(package_id="random", source_kind="third_party", package_manager="",
                   official_source="https://downloads.invalid/app.exe", trusted=False),
        _candidate(package_id="github", source_kind="official_github", package_manager="",
                   official_source="https://github.com/fixture/app/releases", trusted=True),
        _candidate(package_id="site", source_kind="official_site", package_manager="",
                   official_source="https://fixture.example/download", trusted=True),
        _candidate(package_id="winget", source_kind="package_manager", package_manager="winget",
                   official_source="winget://Fixture.App", trusted=True),
    ]

    ranked = SoftwareResolver().rank_candidates(candidates)

    assert [item.package_id for item in ranked] == ["winget", "site", "github"]
    assert all(item.trusted for item in ranked)


def test_winget_subprocess_forces_utf8_decoding() -> None:
    captured = {}

    def runner(_command, **kwargs):
        captured.update(kwargs)
        return {"exit_code": 0, "stdout": "Version: 1.2.3", "stderr": ""}

    result = SoftwareResolver(runner=runner)._run(["winget", "show"], timeout=1)

    assert result["exit_code"] == 0
    assert captured["encoding"] == "utf-8"
    assert captured["errors"] == "replace"


def test_winget_parser_understands_localized_russian_metadata() -> None:
    fields = SoftwareResolver._parse_fields(
        "Найдено Notepad++ [Notepad++.Notepad++]\n"
        "Версия: 8.9.7\nИздатель: Notepad++ Team\n"
        "  Тип установщика: nullsoft\n"
        "  URL-адрес установщика: https://github.com/example/app.x64.exe\n"
        "  SHA256 установщика: 0123456789abcdef\n"
    )

    assert fields["found"] == "Notepad++ [Notepad++.Notepad++]"
    assert fields["version"] == "8.9.7"
    assert fields["publisher"] == "Notepad++ Team"
    assert fields["installer type"] == "nullsoft"
    assert fields["installer url"].endswith("app.x64.exe")
    assert fields["installer sha256"] == "0123456789abcdef"


def test_winget_candidate_infers_architecture_and_preserves_hash() -> None:
    output = (
        "Found Fixture App [Fixture.App]\nVersion: 2.0\nPublisher: Fixture Org\n"
        "Installer type: exe\n"
        "Installer URL: https://github.com/fixture/app/releases/app.x64.exe\n"
        "Installer SHA256: abcdef0123456789\n"
    )

    def runner(_command, **_kwargs):
        return {"exit_code": 0, "stdout": output, "stderr": ""}

    candidate = SoftwareResolver(runner=runner).resolve_winget(
        "Fixture App", package_id="Fixture.App",
    )

    assert candidate is not None
    assert candidate.architecture == "x64"
    assert candidate.download_url.endswith("app.x64.exe")
    assert candidate.sha256 == "abcdef0123456789"


def test_installer_detection_supports_winget_msi_exe_and_portable_zip(tmp_path: Path) -> None:
    engine = InstallerEngine()

    assert engine.detect_type("winget://Fixture.App") == "winget"
    assert engine.detect_type(tmp_path / "setup.msi") == "msi"
    assert engine.detect_type(tmp_path / "setup.exe") == "exe"
    assert engine.detect_type(tmp_path / "portable.zip") == "zip"
    assert engine.detect_type(tmp_path / "payload.txt") == "unknown"
    assert engine.architecture_supported("x64", host="AMD64") is True
    assert engine.architecture_supported("arm64", host="AMD64") is False


def test_installer_exit_zero_is_not_verified_without_installed_artifacts() -> None:
    engine = InstallerEngine(
        installed_probe=lambda _candidate: {"installed": False, "version": ""},
        executable_probe=lambda _candidate: None,
        signature_probe=lambda _path: "NotChecked",
        launch_probe=lambda _path, _candidate: {"launched": False, "window": None},
    )

    evidence = engine.verify(_candidate(), installer_exit=0, launch=True)

    assert evidence.installer_exit == 0
    assert evidence.verified is False
    assert evidence.installed is False
    assert "installed_package" in evidence.failed_checks


def test_installer_verification_requires_version_executable_launch_and_window(tmp_path: Path) -> None:
    executable = tmp_path / "fixture.exe"
    executable.write_bytes(b"MZ fixture")
    engine = InstallerEngine(
        installed_probe=lambda _candidate: {"installed": True, "version": "1.2.3"},
        executable_probe=lambda _candidate: executable,
        signature_probe=lambda _path: "Valid",
        launch_probe=lambda _path, _candidate: {
            "launched": True, "pid": 42,
            "window": {"title": "Fixture App", "process_id": 42},
        },
    )

    evidence = engine.verify(_candidate(), installer_exit=0, launch=True)

    assert evidence.verified is True
    assert evidence.version == "1.2.3"
    assert evidence.executable == str(executable)
    assert evidence.window["title"] == "Fixture App"
    assert evidence.failed_checks == []


def test_file_checkpoint_restores_previous_bytes(tmp_path: Path) -> None:
    target = tmp_path / "config.ini"
    target.write_text("theme=light", encoding="utf-8")
    manager = CheckpointManager(tmp_path / "checkpoints")
    checkpoint = manager.backup_file(target)
    target.write_text("theme=dark", encoding="utf-8")

    result = manager.rollback(checkpoint)

    assert result["restored"] is True
    assert target.read_text(encoding="utf-8") == "theme=light"
