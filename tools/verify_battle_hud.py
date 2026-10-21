"""Whole native viewports and real viewport input, serially on native Windows.

This is development-engine evidence. It does not certify a physical Motorola
X30, final art quality, historical accuracy, or European War 6 equivalence.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

from build_release import ENGINE, P, current_version, source_digest


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--attempt', required=True)
    args = parser.parse_args()
    if not args.attempt.replace('_', '').replace('-', '').isalnum():
        raise SystemExit('Use a simple attempt name.')
    output = P/'reports/battle_hud_native_v0230'/args.attempt
    if output.exists():
        raise SystemExit('Attempt already exists; retain earlier evidence.')
    output.mkdir(parents=True)
    version = current_version()
    driver = P/'tests/battle_hud_test.gd'
    driver_sha, controller_sha = sha(driver), sha(__file__)
    print('BATTLE_HUD_SOURCE_IDENTITY_BEGIN '+version, flush=True)
    identity = source_digest()[0]
    evidence_root = 'res://'+output.relative_to(P).as_posix()
    cases = []
    errors = []
    for resolution, scale, extra, tag in [
        ('1920x1080', '1.0', [], '1920x1080_100_mouse'),
        ('2400x1080', '1.2', ['--mobile-ui-test'], '2400x1080_120_touch'),
        ('1280x720', '1.5', [], '1280x720_150_mouse'),
    ]:
        started = datetime.now(timezone.utc).timestamp()
        log = output/(tag+'.log')
        command = [str(ENGINE), '--path', str(P), '--resolution', resolution,
                   '--position', '0,0', '--script', str(driver), '--',
                   '--ui-scale', scale, '--evidence-root', evidence_root, *extra]
        with log.open('w', encoding='utf-8') as stream:
            run = subprocess.run(command, cwd=P, stdout=stream,
                                 stderr=subprocess.STDOUT, timeout=360)
        report_path = output/tag/'validation.json'
        diagnostic = log.read_text(encoding='utf-8', errors='replace')
        report = json.loads(report_path.read_text(encoding='utf-8')) if report_path.exists() else {}
        valid = (run.returncode == 0 and report.get('passed') and
                 report.get('build_version') == version and
                 not any(text in diagnostic for text in ['SCRIPT ERROR:', '\nERROR:', 'WARNING: ObjectDB']))
        images = []
        for capture in report.get('captures', []):
            path = P/capture['path'].removeprefix('res://')
            fresh = path.stat().st_mtime >= started-2 and sha(path) == capture['sha256']
            if not fresh:
                valid = False
            images.append(dict(path=path.relative_to(P).as_posix(), sha256=sha(path), fresh=fresh))
        if not valid:
            errors.append(tag)
        cases.append(dict(tag=tag, passed=bool(valid), checks=len(report.get('checks', [])),
                          report=report_path.relative_to(P).as_posix(), report_sha256=sha(report_path) if report_path.exists() else None,
                          camera_label_area_fraction=report.get('camera_label_area_fraction'),
                          input_events=report.get('input_events'), input_kind=report.get('input_kind'), images=images))
        print(json.dumps(cases[-1], ensure_ascii=True), flush=True)
        if not valid:
            break
    stable = source_digest()[0] == identity and sha(driver) == driver_sha and sha(__file__) == controller_sha
    if not stable:
        errors.append('source_or_driver_changed_during_run')
    result = dict(passed=not errors and len(cases) == 3, build_version=version,
                  runtime_source_sha256=identity, test_driver_sha256=driver_sha,
                  controller_sha256=controller_sha, source_unchanged_during_tests=stable,
                  created_at_utc=datetime.now(timezone.utc).isoformat(), cases=cases,
                  checks=sum(case['checks'] for case in cases), failures=errors,
                  mode='development_engine_viewport_input', physical_android_device_tested=False,
                  formal_art_approval=False, ew6_parity_claimed=False,
                  manual_compositing=False, original_rasters_changed=False)
    (output/'validation.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print('BATTLE_HUD_RESULT '+str(result['passed'])+' '+str(output/'validation.json'), flush=True)
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
