from __future__ import annotations

import json
from pathlib import Path

from core.llm.llama_server import LlamaServerBackend, find_llama_server


class _Response:
    def __init__(self, payload: object, *, lines: list[bytes] | None = None):
        self.payload = payload
        self.lines = lines
        self.status = 200

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return json.dumps(self.payload, ensure_ascii=False).encode("utf-8")

    def __iter__(self):
        return iter(self.lines or [])


def _backend(tmp_path: Path) -> LlamaServerBackend:
    model = tmp_path / "model.gguf"
    model.write_bytes(b"fixture")
    server = tmp_path / "llama-server.exe"
    server.write_bytes(b"fixture")
    return LlamaServerBackend(model, server_binary=server, port=9876)


def test_find_llama_server_accepts_explicit_path(tmp_path: Path):
    path = tmp_path / "llama-server.exe"
    path.write_bytes(b"fixture")
    assert find_llama_server(path) == path


def test_llama_server_backend_uses_openai_compatible_chat(monkeypatch, tmp_path: Path):
    backend = _backend(tmp_path)
    monkeypatch.setattr(backend, "_ensure_server", lambda: None)
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda *_args, **_kwargs: _Response({"choices": [{"message": {"content": "<think>x</think>готово"}}]}),
    )
    assert backend.direct("привет", max_tokens=8) == "готово"


def test_llama_server_backend_streams_sse(monkeypatch, tmp_path: Path):
    backend = _backend(tmp_path)
    monkeypatch.setattr(backend, "_ensure_server", lambda: None)
    lines = [
        'data: {"choices":[{"delta":{"content":"один "}}]}\n'.encode("utf-8"),
        'data: {"choices":[{"delta":{"content":"два"}}]}\n'.encode("utf-8"),
        b"data: [DONE]\n",
    ]
    monkeypatch.setattr("urllib.request.urlopen", lambda *_args, **_kwargs: _Response({}, lines=lines))
    assert "".join(backend.streaming([{"role": "user", "content": "x"}])) == "один два"


def test_runtime_info_exposes_numeric_gpu_contract(tmp_path: Path):
    backend = _backend(tmp_path)
    info = backend.runtime_info()
    assert info["n_gpu_layers"] == -1
    assert info["gpu_layers"] == "all"
