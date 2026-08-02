from types import SimpleNamespace

from orientation_engine import OrientationEngine, DisplayTransform


def ds(iop, ipp=(0, 0, 0), patient_position='HFS'):
    return SimpleNamespace(
        ImageOrientationPatient=iop,
        ImagePositionPatient=ipp,
        PatientPosition=patient_position,
    )


def test_axial_ge_console_orientation():
    result = OrientationEngine().calculate(ds([1, 0, 0, 0, 1, 0]))
    assert result is not None
    assert (result.top, result.bottom, result.left, result.right) == ('A', 'P', 'R', 'L')


def test_conventional_raster_orientation_without_y_inversion():
    result = OrientationEngine().calculate(
        ds([1, 0, 0, 0, 1, 0]),
        DisplayTransform(y_axis_up=False),
    )
    assert (result.top, result.bottom, result.left, result.right) == ('A', 'P', 'R', 'L')


def test_horizontal_flip_tracks_image():
    result = OrientationEngine().calculate(
        ds([1, 0, 0, 0, 1, 0]),
        DisplayTransform(flip_horizontal=True),
    )
    assert (result.left, result.right) == ('L', 'R')


def test_oblique_geometry_has_valid_labels_and_unit_normal():
    result = OrientationEngine().calculate(ds([0.7071, 0.7071, 0, 0, 0, 1]))
    assert result is not None
    assert result.top and result.bottom and result.left and result.right
    length = sum(value * value for value in result.slice_vector) ** 0.5
    assert abs(length - 1.0) < 1e-6
