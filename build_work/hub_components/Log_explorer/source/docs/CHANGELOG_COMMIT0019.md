# Commit0019

## VIMeasure value view
- VIMeasure is displayed as a normalized value table.
- Default columns: Timestamp / Parameter / Value / Unit.
- Wide numeric VIMeasure records are projected to one row per parameter.
- Raw records remain available internally for Investigation charts.

## Viewer layout
- Vertical splitters open with the main table using almost all available height.
- Detail/message panes start collapsed.
- Tables use expanding size policies and compact row heights.
- The large unused lower blank area is removed.

## Context menu
- Copy Cell
- Copy Row
- Copy Timestamp
- Copy Message / Value
- Filter by This Value
- Clear Pane Filter
- Copy Rule Text
- Add to Noise Rule
- Export Selected Row

The menu is applied to QTableView and QTableWidget instances in the Viewer.
