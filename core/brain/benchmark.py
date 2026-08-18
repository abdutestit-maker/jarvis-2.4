"""Objective provider latency/schema benchmark; no subjective intelligence score."""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable

from .models import BrainRequest, BrainRole, ModelCapabilityProfile


@dataclass(frozen=True)
class BenchmarkReport:
    provider: str
    model: str
    role: str
    ttft_ms: float
    total_latency_ms: float
    tokens_per_second: float
    success: bool
    schema_compliance: bool | None
    output_chars: int
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider, "model": self.model, "role": self.role,
            "ttft_ms": self.ttft_ms, "total_latency_ms": self.total_latency_ms,
            "tokens_per_second": self.tokens_per_second, "success": self.success,
            "schema_compliance": self.schema_compliance, "output_chars": self.output_chars,
            "error": self.error,
        }


class BrainBenchmark:
    def run_stream(self, provider: Any, model: str, request: BrainRequest, *,
                   schema_check: Callable[[str], bool] | None = None) -> BenchmarkReport:
        started = time.perf_counter()
        first_at: float | None = None
        chunks: list[str] = []
        error = ""
        try:
            for piece in provider.stream(request, model=model):
                if first_at is None:
                    first_at = time.perf_counter()
                chunks.append(str(piece))
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
        ended = time.perf_counter()
        text = "".join(chunks)
        total = max(0.000001, ended - started)
        token_estimate = max(1.0, len(text) / 4.0) if text else 0.0
        return BenchmarkReport(
            provider=str(provider.name), model=model, role=request.role.value,
            ttft_ms=round(((first_at or ended) - started) * 1000, 3),
            total_latency_ms=round(total * 1000, 3),
            tokens_per_second=round(token_estimate / total, 3) if text else 0.0,
            success=bool(text and not error),
            schema_compliance=(bool(schema_check(text)) if schema_check and text else None),
            output_chars=len(text), error=error[:240],
        )


class AutoRoleSuggester:
    def suggest(self, profiles: dict[str, ModelCapabilityProfile],
                reports: tuple[BenchmarkReport, ...] | list[BenchmarkReport], *,
                overrides: dict[BrainRole, str] | None = None) -> dict[BrainRole, str]:
        overrides = dict(overrides or {})
        by_key = {f"{report.provider}:{report.model}": report
                  for report in reports if report.success}
        result: dict[BrainRole, str] = {}
        for role in BrainRole:
            if role in overrides:
                result[role] = overrides[role]
                continue
            eligible = [
                (key, profile, by_key[key]) for key, profile in profiles.items()
                if role in profile.roles and key in by_key
            ]
            if not eligible:
                continue
            eligible.sort(key=lambda item: (
                item[1].cost_tier, item[2].total_latency_ms, not item[1].local,
            ))
            result[role] = eligible[0][0]
        return result


__all__ = ["BrainBenchmark", "BenchmarkReport", "AutoRoleSuggester"]
