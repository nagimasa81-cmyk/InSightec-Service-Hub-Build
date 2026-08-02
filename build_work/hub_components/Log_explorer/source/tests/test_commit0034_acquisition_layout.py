from pathlib import Path

root = Path(__file__).resolve().parents[1]
source = (
    root / "foundation" / "investigation.py"
).read_text(encoding="utf-8")

for token in [
    "self.dashboard_splitter = QSplitter(Qt.Vertical)",
    'self.detail_tabs.addTab(self.sonication_table, "Sonication Summary")',
    'self.detail_tabs.addTab(self.events, "Selected Series Events")',
    "self.dashboard_splitter.setSizes([540, 230])",
    "self.chart.setMinimumHeight(360)",
    "self.summary.setMaximumHeight(70)",
    "self.cards.setMaximumHeight(95)",
]:
    assert token in source, token

print("Commit0034 Acquisition chart visibility layout: PASS")
