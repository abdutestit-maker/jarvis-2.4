"""Адаптивный выбор локальной модели под железо пользователя.

Задача продукта: «Джарвис должен запуститься у каждого». Одна и та же
сборка ставится на слабый ноутбук без дискретной видеокарты и на десктоп
с RTX 4090. Нельзя зашивать один GGUF и один ``n_gpu_layers`` — на слабой
машине это либо не влезет в память, либо будет мучительно медленно, а на
мощной — недогрузит GPU.

Этот модуль — ЧИСТЫЙ, самодостаточный слой профилирования. Он:
  1. определяет доступную RAM и (если есть) VRAM NVIDIA;
  2. выбирает подходящий GGUF из ``data/models`` (или помечает, что модель
     нужно докачать);
  3. рекомендует безопасные параметры llama.cpp: ``n_gpu_layers``,
     ``n_ctx``, ``n_batch``;
  4. решает, включать ли speculative decoding (draft-модель Qwen3-1.7B
     для основной 4B) — оно окупается только когда draft реально ускоряет.

ВАЖНО: модуль НЕ импортирует ничего из горячего пути (только stdlib +
опционально ``psutil``). Он ничего не делает сам по себе — его вызывают
явно из ``config``/``factory`` при старте. Все зонды обёрнуты в try/except:
отсутствие psutil или nvidia-smi никогда не роняет приложение, а лишь
понижает точность оценки (safe degradation, как и во всём проекте).

Пример::

    from core.llm.hardware_profile import detect_hardware, recommend_profile

    hw = detect_hardware()
    profile = recommend_profile(hw, models_dir=settings.models_dir)
    print(profile.summary())
"""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

__all__ = [
    "HardwareInfo",
    "ModelProfile",
    "detect_hardware",
    "recommend_profile",
    "apply_profile",
]


# --------------------------------------------------------------------------- #
#  УНИВЕРСАЛЬНАЯ ЛЕСТНИЦА МОДЕЛЕЙ (от слабого ноутбука до рабочей станции).
#
#  Цель продукта: «запустится у каждого». Сборка одна, но при первом запуске
#  Джарвис определяет железо КОНКРЕТНОГО пользователя и выбирает самый сильный
#  вариант, который это железо потянет. Файла нет на диске -> download_required
#  (докачивает model_manager по манифесту — см. docs/CODEX_HANDOFF.md).
#
#  Пороги — консервативные оценки с запасом на KV-cache и оверхед ОС:
#    * min_vram_gb — сколько VRAM нужно, чтобы грузить ВСЕ слои на GPU;
#    * min_ram_gb  — сколько RAM нужно для комфортного запуска на CPU.
#  Значения намеренно с запасом: лучше выбрать чуть меньшую модель и быть
#  отзывчивым, чем упереться в своп/OOM.
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class _ModelSpec:
    key: str            # логический id для манифеста/скачивания
    filename: str       # имя GGUF-файла в data/models
    role: str           # 'core' | 'router/draft'
    min_vram_gb: float  # порог для полного GPU-оффлоада
    min_ram_gb: float   # порог для запуска на CPU
    n_ctx_gpu: int
    n_ctx_cpu: int


#: Лестница CORE-моделей от лёгкой к тяжёлой. Первый элемент — «пол»
#: (запустится почти везде), последний — «потолок» (для мощных машин).
#: Реальные ссылки на скачивание живут в манифесте (Codex), НЕ здесь.
_MODEL_LADDER: List[_ModelSpec] = [
    _ModelSpec("qwen3-0.6b", "Qwen3-0.6B-Q6_K.gguf", "core", 1.5, 3.0, 4096, 2048),
    _ModelSpec("qwen3-1.7b", "Qwen3-1.7B-Q6_K.gguf", "core", 3.0, 5.0, 4096, 2048),
    _ModelSpec("qwen3-4b", "qwen3-4b-instruct-q5_k_m.gguf", "core", 5.0, 9.0, 8192, 4096),
    _ModelSpec("qwen3-8b", "Qwen3-8B-Q5_K_M.gguf", "core", 9.0, 20.0, 8192, 4096),
    _ModelSpec("qwen3-14b", "Qwen3-14B-Q4_K_M.gguf", "core", 14.0, 32.0, 8192, 4096),
]

