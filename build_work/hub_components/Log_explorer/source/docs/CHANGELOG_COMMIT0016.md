# Commit0016 - Viewer & Investigation UX Stabilization

- VIMeasure remains a built-in RC1 file type and is placed before UNKNOWN.
- Smart Discovery / Viewer sources omit UNKNOWN when it has no supported role.
- Viewer uses lazy row exposure for large datasets.
- VIMeasure uses a value-oriented table with dynamic numeric columns.
- Viewer detail area is hidden by default and tables use the full available height.
- Viewer opens inside the active/parent monitor work area.
- Full row context menu implemented.
- WS/CSA/CGA default Type=Err filter applied and visible.
- Investigation reload/update shows a progress popup.
- Empty investigation sources are not shown.
- Chart controls appear only for series present in loaded data.
- Chart area and Chart modes are omitted when no chartable data exists.
