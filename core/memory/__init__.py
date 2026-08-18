"""Слои памяти Джарвиса — публичный контракт.

Импорт из других частей проекта::

    from core.memory import (
        SessionManager, LongTermMemory, Embedder, DocumentRAG,
        GraphMemoryStore, MemoryRetriever,
        load_profile, save_profile, update_profile, get_profile_context,
    )
"""

from __future__ import annotations

from core.memory.budget import estimate_tokens, fit_messages_to_budget
from core.memory.document_rag import DocumentRAG, chunk_text, read_pdf, read_text_file
from core.memory.embedder import Embedder
from core.memory.facts import detect_tone, extract_facts, learn_facts
from core.memory.knowledge_graph import GraphMemoryStore
from core.memory.long_term import LongTermMemory
from core.memory.profile import (
    get_profile_context,
    get_relevant_profile_context,
    load_profile,
    save_profile,
    update_profile,
)
from core.memory.retrieval import MemoryRetriever
from core.memory.relationship import (
    MemoryContext,
    MemoryHierarchy,
    PreferenceLearner,
    RelationshipMemory,
    RelationshipMemoryStore,
    WorkingMemory,
)
from core.memory.short_term import SessionManager

__all__ = [
    "SessionManager",
    "Embedder",
    "LongTermMemory",
    "DocumentRAG",
    "GraphMemoryStore",
    "MemoryRetriever",
    "load_profile",
    "save_profile",
    "update_profile",
    "get_profile_context",
    "get_relevant_profile_context",
    "read_pdf",
    "read_text_file",
    "chunk_text",
    "estimate_tokens",
    "fit_messages_to_budget",
    "extract_facts",
    "learn_facts",
    "detect_tone",
    "MemoryContext",
    "MemoryHierarchy",
    "PreferenceLearner",
    "RelationshipMemory",
    "RelationshipMemoryStore",
    "WorkingMemory",
]
