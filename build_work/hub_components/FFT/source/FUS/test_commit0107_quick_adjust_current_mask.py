from pathlib import Path
import ast
import numpy as np

ROOT = Path(__file__).resolve().parent
APP = (ROOT / "app.py").read_text(encoding="utf-8")
AUTO = (ROOT / "core" / "auto_correct.py").read_text(encoding="utf-8")
HYBRID = (ROOT / "core" / "hybrid_compensation.py").read_text(encoding="utf-8")

def test_syntax():
    ast.parse(APP); ast.parse(AUTO); ast.parse(HYBRID)

def test_recalculate_uses_current_mask_only():
    block = APP.split("def recalculate_quick_adjust_once",1)[1].split("def restore_auto_compensation_result",1)[0]
    assert "recalculate_with_mask(" in block
    assert "auto_correct_with_retry(" not in block
    assert "auto_correct_with_retry(" not in block
    assert "active_mask" in block

def test_explicit_mask_is_authoritative():
    assert "if mask is None:" in HYBRID
    assert 'stats={"source": "explicit_mask"}' in HYBRID

def test_one_pass_function_has_no_detection_or_retry():
    block = AUTO.split("def recalculate_with_mask",1)[1].split("AUTO_RETRY_TRIALS",1)[0]
    assert "detect_artifacts(" not in block
    assert "auto_correct_with_retry(" not in block
    assert "compensate(" in block

def test_current_mask_preserved_runtime():
    from core.auto_correct import recalculate_with_mask
    k = np.zeros((16,16), dtype=np.complex128)
    k[8,8] = 100
    k[2,3] = 25
    m = np.zeros((16,16), dtype=bool); m[2,3] = True
    r = recalculate_with_mask(k,m,removal=60,detail=75,protection=75)
    assert np.array_equal(r.mask,m)
    assert r.metrics["mask_pixels"] == 1.0
