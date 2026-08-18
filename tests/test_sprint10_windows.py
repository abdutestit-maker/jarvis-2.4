"""Sprint 10 contracts for semantic Windows automation and app learning."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from core.operator.knowledge import AppKnowledge, AppKnowledgeStore
from core.operator.windows import AppExplorer, SemanticControl, SemanticSelector
from core.platform.windows import UIAutomationProvider, WindowsCapabilityLayer


def _control(
    name: str,
    control_type: str,
    *,
    automation_id: str = "",
    value: object = None,
    children: list[SemanticControl] | None = None,
) -> SemanticControl:
    return SemanticControl(
        name=name,
        control_type=control_type,
        automation_id=automation_id,
        class_name="FixtureControl",
        value=value,
        children=children or [],
    )


def test_semantic_lookup_prefers_automation_id_and_falls_back_to_role_name() -> None:
    tree = _control("Settings", "Window", children=[
        _control("Enable updates", "CheckBox", automation_id="updates-old"),
        _control("Enable updates", "CheckBox", automation_id="updates-enabled"),
        _control("Theme", "ComboBox", value="Light"),
    ])

    exact = tree.find_best(SemanticSelector(
        automation_id="updates-enabled", name="Enable updates", control_type="CheckBox",
    ))
    fallback = tree.find_best(SemanticSelector(
        name="theme", role="combobox",
    ))

    assert exact is not None and exact.automation_id == "updates-enabled"
    assert fallback is not None and fallback.name == "Theme"
    assert exact.semantic_selector == {
        "automation_id": "updates-enabled",
        "control_type": "CheckBox",
        "name": "Enable updates",
    }
    assert "rectangle" not in exact.to_dict()


def test_app_explorer_builds_structured_map_from_accessibility_tree() -> None:
    tree = _control("Fixture App", "Window", children=[
        _control("File", "MenuItem"),
        _control("General", "TabItem"),
        _control("Save", "Button", automation_id="save"),
        _control("Theme", "ComboBox", value="Dark"),
        _control("User name", "Edit", value="Ada"),
    ])

    class FakeLayer:
        def ui_tree(self, **_kwargs):
            return SimpleNamespace(ok=True, value=tree.to_dict(), error=None)

    knowledge = AppExplorer(FakeLayer()).explore("Fixture App")

    assert knowledge.application == "Fixture App"
    assert [item["name"] for item in knowledge.menus] == ["File"]
    assert {item["name"] for item in knowledge.settings} == {"Theme", "User name"}
    assert any(item["automation_id"] == "save" for item in knowledge.controls)
    assert knowledge.discovery_steps >= 1


def test_app_knowledge_persists_semantic_selectors_but_filters_secrets(tmp_path: Path) -> None:
    store = AppKnowledgeStore(tmp_path)
    knowledge = AppKnowledge(
        application="Fixture App",
        executable="fixture.exe",
        windows=[{"name": "Fixture App", "control_type": "Window"}],
        settings=[{
            "name": "API token",
            "control_type": "Edit",
            "value": "secret-value",
            "semantic_selector": {"name": "API token", "control_type": "Edit"},
        }],
        controls=[{
            "name": "Apply",
            "control_type": "Button",
            "semantic_selector": {"automation_id": "apply", "control_type": "Button"},
        }],
        successful_selectors={"theme": {"name": "Theme", "control_type": "ComboBox"}},
        best_execution_method="uia",
        verification_rules=[{"path": "settings.theme", "equals": "Dark"}],
    )

    path = store.save(knowledge)
    raw = path.read_text(encoding="utf-8")
    loaded = store.load("Fixture App")

    assert loaded is not None
    assert loaded.successful_selectors["theme"]["name"] == "Theme"
    assert "secret-value" not in raw
    assert "password" not in raw.lower()
    assert json.loads(raw)["settings"][0]["value"] == "[REDACTED]"


class _FakeInfo:
    def __init__(self, name: str, control_type: str, automation_id: str = "") -> None:
        self.name = name
        self.control_type = control_type
        self.automation_id = automation_id
        self.class_name = "Fixture"
        self.enabled = True
        self.visible = True
        self.process_id = 42
        self.handle = 100


class _FakeWrapper:
    def __init__(self, name: str, control_type: str, automation_id: str = "") -> None:
        self.element_info = _FakeInfo(name, control_type, automation_id)
        self.invoked = 0
        self.value = ""
        self.toggled = False
        self._children: list[_FakeWrapper] = []

    def descendants(self):
        return list(self._children)

    def children(self):
        return list(self._children)

    def invoke(self):
        self.invoked += 1

    def set_edit_text(self, value):
        self.value = value

    def get_value(self):
        return self.value

    def toggle(self):
        self.toggled = not self.toggled

    def get_toggle_state(self):
        return int(self.toggled)

    def window_text(self):
        return self.element_info.name


class _FakeDesktop:
    def __init__(self):
        self.window = _FakeWrapper("Fixture App", "Window")
        self.apply = _FakeWrapper("Apply", "Button", "apply-button")
        self.name = _FakeWrapper("User name", "Edit", "user-name")
        self.enabled = _FakeWrapper("Enabled", "CheckBox", "enabled")
        self.window._children = [self.apply, self.name, self.enabled]

    def windows(self):
        return [self.window]


def test_real_uia_provider_contract_uses_semantic_controls_without_coordinates() -> None:
    desktop = _FakeDesktop()
    provider = UIAutomationProvider(desktop_factory=lambda: desktop)
    layer = WindowsCapabilityLayer.with_uia_provider(provider)

    tree = layer.ui_tree(window_title="Fixture App")
    invoked = layer.ui_invoke(window_title="Fixture App", selector={"automation_id": "apply-button"})
    valued = layer.ui_set_value(
        window_title="Fixture App", selector={"name": "User name", "control_type": "Edit"},
        value="Grace",
    )
    toggled = layer.ui_toggle(
        window_title="Fixture App", selector={"automation_id": "enabled"}, state=True,
    )

    assert tree.ok and tree.provider == "uia"
    assert invoked.ok and desktop.apply.invoked == 1
    assert valued.ok and desktop.name.value == "Grace"
    assert toggled.ok and desktop.enabled.toggled is True
    assert "coordinates" not in str(tree.value).lower()

