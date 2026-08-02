# C0041 Triple Verification

## Check 1 — Source path and parser verification

- Planning CT is restricted to metadata-backed 512 x 512 CtImage rows.
- Field 16 uses signed 16-bit decoding; CT datatype is no longer guessed.
- SonicationSummary, MriImageParams, and ProtocolData use the ADO `z:row` parser.
- Orientation is calculated from MR row/column direction cosines.

## Check 2 — Real export verification: 17-00-24_ANx

- Planning CT image payloads: 351.
- Signed field-16 CT images: 153.
- Signed CT images are 512 x 512, non-constant, and include negative HU-like values.
- Sonication timing rows: 8.
- Sonication 7: planned power 962.000061 W; planned duration 18 s; actual duration 19.053528 s.
- Sonication 7 orientation from direction cosines: Coronal.
- Sonication 7 frequency direction: ROW.

## Check 3 — Display-path and package verification

- Right-side navigator, Temperature/Spectrum, and Power/Score use a non-collapsible vertical splitter.
- Power/Score receives a dedicated viewport instead of conflicting fixed minimum heights.
- XD elements and color bar use the same 256-entry blue/cyan/green/yellow/red LUT.
- `verify_source.py`: VERIFY_SOURCE_OK.
- pytest: 11 passed with the supplied real export enabled.
- All Python sources compile successfully.
- PySide6 runtime rendering could not be launched in this Linux validation container because PySide6 is not installed; Windows EXE visual confirmation remains required.
