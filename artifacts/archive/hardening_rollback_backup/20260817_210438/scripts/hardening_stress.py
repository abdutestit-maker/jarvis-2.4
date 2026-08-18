"""Bounded local stress probe for executor, TTS queue and persistence."""
from __future__ import annotations

import threading
import time
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.actions.base import ActionResult, Tool, ToolContext
from core.actions.executor import ToolExecutor
from core.actions.registry import ToolRegistry
from core.security.atomic import BoundedJSONStore
from core.voice.tts_queue import TTSQueue


class SleepTool(Tool):
    name = "hardening_stress_sleep"

    @property
    def description(self) -> str:
        return "short deterministic stress task"

    @property
    def input_schema(self) -> dict:
        return {"type": "object", "properties": {"delay": {"type": "number"}}}

    def run(self, params: dict, context: ToolContext):
        time.sleep(float(params.get("delay", 0.02)))
        return ActionResult(self.name, params, True, output={"ok": True})


def main() -> None:
    executor = ToolExecutor(max_parallel=4)
    context = ToolContext()
    registry = ToolRegistry()
    registry.register(SleepTool())
    results: list[object] = []
    lock = threading.Lock()

    def call() -> None:
        result = executor.execute(registry, "hardening_stress_sleep", {"delay": 0.02},
                                  context, max_retries=0, timeout_sec=1)
        with lock:
            results.append(result)

    threads = [threading.Thread(target=call) for _ in range(24)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    class FakeTTS:
        def speak(self, _text: str, blocking: bool = True) -> None:
            time.sleep(0.001)

        def stop_speaking(self) -> None:
            return None

    queue = TTSQueue(FakeTTS())
    queue.start()
    for index in range(40):
        queue.add_to_queue(f"stress-{index}")
    queue.wait_until_done(timeout=5)
    queue.stop(wait=True)

    store = BoundedJSONStore(Path("artifacts") / "hardening_stress_store.json", max_records=32)
    for index in range(100):
        store.append({"id": str(index), "value": index})
    print({
        "executor_results": len(results),
        "executor_failures": sum(not bool(getattr(item, "ok", False)) for item in results),
        "tts_stopped": queue.stopped.is_set(),
        "bounded_records": len(store.load()),
        "bounded_limit": 32,
    })


if __name__ == "__main__":
    main()
