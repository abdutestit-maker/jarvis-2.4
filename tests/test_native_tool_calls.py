from __future__ import annotations

import pytest
import threading

from core.llm.backend import ToolsNotSupportedError
from core.llm.tool_calls import ToolCall, ToolCallResponse, parse_tool_calls


def test_parse_native_openai_tool_call_and_json_arguments():
    response = {
        "choices": [{
            "message": {
                "content": "",
                "tool_calls": [{
                    "id": "call-1",
                    "type": "function",
                    "function": {
                        "name": "current_time",
                        "arguments": "{}",
                    },
                }],
            },
        }],
    }

    parsed = parse_tool_calls(response)

    assert parsed.content == ""
    assert list(parsed.tool_calls) == [ToolCall("call-1", "current_time", {})]


def test_parse_native_tool_call_rejects_non_object_arguments():
    response = {
        "choices": [{
            "message": {
                "tool_calls": [{
                    "id": "call-2",
                    "function": {"name": "current_time", "arguments": "[]"},
                }],
            },
        }],
    }

    with pytest.raises(ValueError, match="object"):
        parse_tool_calls(response)


def test_parse_anthropic_tool_use_content_blocks():
    response = {
        "content": [
            {"type": "text", "text": "готовлю результат"},
            {"type": "tool_use", "id": "toolu-1", "name": "current_time", "input": {}},
        ],
    }

    parsed = parse_tool_calls(response)

    assert parsed.content == "готовлю результат"
    assert parsed.first_tool_call == ToolCall("toolu-1", "current_time", {})


def test_tool_call_response_is_serializable_and_immutable():
    call = ToolCall("call-3", "play_music", {"mood": "focus"})
    response = ToolCallResponse(content="", tool_calls=(call,))

    assert response.to_dict()["tool_calls"][0]["function"]["name"] == "play_music"
    with pytest.raises(TypeError):
        call.arguments["mood"] = "sleep"  # type: ignore[index]


def test_base_backend_keeps_compatibility_but_exposes_clear_native_error():
    from conftest import FakeBackend

    with pytest.raises(ToolsNotSupportedError):
        FakeBackend().chat_with_tools([], tools=[])


def test_agent_accepts_native_call_before_legacy_json_planner(settings):
    from conftest import FakeBackend
    from core.agent import Agent
    from core.capabilities import CAPABILITIES
    from core.llm import Tier

    class NativeBackend(FakeBackend):
        supports_tools = True

        def __init__(self):
            super().__init__(settings)
            self.native_calls = 0

        def chat_with_tools(self, messages, tools, **kwargs):
            self.native_calls += 1
            return ToolCallResponse(
                tool_calls=(ToolCall("native-1", "current_time", {}),),
            )

    backend = NativeBackend()
    agent = Agent(settings)
    agent._backend_for_routing = lambda _routing: (backend, Tier.FAST)
    cap = CAPABILITIES.get("current_time")
    decision, error = agent._decide_with_model(
        "покажи время",
        [cap],
        None,
        threading.Event(),
    )

    assert error == ""
    assert decision is not None and decision.tool == "current_time"
    assert backend.native_calls == 1


def test_local_qwen_forwards_native_schema_to_llama(tmp_path):
    from core.llm.local_qwen import LocalQwenBackend

    class LlamaStub:
        def __init__(self):
            self.kwargs = None

        def create_chat_completion(self, **kwargs):
            self.kwargs = kwargs
            return {
                "choices": [{
                    "message": {
                        "content": "",
                        "tool_calls": [{
                            "id": "call-4",
                            "function": {"name": "current_time", "arguments": "{}"},
                        }],
                    },
                }],
            }

    model = tmp_path / "model.gguf"
    model.write_bytes(b"fixture")
    backend = LocalQwenBackend(model)
    llama = LlamaStub()
    backend._llama = llama

    result = backend.chat_with_tools(
        [{"role": "user", "content": "время"}],
        [{"type": "function", "function": {
            "name": "current_time", "description": "time",
            "parameters": {"type": "object"},
        }}],
    )

    assert result.first_tool_call is not None
    assert llama.kwargs["tools"][0]["function"]["name"] == "current_time"
