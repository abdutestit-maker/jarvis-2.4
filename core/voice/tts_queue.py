"""Потоковая очередь озвучки (TTSQueue).

``TTSQueue`` — отдельный поток, который последовательно озвучивает тексты,
добавленные через ``add_to_queue``. Позволяет не блокировать основной цикл
и корректно останавливать/очищать очередь.
"""

from __future__ import annotations

import queue
import threading
import time
from typing import Optional

from core.utils.logger import get_logger

__all__ = ["TTSQueue"]

log = get_logger(__name__)


class TTSQueue:
    """Очередь TTS задач в отдельном потоке."""

    def __init__(self, tts_engine) -> None:
        """
        Args:
            tts_engine: экземпляр с методом ``speak(text: str, blocking: bool)``
                и ``stop_speaking()`` (например, ``PiperTTS``).
        """
        self._tts = tts_engine
        self._queue: "queue.Queue[Optional[str]]" = queue.Queue()
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._paused = False
        self._lock = threading.Lock()

    def start(self) -> None:
        """Запускает поток очереди."""
        with self._lock:
            if self._running:
                return
            self._running = True
            self._paused = False
            self._thread = threading.Thread(target=self._worker, daemon=True, name="TTSQueue")
            self._thread.start()
            log.info("TTSQueue запущен")

    def stop(self, wait: bool = True, timeout: float = 5.0) -> None:
        """Останавливает очередь.

        Args:
            wait: ждать завершения текущего воспроизведения.
            timeout: макс. время ожидания в секундах.
        """
        with self._lock:
            if not self._running:
                return
            self._running = False
            # Разбудим воркер
            try:
                self._queue.put_nowait(None)
            except Exception:
                pass

        if wait and self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)

        # Останавливаем текущее воспроизведение
        try:
            self._tts.stop_speaking()
        except Exception:
            pass

        log.info("TTSQueue остановлен")

    def add_to_queue(self, text: str) -> None:
        """Добавляет текст в очередь озвучки.

        Args:
            text: текст для озвучивания.
        """
        if not text or not text.strip():
            return
        if not self._running:
            log.warning("TTSQueue не запущен, текст не добавлен: %s", text[:50])
            return
        self._queue.put(text.strip())
        log.debug("TTSQueue: добавлен текст (%d символов)", len(text))

    def clear(self) -> int:
        """Очищает очередь. Возвращает число удалённых элементов."""
        count = 0
        while True:
            try:
                self._queue.get_nowait()
                count += 1
            except queue.Empty:
                break
        log.info("TTSQueue: очищено %d элементов", count)
        return count

    def interrupt(self) -> None:
        """Прерывает текущую озвучку и очищает очередь (П1 §1.2).

        Используется, когда пользователь перебивает J.A.R.V.I.S. голосом:
        всё, что ещё не произнесено, отменяется, а играющая фраза —
        останавливается. Thread-safe.
        """
        # 1) Очистить очередь ожидания.
        cleared = self.clear()
        # 2) Остановить текущее воспроизведение (если движок поддерживает).
        try:
            self._tts.stop_speaking()
        except Exception:
            pass
        if cleared:
            log.info("TTSQueue: прерывание, очищено %d ожидавших фраз", cleared)

    def wait_until_done(self, timeout: Optional[float] = None) -> bool:
        """Ждёт, пока очередь опустеет и текущее воспроизведение завершится.


        Args:
            timeout: макс. время ожидания (None = бесконечно).

        Returns:
            True — очередь пуста, False — таймаут.
        """
        start = time.time()
        while self._running:
            if self._queue.empty():
                # Очередь пуста, но может играть текущий файл
                # Даём чуть времени на завершение
                time.sleep(0.1)
                if self._queue.empty():
                    return True
            if timeout is not None and time.time() - start > timeout:
                return False
            time.sleep(0.05)
        return True

    def pause(self) -> None:
        """Приостанавливает обработку очереди (текущий текст доиграет)."""
        with self._lock:
            self._paused = True
        log.debug("TTSQueue: приостановлен")

    def resume(self) -> None:
        """Возобновляет обработку очереди."""
        with self._lock:
            self._paused = False
        log.debug("TTSQueue: возобновлён")

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def queue_size(self) -> int:
        return self._queue.qsize()

    # --------------------------------------------------------------------- #
    #  Внутренний воркер
    # --------------------------------------------------------------------- #

    def _worker(self) -> None:
        while self._running:
            try:
                text = self._queue.get(timeout=0.2)
            except queue.Empty:
                continue

            if text is None:  # сигнал остановки
                break

            with self._lock:
                if self._paused:
                    # Положили обратно и ждём
                    self._queue.put(text)
                    time.sleep(0.5)
                    continue

            try:
                # blocking=True — ждём завершения воспроизведения
                self._tts.speak(text, blocking=True)
            except Exception as exc:
                log.error("TTSQueue worker ошибка: %s", exc)

        log.debug("TTSQueue worker завершён")