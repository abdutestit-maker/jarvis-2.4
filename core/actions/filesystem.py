"""Файловая система (filesystem) — операции в пределах documents_dir.

Инструменты для чтения/записи/поиска файлов в безопасной директории
(``settings.paths.documents_dir``). Доступ ко всей ФС НЕ предоставляется.

Инструменты:
- ``ListFilesTool`` — список файлов в директории.
- ``ReadFileTool`` — чтение файла.
- ``WriteFileTool`` — запись файла (создаёт родительские директории).
- ``SearchFilesTool`` — поиск файлов по содержимому/имени.
"""

from __future__ import annotations

import fnmatch
from pathlib import Path
from typing import Any, Dict, List

from config.settings import Settings
from core.actions.base import ActionResult, Tool, ToolContext
from core.actions.registry import DEFAULT_REGISTRY
from core.utils.logger import get_logger
from core.utils.paths import ensure_parent

__all__ = [
    "resolve_docs_path",
    "list_files",
    "read_file",
    "write_file",
    "search_files",
    "ListFilesTool",
    "ReadFileTool",
    "WriteFileTool",
    "SearchFilesTool",
]

log = get_logger(__name__)

#: Максимальный размер читаемого файла (10 МБ)
_MAX_READ_SIZE = 10 * 1024 * 1024

#: Максимальное число результатов поиска
_MAX_SEARCH_RESULTS = 50


def resolve_docs_path(path: str, settings: Settings) -> Path:
    """Преобразует относительный путь в абсолютный внутри documents_dir.

    Args:
        path: относительный путь (например, "notes/todo.txt").
        settings: конфигурация.

    Returns:
        Абсолютный Path внутри documents_dir.

    Raises:
        ValueError: если путь пытается выйти за пределы documents_dir.
    """
    docs_dir = settings.paths.resolved("documents_dir")
    docs_dir.mkdir(parents=True, exist_ok=True)

    target = (docs_dir / path).resolve()
    try:
        target.relative_to(docs_dir.resolve())
    except ValueError:
        raise ValueError(f"Путь '{path}' выходит за пределы documents_dir")

    return target


def list_files(dir_path: str, settings: Settings, recursive: bool = False) -> List[str]:
    """Возвращает список файлов в директории.

    Args:
        dir_path: относительный путь внутри documents_dir (пусто = корень).
        settings: конфигурация.
        recursive: рекурсивно обходить поддиректории.

    Returns:
        Список относительных путей к файлам.
    """
    base = resolve_docs_path(dir_path, settings)
    if not base.exists() or not base.is_dir():
        return []

    files: List[str] = []
    if recursive:
        for p in base.rglob("*"):
            if p.is_file():
                try:
                    files.append(str(p.relative_to(settings.paths.resolved("documents_dir"))))
                except ValueError:
                    pass
    else:
        for p in base.iterdir():
            if p.is_file():
                try:
                    files.append(str(p.relative_to(settings.paths.resolved("documents_dir"))))
                except ValueError:
                    pass
    return sorted(files)


def read_file(path: str, settings: Settings, max_size: int = _MAX_READ_SIZE) -> str:
    """Читает текстовый файл.

    Args:
        path: относительный путь внутри documents_dir.
        settings: конфигурация.
        max_size: максимальный размер файла в байтах.

    Returns:
        Содержимое файла (UTF-8, fallback cp1251).

    Raises:
        ValueError: если файл слишком большой или не найден.
    """
    target = resolve_docs_path(path, settings)
    if not target.is_file():
        raise ValueError(f"Файл не найден: {path}")

    size = target.stat().st_size
    if size > max_size:
        raise ValueError(f"Файл слишком большой: {size} байт (лимит {max_size})")

    try:
        return target.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return target.read_text(encoding="cp1251", errors="replace")


def write_file(path: str, content: str, settings: Settings) -> ActionResult:
    """Записывает файл (создаёт родительские директории).

    Args:
        path: относительный путь внутри documents_dir.
        content: текст для записи.
        settings: конфигурация.

    Returns:
        ActionResult с ok=True при успехе.
    """
    try:
        target = resolve_docs_path(path, settings)
        ensure_parent(target)
        target.write_text(content, encoding="utf-8")
        log.info("Файл записан: %s (%d байт)", path, len(content.encode("utf-8")))
        return ActionResult(
            tool="write_file",
            args={"path": path, "size": len(content)},
            ok=True,
            output=f"Файл сохранён: {path} ({len(content)} символов)",
        )
    except Exception as exc:
        log.error("Ошибка записи файла %s: %s", path, exc)
        return ActionResult(
            tool="write_file",
            args={"path": path},
            ok=False,
            error=f"Не удалось записать файл: {exc}",
        )


def search_files(
    query: str,
    settings: Settings,
    dir_path: str = "",
    max_results: int = _MAX_SEARCH_RESULTS,
) -> List[str]:
    """Ищет файлы по имени или содержимому (простой текстовый поиск).

    Args:
        query: поисковая строка.
        settings: конфигурация.
        dir_path: директория для поиска (относительно documents_dir).
        max_results: максимум результатов.

    Returns:
        Список относительных путей к найденным файлам.
    """
    if not query or not query.strip():
        return []

    base = resolve_docs_path(dir_path, settings)
    if not base.exists():
        return []

    query_lower = query.lower()
    results: List[str] = []

    for p in base.rglob("*"):
        if len(results) >= max_results:
            break
        if not p.is_file():
            continue

        # Поиск по имени
        if query_lower in p.name.lower():
            try:
                results.append(str(p.relative_to(settings.paths.resolved("documents_dir"))))
                continue
            except ValueError:
                pass

        # Поиск по содержимому (только текстовые файлы, до 1 МБ)
        if p.stat().st_size > 1024 * 1024:
            continue
        if p.suffix.lower() not in (".txt", ".md", ".py", ".json", ".yaml", ".yml", ".ini", ".cfg", ".conf", ".log", ".csv"):
            continue

        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
            if query_lower in text.lower():
                results.append(str(p.relative_to(settings.paths.resolved("documents_dir"))))
        except Exception:
            pass

    return results


