"""Factual self-knowledge derived from live registries and providers."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping

from core.cognitive.models import CurrentMindState


@dataclass(frozen=True)
class SelfModelSnapshot:
    tool_names: tuple[str, ...]
    capability_names: tuple[str, ...]
    provider_names: tuple[str, ...]


@dataclass(frozen=True)
class SelfKnowledgeAnswer:
    known: bool
    text: str = ""
    evidence: tuple[str, ...] = ()


def _provider_available(provider: Any) -> bool:
    if provider is None:
        return False
    availability = getattr(provider, "available", True)
    try:
        return bool(availability() if callable(availability) else availability)
    except Exception:
        return False


class CapabilitySelfModel:
    """Read-only view of what this runtime can factually use right now."""

    def __init__(self, registry: Any, *, capability_registry: Any = None,
                 providers: Mapping[str, Any] | None = None,
                 risk_policy: Any = None, brain_fabric: Any = None) -> None:
        self.registry = registry
        self.capability_registry = capability_registry
        self.providers = dict(providers or {})
        self.risk_policy = risk_policy
        self.brain_fabric = brain_fabric

    def snapshot(self) -> SelfModelSnapshot:
        tools = tuple(sorted(
            str(getattr(tool, "name", "")) for tool in self.registry.list_tools()
            if getattr(tool, "name", "")
        ))
        capabilities: tuple[str, ...] = ()
        if self.capability_registry is not None:
            try:
                capabilities = tuple(sorted(
                    str(getattr(capability, "name", ""))
                    for capability in self.capability_registry.all(only_available=True)
                    if getattr(capability, "name", "")
                ))
            except (AttributeError, TypeError):
                capabilities = ()
        providers = tuple(sorted(
            name for name, provider in self.providers.items()
            if _provider_available(provider)
        ))
        return SelfModelSnapshot(tools, capabilities, providers)

    def answer(self, question: str, state: CurrentMindState) -> SelfKnowledgeAnswer:
        value = " ".join((question or "").casefold().replace("ё", "е").split())
        snapshot = self.snapshot()
        if re.search(r"(какой.*мозг|какая.*модель|какой.*провайдер|brain.*working)", value):
            result = getattr(self.brain_fabric, "last_result", None) if self.brain_fabric else None
            route = getattr(self.brain_fabric, "last_route", None) if self.brain_fabric else None
            if result is not None:
                provider, model = result.provider, result.model
                primary = getattr(route, "primary", None)
            elif route is not None:
                primary = route.primary
                provider, model = primary.provider, primary.model
            else:
                return SelfKnowledgeAnswer(
                    True, "Сейчас модель ещё не выбрана для активной задачи.",
                    ("brain_fabric:no_active_route",),
                )
            local = bool(getattr(primary, "local", False))
            text = ("Сейчас разговор ведёт локальная модель."
                    if local else "Сейчас используется подключённый внешний провайдер.")
            return SelfKnowledgeAnswer(True, text, (f"{provider}:{model}",))
        if re.search(r"(чем.*закончил|что.*получил|что.*проверен|какой.*результат)", value):
            if state.last_verified_result:
                subject = f" «{state.current_goal}»" if state.current_goal else ""
                return SelfKnowledgeAnswer(
                    True, f"Последняя задача{subject} завершена, результат проверен.",
                    ("mind_state:last_verified_result",),
                )
            return SelfKnowledgeAnswer(True, "Подтверждённого результата пока нет.",
                                       ("mind_state:no_verified_result",))
        if re.search(r"(что ты сейчас дела|чем ты занят|текущ.*задач)", value):
            if not state.current_goal:
                return SelfKnowledgeAnswer(True, "Сейчас активной задачи нет.", ("mind_state:idle",))
            detail = f" Сейчас: {state.active_task}." if state.active_task else ""
            return SelfKnowledgeAnswer(
                True, f"Работаю над задачей: {state.current_goal}.{detail}",
                (f"mind_state:{state.mission_state}",),
            )

        if re.search(r"(почему.*подтвержден|зачем.*подтвержден)", value):
            evidence = "risk policy unavailable"
            if self.risk_policy is not None:
                decision = self.risk_policy.decide(confidence=0.99, risk="high")
                evidence = str(getattr(decision, "reason", "risk gate"))
            return SelfKnowledgeAnswer(
                True,
                "Операция может существенно изменить систему, поэтому мне потребуется ваше подтверждение.",
                (evidence,),
            )

        if re.search(r"(устанавлива|установить|ставить).*(программ|прилож)|"
                     r"(умеешь|можешь).*(установ)", value):
            installer = next((
                name for name in snapshot.provider_names
                if "install" in name.casefold() or "software" in name.casefold()
            ), "")
            if installer:
                return SelfKnowledgeAnswer(
                    True,
                    "Да. Могу найти доверенный источник, установить программу и проверить результат.",
                    (installer,),
                )
            return SelfKnowledgeAnswer(
                True, "Компонент установки сейчас не зарегистрирован.",
                ("runtime provider registry",),
            )

        if re.search(r"(разобраться сам|научиться|найти способ)", value):
            if snapshot.tool_names or snapshot.capability_names:
                return SelfKnowledgeAnswer(
                    True,
                    "Да. Сначала проверю готовые возможности, затем составлю и проверю безопасный способ.",
                    (f"tools={len(snapshot.tool_names)}", f"capabilities={len(snapshot.capability_names)}"),
                )
            return SelfKnowledgeAnswer(True, "Сначала исследую задачу и проверю способ выполнения.",
                                       ("empty runtime registry",))

        if re.search(r"(что ты умеешь|твои возможност|какие инструменты)", value):
            if not snapshot.tool_names:
                return SelfKnowledgeAnswer(True, "Доступные действия пока не зарегистрированы.",
                                           ("runtime registry",))
            categories = self._categories(snapshot.tool_names)
            return SelfKnowledgeAnswer(
                True, "Сейчас доступны: " + ", ".join(categories) + ".",
                tuple(snapshot.tool_names),
            )
        return SelfKnowledgeAnswer(False)

    @staticmethod
    def _categories(names: tuple[str, ...]) -> list[str]:
        groups = []
        joined = " ".join(names)
        for needle, label in (
            ("file", "работа с локальными файлами"),
            ("app", "запуск приложений"),
            ("browser", "управление браузером"),
            ("reminder", "напоминания"),
            ("system", "проверка системы"),
            ("web", "поиск информации"),
        ):
            if needle in joined:
                groups.append(label)
        return groups or [f"{len(names)} локальных действий"]


__all__ = ["CapabilitySelfModel", "SelfKnowledgeAnswer", "SelfModelSnapshot"]
