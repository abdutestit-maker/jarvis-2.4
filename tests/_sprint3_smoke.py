"""Sprint 3 — LIVE SMOKE TEST (STEP 7). Запуск: python tests/_sprint3_smoke.py

Реальные сетевые вызовы anymodel + реальная файловая система (без моков):
  TEST A — Tool timeout: web_fetch на non-routable адрес убивается watchdog'ом
  TEST B — RepairLoop limit: несуществующий файл -> 3 попытки -> остановка
           + risk gate: удаление системного файла блокируется гейтом
  TEST C — Fast fallback: сломанный TIER 1 -> быстрый ответ фолбэка + [degraded]
  TEST D — «Привет» остаётся в conversation path (регрессия Sprint 2)
  TEST E — «Какие файлы в documents?» -> action path с реальным list_files
"""
from __future__ import annotations

import copy
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import load_config
from core.actions import DEFAULT_REGISTRY, ToolContext
from core.actions.executor import execute_tool
from core.agent import Agent, AgentConfig
from core.repair import RepairLoop
from core.safety import assess_risk

PASS, FAIL = "  [PASS]", "  [FAIL]"
results: list = []


def report(name: str, ok: bool, detail: str) -> None:
    results.append((name, ok))
    print(f"{PASS if ok else FAIL} {name}: {detail}")


def main() -> int:
    settings = load_config()
    ctx = ToolContext(user_id="default", settings=settings, state=None)

    # ------------------------------------------------------------------ #
    print("\n=== TEST A — Tool timeout (web_fetch на non-routable адрес) ===")
    smoke_cfg = copy.deepcopy(settings)
    smoke_cfg.limits.tool_timeout_web_sec = 6.0  # не ждём 30 c в смоке
    ctx_a = ToolContext(user_id="default", settings=smoke_cfg, state=None)
    # httpbin delay=10: соединение принимается, но тело не приходит 10 c.
    # Внутренний таймаут web_fetch = 15 c, watchdog смока = 6 c -> побеждает
    # watchdog (именно его и проверяем).
    started = time.perf_counter()
    result = execute_tool(DEFAULT_REGISTRY, "web_fetch",
                          {"url": "https://httpbin.org/delay/10"}, ctx_a)
    elapsed = time.perf_counter() - started
    report("A1 таймаут сработал", not result.ok and "Таймаут выполнения" in (result.error or ""),
           f"error='{(result.error or '')[:80]}...' за {elapsed:.1f} c")
    report("A2 watchdog не завис", elapsed < 15, f"{elapsed:.1f} c (< 15 c)")

    # ------------------------------------------------------------------ #
    print("\n=== TEST B — RepairLoop limit + risk gate (реальный FS) ===")
    loop = RepairLoop(DEFAULT_REGISTRY, max_attempts=3)
    started = time.perf_counter()
    repair = loop.run("read_file", {"path": "Z:/definitely/missing/file.txt"}, ctx,
                      verification=lambda r: False)
    elapsed = time.perf_counter() - started
    report("B1 max 3 попытки -> остановка",
           not repair.ok and repair.attempts == 3 and elapsed < 30,
           f"attempts={repair.attempts}, {elapsed:.1f} c")

    def gate(tool, args):
        risk = assess_risk(f"удали файл {args.get('path', '')}", tool, args)
        return "; ".join(risk.reasons) if risk.needs_confirmation else None

    repair2 = loop.run("read_file", {"path": "C:/Windows/System32/cmd.exe"}, ctx,
                       verification=lambda r: False, risk_gate=gate)
    report("B2 risk gate блокирует опасный повтор",
           not repair2.ok and repair2.needs_human,
           f"needs_human={repair2.needs_human}, msg='{repair2.human_message[:60]}...'")

    # ------------------------------------------------------------------ #
    print("\n=== TEST C — Fast fallback (TIER 1 сломан) ===")
    broken = copy.deepcopy(settings)
    broken.model_tiers.fast = "am/nonexistent-broken-model"  # 404 -> мгновенный сбой
    broken.source_path = settings.source_path
    agent_c = Agent(broken, config=AgentConfig(enable_skill_forge=False))
    started = time.perf_counter()
    outcome = agent_c.execute("Привет, как твои дела?")
    elapsed = time.perf_counter() - started
    report("C1 фолбэк ответил быстро (без 30-секундного зависания)",
           elapsed < 25 and outcome.mode == "conversation",
           f"mode={outcome.mode}, {elapsed:.1f} c")
    report("C2 ответ помечен [degraded] (не маскируем фолбэк)",
           outcome.degraded or outcome.mode == "model_error",
           f"degraded={outcome.degraded}, text='{outcome.text[:60]}...'")

    # ------------------------------------------------------------------ #
    print("\n=== TEST D — Conversation без tool (регрессия Sprint 2) ===")
    agent = Agent(settings, config=AgentConfig(enable_skill_forge=False))
    started = time.perf_counter()
    outcome_d = agent.execute("Привет")
    elapsed = time.perf_counter() - started
    report("D1 остался в conversation path",
           outcome_d.mode == "conversation" and outcome_d.tool_used is None,
           f"mode={outcome_d.mode}, {elapsed:.1f} c")
    report("D2 осмысленный ответ", len(outcome_d.text) > 5,
           f"text='{outcome_d.text[:70]}...'")

    # ------------------------------------------------------------------ #
    print("\n=== TEST E — Action с tool (регрессия) ===")
    started = time.perf_counter()
    outcome_e = agent.execute("Какие файлы в папке documents?")
    elapsed = time.perf_counter() - started
    report("E1 action path с инструментом",
           outcome_e.tool_used == "list_files" and outcome_e.mode in ("tool", "fast_path"),
           f"tool={outcome_e.tool_used}, mode={outcome_e.mode}, {elapsed:.1f} c")
    report("E2 верифицированный результат", outcome_e.verified,
           f"verified={outcome_e.verified}")

    # ------------------------------------------------------------------ #
    ok_count = sum(1 for _, ok in results if ok)
    print(f"\n=== ИТОГ SMOKE: {ok_count}/{len(results)} PASS ===")
    return 0 if ok_count == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
