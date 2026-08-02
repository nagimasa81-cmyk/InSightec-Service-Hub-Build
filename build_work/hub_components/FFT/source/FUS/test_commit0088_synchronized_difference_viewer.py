import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import numpy as np
from PySide6.QtWidgets import QApplication
from app import CompensationComparisonDialog


def _app():
    return QApplication.instance() or QApplication([])


def test_difference_arrays_are_visible_in_gui_panels():
    _app()
    before=np.zeros((16,16),float); before[6:10,6:10]=2
    after=before.copy(); after[7:9,7:9]=0.5
    diff=np.abs(after-before)
    dlg=CompensationComparisonDialog(before,after,diff,diff,np.zeros_like(diff))
    assert np.asarray(dlg.before_panel.image_item.image).shape == (16,16)
    assert np.asarray(dlg.after_panel.image_item.image).shape == (16,16)
    assert np.asarray(dlg.diff_image_panel.image_item.image).max() > 0
    assert len(dlg.panels) == 5
    dlg.close()


def test_before_after_common_levels_and_cursor_sync():
    _app()
    before=np.arange(256,dtype=float).reshape(16,16)
    after=before*0.8
    diff=np.abs(after-before)
    dlg=CompensationComparisonDialog(before,after,diff,diff,diff)
    assert dlg.before_panel.current_levels == dlg.after_panel.current_levels
    dlg._sync_cursor(dlg.before_panel,4,9)
    assert int(round(dlg.after_panel.hline.value())) == 4
    assert int(round(dlg.after_panel.vline.value())) == 9
    assert int(round(dlg.diff_fft_panel.hline.value())) == 4
    dlg.close()
