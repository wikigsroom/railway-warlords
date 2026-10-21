"""Current-source cinema layout checks, retaining every earlier attempt."""
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
    output = P/'reports/battle_hud_cinema_v0230'/args.attempt
    if output.exists():
        raise SystemExit('Evidence attempt already exists.')
    output.mkdir(parents=True)
    driver = P/'tests/hud_native_test.gd'
    driver_sha, controller_sha = sha(driver), sha(__file__)
    identity = source_digest()[0]
    evidence_root = 'res://'+output.relative_to(P).as_posix()
    cases = []
    for resolution, scale, tag in [('1920x1080', '1.0', '1920x1080_100'),
                                   ('1280x720', '1.5', '1280x720_150')]:
        with (output/(tag+'.log')).open('w', encoding='utf-8') as log:
            run = subprocess.run([str(ENGINE), '--path', str(P), '--resolution', resolution,
                                  '--position', '0,0', '--script', str(driver), '--',
                                  '--ui-scale', scale, '--evidence-root', evidence_root],
                                 cwd=P, stdout=log, stderr=subprocess.STDOUT, timeout=420)
        path = output/tag/'validation.json'
        report = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
        diagnostic = (output/(tag+'.log')).read_text(encoding='utf-8', errors='replace')
        passed = run.returncode == 0 and report.get('passed') and report.get('build_version') == current_version() and not any(marker in diagnostic for marker in ['SCRIPT ERROR:', '\nERROR:', 'WARNING: ObjectDB'])
        images = [dict(path=image.relative_to(P).as_posix(), sha256=sha(image)) for image in sorted((output/tag).glob('*.png'))]
        cases.append(dict(tag=tag, passed=bool(passed), checks=len(report.get('checks', [])),
                          report=path.relative_to(P).as_posix(), report_sha256=sha(path) if path.exists() else None,
                          legal_published_commands=report.get('legal_published_commands'), images=images))
        print(json.dumps({key: value for key, value in cases[-1].items() if key != 'images'}), flush=True)
        if not passed:
            break
    stable = source_digest()[0] == identity and sha(driver) == driver_sha and sha(__file__) == controller_sha
    result = dict(passed=stable and len(cases) == 2 and all(case['passed'] for case in cases),
                  build_version=current_version(), runtime_source_sha256=identity,
                  test_driver_sha256=driver_sha, controller_sha256=controller_sha,
                  source_unchanged_during_tests=stable, checks=sum(case['checks'] for case in cases),
                  cases=cases, created_at_utc=datetime.now(timezone.utc).isoformat(),
                  mode='development_engine_legal_campaign_commands',
                  physical_android_device_tested=False, formal_animation_art_approval=False,
                  raw_full_viewports=True, manual_compositing=False)
    (output/'validation.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print('BATTLE_CINEMA_RESULT '+str(result['passed']), flush=True)
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
