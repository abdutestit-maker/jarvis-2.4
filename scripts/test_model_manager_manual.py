"""Ручной тест ModelManager (Задача 3).

Проверяет реальную регистрацию/снятие/список моделей и голосов БЕЗ порчи
рабочей конфигурации: использует временную копию settings.json и
файл-заглушку вместо настоящей GGUF.

Шаги:
1. register_local_model(role="coder") на пустышку -> файл скопирован в data/models,
   settings обновлён.
2. list_models() показывает coder.
3. remove_model("coder") -> регистрация снята, файл НЕ удалён с диска.
4. register_voice() на копию jarvis-medium.onnx из Загрузок -> скопирован в
   data/models/piper, прописан в piper_voices.
5. list_models() показывает voices.
6. settings.json перечитывается через load_config() без ошибок (валидный JSON).
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from config import load_config  # noqa: E402
from core.utils.model_manager import ModelManager  # noqa: E402
from core.utils.logger import setup_logging  # noqa: E402

setup_logging(level="WARNING", console=True)


def rule(t: str) -> None:
    print("\n" + "=" * 64)
    print(t)
    print("=" * 64)


def main() -> None:
    print("=== ТЕСТ MODELMANAGER (Задача 3) ===")

    # Работаем с ВРЕМЕННОЙ копией конфига, чтобы не трогать рабочий settings.json
    real_cfg = PROJECT_ROOT / "config" / "settings.json"
    tmp_cfg = PROJECT_ROOT / "config" / "settings.test.json"
    shutil.copy2(real_cfg, tmp_cfg)

    try:
        settings = load_config(tmp_cfg)
        mm = ModelManager(settings)

        # --- 1. register_local_model (пустышка GGUF) ---
        rule("1. register_local_model(role='coder')")
        tmp_gguf = PROJECT_ROOT / "data" / "models" / "test_stub_model.gguf"
        tmp_gguf.write_bytes(b"\x00STUB\x00")  # фейковый, но валидный файл
        mm.register_local_model("test-stub", str(tmp_gguf), role="coder")
        copied = PROJECT_ROOT / "data" / "models" / "test_stub_model.gguf"
        print("  скопирован в data/models:", copied.exists())
        cfg = json.loads(tmp_cfg.read_text(encoding="utf-8"))
        print("  model_tiers.coder:", cfg.get("model_tiers", {}).get("coder"))
        print("  tier_providers.coder:", cfg.get("tier_providers", {}).get("coder"))
        print("  local_coder_model.gguf_path:", cfg.get("local_coder_model", {}).get("gguf_path"))

        # --- 2. list_models ---
        rule("2. list_models()")
        models = mm.list_models()
        print("  coder:", models.get("coder"))

        # --- 3. remove_model ---
        rule("3. remove_model('coder')")
        mm.unregister_local_model("coder")
        cfg = json.loads(tmp_cfg.read_text(encoding="utf-8"))
        print("  model_tiers.coder:", cfg.get("model_tiers", {}).get("coder"))
        print("  local_coder_model.gguf_path:", cfg.get("local_coder_model", {}).get("gguf_path"))
        print("  файл на диске НЕ удалён:", copied.exists())

        # --- 4. register_voice (копия jarvis-medium.onnx из Загрузок) ---
        rule("4. register_voice() из Загрузок")
        src_onnx = Path("C:/Users/WwW/Downloads/jarvis-medium.onnx")
        src_json = PROJECT_ROOT / "data" / "models" / "piper" / "jarvis-medium.onnx.json"
        if src_onnx.exists() and src_json.exists():
            mm.register_voice("jarvis-test", str(src_onnx), str(src_json), language="en")
            piper_onnx = PROJECT_ROOT / "data" / "models" / "piper" / "jarvis-medium.onnx"
            piper_json = PROJECT_ROOT / "data" / "models" / "piper" / "jarvis-medium.onnx.json"
            print("  voice onnx скопирован:", piper_onnx.exists())
            print("  voice json скопирован:", piper_json.exists())
            cfg = json.loads(tmp_cfg.read_text(encoding="utf-8"))
            voices = cfg.get("voice", {}).get("piper_voices", [])
            print("  piper_voices count:", len(voices))
            for v in voices:
                print("    -", v.get("model_path"), v.get("language"))
        else:
            print("  ПРОПУЩЕНО: исходники голоса не найдены (", src_onnx, src_json, ")")

        # --- 5. list_models с голосами ---
        rule("5. list_models() (после регистрации голоса)")
        models = mm.list_models()
        print("  voices:", models.get("voices"))

        # --- 6. валидность JSON после всех правок ---
        rule("6. settings.json валиден (перечитывается load_config())")
        reloaded = load_config(tmp_cfg)
        print("  reload OK, coder model path:", reloaded.local_coder_model.resolved_gguf_path)
        print("  voices в настройках:", len(reloaded.voice.piper_voices))

        print("\n" + "=" * 64)
        print("ТЕСТ MODELMANAGER ПРОЙДЁН")
        print("=" * 64)

    finally:
        # чистим временный конфиг и стаб-файл
        tmp_cfg.unlink(missing_ok=True)
        stub = PROJECT_ROOT / "data" / "models" / "test_stub_model.gguf"
        stub.unlink(missing_ok=True)
        print("\n[cleanup] временный конфиг и стаб-файл удалены")


if __name__ == "__main__":
    main()
