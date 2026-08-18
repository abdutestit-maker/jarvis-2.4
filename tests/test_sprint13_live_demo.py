from scripts.sprint13_live_demo import run_demo


def test_safe_real_files_live_demo(tmp_path):
    result = run_demo(tmp_path / "demo")

    assert result["verified"] is True
    assert result["acquisition"] == "composed"
    assert result["second_run_acquisition"] == "learned"
    assert result["actual_files"] == ["md/beta.md", "txt/alpha.txt", "txt/gamma.txt"]
    assert result["restart_last_verified"] is True
    assert all(item["addressed"] for item in result["address_recognition"])
    assert not any(item["addressed"] for item in result["false_wakes"])
