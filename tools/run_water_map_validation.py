"""Validate the water/grid revision on native Windows and signed Android."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
import os
import subprocess
import sys
from build_release import P, ROOT, current_version, source_digest, ENGINE


def main():
    if current_version() != '0.2.27':
        raise SystemExit('This pipeline targets 0.2.27.')
    progress = ROOT / 'output/water_map_validation_progress.json'
    state = dict(version=current_version(), pid=os.getpid(), terminal=False, stages=[],
        runtime_source_sha256=source_digest()[0], started_at_utc=datetime.now(timezone.utc).isoformat())

    def save():
        pending = progress.with_suffix('.tmp')
        pending.write_text(json.dumps(state, indent=2) + '\n', encoding='utf-8')
        pending.replace(progress)

    def run(name, extra=(), native=False):
        log = P / 'reports' / ('coast_geometry_native.log' if native else 'water_validation_' + name + '.log')
        command = [str(ENGINE), '--headless', '--path', str(P), '--script', 'res://tests/coast_geometry_test.gd'] if native else [sys.executable, '-X', 'utf8', 'tools/' + name + '.py', *extra]
        print('WATER_VALIDATION_BEGIN ' + name, flush=True)
        started = datetime.now(timezone.utc).isoformat()
        with log.open('w', encoding='utf-8') as out:
            result = subprocess.run(command, cwd=P, stdout=out, stderr=subprocess.STDOUT)
        print('WATER_VALIDATION_' + ('PASS ' if result.returncode == 0 else 'FAILED ') + name, flush=True)
        return dict(name=name, exit_code=result.returncode, log=log.relative_to(P).as_posix(),
            started_at_utc=started, finished_at_utc=datetime.now(timezone.utc).isoformat())

    def finish(passed):
        state.update(terminal=True, passed=passed, finished_at_utc=datetime.now(timezone.utc).isoformat())
        save()
        return 0 if passed else 1

    state['current_stage'] = 'exports_and_regressions'
    save()
    with ThreadPoolExecutor(max_workers=2) as pool:
        jobs = [pool.submit(run, 'build_release'), pool.submit(run, 'run_validation')]
        for job in as_completed(jobs):
            state['stages'].append(job.result());save()
    if any(row['exit_code'] for row in state['stages']):
        return finish(False)
    steps = [('coast_geometry_test', (), True), ('seal_coast_native_geometry', (), False),
        ('seal_regression_dependencies', (), False), ('validate_project', (), False),
        ('audit_ground_macros', (), False), ('verify_ground_continuity', (), False),
        ('verify_water_continuity', (), False), ('run_final_ui_refinement_qa', (), False),
        ('capture_coast_detail', (), False), ('capture_water_maps', (), False),
        ('audit_coast_scope', (), False), ('audit_water_map_scope', (), False)]
    for name, extra, native in steps:
        state['current_stage'] = name;save()
        state['stages'].append(run(name, extra, native));save()
        if state['stages'][-1]['exit_code']:
            return finish(False)
    if source_digest()[0] != state['runtime_source_sha256']:
        state['failure'] = 'Runtime source changed during validation'
        return finish(False)
    return finish(True)


if __name__ == '__main__':
    raise SystemExit(main())
