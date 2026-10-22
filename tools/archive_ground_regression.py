"""Archive fresh review-copy regressions without replacing the 0.2.35 reports."""
from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import sys

P = Path(__file__).resolve().parents[1]
R = P / 'reports/geographic_ground_v0237'
STAGE = P.parents[1] / 'game/railway_warlords_review_0237'


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--attempt', default='01')
    args = parser.parse_args()
    sys.path.insert(0, str(STAGE / 'tools'))
    from run_validation import CHECKS
    seal_path = R / 'preview_stage01.json'
    seal = json.loads(seal_path.read_bytes())
    creation = datetime.fromisoformat(seal['created_at_utc']).timestamp()
    out = R / ('regression' + args.attempt)
    if out.exists():
        raise FileExistsError(out)
    changed_file_checks = 0
    fresh_code_checks = 0
    for name, expected in seal['file_sha256'].items():
        path = STAGE / name
        retained = name.startswith('assets/') and path.stat().st_mtime <= creation
        if not retained:
            assert sha(path) == expected, 'Sealed regression input changed: ' + name
            changed_file_checks += 1
        if path.suffix in ['.gd', '.tscn', '.gdshader']:
            fresh_code_checks += 1
    metadata_path = STAGE / 'reports/sample_state_v2.json'
    metadata = json.loads(metadata_path.read_bytes())
    fingerprint = metadata['content_hash']
    assert fingerprint == '1f7e449dc80b289ab5274fda5636519d1e3a320062d04f95374669302b754256'
    rows = []
    files = [metadata_path, STAGE / 'reports/export_metadata_validation.log']
    for name in CHECKS:
        report = STAGE / 'reports' / ('rule_tests.json' if name == 'run_tests' else name.removesuffix('_test')+'_tests.json')
        log = STAGE / 'reports' / (name+'_v0237.log')
        assert min(report.stat().st_mtime, log.stat().st_mtime) >= creation
        diagnostic = log.read_text(encoding='utf-8', errors='replace')
        assert 'SCRIPT ERROR:' not in diagnostic and '\nERROR:' not in diagnostic
        value = json.loads(report.read_bytes())
        checks = value['checks']
        assert checks and not value.get('failed', 0) and not value.get('failures', [])
        assert value.get('content_hash', fingerprint) == fingerprint
        assert all(not isinstance(c, dict) or c.get('passed', True) for c in checks)
        if 'passed' in value:
            assert value['passed'] is True or value['passed'] == len(checks)
        rows.append(dict(id=name, passed=True, checks=len(checks),
                         report=report.name, report_sha256=sha(report),
                         log=log.name, log_sha256=sha(log)))
        files.extend([report, log])
    assert len(rows) == 30
    export_path = R / 'preview_export01.json'
    export = json.loads(export_path.read_bytes())
    assert export['passed'] and export['stage_copy_receipt_sha256'] == sha(seal_path)
    out.mkdir(exist_ok=False)
    for path in files:
        shutil.copyfile(path, out / path.name)
        assert sha(out / path.name) == sha(path)
    engine = P.parents[1] / '.toolchain/godot/Godot_v4.7.2-stable_win64_console.exe'
    result = dict(passed=True, version='0.2.37', channel='development_review',
                  completed_at_utc=datetime.now(timezone.utc).isoformat(),
                  controller_sha256=sha(__file__), engine_sha256=sha(engine),
                  stage_copy_receipt_sha256=sha(seal_path), export_receipt_sha256=sha(export_path),
                  runtime_source_merkle_sha256=export['runtime_source_merkle_sha256'],
                  source_identity_method='Complete copy SHA256 seal, fresh non-art and later-touched-file SHA256; immutable-art copy seal retained',
                  freshly_checked_nonretained_files=changed_file_checks,
                  code_or_scene_files_in_seal=fresh_code_checks,
                  content_hash=fingerprint, groups=len(rows), checks=sum(r['checks'] for r in rows),
                  reports=rows, previous_release_reports_replaced=False,
                  formal_art_approval=False, physical_android_device_tested=False)
    with (out / 'validation.json').open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2); stream.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k!='reports'}), flush=True)


if __name__ == '__main__':
    main()
