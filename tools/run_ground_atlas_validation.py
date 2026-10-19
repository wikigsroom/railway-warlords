"""Validate the quiet-ground release with native Windows tools and full evidence."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
import os
import subprocess
import sys
from build_release import P, ROOT, current_version, source_digest


def main():
    version = current_version()
    if version != '0.2.25':
        raise SystemExit('This validation run targets 0.2.25.')
    progress = ROOT / 'output/ground_atlas_validation_progress.json'
    state = dict(version=version, pid=os.getpid(), terminal=False, stages=[],
                 runtime_source_sha256=source_digest()[0],
                 started_at_utc=datetime.now(timezone.utc).isoformat())

    def save():
        pending = progress.with_suffix('.tmp')
        pending.write_text(json.dumps(state, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        pending.replace(progress)

    def run(name, extra=()):
        log = P / 'reports' / ('ground_atlas_pipeline_' + name + '_v0225.log')
        print('VALIDATION_BEGIN ' + name, flush=True)
        started = datetime.now(timezone.utc).isoformat()
        with log.open('w', encoding='utf-8') as stream:
            result = subprocess.run([sys.executable, '-X', 'utf8', 'tools/' + name + '.py', *extra],
                                    cwd=P, stdout=stream, stderr=subprocess.STDOUT)
        print('VALIDATION_' + ('PASS ' if result.returncode == 0 else 'FAILED ') + name, flush=True)
        return dict(name=name, exit_code=result.returncode, log=log.relative_to(P).as_posix(),
                    started_at_utc=started, finished_at_utc=datetime.now(timezone.utc).isoformat())

    def failed():
        state.update(terminal=True, passed=False, finished_at_utc=datetime.now(timezone.utc).isoformat())
        save()
        return 1

    state['current_stage'] = 'native_exports_and_rule_regressions'
    save()
    # These two read the frozen runtime independently. Rule fixtures write only
    # reports; export writes only platform builds and its own export receipts.
    with ThreadPoolExecutor(max_workers=2) as pool:
        jobs = [pool.submit(run, name) for name in ['build_release', 'run_validation']]
        for job in as_completed(jobs):
            state['stages'].append(job.result())
            save()
    if any(row['exit_code'] for row in state['stages']):
        return failed()
    steps = [('seal_regression_dependencies', ()), ('validate_project', ()),
             ('audit_ground_macros', ()),
             ('archive_native_review', ('--review', 'atlas_office_native_review.json')),
             ('verify_ground_continuity', ()), ('run_final_ui_refinement_qa', ())]
    for name, extra in steps:
        state['current_stage'] = name
        save()
        state['stages'].append(run(name, extra))
        save()
        if state['stages'][-1]['exit_code']:
            return failed()
    final = source_digest()[0]
    if final != state['runtime_source_sha256']:
        state['failure'] = 'Runtime changed during validation'
        return failed()
    state.update(terminal=True, passed=True, final_runtime_source_sha256=final,
                 finished_at_utc=datetime.now(timezone.utc).isoformat())
    save()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
