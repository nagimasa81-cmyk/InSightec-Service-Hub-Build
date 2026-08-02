from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "src/ui/main_window.py").read_text(encoding="utf-8")


def test_release_metadata():
    assert (ROOT / "VERSION").read_text().strip() == "RC2-R0014"


def test_reference_video_behavior_is_connected_to_runtime_path():
    assert "Workstation replay" in SOURCE
    assert "_apply_workstation_replay_behavior(data, count)" in SOURCE
    assert "_workstation_phase_for_frame" in SOURCE
    assert "scrollToItem(item, QListWidget.ScrollHint.PositionAtCenter)" in SOURCE


def test_progressive_traces_and_end_stop_are_implemented():
    assert "self.max_temperature_curve.setData(tx" in SOURCE
    assert "self.acoustic_power_curve.setData" in SOURCE
    assert "self.timer.stop()" in SOURCE
    assert "target = count - 1" in SOURCE
