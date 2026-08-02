from pathlib import Path
import os
import numpy as np

from src.services.planning_data_service import PlanningDataService
from src.services.import_service import ImportService
from src.services.sonication_metadata_service import SonicationMetadataService
from src.services.sonication_timing_service import SonicationTimingService


def test_c0040_static_contracts():
    root=Path(__file__).parents[1]
    main=(root/'src/ui/main_window.py').read_text()
    planning=(root/'src/services/planning_data_service.py').read_text()
    meta=(root/'src/services/sonication_metadata_service.py').read_text()
    assert 'self.right_vertical_split = QSplitter(Qt.Orientation.Vertical)' in main
    assert 'def _draw_color_bar(self, painter, bar, lo, hi):' in main and 'self._display_color(normalized)' in main
    assert 'if sx != 512 or sy != 512' in planning
    assert 'dtype = "<i2" if field == 16 else "<u2"' in planning
    assert '_orientation_from_cosines' in meta
    assert 'parse_ado_rowset(path)' in meta


def test_c0040_real_export_when_available():
    path=os.environ.get('SRE_TEST_EXPORT')
    if not path:
        return
    source=Path(path)
    importer=ImportService(); workspace=importer.open(source)
    try:
        root = next((x.parent for x in workspace.rglob("CtImage.xml")), workspace)
        summary=PlanningDataService().discover(root)
        ct=summary.by_category('PLANNING_CT')
        assert ct, 'No Planning CT assets'
        signed=[a for a in ct if a.field_index==16]
        assert signed and signed[0].dtype=='<i2' and signed[0].width==512
        a=signed[0]
        image=np.fromfile(a.path,dtype=a.dtype).reshape(a.height,a.width)
        assert image.std()>0 and image.min()<0
        timings=SonicationTimingService().read_all(root)
        assert len(timings)>=8 and timings[6].planned_power_w is not None and timings[6].actual_duration_s is not None
    finally:
        importer.release(workspace)
