# RC1-C0041 Triple Verified Data Binding

- Restrict Planning CT to metadata-backed 512x512 CT families; decode field 16 as signed CT/HU data.
- Parse only real ADO row records and derive orientation from MR direction cosines.
- Replace over-constrained right layout with a vertical splitter so Power/Score has a visible plot viewport.
- Use one 256-entry high-contrast LUT for XD elements and the color bar.
- Add real-data regression tests for CT, metadata, layout, and LUT.
