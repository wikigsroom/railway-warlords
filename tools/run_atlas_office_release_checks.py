"""Run the frozen native release checks; keep an explicit external exit receipt."""
from datetime import datetime, timezone
import json
import os
import subprocess
import sys
from build_release import P, ROOT, ENGINE, current_version, source_digest


def main():
    version = current_version()
    before = source_digest()[0]
    progress = ROOT / 'output/atlas_office_pipeline_progress.json'
    record = dict(version=version, pid=os.getpid(), runtime_source_sha256=before,
                  started_at_utc=datetime.now(timezone.utc).isoformat(), terminal=False, stages=[])

    def save():
        progress.write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    scripts = ['run_validation', 'seal_regression_dependencies', 'validate_project', 'build_release',
               'archive_native_review', 'run_final_ui_refinement_qa']
    stages = [('import', [str(ENGINE), '--headless', '--path', str(P), '--editor', '--import', '--quit'])]
    stages.extend((name, [sys.executable, '-X', 'utf8', str(P / 'tools' / (name + '.py'))]) for name in scripts)
    save()
    for name, command in stages:
        record['current_stage'] = name
        save()
        print('RELEASE_CHECK_BEGIN ' + name, flush=True)
        log = P / 'reports' / ('atlas_office_pipeline_' + name + '_v' + version.replace('.', '') + '.log')
        with log.open('w', encoding='utf-8') as stream:
            result = subprocess.run(command, cwd=P, stdout=stream, stderr=subprocess.STDOUT)
        row = dict(name=name, exit_code=result.returncode, log=log.relative_to(P).as_posix())
        record['stages'].append(row)
        if result.returncode:
            record.update(terminal=True, passed=False, finished_at_utc=datetime.now(timezone.utc).isoformat())
            save()
            print('RELEASE_CHECK_FAILED ' + name, flush=True)
            return result.returncode
        print('RELEASE_CHECK_PASS ' + name, flush=True)
        save()
    after = source_digest()[0]
    record.update(terminal=True, passed=after == before, final_runtime_source_sha256=after,
                  finished_at_utc=datetime.now(timezone.utc).isoformat())
    save()
    print('RELEASE_CHECK_COMPLETE ' + str(record['passed']), flush=True)
    return 0 if record['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
