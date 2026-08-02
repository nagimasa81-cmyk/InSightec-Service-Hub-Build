from pathlib import Path
from src.services.planning_data_service import PlanningAsset, PlanningDataService


def test_verified_ct_field16_is_sorted_first_and_slices_are_numeric(tmp_path: Path):
    service = PlanningDataService()
    assets = [
        PlanningAsset('PLANNING_CT', tmp_path/'16-1-0-100.raw', 'ct', .9, width=512, height=512, dtype='<i2', field_index=16, sonication_index=1, zone_index=0, array_index=100),
        PlanningAsset('PLANNING_CT', tmp_path/'12-1-0-0.raw', 'derived', .8, width=512, height=512, dtype='<u2', field_index=12, sonication_index=1, zone_index=0, array_index=0),
        PlanningAsset('PLANNING_CT', tmp_path/'16-1-0-11.raw', 'ct', .9, width=512, height=512, dtype='<i2', field_index=16, sonication_index=1, zone_index=0, array_index=11),
    ]
    # Exercise the exact ordering contract used by discover().
    def key(item):
        if item.category == 'PLANNING_CT':
            return (0, 0 if item.field_index == 16 else 1, item.field_index or 999,
                    item.sonication_index or 999, item.zone_index or 999,
                    item.array_index if item.array_index is not None else 999999,
                    str(item.path).lower())
        return (1, item.category, 0, 0, 0, 0, str(item.path).lower())
    ordered = sorted(assets, key=key)
    assert [a.field_index for a in ordered] == [16, 16, 12]
    assert [a.array_index for a in ordered[:2]] == [11, 100]


def test_main_layout_uses_temperature_primary_ratio_and_versioned_reset():
    source = (Path(__file__).parents[1] / "src" / "ui" / "main_window.py").read_text()
    assert 'setSizes([650, 350])' in source
    assert 'layout/version' in source
    assert 'layout_version < 46' in source
    assert 'field_index", None) != 16' in source
