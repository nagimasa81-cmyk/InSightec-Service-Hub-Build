from core.dicom_provider import DicomNavigationProvider
from core.raw_provider import ExplorerNavigationProvider


class Item:
    def __init__(self, name, parent):
        self.name = name
        self._parent = parent

    def parent(self):
        return self._parent


def test_dicom_next_reports_series_change():
    provider = DicomNavigationProvider(
        groups_factory=lambda: [("S1", [0, 1]), ("S2", [4, 5])],
        current_index=lambda: 1,
    )
    result = provider.next()
    assert result is not None
    series_changed, current_item = result
    assert series_changed is True
    assert current_item == 4
    assert result.location.group_index == 1
    assert result.location.index_in_group == 0


def test_dicom_previous_reports_series_change():
    provider = DicomNavigationProvider(
        groups_factory=lambda: [("S1", [0, 1]), ("S2", [4, 5])],
        current_index=lambda: 4,
    )
    result = provider.previous()
    assert result is not None
    assert result.series_changed is True
    assert result.current_item == 1
    assert result.location.index_in_group == 1


def test_dicom_move_inside_series_does_not_report_change():
    provider = DicomNavigationProvider(
        groups_factory=lambda: [("S1", [0, 1, 2]), ("S2", [4])],
        current_index=lambda: 1,
    )
    result = provider.next()
    assert result is not None
    assert result.series_changed is False
    assert result.current_item == 2


def test_raw_next_crosses_folder_boundary():
    folder_a, folder_b = object(), object()
    a1, a2 = Item("a1", folder_a), Item("a2", folder_a)
    b1, b2 = Item("b1", folder_b), Item("b2", folder_b)
    provider = ExplorerNavigationProvider(
        items_factory=lambda: [a1, a2, b1, b2],
        current_item=lambda: a2,
    )
    result = provider.next()
    assert result is not None
    assert result.series_changed is True
    assert result.current_item is b1
    assert result.location.index_in_group == 0


def test_raw_previous_crosses_folder_boundary():
    folder_a, folder_b = object(), object()
    a1, a2 = Item("a1", folder_a), Item("a2", folder_a)
    b1, b2 = Item("b1", folder_b), Item("b2", folder_b)
    provider = ExplorerNavigationProvider(
        items_factory=lambda: [a1, a2, b1, b2],
        current_item=lambda: b1,
    )
    result = provider.previous()
    assert result is not None
    assert result.series_changed is True
    assert result.current_item is a2
    assert result.location.index_in_group == 1