# --------------------------------------------------------------------------- #
# Tool-обёртки
# --------------------------------------------------------------------------- #


class ListFilesTool(Tool):
    """Инструмент: список файлов в директории."""

    @property
    def name(self) -> str:
        return "list_files"

    @property
    def description(self) -> str:
        return (
            "Возвращает список файлов в указанной директории внутри documents_dir. "
            "Можно включить рекурсивный обход поддиректорий."
        )

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "dir_path": {
                    "type": "string",
                    "description": "Относительный путь к директории (пусто = корень documents_dir).",
                    "default": "",
                },
                "recursive": {
                    "type": "boolean",
                    "description": "Рекурсивно обходить поддиректории.",
                    "default": False,
                },
            },
            "additionalProperties": False,
        }

    def run(self, args: Dict[str, Any], context: ToolContext) -> ActionResult:
        dir_path = args.get("dir_path", "")
        recursive = args.get("recursive", False)

        files = list_files(dir_path, context.settings, recursive)
        if not files:
            return ActionResult(
                tool=self.name,
                args=args,
                ok=True,
                output=f"Директория '{dir_path or '(корень)'}' пуста или не существует.",
            )

        lines = [f"Файлы в '{dir_path or '(корень)'}':"]
        for f in files:
            lines.append(f"  📄 {f}")
        return ActionResult(
            tool=self.name,
            args=args,
            ok=True,
            output="\n".join(lines),
        )


class ReadFileTool(Tool):
    """Инструмент: чтение файла."""

    @property
    def name(self) -> str:
        return "read_file"

    @property
    def description(self) -> str:
        return (
            "Читает текстовый файл из documents_dir. Поддерживает UTF-8 и cp1251. "
            "Максимальный размер файла — 10 МБ."
        )

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Относительный путь к файлу внутри documents_dir.",
                },
            },
            "required": ["path"],
            "additionalProperties": False,
        }

    def run(self, args: Dict[str, Any], context: ToolContext) -> ActionResult:
        path = args["path"]
        try:
            content = read_file(path, context.settings)
            # §22 — содержимое файла это внешние ДАННЫЕ, не команды.
            # Оборачиваем на границе инструмент→модель.
            from core.safety import wrap_untrusted
            preview = wrap_untrusted(
                content[:1000] + ("… [обрезано]" if len(content) > 1000 else ""),
                source=f"read_file ({path})",
            )
            return ActionResult(
                tool=self.name,
                args=args,
                ok=True,
                output=f"Содержимое {path}:\n\n{preview}",
            )
        except Exception as exc:
            return ActionResult(
                tool=self.name,
                args=args,
                ok=False,
                error=f"Не удалось прочитать файл: {exc}",
            )


class WriteFileTool(Tool):
    """Инструмент: запись файла."""

    @property
    def name(self) -> str:
        return "write_file"

    @property
    def description(self) -> str:
        return (
            "Создаёт или перезаписывает текстовый файл в documents_dir. "
            "Автоматически создаёт недостающие родительские директории."
        )

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Относительный путь к файлу внутри documents_dir.",
                },
                "content": {
                    "type": "string",
                    "description": "Текст для записи в файл.",
                },
            },
            "required": ["path", "content"],
            "additionalProperties": False,
        }

    def run(self, args: Dict[str, Any], context: ToolContext) -> ActionResult:
        return write_file(args["path"], args["content"], context.settings)


class SearchFilesTool(Tool):
    """Инструмент: поиск файлов по имени или содержимому."""

    @property
    def name(self) -> str:
        return "search_files"

    @property
    def description(self) -> str:
        return (
            "Ищет файлы в documents_dir по имени или текстовому содержимому. "
            "По содержимому ищет только в текстовых файлах (.txt, .md, .py, .json и др.) до 1 МБ."
        )

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Поисковый запрос (подстрока в имени или тексте файла).",
                },
                "dir_path": {
                    "type": "string",
                    "description": "Директория для поиска (относительно documents_dir, пусто = везде).",
                    "default": "",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Максимальное число результатов.",
                    "default": 50,
                    "minimum": 1,
                    "maximum": 200,
                },
            },
            "required": ["query"],
            "additionalProperties": False,
        }

    def run(self, args: Dict[str, Any], context: ToolContext) -> ActionResult:
        query = args["query"]
        dir_path = args.get("dir_path", "")
        max_results = args.get("max_results", _MAX_SEARCH_RESULTS)

        results = search_files(query, context.settings, dir_path, max_results)

        if not results:
            return ActionResult(
                tool=self.name,
                args=args,
                ok=True,
                output=f"Файлы по запросу «{query}» не найдены.",
            )

        lines = [f"Найдено файлов по «{query}» ({len(results)}):"]
        for f in results:
            lines.append(f"  📄 {f}")
        return ActionResult(
            tool=self.name,
            args=args,
            ok=True,
            output="\n".join(lines),
        )


# Авто-регистрация
DEFAULT_REGISTRY.register(ListFilesTool())
DEFAULT_REGISTRY.register(ReadFileTool())
DEFAULT_REGISTRY.register(WriteFileTool())
DEFAULT_REGISTRY.register(SearchFilesTool())