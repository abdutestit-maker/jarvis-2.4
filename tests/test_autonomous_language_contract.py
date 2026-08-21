"""Regression checks for language-agnostic autonomous routing contracts."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class AutonomousLanguageContractTests(unittest.TestCase):
    def test_frontend_does_not_predict_missions_or_onboarding(self):
        app = (ROOT / "jarvis" / "src" / "App.tsx").read_text(encoding="utf-8")
        shell = (ROOT / "jarvis" / "src" / "operator" / "OperatorShell.tsx").read_text(encoding="utf-8")
        self.assertNotIn("needsMission(", app)
        self.assertNotIn("firstLaunch", app)
        self.assertNotIn("firstLaunch", shell)
        self.assertNotIn("Как тебя зовут?", shell)

    def test_backend_risk_is_audit_only(self):
        agent = (ROOT / "core" / "agent.py").read_text(encoding="utf-8")
        self.assertIn("execution_not_paused", agent)
        self.assertIn("confirmation_timeout_sec: float = 0.0", agent)
        self.assertIn("capability risk recorded; autonomous execution continues", agent)

    def test_arbitrary_language_reaches_single_command_entrypoint(self):
        app = (ROOT / "jarvis" / "src" / "App.tsx").read_text(encoding="utf-8")
        self.assertIn("backend.sendCommand(text, [])", app)
        self.assertNotIn("resolve_keyword_tool", app)
        self.assertNotIn("TOOL_CALL", app)


if __name__ == "__main__":
    unittest.main()
Записал контрактные тесты для свободных формулировок и автономного режима. Они проверяют архитектурные инварианты без импорта тяжёлых runtime-зависимостей.

Теперь запускаю их вместе с компиляцией и frontend-сборкой.
