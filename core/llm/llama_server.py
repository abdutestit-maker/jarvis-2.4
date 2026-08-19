"""Local llama.cpp server backend with Vulkan/CUDA sidecar support.

The project keeps ``LocalQwenBackend`` as the compatibility fallback.  When a
portable ``llama-server`` is installed, this adapter runs the same GGUF behind
the loopback OpenAI-compatible endpoint so GPU offload is real instead of a
wish encoded in ``n_gpu_layers``.  No cloud endpoint is involved.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Sequence

from core.llm.backend import (
    BackendUnavailable,
    ToolsNotSupportedError,
    prepend_system,
    strip_reasoning_blocks,
)
from core.llm.local_qwen import LocalQwenBackend
from core.llm.tool_calls import ToolCallResponse, parse_tool_calls

__all__ = ["find_llama_server", "LlamaServerBackend"]


def _visible_stream_piece(piece: str, *, state: dict[str, bool]) -> str:
    """Remove reasoning tags without stripping meaningful token whitespace."""
    text = str(piece or "")
    visible: list[str] = []
    while text:
        lowered = text.casefold()
        if state.get("in_think", False):
            end = lowered.find("</think>")
            if end < 0:
                return "".join(visible)
            text = text[end + len("</think>"):]
            state["in_think"] = False
            continue
        start = lowered.find("<think>")
        if start < 0:
            visible.append(text)
            break
        visible.append(text[:start])
        text = text[start + len("<think>"):]
        state["in_think"] = True
    return "".join(visible)


def _existing_file(value: str | Path | None) -> Optional[Path]:
    if not value:
        return None
    try:
        candidate = Path(value).expanduser()
        return candidate if candidate.is_file() else None
    except (OSError, TypeError, ValueError):
        return None


def find_llama_server(configured: str | Path | None = None) -> Optional[Path]:
    """Find the official llama.cpp executable without touching the network."""

    candidates: list[Path] = []
    explicit = _existing_file(configured)
    if explicit:
        candidates.append(explicit)
    for env_name in ("JARVIS_LLAMA_SERVER", "LLAMA_SERVER"):
        env_path = _existing_file(os.environ.get(env_name))
        if env_path:
            candidates.append(env_path)
    for name in ("llama-server.exe", "llama-server"):
        found = shutil.which(name)
        if found:
            candidates.append(Path(found))
    root = Path(__file__).resolve().parents[2]
    candidates.extend([
        root / "runtime" / "llama-server.exe",
        root / "runtime" / "llama-server",
        root / "data" / "runtime" / "llama-server.exe",
        root / "data" / "runtime" / "llama-server",
    ])
    local_appdata = os.environ.get("LOCALAPPDATA", "")
    if local_appdata:
        package_root = Path(local_appdata) / "Microsoft" / "WinGet" / "Packages"
        try:
            for package in package_root.glob("ggml.llamacpp*"):
                candidates.extend(package.rglob("llama-server.exe"))
        except OSError:
            pass
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate).casefold()
        if key in seen:
            continue
        seen.add(key)
        if candidate.is_file():
            return candidate
    return None


class LlamaServerBackend(LocalQwenBackend):
    """``LLMBackend`` compatibility facade over a loopback llama-server."""

    supports_tools = True

    def __init__(
        self,
        gguf_path: Path | str,
        *,
        model_id: str = "qwen-4b-local",
        server_binary: Path | str | None = None,
        host: str = "127.0.0.1",
        port: int = 8782,
        n_ctx: int = 4096,
        n_batch: int = 768,
        n_threads: Optional[int] = None,
        temperature: float = 0.25,
        max_tokens: int = 384,
        gpu_layers: str = "all",
        startup_timeout_sec: float = 30.0,
        request_timeout_sec: float = 45.0,
        verbose: bool = False,
    ) -> None:
        # The superclass supplies the stable public fields and keeps this
        # class an isinstance(LocalQwenBackend) for existing integrations.
        super().__init__(
            gguf_path=gguf_path,
            model_id=model_id,
            n_gpu_layers=0,
            n_ctx=n_ctx,
            n_threads=n_threads,
            n_batch=n_batch,
            temperature=temperature,
            max_tokens=max_tokens,
            verbose=verbose,
        )
        self.name = f"local-server:{Path(gguf_path).stem}"
        self._server_binary = find_llama_server(server_binary)
        self._host = str(host or "127.0.0.1")
        self._port = int(port)
        self._gpu_layers = str(gpu_layers or "all")
        self._startup_timeout = max(2.0, float(startup_timeout_sec))
        self._request_timeout = max(2.0, float(request_timeout_sec))
        self._server_process: subprocess.Popen[str] | None = None
        self._server_lock = threading.RLock()
        self._server_started_at = 0.0
        self._warmup_ms = 0.0
        self._warmup_complete = False
        self._last_error: Optional[str] = None

    @property
    def _base_url(self) -> str:
        return f"http://{self._host}:{self._port}"

    def _health(self, timeout: float = 0.8) -> bool:
        try:
            with urllib.request.urlopen(f"{self._base_url}/health", timeout=timeout) as response:
                return 200 <= int(response.status) < 300
        except (OSError, urllib.error.URLError, TimeoutError):
            return False

    def _ensure_server(self) -> None:
        with self._server_lock:
            if self._health():
                return
            if self._server_binary is None:
                raise BackendUnavailable(
                    "llama-server не найден. Установите официальный пакет llama.cpp "
                    "или укажите JARVIS_LLAMA_SERVER."
                )
            if not self._gguf_path.is_file():
                raise BackendUnavailable(f"Файл модели не найден: {self._gguf_path}")
            if self._server_process is not None and self._server_process.poll() is not None:
                self._server_process = None
            args = [
                str(self._server_binary),
                "-m", str(self._gguf_path),
                "-ngl", self._gpu_layers,
                "-c", str(self._n_ctx),
                "-b", str(self._n_batch),
                "--host", self._host,
                "--port", str(self._port),
                "--no-webui",
            ]
            if self._n_threads:
                args.extend(["-t", str(self._n_threads)])
            creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            started = time.perf_counter()
            try:
                self._server_process = subprocess.Popen(
                    args,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=creation_flags,
                )
            except (OSError, ValueError) as exc:
                self._last_error = f"{type(exc).__name__}: {exc}"
                raise BackendUnavailable(f"Не удалось запустить llama-server: {exc}") from exc
            self._server_started_at = time.perf_counter()
            deadline = time.perf_counter() + self._startup_timeout
            while time.perf_counter() < deadline:
                if self._health(timeout=0.8):
                    self._last_error = None
                    self._server_started_at = time.perf_counter() - started
                    return
                if self._server_process.poll() is not None:
                    break
                time.sleep(0.15)
            code = self._server_process.poll() if self._server_process else None
            self._last_error = f"llama-server не стал готов за {self._startup_timeout:.1f} с (exit={code})"
            raise BackendUnavailable(self._last_error)

    def _request(self, payload: Dict[str, Any], *, stream: bool = False):
        self._ensure_server()
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            f"{self._base_url}/v1/chat/completions",
            data=body,
            headers={"Content-Type": "application/json", "Accept": "text/event-stream" if stream else "application/json"},
            method="POST",
        )
        try:
            return urllib.request.urlopen(request, timeout=self._request_timeout)
        except (OSError, urllib.error.URLError, TimeoutError) as exc:
            raise BackendUnavailable(f"llama-server request failed: {exc}") from exc

    @staticmethod
    def _payload_messages(messages: List[Dict[str, Any]], system: Optional[str]) -> list[dict[str, str]]:
        return prepend_system(messages, system)

    @staticmethod
    def _content(payload: Dict[str, Any]) -> str:
        try:
            content = payload["choices"][0]["message"].get("content", "")
        except (KeyError, IndexError, TypeError) as exc:
            raise BackendUnavailable("llama-server returned an invalid response shape") from exc
        return strip_reasoning_blocks(str(content or "")).strip()

    def chat(self, messages: List[Dict[str, Any]], system: Optional[str] = None,
             max_tokens: Optional[int] = None, temperature: Optional[float] = None) -> str:
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": self._payload_messages(messages, system),
            "stream": False,
            "max_tokens": int(max_tokens or self._max_tokens),
            "temperature": self._temperature if temperature is None else float(temperature),
        }
        with self._request(payload) as response:
            try:
                data = json.loads(response.read().decode("utf-8"))
            except (ValueError, UnicodeDecodeError) as exc:
                raise BackendUnavailable(f"llama-server returned malformed JSON: {exc}") from exc
        return self._content(data)

    def direct(self, prompt: str, system: Optional[str] = None,
               max_tokens: Optional[int] = None, temperature: Optional[float] = None) -> str:
        if not (prompt or "").strip():
            raise ValueError("direct(): пустой prompt")
        return self.chat([{"role": "user", "content": prompt}], system, max_tokens, temperature)

    def streaming(self, messages: List[Dict[str, Any]], system: Optional[str] = None,
                  max_tokens: Optional[int] = None, temperature: Optional[float] = None) -> Generator[str, None, None]:
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": self._payload_messages(messages, system),
            "stream": True,
            "max_tokens": int(max_tokens or self._max_tokens),
            "temperature": self._temperature if temperature is None else float(temperature),
        }
        think_state = {"in_think": False}
        with self._request(payload, stream=True) as response:
            for raw_line in response:
                line = raw_line.decode("utf-8", errors="replace").strip()
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    payload = json.loads(data)
                    piece = payload.get("choices", [{}])[0].get("delta", {}).get("content", "")
                except (ValueError, TypeError, KeyError, IndexError) as exc:
                    raise BackendUnavailable(f"llama-server stream malformed: {exc}") from exc
                if piece:
                    visible = _visible_stream_piece(str(piece), state=think_state)
                    if visible:
                        yield visible

    def chat_with_tools(self, messages: List[Dict[str, Any]],
                        tools: Sequence[Dict[str, Any]],
                        system: Optional[str] = None,
                        tool_choice: str | Dict[str, Any] = "auto",
                        max_tokens: Optional[int] = None,
                        temperature: Optional[float] = None) -> ToolCallResponse:
        if not tools:
            raise ValueError("chat_with_tools(): список инструментов пуст")
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": self._payload_messages(messages, system),
            "tools": list(tools),
            "tool_choice": tool_choice,
            "stream": False,
            "max_tokens": int(max_tokens or self._max_tokens),
            "temperature": self._temperature if temperature is None else float(temperature),
        }
        with self._request(payload) as response:
            try:
                data = json.loads(response.read().decode("utf-8"))
            except (ValueError, UnicodeDecodeError) as exc:
                raise ToolsNotSupportedError(f"llama-server returned malformed tool JSON: {exc}") from exc
        try:
            return parse_tool_calls(data)
        except ValueError as exc:
            raise ToolsNotSupportedError(f"llama-server native tool response invalid: {exc}") from exc

    def warm_up(self) -> None:
        started = time.perf_counter()
        self._ensure_server()
        self._warmup_ms = (time.perf_counter() - started) * 1000.0
        self._warmup_complete = True

    def list_models(self) -> List[str]:
        return [self.model] if self._gguf_path.is_file() else []

    def is_available(self) -> bool:
        return bool(self._gguf_path.is_file() and self._server_binary is not None)

    def unavailable_reason(self) -> Optional[str]:
        if self.is_available():
            return None
        if not self._gguf_path.is_file():
            return f"Файл модели не найден: {self._gguf_path}"
        return "llama-server не найден"

    def runtime_info(self) -> Dict[str, Any]:
        gpu_layers = self._gpu_layers.casefold()
        numeric_gpu_layers = -1 if gpu_layers in {"all", "-1", "auto"} else int(gpu_layers) if gpu_layers.isdigit() else 0
        return {
            "backend": "vulkan/cuda llama-server",
            "runtime_backend": "vulkan",
            "model_path": str(self._gguf_path),
            "model_exists": self._gguf_path.is_file(),
            "server_binary": str(self._server_binary or ""),
            "server_running": bool(self._server_process and self._server_process.poll() is None),
            "server_pid": self._server_process.pid if self._server_process else None,
            "host": self._host,
            "port": self._port,
            # Keep the familiar numeric contract (-1 means all layers) while
            # retaining the exact server flag for diagnostics and packaging.
            "n_gpu_layers": numeric_gpu_layers,
            "gpu_layers": self._gpu_layers,
            "n_ctx": self._n_ctx,
            "n_batch": self._n_batch,
            "warmup_ms": round(self._warmup_ms, 3),
            "warmup_complete": self._warmup_complete,
            "startup_seconds": round(float(self._server_started_at or 0.0), 3),
            "error": self._last_error,
        }

    def close(self) -> None:
        with self._server_lock:
            process, self._server_process = self._server_process, None
            if process is None:
                return
            try:
                process.terminate()
                process.wait(timeout=3.0)
            except (OSError, subprocess.TimeoutExpired):
                try:
                    process.kill()
                except OSError:
                    pass
