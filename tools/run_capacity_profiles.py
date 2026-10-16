"""Measure the verified native EXE sequentially; desktop profiles are not phones."""
import json
import subprocess
from build_release import P, current_version, source_digest
from package_delivery import sha


def main():
    tag = 'v' + current_version().replace('.', '')
    exe = P / 'build/windows/RailwayWarlords.exe'
    exports = json.loads((P / 'reports/export_results.json').read_text(encoding='utf-8'))
    windows = next(row for row in exports if row['target'] == 'windows')
    if not windows['export_verified'] or windows['sha256'] != sha(exe) or windows['runtime_source_sha256'] != source_digest()[0]:
        raise SystemExit('A verified export of the current complete runtime is required.')
    for profile, resolution in [('windows', '1920x1080'), ('x30', '2400x1080')]:
        name = f'capacity_{profile}_{tag}'
        log = P / 'reports' / (name + '.log')
        args = [str(exe), '--resolution', resolution, '--log-file', str(log), '--',
                '--qa-session', '--ui-scale', '1.2' if profile == 'x30' else '1.0',
                '--capacity-benchmark', '--capacity-duration', '60',
                '--capacity-fixture', str(P / 'tests/fixtures/capacity_full_conquest.json'),
                '--capacity-report', str(P / 'reports' / (name + '.json')),
                '--capture-path', str(P / 'reports/screenshots' / (name + '.png'))]
        if profile == 'x30':
            args.append('--mobile-ui-test')
        with (P / 'reports' / (name + '_stdout.log')).open('w', encoding='utf-8') as stream:
            result = subprocess.run(args, cwd=P, stdout=stream, stderr=subprocess.STDOUT, timeout=240)
        diagnostic = log.read_text(encoding='utf-8', errors='replace')
        if result.returncode or any(marker in diagnostic for marker in ('SCRIPT ERROR:', '\nERROR:', 'WARNING: ObjectDB')):
            raise SystemExit('Native capacity execution failed: ' + name)
        report = json.loads((P / 'reports' / (name + '.json')).read_text(encoding='utf-8'))
        report['runtime_source_sha256']=windows['runtime_source_sha256']
        report['windows_exe_sha256']=windows['sha256']
        report['export_identity_verified_by_driver']=True
        (P / 'reports' / (name + '.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(json.dumps({'profile': profile, 'passed': report['render_target_passed'],
                         'stages': [{k: stage[k] for k in ('stage', 'average_fps', 'frame_ms_p95', 'minimum_drawable_units')}
                                    for stage in report['stages']]}, ensure_ascii=False), flush=True)
        if not report['render_target_passed']:
            raise SystemExit('Native 60 FPS target failed: ' + name)


if __name__ == '__main__':
    main()
