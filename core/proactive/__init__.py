"""Proactive — публичный контракт.

Импорт::

    from core.proactive import Proactor, BackgroundScheduler
"""

from __future__ import annotations

from core.proactive.background_tasks import BackgroundScheduler
from core.proactive.proactor import Proactor

__all__ = ["Proactor", "BackgroundScheduler"]