"""Comprehensive before/after verification for J.A.R.V.I.S. tasks.

Runs under the ACTIVE python (the one that runs main.py). Captures:
- env: exe, llama_cpp path/version, supports_gpu_offload()
- verbose llama.cpp backend log during fast-model load (CUDA vs CPU, offloaded layers)
- live nvidia-smi GPU util + VRAM during load+generation
- "привет" turn time  (Task 4 timing)
- "напиши функцию..."  (Task 2: must stay fast, no deleted-gguf load)
- coder-provocation     (honest report of routing)
- ModelManager.list_models() == `модели` command (Task 2: coder not local)
"""
import sys, os, time, threading, subprocess, json
ROOT = r"E:\jarvis-project"
sys.path.insert(0, ROOT)
os.chdir(ROOT)

import llama_cpp
from config import load_config
from core.orchestrator import Orchestrator
from core.utils.model_manager import ModelManager
from core.utils.logger import setup_logging

NV = r"C:/Windows/system32/nvidia-smi"
GPU = []
_stop = threading.Event()

def sampler():
    while not _stop.is_set():
        try:
            out = subprocess.run(
                [NV, "--query-gpu=utilization.gpu,memory.used",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=5)
            line = out.stdout.strip().splitlines()
            if line:
                u, m = line[0].split(",")
                GPU.append((time.perf_counter(), int(u), int(m)))
        except Exception:
            pass
        time.sleep(0.3)

setup_logging(level="INFO", console=True)

print("=== ENV ===")
print("python:", sys.executable)
print("llama_cpp:", llama_cpp.__file__)
print("version:", getattr(llama_cpp, "__version__", "?"))
try:
    print("supports_gpu_offload:", llama_cpp.llama_supports_gpu_offload())
except Exception as e:
    print("supports_gpu_offload ERR:", e)

settings = load_config()
print("n_gpu_layers(fast):", settings.local_model.n_gpu_layers)
print("coder tier_providers:", settings.get_provider("coder"),
      "| model_tiers.coder:", settings.get_model_id("coder"))
print("local_coder_model.gguf_path:", repr(settings.local_coder_model.gguf_path))
settings.local_model.verbose = True   # capture CUDA/CPU backend log to stderr
settings.voice.tts_enabled = False

_stop.clear()
th = threading.Thread(target=sampler, daemon=True)
th.start()

try:
    print("\n=== ORCH START (warms fast Qwen3-4B; backend log below) ===")
    orch = Orchestrator(settings)
    orch.start()

    def run(label, prompt):
        t0 = time.perf_counter()
        st = orch.handle_input(prompt)
        dt = time.perf_counter() - t0
        print(f"\n--- {label} ---")
        print(f"turn={dt:.2f}s tier={st.get('tier')} intent={st.get('intent')} err={st.get('error')}")
        print(f"resp={(st.get('response') or '')[:140]!r}")
        return dt, st

    run("привет  (Task4: generation timing)", "привет")
    run("напиши функцию на Python для сортировки списка  (Task2: expect fast)",
        "напиши функцию на Python для сортировки списка")
    run("provoke coder escalation",
        "Спроектируй сложную распределённую микросервисную систему на Python: "
        "асинхронный API-шлюз, event-sourcing, CQRS, интеграционные тесты и CI/CD")

    print("\n=== MODELS (модели command) ===")
    mm = ModelManager(settings)
    print(json.dumps(mm.list_models(), ensure_ascii=False, indent=2))

finally:
    _stop.set()
    th.join(timeout=2)
    try:
        orch.shutdown()
    except Exception:
        pass

if GPU:
    utils = [s[1] for s in GPU]; mems = [s[2] for s in GPU]
    print(f"\n=== GPU SAMPLES (n={len(GPU)}) ===")
    print(f"max_util={max(utils)}% min_util={min(utils)}% "
          f"mem_used_min={min(mems)} mem_used_max={max(mems)} MiB")
    step = max(1, len(utils) // 30)
    print("util series:", utils[::step])
else:
    print("\n=== GPU SAMPLES: NONE (nvidia-smi unavailable) ===")
print("\n=== VERIFY DONE ===")
