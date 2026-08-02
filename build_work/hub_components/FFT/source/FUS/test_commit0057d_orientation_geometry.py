from pathlib import Path
import ast
import math
import re

source = Path(__file__).with_name("app.py").read_text(encoding="utf-8")
ast.parse(source)

required = [
    'APP_VERSION = "5.7.4 RC1 DICOM Orientation Geometry Fix Commit0057d"',
    "def _dicom_orientation_labels",
    "screen right follows increasing image columns",
    "panel.set_orientation_labels",
    'empty_values = {',
    'display_mode == "both"',
    "PatientPosition",
    "ImageOrientationPatient",
    "ImagePositionPatient",
    "self.raw_preview_cache",
]
for token in required:
    assert token in source, token

assert '"top": "H"' not in re.search(
    r"def _apply_image_orientation\(self\):.*?(?=\n    def |\Z)",
    source,
    re.S,
).group(0)

samples = [{'file': '24-1.dcm', 'PatientPosition': 'HFS', 'ImageOrientationPatient': [-0.0348960664575, 0.9993909468, 1.4561991e-08, -8.34337971e-07, -1.4561991e-08, -0.9999999999996], 'ImagePositionPatient': [-2.856022556936, -145.60236366068, 81.231518097239]}, {'file': '26-9.dcm', 'PatientPosition': 'HFS', 'ImageOrientationPatient': [0.99980051701471, 3.53897481e-05, 0.01997310503357, 0.00261747761339, 0.99114205968824, -0.1327801428223], 'ImagePositionPatient': [-121.03395492908, -152.22532484667, -14.672675805322]}]
assert samples

def normalize(v):
    m = math.sqrt(sum(x*x for x in v))
    return [x/m for x in v]

def label(v):
    items = [
        (abs(v[0]), "L" if v[0] >= 0 else "R"),
        (abs(v[1]), "P" if v[1] >= 0 else "A"),
        (abs(v[2]), "H" if v[2] >= 0 else "F"),
    ]
    items.sort(reverse=True)
    values = [name for mag, name in items if mag >= 0.20]
    return "".join(values[:2] or [items[0][1]])

for record in samples:
    iop = record["ImageOrientationPatient"]
    assert iop and len(iop) == 6
    column_direction = normalize(iop[:3])
    row_direction = normalize(iop[3:])
    edges = {
        "left": label([-x for x in column_direction]),
        "right": label(column_direction),
        "top": label([-x for x in row_direction]),
        "bottom": label(row_direction),
    }
    assert edges["left"] != edges["right"]
    assert edges["top"] != edges["bottom"]

print("Commit0057d DICOM orientation geometry regression: PASS")
