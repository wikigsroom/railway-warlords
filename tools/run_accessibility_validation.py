"""Exercise actual native UI at minimum and 4K windows, including 150% fonts."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import subprocess
import uuid

from build_release import ENGINE, P, current_version, source_digest


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def main():
    run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8]
    folder = P / 'reports/accessibility' / run_id
    folder.mkdir(parents=True, exist_ok=False)
    runtime = source_digest()[0]
    sources = [P / 'tests/accessibility_native_test.gd', P / 'tests/immutable_state_fingerprint.gd', Path(__file__)]
    records = [{'file': path.relative_to(P).as_posix(), 'sha256': sha(path)} for path in sources]
    profiles = [('minimum_standard', '1280x720', '1.0', False), ('minimum_large_text', '1280x720', '1.5', False), ('4k_large_text', '3840x2160', '1.5', False), ('4k_logical_large_text', '3840x2160', '1.5', True)]
    results = []
    for name, resolution, scale, logical in profiles:
        output = folder / name
        output.mkdir()
        command = [str(ENGINE), '--path', str(P), '--script', 'tests/accessibility_native_test.gd']
        if logical:
            command.insert(1, '--headless')
        else:
            command.extend(['--resolution', resolution, '--position', '-20000,-20000'])
        command.extend(['--', '--qa-session', '--ui-scale', scale, '--expected-window', resolution, '--output-root', str(output)])
        if logical:
            command.append('--logical-viewport')
        log = output / 'native.log'
        with log.open('w', encoding='utf-8') as stream:
            process = subprocess.Popen(command, cwd=P, stdout=stream, stderr=subprocess.STDOUT)
            print('Native accessibility profile:', name, 'PID', process.pid, flush=True)
            try:
                process.wait(timeout=60)
            except subprocess.TimeoutExpired:
                process.terminate()
                process.wait(timeout=10)
        report_path = output / 'result.json'
        report = json.loads(report_path.read_text(encoding='utf-8')) if report_path.is_file() else {}
        diagnostics = log.read_text(encoding='utf-8', errors='replace')
        passed = process.returncode == 0 and report.get('passed', False)
        passed = passed and not any(marker in diagnostics for marker in ('SCRIPT ERROR:', '\nERROR:', 'WARNING: ObjectDB'))
        results.append({'name': name, 'resolution': resolution, 'ui_scale': float(scale), 'passed': passed,
                        'native_pid': process.pid, 'native_exit_code': process.returncode,
                        'checks': len(report.get('checks', [])), 'failures': report.get('failures', []), 'logical_viewport': logical,
                        'report': report_path.relative_to(P).as_posix()})
        print(json.dumps(results[-1], ensure_ascii=False), flush=True)
        if not passed:
            print(diagnostics[-2500:], flush=True)
    unchanged = runtime == source_digest()[0] and all(sha(P / row['file']) == row['sha256'] for row in records)
    artifacts = [{'file': path.relative_to(P).as_posix(), 'sha256': sha(path), 'bytes': path.stat().st_size}
                 for path in sorted(folder.rglob('*')) if path.is_file()]
    evidence = {'passed': unchanged and all(row['passed'] for row in results), 'version': current_version(),
                'created_at_utc': datetime.now(timezone.utc).isoformat(), 'runtime_source_sha256': runtime,
                'native_engine_sha256': sha(ENGINE), 'sources_unchanged_during_run': unchanged, 'sources': records,
                'run_directory': folder.relative_to(P).as_posix(), 'profiles': results, 'artifacts': artifacts,
                'physical_android_device_tested': False,
                'scope': 'Native Windows Godot project at actual 1280x720 and the host-limited 3840x2160 attempt, plus an explicit headless 3840x2160 logical canvas. Real GUI mouse dispatch is used for native profiles; logical 4K verifies layout and input on the full requested canvas but is not a physical 4K display or Android result.'}
    (folder / 'evidence.json').write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding='utf-8')
    # Keep the latest truthfully failing profile at the stable report path too;
    # a missing file would make the 4K hardware limitation invisible.
    (P / 'reports/accessibility_evidence.json').write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'passed': evidence['passed'], 'profiles': len(results), 'checks': sum(row['checks'] for row in results), 'run_directory': evidence['run_directory']}), flush=True)
    raise SystemExit(0 if evidence['passed'] else 1)


if __name__ == '__main__':
    main()
