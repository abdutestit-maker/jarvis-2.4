"""Тест латентности локальной модели Qwen2.5-Coder-7B (GGUF).

Загружает модель через LocalQwenBackend, замеряет:
- warm_up() время
- chat() время на 2-3 тестовых запросах
Сравнивает с бюджетом settings.limits.local_latency_budget_sec (1.5 сек).
"""

from __future__ import annotations

import time
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from config import load_config  # noqa: E402
from core.llm.local_qwen import LocalQwenBackend  # noqa: E402
from core.utils.logger import setup_logging  # noqa: E402

setup_logging(level="INFO", console=True)


def test_latency() -> None:
    settings = load_config()
    print(f"Model path: {settings.local_model.gguf_path}")
    print(f"Quantization: {settings.local_model.quantization}")
    print(f"n_gpu_layers: {settings.local_model.n_gpu_layers}")
    print(f"n_ctx: {settings.local_model.n_ctx}")
    print(f"n_batch: {settings.local_model.n_batch}")
    print(f"Temperature: {settings.local_model.temperature}")
    print(f"Max tokens: {settings.local_model.max_tokens}")
    print("-" * 60)

    backend = LocalQwenBackend.from_settings(settings)

    # 1. Warmup
    print("\n=== WARMUP ===")
    start = time.perf_counter()
    backend.warm_up()
    warmup_time = time.perf_counter() - start
    print(f"Warmup time: {warmup_time:.2f}s")
    print(f"Available: {backend.is_available()}")

    if not backend.is_available():
        print("❌ Model not loaded!")
        return

    # 2. Test queries
    test_prompts = [
        "Привет! Как дела?",
        "Напиши функцию на Python для сортировки списка.",
        "Объясни что такое асинхронность простыми словами.",
    ]

    print("\n=== LATENCY TESTS ===")
    latencies = []
    for i, prompt in enumerate(test_prompts, 1):
        print(f"\nTest {i}: {prompt[:50]}...")
        messages = [{"role": "user", "content": prompt}]

        start = time.perf_counter()
        try:
            response = backend.chat(messages, system="Ты — Джарвис. Отвечай кратко.")
            elapsed = time.perf_counter() - start
            latencies.append(elapsed)
            print(f"  Time: {elapsed:.2f}s")
            print(f"  Response: {response[:100]}...")
        except Exception as e:
            print(f"  Error: {e}")
            latencies.append(float('inf'))

    # 3. Summary
    print("\n=== SUMMARY ===")
    valid_latencies = [l for l in latencies if l != float('inf')]
    if valid_latencies:
        avg_latency = sum(valid_latencies) / len(valid_latencies)
        max_latency = max(valid_latencies)
        min_latency = min(valid_latencies)
        budget = settings.limits.local_latency_budget_sec

        print(f"Budget: {budget}s")
        print(f"Min: {min_latency:.2f}s")
        print(f"Avg: {avg_latency:.2f}s")
        print(f"Max: {max_latency:.2f}s")

        if avg_latency <= budget:
            print(f"✅ WITHIN BUDGET (avg {avg_latency:.2f}s <= {budget}s)")
            print("   -> Can use as FAST tier (face)")
        else:
            print(f"❌ OVER BUDGET (avg {avg_latency:.2f}s > {budget}s)")
            print("   -> Should NOT use as FAST tier")
            print("   -> Better suited for CODER tier (offline code specialist)")

        # Also check individual responses
        over_budget_count = sum(1 for l in valid_latencies if l > budget)
        print(f"  Responses over budget: {over_budget_count}/{len(valid_latencies)}")
    else:
        print("No valid responses")


if __name__ == "__main__":
    test_latency()