#: Черновая (draft) модель для speculative decoding: одно семейство с core,
#: заметно меньше. Включается только если хватает памяти держать core+draft.
_DRAFT_SPEC = _ModelSpec("qwen3-1.7b", "Qwen3-1.7B-Q6_K.gguf", "router/draft",
                         3.0, 5.0, 4096, 2048)

#: Абсолютный «пол» — если не удалось определить железо, берём самый лёгкий core.
_FLOOR_SPEC = _MODEL_LADDER[0]


@dataclass
class HardwareInfo:
    """Снимок железа. Все поля best-effort; None = определить не удалось."""

    total_ram_gb: Optional[float] = None
    available_ram_gb: Optional[float] = None
    cpu_count: Optional[int] = None
    has_cuda_gpu: bool = False
    gpu_name: Optional[str] = None
    vram_total_gb: Optional[float] = None
    vram_free_gb: Optional[float] = None
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
        return {
            "total_ram_gb": self.total_ram_gb,
            "available_ram_gb": self.available_ram_gb,
            "cpu_count": self.cpu_count,
            "has_cuda_gpu": self.has_cuda_gpu,
            "gpu_name": self.gpu_name,
            "vram_total_gb": self.vram_total_gb,
            "vram_free_gb": self.vram_free_gb,
            "notes": list(self.notes),
        }


@dataclass
class ModelProfile:
    """Рекомендация: какую модель и с какими параметрами грузить."""

    #: Класс железа: 'gpu_high' | 'gpu_mid' | 'gpu_low' | 'cpu_high' | 'cpu_low'.
    tier: str
    #: Имя файла основной модели (может отсутствовать на диске → download_required).
    core_model: str
    #: Рекомендованные параметры llama.cpp для основной модели.
    n_gpu_layers: int
    n_ctx: int
    n_batch: int
    #: Speculative decoding: draft-модель (или None, если не окупается).
    draft_model: Optional[str] = None
    #: Нужна ли докачка модели (файла нет в models_dir).
    download_required: bool = False
    reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
        return {
            "tier": self.tier,
            "core_model": self.core_model,
            "n_gpu_layers": self.n_gpu_layers,
            "n_ctx": self.n_ctx,
            "n_batch": self.n_batch,
            "draft_model": self.draft_model,
            "download_required": self.download_required,
            "reasons": list(self.reasons),
        }

    def summary(self) -> str:
        gpu = "все слои на GPU" if self.n_gpu_layers < 0 else (
            "CPU" if self.n_gpu_layers == 0 else f"{self.n_gpu_layers} слоёв на GPU"
        )
        draft = f", draft={self.draft_model}" if self.draft_model else ""
        dl = " (ТРЕБУЕТСЯ ДОКАЧКА)" if self.download_required else ""
        return (
            f"[{self.tier}] {self.core_model}{dl}: {gpu}, "
            f"n_ctx={self.n_ctx}, n_batch={self.n_batch}{draft}"
        )


# --------------------------------------------------------------------------- #
#  Детект железа
# --------------------------------------------------------------------------- #

def _detect_ram(info: HardwareInfo) -> None:
    try:
        import psutil  # type: ignore

        vm = psutil.virtual_memory()
        info.total_ram_gb = round(vm.total / (1024 ** 3), 2)
        info.available_ram_gb = round(vm.available / (1024 ** 3), 2)
        info.cpu_count = psutil.cpu_count(logical=True)
        return
    except Exception:  # psutil не установлен или упал — не критично
        info.notes.append("psutil недоступен, оценка RAM по os.*")

    # Fallback без psutil.
    try:
        info.cpu_count = os.cpu_count()
        if hasattr(os, "sysconf") and "SC_PAGE_SIZE" in os.sysconf_names and \
                "SC_PHYS_PAGES" in os.sysconf_names:
            total = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
            info.total_ram_gb = round(total / (1024 ** 3), 2)
    except Exception:
        info.notes.append("RAM определить не удалось")


