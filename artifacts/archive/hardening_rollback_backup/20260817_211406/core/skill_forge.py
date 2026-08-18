"""Skill Forge — кузница навыков для неизвестных задач (§6, §7, §32, §42).

Когда J.A.R.V.I.S. не умеет делать X:
    1. определить отсутствие capability;
    2. исследовать X;
    3. найти подход;
    4. создать procedure / script / connector;
    5. выполнить безопасный тест;
    6. проверить результат;
    7. сохранить skill;
    8. в следующий раз использовать его.

Каждый навык имеет manifest (§7):
    name, description, triggers, required_inputs, tools, risk,
    procedure, success_criteria, test_cases, version, last_verified, dependencies

Статусы (§7): draft -> testing -> stable -> needs_repair -> deprecated

Навык НЕ считается stable, пока его не проверили.

Хранится в data/skills/ как markdown-файл с YAML frontmatter (читаемо
человеком и парсится машиной). Позволяет искать навык по триггерам и
переиспользовать при похожих задачах (UNKNOWN != IMPOSSIBLE, §32, §42).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from config.settings import Settings
from core.security.atomic import atomic_write_text
from core.utils.logger import get_logger
from core.utils.paths import PROJECT_ROOT, resolve_path

__all__ = ["SkillStatus", "SkillManifest", "SkillForge", "match_skill"]

log = get_logger(__name__)


class SkillStatus(str, Enum):  # noqa: F811  (re-declared intentionally)
    DRAFT = "draft"
    TESTING = "testing"
    STABLE = "stable"
    NEEDS_REPAIR = "needs_repair"
    DEPRECATED = "deprecated"


@dataclass
class SkillManifest:
    """Манифест навыка (§7)."""

    name: str
    description: str = ""
    triggers: List[str] = field(default_factory=list)
    required_inputs: List[str] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)
    risk: str = "low"           # low | medium | high (§27)
    procedure: str = ""
    success_criteria: str = ""
    test_cases: List[str] = field(default_factory=list)
    version: str = "0.1.0"
    last_verified: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    status: SkillStatus = SkillStatus.DRAFT
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source_task_id: Optional[str] = None

    def to_frontmatter(self) -> str:
        """YAML frontmatter (без зависимости от pyyaml — пишем вручную)."""
        def yaml_list(items: List[str]) -> str:
            if not items:
                return "[]"
            return "[" + ", ".join(f'"{x}"' for x in items) + "]"

        lines = [
            "---",
            f'name: "{self.name}"',
            f'description: "{self.description}"',
            f"triggers: {yaml_list(self.triggers)}",
            f"required_inputs: {yaml_list(self.required_inputs)}",
            f"tools: {yaml_list(self.tools)}",
            f'risk: "{self.risk}"',
            f"status: {self.status.value}",
            f"version: \"{self.version}\"",
            f"last_verified: {self.last_verified or 'null'}",
            f"dependencies: {yaml_list(self.dependencies)}",
            f"source_task_id: {self.source_task_id or 'null'}",
            f"created_at: {self.created_at}",
            f"updated_at: {self.updated_at}",
            "---",
        ]
        return "\n".join(lines)

    def to_markdown(self) -> str:
        body = [
            f"# Skill: {self.name}",
            "",
            f"**Статус:** {self.status.value}  ",
            f"**Risk:** {self.risk}  ",
            f"**Описание:** {self.description}",
            "",
            "## Triggers",
        ]
        body += [f"- {t}" for t in self.triggers] or ["- (нет)"]
        body += ["", "## Required inputs"]
        body += [f"- {t}" for t in self.required_inputs] or ["- (нет)"]
        body += ["", "## Procedure", "", self.procedure or "(пусто)", ""]
        body += ["## Success criteria", "", self.success_criteria or "(не заданы)", ""]
        body += ["## Test cases"]
        body += [f"- {t}" for t in self.test_cases] or ["- (нет)"]
        return "\n".join(body)

    def to_file_text(self) -> str:
        return self.to_frontmatter() + "\n\n" + self.to_markdown()

    @classmethod
    def from_file_text(cls, text: str) -> "SkillManifest":
        """Парсит markdown+frontmatter (без pyyaml)."""
        fm: Dict[str, Any] = {}
        body = text
        m = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", text, re.DOTALL)
        if m:
            fm_raw, body = m.group(1), m.group(2)
            for line in fm_raw.splitlines():
                if ":" not in line:
                    continue
                key, _, val = line.partition(":")
                key = key.strip()
                val = val.strip()
                val = val.strip('"').strip("'")
                if val.startswith("[") and val.endswith("]"):
                    inner = val[1:-1].strip()
                    fm[key] = [x.strip().strip('"').strip("'") for x in inner.split(",")] if inner else []
                elif val == "null" or val == "":
                    fm[key] = None
                else:
                    fm[key] = val
        status = SkillStatus(fm.get("status", "draft")) if fm.get("status") else SkillStatus.DRAFT
        return cls(
            name=fm.get("name", "unnamed"),
            description=fm.get("description", "") or "",
            triggers=list(fm.get("triggers") or []),
            required_inputs=list(fm.get("required_inputs") or []),
            tools=list(fm.get("tools") or []),
            risk=fm.get("risk", "low") or "low",
            procedure=body,
            success_criteria=fm.get("success_criteria", "") or "",
            test_cases=list(fm.get("test_cases") or []),
            version=fm.get("version", "0.1.0") or "0.1.0",
            last_verified=fm.get("last_verified"),
            dependencies=list(fm.get("dependencies") or []),
            status=status,
            source_task_id=fm.get("source_task_id"),
        )


class SkillForge:
    """Кузница навыков: поиск, создание, верификация, сохранение."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        if settings is not None:
            base = settings.paths.resolved("data_dir") or (PROJECT_ROOT / "data")
        else:
            base = PROJECT_ROOT / "data"
        self._dir = Path(base) / "skills"
        self._dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ #
    #  Поиск
    # ------------------------------------------------------------------ #
    def load_all(self) -> List[SkillManifest]:
        out: List[SkillManifest] = []
        for p in self._dir.glob("*.md"):
            try:
                out.append(SkillManifest.from_file_text(p.read_text(encoding="utf-8")))
            except Exception as exc:
                log.warning("SkillForge: не удалось прочитать %s: %s", p, exc)
        return out

    def find(self, name: str) -> Optional[SkillManifest]:
        p = self._dir / f"{_slug(name)}.md"
        if p.is_file():
            try:
                return SkillManifest.from_file_text(p.read_text(encoding="utf-8"))
            except Exception as exc:
                log.warning("SkillForge: не удалось прочитать %s: %s", p, exc)
        return None

    def match(self, goal: str) -> Optional[SkillManifest]:
        """Ищет подходящий навык по триггерам/имени (подстрока, регистр-независимо)."""
        goal_l = goal.lower()
        for skill in self.load_all():
            if skill.status in (SkillStatus.DEPRECATED,):
                continue
            for trig in skill.triggers:
                if trig.lower() in goal_l:
                    return skill
            if skill.name.lower() in goal_l:
                return skill
        return None

    # ------------------------------------------------------------------ #
    #  Создание / обновление
    # ------------------------------------------------------------------ #
    def save(self, skill: SkillManifest) -> Path:
        """Сохраняет навык на диск (атомарно). Обновляет updated_at."""
        skill.updated_at = datetime.now(timezone.utc).isoformat()
        p = self._dir / f"{_slug(skill.name)}.md"
        atomic_write_text(p, skill.to_file_text())
        log.info("SkillForge: навык '%s' сохранён (%s)", skill.name, skill.status.value)
        return p

    def create_draft(self, name: str, goal: str, task_id: Optional[str] = None,
                     triggers: Optional[List[str]] = None) -> SkillManifest:
        """Создаёт черновик навыка из неизвестной задачи (§6)."""
        draft = SkillManifest(
            name=name,
            description=f"Авто-черновик из задачи: {goal[:200]}",
            triggers=triggers or [goal.split("\n")[0][:80]],
            required_inputs=[],
            tools=[],
            risk="medium",
            procedure="",
            success_criteria="",
            test_cases=[],
            status=SkillStatus.DRAFT,
            source_task_id=task_id,
        )
        self.save(draft)
        return draft

    def mark_verified(self, name: str, success: bool) -> Optional[SkillManifest]:
        """Переводит навык в stable/testing/needs_repair по результату проверки (§7)."""
        skill = self.find(name)
        if skill is None:
            return None
        skill.last_verified = datetime.now(timezone.utc).isoformat()
        if success:
            skill.status = SkillStatus.STABLE if skill.status != SkillStatus.TESTING else SkillStatus.STABLE
            if skill.status == SkillStatus.DRAFT:
                skill.status = SkillStatus.TESTING
        else:
            skill.status = SkillStatus.NEEDS_REPAIR
        self.save(skill)
        return skill


def match_skill(forge: SkillForge, goal: str) -> Optional[SkillManifest]:
    """Удобная обёртка: поиск подходящего навыка (§6)."""
    return forge.match(goal)


def _slug(name: str) -> str:
    """Превращает имя навыка в безопасное имя файла."""
    s = re.sub(r"[^\w\-]+", "_", name.strip().lower())
    s = re.sub(r"_+", "_", s).strip("_")
    return s or "unnamed"
