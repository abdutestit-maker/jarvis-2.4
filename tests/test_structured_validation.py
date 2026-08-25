from core.structured import validate_tool_call
from core.actions.app_control import OpenAppTool
from core.actions.base import ToolContext


SCHEMA = {
    "type": "object",
    "properties": {
        "action": {"type": "string", "enum": ["open", "click"]},
        "count": {"type": "integer", "minimum": 1},
    },
    "required": ["action"],
    "additionalProperties": False,
}


def validate(arguments):
    return validate_tool_call(
        {"tool": "fixture", "arguments": arguments},
        ["fixture"],
        schema_lookup=lambda _: SCHEMA,
    )


def test_tool_call_rejects_enum_value_before_executor():
    decision, error = validate({"action": "press_enter"})
    assert decision is None
    assert "press_enter" in error


def test_tool_call_rejects_additional_property_before_executor():
    decision, error = validate({"action": "click", "key": "Enter"})
    assert decision is None
    assert "key" in error


def test_tool_call_rejects_wrong_type_before_executor():
    decision, error = validate({"action": "open", "count": "2"})
    assert decision is None
    assert "integer" in error


def test_tool_call_accepts_schema_valid_arguments():
    decision, error = validate({"action": "click", "count": 1})
    assert error == ""
    assert decision is not None
    assert decision.arguments["action"] == "click"


def test_explorer_rejects_nonexistent_target_before_launch(tmp_path):
    missing = tmp_path / "missing.txt"
    result = OpenAppTool().run(
        {"name": "Проводник", "target_path": str(missing)},
        ToolContext(),
    )
    assert result.ok is False
    assert "target_path не найден" in str(result.error)


def test_target_path_opens_existing_file_in_selected_app(tmp_path, monkeypatch):
    target = tmp_path / "notes.txt"
    target.write_text("hello", encoding="utf-8")
    seen = {}

    def fake_open(name, settings, args):
        seen.update(name=name, args=args)
        from core.actions.base import ActionResult
        return ActionResult("open_app", {"name": name, "args": args}, True, output="started")

    monkeypatch.setattr("core.actions.app_control.open_app", fake_open)
    result = OpenAppTool().run(
        {"name": "блокнот", "target_path": str(target)},
        ToolContext(),
    )

    assert result.ok is True
    assert seen["name"] == "блокнот"
    assert str(target.resolve()) in seen["args"]


def test_explorer_opens_directory_instead_of_selecting_its_parent(tmp_path, monkeypatch):
    seen = {}

    def fake_open(name, settings, args):
        seen.update(name=name, args=args)
        from core.actions.base import ActionResult
        return ActionResult("open_app", {"name": name, "args": args}, True, output="started")

    monkeypatch.setattr("core.actions.app_control.open_app", fake_open)
    result = OpenAppTool().run(
        {"name": "Проводник", "target_path": str(tmp_path)},
        ToolContext(),
    )

    assert result.ok is True
    assert seen["args"] == f'"{tmp_path.resolve()}"'
    assert "/select," not in seen["args"]


def test_explorer_selects_file_in_containing_directory(tmp_path, monkeypatch):
    target = tmp_path / "notes.txt"
    target.write_text("hello", encoding="utf-8")
    seen = {}

    def fake_open(name, settings, args):
        seen.update(name=name, args=args)
        from core.actions.base import ActionResult
        return ActionResult("open_app", {"name": name, "args": args}, True, output="started")

    monkeypatch.setattr("core.actions.app_control.open_app", fake_open)
    result = OpenAppTool().run(
        {"name": "Проводник", "target_path": str(target)},
        ToolContext(),
    )

    assert result.ok is True
    assert seen["args"] == f'/select,"{target.resolve()}"'
