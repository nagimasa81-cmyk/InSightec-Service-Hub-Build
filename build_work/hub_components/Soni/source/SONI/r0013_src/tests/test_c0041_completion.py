from pathlib import Path
import numpy as np
from src.services.sonication_metadata_service import SonicationMetadataService
from src.services.planning_data_service import PlanningDataService

def test_no_watt_to_percent_fallback():
    text=(Path(__file__).parents[1]/"src/ui/main_window.py").read_text(encoding="utf-8")
    assert "np.full(tx.shape,float(self.current.planned_power_w)" not in text
    assert "Measured Power % unavailable" in text
    assert "setYRange(0.0, 110.0" in text

def test_xd_raster_uses_shared_lut():
    text=(Path(__file__).parents[1]/"src/ui/main_window.py").read_text(encoding="utf-8")
    assert "def _draw_color_bar(self, painter, bar, lo, hi):" in text
    assert "self._display_color(normalized)" in text
    assert "painter.drawLine(left, y, right, y)" in text

def test_ct_metadata_not_display_image(tmp_path):
    (tmp_path/"CtImage.xml").write_text("<root/>",encoding="utf-8")
    (tmp_path/"CtVolumeData.xml").write_text("<root/>",encoding="utf-8")
    summary=PlanningDataService().discover(tmp_path)
    assert not summary.by_category("PLANNING_CT")
    assert len(summary.by_category("PLANNING_METADATA")) == 2
