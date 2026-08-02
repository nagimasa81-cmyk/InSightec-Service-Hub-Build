from pathlib import Path
import json

text = Path('app.py').read_text(encoding='utf-8')
assert 'def _raw_compensation_diagnostic' in text
assert 'raw_comp_analysis=self._raw_compensation_diagnostic(actual_raw)' in text
assert 'def run_artifact_diag_auto_analysis' in text
assert 'self.tabs.setCurrentIndex(3)' in text
assert 'Quick Spike Detect — Work in Progress' in text
assert 'Other Tabs — Work in Progress' in text
meta=json.loads(Path('version.json').read_text())
assert meta['commit']=='0120' and meta['version']=='5.49.0'
print('Commit0120 focused checks: PASS')
