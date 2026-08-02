from pathlib import Path
import ast
import numpy as np

APP = Path(__file__).with_name("app.py")
SOURCE = APP.read_text(encoding="utf-8")


def _static_method(name):
    tree = ast.parse(SOURCE)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            module = ast.Module(body=[node], type_ignores=[])
            ns = {"np": np}
            exec(compile(ast.fix_missing_locations(module), str(APP), "exec"), ns)
            return ns[name]
    raise AssertionError(name)


def test_real_original_only_exposes_magnitude():
    fn = _static_method("_available_components_for_array")
    assert fn(np.ones((4, 4)), fft=False) == ["Magnitude"]


def test_complex_original_exposes_real_imaginary_phase():
    fn = _static_method("_available_components_for_array")
    data = np.ones((4, 4), dtype=np.complex128) * (1 + 2j)
    assert fn(data, fft=False) == ["Magnitude", "Real", "Imaginary", "Phase"]


def test_fft_exposes_only_supported_components_including_log():
    fn = _static_method("_available_components_for_array")
    assert fn(np.ones((4, 4), dtype=np.complex128), fft=True) == [
        "Magnitude", "Log Magnitude", "Real", "Imaginary", "Phase"
    ]


def test_display_log_magnitude_is_distinct():
    fn = _static_method("_display_component")
    data = np.array([[0 + 0j, 3 + 4j]])
    assert np.allclose(fn(data, "Magnitude"), [[0.0, 5.0]])
    assert np.allclose(fn(data, "Log Magnitude"), np.log1p([[0.0, 5.0]]))


def test_menu_is_generated_from_available_components_not_fixed_list():
    block = SOURCE[SOURCE.index("def _show_component_menu"):SOURCE.index("def mousePressEvent", SOURCE.index("def _show_component_menu"))]
    assert "for component in self.available_components" in block
    assert 'for component in ("Magnitude", "Real", "Imaginary", "Phase")' not in block


def test_component_change_resets_levels():
    block = SOURCE[SOURCE.index("def _set_panel_component"):SOURCE.index("def refresh_images", SOURCE.index("def _set_panel_component"))]
    assert "self.raw_window_level = None" in block
    assert "self.original_window_level = None" in block
