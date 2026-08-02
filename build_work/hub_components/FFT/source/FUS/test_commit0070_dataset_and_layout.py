from pathlib import Path
import ast
import numpy as np

SOURCE_PATH = Path(__file__).with_name('app.py')
SOURCE = SOURCE_PATH.read_text(encoding='utf-8')
TREE = ast.parse(SOURCE)


def test_version_and_atomic_workspace_path():
    assert 'Commit0070' in SOURCE
    assert 'def _render_current_image_atomically' in SOURCE
    assert 'self._render_current_image_atomically()' in SOURCE
    assert 'setUpdatesEnabled(False)' in SOURCE


def test_default_geometry_uses_real_splitter_width():
    assert 'width = max(int(self.image_splitter.width()), 2)' in SOURCE
    assert 'self.image_splitter.setSizes([half, width - half])' in SOURCE


def test_directional_detector_keeps_central_axes_available():
    assert 'def _directional_kspace_line_features' in SOURCE
    assert 'only a small DC box is excluded' in SOURCE
    assert 'directional_rows' in SOURCE
    assert 'directional_cols' in SOURCE


def test_periodic_stripe_has_strong_directional_kspace_line():
    namespace = {'np': np}
    # Load only the static/class helpers without importing the Qt application.
    class_node = next(n for n in TREE.body if isinstance(n, ast.ClassDef) and n.name == 'MainWindow')
    wanted = {'_robust_zscore', '_directional_kspace_line_features'}
    nodes = [n for n in class_node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name in wanted]
    mini = ast.Module(body=[ast.ClassDef(name='Detector', bases=[], keywords=[], body=nodes, decorator_list=[])], type_ignores=[])
    ast.fix_missing_locations(mini)
    exec(compile(mini, '<detector>', 'exec'), namespace)
    Detector = namespace['Detector']
    rows = cols = 256
    yy, xx = np.indices((rows, cols))
    image = np.exp(-(((xx-cols/2)/45)**2 + ((yy-rows/2)/55)**2))
    image += 0.35 * np.sin(2*np.pi*yy/11.0)
    frequency = np.abs(np.fft.fftshift(np.fft.fft2(image)))
    features = Detector._directional_kspace_line_features(frequency)
    assert features['maximum'] >= 7.0
    assert features['rows'] or features['cols']
