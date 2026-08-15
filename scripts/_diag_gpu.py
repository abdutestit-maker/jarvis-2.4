"""Focused GPU diagnostic (BEFORE/AFTER).
Captures the decisive Task-4 evidence:
- verbose llama.cpp backend init log (CUDA vs CPU, offloaded layers) -> stderr
- 'привет' generation turn time
- live nvidia-smi: util, VRAM, AND per-PID compute-apps (does OUR python PID hit the GPU?)
Run with:  python _diag_gpu.py > _diag_gpu.log 2>&1
"""
import sys, os, time, threading, subprocess
ROOT = r"E:\jarvis-project"
sys.path.insert(0, ROOT)
os.chdir(ROOT)

import llama_cpp
from config import load_config
from core.orchestrator import Orchestrator
from core.utils.logger import setup_logging

NV = r"C:/Windows/system32/nvidia-smi"
MY_PID = os.getpid()

samples = []
_stop = threading.Event()

def sampler():
    while not _stop.is_set():
        try:
            out = subprocess.run([NV, "--query-gpu=utilization.gpu,memory.used",
                                  "--format=csv,noheader,nounits"],
                                 capture_output=True, text=True, timeout=5)
            line = out.stdout.strip().splitlines()
            util, mem = (line[0].split(",") if line else ("?", "?"))[:2]
            apps = subprocess.run([NV, "--query-compute-apps=pid,used_memory",
                                   "--format=csv,noheader"],
                                  capture_output=True, text=True, timeout=5)
            hit = any(f"{MY_PID}" in l for l in apps.stdout.splitlines())
            samples.append((time.perf_counter(), util.strip(), mem.strip(),
                            "PYTHON_ON_GPU" if hit else "", apps.stdout.strip()))
        except Exception:
            pass
        time.sleep(0.2)

setup_logging(level="INFO", console=True)
print("=== ENV (BEFORE/AFTER) ===")
print("python:", sys.executable)
print("llama_cpp:", llama_cpp.__file__)
print("version:", getattr(llama_cpp, "__version__", "?"))
print("MY_PID:", MY_PID)
try:
    print("supports_gpu_offload:", llama_cpp.llama_supports_gpu_offload())
except Exception as e:
    print("supports_gpu_offload ERR:", e)

settings = load_config()
print("n_gpu_layers(fast):", settings.local_model.n_gpu_layers)
settings.local_model.verbose = True  # verbose llama.cpp backend init -> stderr
settings.voice.tts_enabled = False

print("\n=== ORCH START (verbose llama.cpp backend init below) ===", flush=True)
_stop.clear()
th = threading.Thread(target=sampler, daemon=True)
th.start()
try:
    orch = Orchestrator(settings)
    orch.start()

    t0 = time.perf_counter()
    st = orch.handle_input("привет")
    dt = time.perf_counter() - t0
    print(f"\n=== 'привет' TURN (Task4 timing) ===")
    print(f"turn={dt:.2f}s tier={st.get('tier')} intent={st.get('intent')} err={st.get('error')}")
finally:
    _stop.set()
    th.join(timeout=2)
    try:
        orch.shutdown()
    except Exception:
        pass

if samples:
    utils = [int(s[1]) for s in samples if s[1].isdigit()]
    python_hit = any(s[3] for s in samples)
    print(f"\n=== GPU SAMPLES (n={len(samples)}) ===")
    print(f"max_util={max(utils)}% min_util={min(utils)}%")
    print(f"OUR PYTHON PID ON GPU DURING RUN: {python_hit}")
    # show any sample where our python was on the GPU, or the busy window
    busy = [s for s in samples if s[1].isdigit() and int(s[1]) >= 15]
    print(f"busy-util samples (>=15%): {len(busy)}; example:", busy[0] if busy else None)
print("\n=== DIAG DONE ===")