def _detect_nvidia(info: HardwareInfo) -> None:
    """Определяет NVIDIA GPU/VRAM через nvidia-smi. Best-effort, без зависимостей."""
    smi = shutil.which("nvidia-smi")
    if not smi:
        info.notes.append("nvidia-smi не найден — считаем, что дискретной NVIDIA нет")
        return
    try:
        out = subprocess.run(
            [smi, "--query-gpu=name,memory.total,memory.free",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5, check=False,
        )
        line = (out.stdout or "").strip().splitlines()
        if not line:
            return
        # Берём первую (обычно самую мощную) карту.
        parts = [p.strip() for p in line[0].split(",")]
        if len(parts) >= 3:
            info.has_cuda_gpu = True
            info.gpu_name = parts[0]
            info.vram_total_gb = round(float(parts[1]) / 1024, 2)
            info.vram_free_gb = round(float(parts[2]) / 1024, 2)
    except Exception as exc:  # noqa: BLE001 — любая ошибка зонда не критична
        info.notes.append(f"nvidia-smi зонд не удался: {type(exc).__name__}")


def detect_hardware() -> HardwareInfo:
    """Собирает best-effort снимок железа. Никогда не бросает исключений."""
    info = HardwareInfo()
    _detect_ram(info)
    _detect_nvidia(info)
    return info


# --------------------------------------------------------------------------- #
#  Рекомендация профиля
# --------------------------------------------------------------------------- #

def _model_present(models_dir: Optional[Path], name: str) -> bool:
    if models_dir is None:
        return False
    try:
        return (Path(models_dir) / name).is_file()
    except Exception:
        return False


def _pick_from_ladder(vram: float, ram: float) -> tuple[_ModelSpec, bool, str]:
    """Возвращает (лучшая посильная модель, на_gpu, причина).

    Идём по лестнице СВЕРХУ ВНИЗ и берём самую сильную модель, которую
    железо реально тянет: сначала пытаемся уместить целиком на GPU (по VRAM),
    иначе — на CPU (по RAM). Так один и тот же код на RTX 4090 выберет 14B,
    а на офисном ноутбуке без видеокарты — 1.7B или 0.6B. Всегда что-то
    вернём: в худшем случае «пол» лестницы.
    """
    if vram > 0:
        for spec in reversed(_MODEL_LADDER):
            if vram >= spec.min_vram_gb:
                return spec, True, (
                    f"VRAM {vram} ГБ ≥ {spec.min_vram_gb} — {spec.key} целиком на GPU"
                )
    if ram > 0:
        for spec in reversed(_MODEL_LADDER):
            if ram >= spec.min_ram_gb:
                return spec, False, (
                    f"RAM {ram} ГБ ≥ {spec.min_ram_gb} — {spec.key} на CPU"
                )
    return _FLOOR_SPEC, False, (
        "железо определить не удалось — берём самый лёгкий core (пол лестницы)"
    )


def recommend_profile(hw: Optional[HardwareInfo] = None,
                      models_dir: Optional[Path] = None) -> ModelProfile:
    """Выбирает модель и параметры llama.cpp под железо КОНКРЕТНОГО юзера.

    Универсальность: одна сборка обслуживает и слабый ноутбук, и мощный ПК.
    При старте у пользователя определяется его железо и выбирается самый
    сильный вариант из :data:`_MODEL_LADDER`, который эта машина тянет.

    Философия (см. docs/JARVIS_REBUILD_PLAN.md):
      * на данном железе — ОДИН сильный core, а не связка двух моделей;
      * маленькие модели (0.6B/1.7B) — это «пол» для слабых машин ИЛИ роль
        router/draft на сильных, НЕ «умный» тир эскалации;
      * на GPU грузим все слои; на CPU держим меньший контекст ради памяти;
      * speculative decoding включаем только при запасе VRAM (нужно держать
        core + draft одновременно), иначе профита нет.

    Args:
        hw: снимок железа. Если None — определяется автоматически.
        models_dir: каталог с GGUF — чтобы проверить наличие файла и выставить
            ``download_required`` (докачка по манифесту).

    Returns:
        :class:`ModelProfile` — всегда валидный, даже на «голой» машине.
    """
    hw = hw or detect_hardware()
    vram = hw.vram_total_gb or 0.0
    ram = hw.total_ram_gb or 0.0

    spec, on_gpu, reason = _pick_from_ladder(vram, ram)
    reasons: List[str] = [reason]

    if on_gpu:
        n_gpu_layers = -1
        n_ctx = spec.n_ctx_gpu
        n_batch = 1024 if vram >= 12 else 768 if vram >= 8 else 512
        tier = "gpu_high" if vram >= 12 else "gpu_mid" if vram >= 8 else "gpu_low"
        # Speculative decoding окупается, когда после core остаётся запас VRAM
        # на draft (~2 ГБ). Иначе draft вытеснит core и всё станет медленнее.
        draft = None
        headroom = vram - spec.min_vram_gb
        if headroom >= _DRAFT_SPEC.min_vram_gb and spec.key not in {_DRAFT_SPEC.key, "qwen3-0.6b"}:
            draft = _DRAFT_SPEC.filename
            reasons.append(
                f"Запас VRAM {round(headroom, 1)} ГБ — включаем speculative draft {_DRAFT_SPEC.key}"
            )
    else:
        n_gpu_layers = 0
        n_ctx = spec.n_ctx_cpu
        n_batch = 512 if ram >= 16 else 256
        tier = "cpu_high" if ram >= 16 else "cpu_low"
        draft = None  # на CPU speculative decoding обычно не окупается

    profile = ModelProfile(
        tier=tier, core_model=spec.filename, n_gpu_layers=n_gpu_layers,
        n_ctx=n_ctx, n_batch=n_batch, draft_model=draft,
    )
    profile.download_required = not _model_present(models_dir, spec.filename)
    if profile.download_required:
        reasons.append(f"файла {spec.filename} нет локально — требуется докачка по манифесту")
    profile.reasons = reasons
    return profile


def apply_profile(settings: object, *, logger: object | None = None) -> ModelProfile:
    """Apply a safe, present-on-disk hardware profile to runtime settings.

    The function intentionally does not download anything and does not write
    ``settings.json``.  A missing recommended GGUF leaves the configured file
    untouched so a first launch cannot turn into a guaranteed missing-model
    error.  The future model manager can download the profile and call this
    function again on the next start.
    """
    models_dir = Path(getattr(settings, "models_dir", Path("data/models")))
    profile = recommend_profile(
        models_dir=models_dir,
    )
    local = getattr(settings, "local_model", None)
    if local is None or not bool(getattr(local, "auto_profile", True)):
        return profile

    selected = models_dir / profile.core_model
    if not selected.is_file():
        profile.reasons.append(
            f"профиль {profile.core_model} ещё не скачан — текущий GGUF сохранён"
        )
        return profile

    # Avoid requesting CUDA layers from a CPU-only llama-cpp build.  The probe
    # is optional and never prevents the application from starting.
    gpu_layers = profile.n_gpu_layers
    if gpu_layers != 0:
        try:
            import llama_cpp  # type: ignore
            probe = getattr(llama_cpp, "llama_supports_gpu_offload", None)
            if not callable(probe) or not bool(probe()):
                gpu_layers = 0
                profile.reasons.append("llama.cpp GPU-offload недоступен — используем CPU")
        except Exception:
            gpu_layers = 0
            profile.reasons.append("llama.cpp не подтвердил GPU-offload — используем CPU")

    # Keep config paths portable and stable across Windows/Linux releases.
    local.gguf_path = f"data/models/{profile.core_model}"
    local.n_gpu_layers = gpu_layers
    local.n_ctx = profile.n_ctx
    local.n_batch = profile.n_batch
    draft_path = models_dir / profile.draft_model if profile.draft_model else None
    if draft_path is not None and draft_path.is_file() and gpu_layers != 0:
        local.draft_model_path = f"data/models/{profile.draft_model}"
        local.speculative_decoding = True
    else:
        local.draft_model_path = ""
        local.speculative_decoding = False
    profile.n_gpu_layers = gpu_layers
    if logger is not None:
        try:
            logger.info("Hardware profile applied: %s", profile.summary())
        except Exception:
            pass
    return profile


if __name__ == "__main__":  # ручная проверка: python -m core.llm.hardware_profile
    _hw = detect_hardware()
    print("HARDWARE:", _hw.to_dict())
    _models = Path(__file__).resolve().parents[2] / "data" / "models"
    _profile = recommend_profile(_hw, models_dir=_models)
    print("PROFILE :", _profile.summary())
    for _r in _profile.reasons:
        print("  -", _r)
