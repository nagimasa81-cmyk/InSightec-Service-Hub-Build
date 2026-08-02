import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import pytest
pytest.importorskip('PySide6')
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QTreeWidget, QTreeWidgetItem

from navigation_controller import NavigationController


def _item(parent, text, data):
    node = QTreeWidgetItem([text])
    node.setData(0, Qt.UserRole, data)
    parent.addChild(node)
    return node


def test_provider_uses_exam_series_tree_order_for_boundary_navigation():
    app = QApplication.instance() or QApplication([])
    tree = QTreeWidget()
    root = QTreeWidgetItem(['DICOM'])
    tree.addTopLevelItem(root)
    patient = _item(root, 'Patient', ('patient', 'p'))
    exam = _item(patient, 'Exam', ('exam', 'study'))
    series_a = _item(exam, 'Series A', ('series', 'A'))
    _item(series_a, 'A1', ('dicom', 0))
    a2 = _item(series_a, 'A2', ('dicom', 1))
    series_b = _item(exam, 'Series B', ('series', 'B'))
    b1 = _item(series_b, 'B1', ('dicom', 2))
    _item(series_b, 'B2', ('dicom', 3))
    tree.setCurrentItem(a2)

    class Window:
        pass

    window = Window()
    window.tree = tree
    window.slice_index = 1
    controller = NavigationController(window)
    provider = controller._dicom_provider()

    result = provider.next()
    assert result is not None
    assert result.series_changed is True
    assert result.current_item == 2

    window.slice_index = 2
    tree.setCurrentItem(b1)
    result = controller._dicom_provider().previous()
    assert result is not None
    assert result.series_changed is True
    assert result.current_item == 1
