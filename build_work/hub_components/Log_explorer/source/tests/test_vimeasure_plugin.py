"""Standalone validation for the VIMeasure File Type plugin ZIP.

Does not require PySide6 and can run in CI before building the EXE.
"""
import json
import re
import sys
import zipfile
from pathlib import Path


def validate(plugin_zip: Path) -> int:
    errors = []
    if not plugin_zip.exists():
        print(f'SKIP: optional VIMeasure plugin ZIP not bundled: {plugin_zip}')
        return 0
    with zipfile.ZipFile(plugin_zip, 'r') as zf:
        names = set(zf.namelist())
        required = {'manifest.json','parser.json','viewer_defaults.json','investigation_profile.json','tests/test_report.json'}
        missing = sorted(required - names)
        if missing:
            errors.append('Missing files: ' + ', '.join(missing))
        manifest = json.loads(zf.read('manifest.json'))
        parser = json.loads(zf.read('parser.json'))
        viewer = json.loads(zf.read('viewer_defaults.json'))
        investigation = json.loads(zf.read('investigation_profile.json'))
        report = json.loads(zf.read('tests/test_report.json'))
        if manifest.get('id') != 'vimeasure': errors.append('manifest id must be vimeasure')
        if 'VIMeasure_*.txt' not in manifest.get('patterns', []): errors.append('missing VIMeasure filename pattern')
        if parser.get('format') != 'structured_whitespace': errors.append('wrong parser format')
        try:
            re.compile(parser.get('header_line_regex',''))
            re.compile(parser.get('data_line_regex',''))
        except Exception as exc:
            errors.append('invalid regex: ' + str(exc))
        if 'Timestamp' not in viewer.get('default_visible_columns', []): errors.append('Timestamp not visible by default')
        if 'sonication' not in investigation.get('profiles', []): errors.append('not registered for sonication')
        if not report.get('passed'): errors.append('embedded parser tests did not pass')
        sample_names = [n for n in names if n.startswith('sample/') and n.lower().endswith('.txt')]
        if len(sample_names) < 2: errors.append('at least two sample logs required')
    if errors:
        print('FAIL')
        for e in errors: print('-', e)
        return 1
    print('PASS:', plugin_zip.name)
    print('Embedded samples:', len(sample_names))
    print('Embedded parsed rows:', sum(x.get('parsed_rows',0) for x in report.get('results',[])))
    return 0


if __name__ == '__main__':
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / 'sample_plugins' / 'VIMeasure_FileType_Update_v1_0_0.plugin.zip'
    raise SystemExit(validate(target))
