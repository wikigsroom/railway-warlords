"""Measure real background-rule handoffs in a native window; never a phone claim."""
import argparse
import json
import subprocess
from build_release import P, ENGINE, current_version, source_digest
from package_delivery import sha


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', action='store_true')
    parser.add_argument('--profile', choices=['all', 'windows', 'x30'], default='all')
    options = parser.parse_args()
    version = current_version()
    tag = 'v' + version.replace('.', '')
    runtime, _ = source_digest()
    binary = ENGINE if options.source else P / 'build/windows/RailwayWarlords.exe'
    if not options.source:
        exports = json.loads((P / 'reports/export_results.json').read_text(encoding='utf-8'))
        windows = next(row for row in exports if row['target'] == 'windows')
        if not windows['export_verified'] or windows['sha256'] != sha(binary) or windows['runtime_source_sha256'] != runtime:
            raise SystemExit('Verified current native export required.')
    fixture = P / 'tests/fixtures/capacity_full_conquest.json'
    for profile, size in [('windows', '1920x1080'), ('x30', '2400x1080')]:
        if options.profile not in ('all', profile):
            continue
        name = 'responsiveness_' + profile + '_' + tag + ('_dev' if options.source else '')
        report_path = P / 'reports' / (name + '.json')
        log = P / 'reports' / (name + '.log')
        capture = P / 'reports/screenshots' / (name + '.png')
        args = [str(binary)]
        if options.source:
            args += ['--path', str(P)]
        args += ['--log-file', str(log), '--resolution', size, '--', '--qa-session',
                 '--responsiveness-test', '--capacity-fixture', str(fixture),
                 '--responsiveness-report', str(report_path), '--capture-path', str(capture)]
        if profile == 'x30':
            args.append('--mobile-ui-test')
        with (P / 'reports' / (name + '_stdout.log')).open('w', encoding='utf-8') as stream:
            completed = subprocess.run(args, cwd=P, stdout=stream, stderr=subprocess.STDOUT, timeout=180)
        diagnostic = log.read_text(encoding='utf-8', errors='replace')
        if completed.returncode or any(marker in diagnostic for marker in ('SCRIPT ERROR:', '\nERROR:', 'WARNING: ObjectDB')):
            raise SystemExit('Native responsiveness failed: ' + name)
        value = json.loads(report_path.read_text(encoding='utf-8'))
        value.update(runtime_source_sha256=runtime, fixture_file_sha256=sha(fixture),
                     binary_sha256=sha(binary), native_capture_sha256=sha(capture))
        report_path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps({k: value[k] for k in ('passed', 'command_count', 'main_handoff_us_max',
                                              'planning_frames', 'animation_frames', 'average_fps')}, ensure_ascii=False), flush=True)
        if not value['passed']:
            raise SystemExit('The active-play 8 ms handoff target failed: ' + name)


if __name__ == '__main__':
    main()
