"""Ядро Джарвиса.

Состав (по частям разработки):
    * ``core.state``   — контракт состояния графа (Часть 1);
    * ``core.llm``     — LLM-бэкенды и тиры совета (Часть 1);
    * ``core.utils``   — логирование, пути (Часть 1);
    * ``core.router``  — совет мудрецов, keyword-роутер (Часть 2);
    * ``core.memory``  — короткая/долгая память, RAG, knowledge graph (Часть 3);
    * ``core.actions`` — Action Engine (Часть 4);
    * ``core.voice``   — Piper TTS, уведомления (Часть 5);
    * ``core.proactive`` — проактивное поведение (Часть 5).

Здесь сознательно нет тяжёлых импортов: ``import core`` не должен тянуть
llama-cpp или chromadb.
"""

from __future__ import annotations

__version__ = "0.1.0"

__all__ = ["__version__"]
