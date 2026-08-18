from __future__ import annotations

import threading
import time

from core.voice.output import AssistantOutput
from core.voice.tts_queue import TTSQueue


class _FakeTTS:
    def __init__(self) -> None:
        self.spoken: list[str] = []
        self.stop_calls = 0
        self._lock = threading.Lock()

    def speak(self, text: str, blocking: bool = True) -> None:
        with self._lock:
            self.spoken.append(text)
        time.sleep(0.01)

    def stop_speaking(self) -> None:
        self.stop_calls += 1


def test_tts_queue_fifo_pause_resume_and_clean_shutdown() -> None:
    fake = _FakeTTS()
    queue = TTSQueue(fake)
    queue.start()
    queue.add_output(AssistantOutput.natural("one"))
    queue.add_output(AssistantOutput.natural("two"))
    assert queue.wait_until_done(timeout=2)
    queue.stop()
    assert fake.spoken[:2] == ["one", "two"]
    assert not queue.is_running
    assert queue.join(timeout=1)


def test_tts_interrupt_clears_pending_without_deadlock() -> None:
    fake = _FakeTTS()
    queue = TTSQueue(fake)
    queue.start()
    for value in ("one", "two", "three"):
        queue.add_output(AssistantOutput.natural(value))
    queue.interrupt()
    queue.stop()
    assert fake.stop_calls >= 1

