import json

from scripts.sprint14_live_demo import run_demo


def test_real_local_metacognition_live_demo(tmp_path):
    result = run_demo(tmp_path / "live")

    assert result["stale_value"] == "1.0"
    assert result["observed_value"] == "2.0"
    assert result["contradictions"]
    assert result["misleading_action_reported_success"] is True
    assert result["misleading_action_verified"] is False
    assert result["final_verified"] is True
    assert result["selected_repair"] == "atomic_config"
    assert result["second_run_calls"] == ["atomic_config"]
    assert result["second_run_skipped"] == ["cached_provider"]
    assert result["provenance_response"] == "Я проверил это в локальной системе."

    audit = json.loads(open(result["audit_bundle"], encoding="utf-8").read())
    assert audit["failure_episodes"]
    transitions = [item for item in audit["events"] if item["type"] == "belief_transition"]
    assert transitions and "confidence_inputs" in transitions[0]["payload"]
    assert any(item["payload"].get("contradictions") for item in transitions)
    assert any(item["type"] == "strategy_change" for item in audit["events"])
    assert any(item["type"] == "verification" for item in audit["events"])
    assert "reasoning" not in json.dumps(audit, ensure_ascii=False)
