from __future__ import annotations

from core.intelligence import UniversalIntake
from core.operator import SetupMission
from core.router.intent_router import resolve_keyword_tool


def test_system_status_is_a_deterministic_system_intent() -> None:
    assert resolve_keyword_tool("Системный статус") == "system"
    contract = UniversalIntake().classify("Системный статус")
    assert contract.intent_family == "operate"


def test_setup_mission_exposes_one_verified_pipeline() -> None:
    mission = SetupMission.__new__(SetupMission)
    assert mission.pipeline == (
        "understand", "trusted_source", "verify_publisher", "verify_hash",
        "verify_signature", "install", "launch", "inspect",
        "desired_state_diff", "configure", "observe", "verify", "repair", "learn",
    )
