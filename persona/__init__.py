"""Persona — публичный контракт.

Импорт::

    from persona import build_system_prompt, load_persona_text
"""

from __future__ import annotations

from persona.system_prompt import build_system_prompt, load_persona_text

__all__ = ["build_system_prompt", "load_persona_text"]