from core.dicom_provider import DicomNavigationProvider
from core.display_state import DisplayState


def test_dicom_provider_crosses_group_boundary():
    current = {"value": 1}
    provider = DicomNavigationProvider(
        groups_factory=lambda: [("A", [0, 1]), ("B", [4, 5])],
        current_index=lambda: current["value"],
    )
    result = provider.next()
    assert result is not None
    assert result.series_changed is True
    assert result.current_item == 4
    assert result.location.group_index == 1
    assert result.location.index_in_group == 0


def test_dicom_provider_previous_crosses_group_boundary():
    provider = DicomNavigationProvider(
        groups_factory=lambda: [("A", [0, 1]), ("B", [4, 5])],
        current_index=lambda: 4,
    )
    result = provider.previous()
    assert result is not None
    assert result.series_changed is True
    assert result.current_item == 1
    assert result.location.group_index == 0
    assert result.location.index_in_group == 1


def test_dicom_provider_clamps_at_ends():
    provider = DicomNavigationProvider(
        groups_factory=lambda: [("A", [2, 3])],
        current_index=lambda: 2,
    )
    assert provider.previous().current_item == 2
    assert provider.jump(999).current_item == 3


def test_display_state_normalizes_invalid_values():
    state = DisplayState(mode="invalid", zoom=0, rotation=-90).normalized()
    assert state.mode == "Both"
    assert state.zoom == 0.01
    assert state.rotation == 270
