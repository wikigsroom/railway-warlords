"""Continue from two verified exports and all 30 regressions; rerun retained native gates."""
from datetime import datetime, timezone
import argparse
import json
import subprocess
import sys

from build_release import ENGINE, P, ROOT, current_version, source_digest
from package_delivery import read, require, sha


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--resume', action='store_true', help='Continue only after a recorded terminal failure of the same frozen build')
    args = parser.parse_args()
    require(current_version() == '0.2.29', 'This pipeline targets 0.2.29')
    runtime = source_digest()[0]
    exports = read(P / 'reports/export_results.json')
    for target, filename in [('windows', 'RailwayWarlords.exe'), ('android', 'RailwayWarlords.apk')]:
        row = next(r for r in exports if r['target'] == target)
        require(row['export_verified'] and row['runtime_source_sha256'] == runtime
            and row['sha256'] == sha(P / 'build' / target / filename), 'Current verified export required')
    progress = ROOT / 'output/map_composition_validation_progress.json'
    state = dict(version=current_version(), terminal=False, stages=[], runtime_source_sha256=runtime,
        started_at_utc=datetime.now(timezone.utc).isoformat())

    def save():
        pending = progress.with_suffix('.tmp')
        pending.write_text(json.dumps(state, indent=2) + '\n', encoding='utf-8')
        pending.replace(progress)

    steps = [
        ('seal_regression_dependencies', ()), ('coast_geometry_test', ()),
        ('seal_coast_native_geometry', ()), ('validate_project', ()), ('audit_ground_macros', ()),
        ('verify_ground_continuity', ()), ('verify_water_continuity', ()),
        ('run_final_ui_refinement_qa', ()), ('capture_commander_roster', ()),
        ('capture_coast_detail', ()), ('capture_water_maps', ()),
        ('audit_commander_scope', ()), ('record_commander_performance', ()),
        ('audit_map_composition', ()),
        ('capture_map_composition', ('--expected-content-hash', 'd9932b5aa389f0a482bf3def34201b14209071584bb4e06dc5f2c255dd010ef6')),
        ('seal_map_composition', ()),
    ]
    first_step = 0
    if args.resume:
        previous = read(progress)
        require(previous.get('terminal') and previous.get('passed') is False,
            'Resume requires a terminal failed attempt, never a live or completed run')
        require(previous.get('version') == current_version()
            and previous.get('runtime_source_sha256') == runtime, 'The failed attempt must use these exact frozen sources')
        prior_stages = previous.get('stages', [])
        require(prior_stages and prior_stages[-1]['exit_code'] != 0,
            'A concrete failed stage is required')
        prefix = prior_stages[:-1]
        require(len(prefix) < len(steps) and all(row['exit_code'] == 0
            and row['name'] == steps[index][0] for index, row in enumerate(prefix)),
            'Only the recorded, successful ordered prefix can be retained')
        first_step = len(prefix)
        require(prior_stages[-1]['name'] == steps[first_step][0], 'Resume must start at the failed stage')
        state = previous
        state.setdefault('resume_history', []).append(dict(
            failed_stage=prior_stages[-1], resumed_at_utc=datetime.now(timezone.utc).isoformat(),
            runtime_source_sha256=runtime, windows_and_android_binaries_rehashed=True))
        state.update(terminal=False, stages=prefix)
        state.pop('passed', None)
        state.pop('finished_at_utc', None)
    for name, extra in steps[first_step:]:
        state['current_stage'] = name
        save()
        log = P / 'reports' / ('coast_geometry_native.log' if name == 'coast_geometry_test' else 'composition_validation_' + name + '.log')
        command = [str(ENGINE), '--headless', '--path', str(P), '--script', 'res://tests/coast_geometry_test.gd'] if name == 'coast_geometry_test' else [sys.executable, '-X', 'utf8', 'tools/' + name + '.py', *extra]
        print('COMPOSITION_VALIDATION_BEGIN ' + name, flush=True)
        started = datetime.now(timezone.utc).isoformat()
        with log.open('w', encoding='utf-8') as out:
            result = subprocess.run(command, cwd=P, stdout=out, stderr=subprocess.STDOUT)
        state['stages'].append(dict(name=name, exit_code=result.returncode, log=log.relative_to(P).as_posix(),
            started_at_utc=started, finished_at_utc=datetime.now(timezone.utc).isoformat()))
        save()
        print('COMPOSITION_VALIDATION_' + ('PASS ' if result.returncode == 0 else 'FAILED ') + name, flush=True)
        if result.returncode:
            state.update(terminal=True, passed=False)
            save()
            return 1
    require(source_digest()[0] == runtime, 'Frozen source changed during native validation')
    state.update(terminal=True, passed=True, finished_at_utc=datetime.now(timezone.utc).isoformat())
    save()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
