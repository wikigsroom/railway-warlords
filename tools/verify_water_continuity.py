"""Bind the native water GPU fixture to the current shipping executable."""
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
from build_release import P, current_version, source_digest
from package_delivery import read, require, sha


def main():
    runtime = source_digest()[0]
    exe = P / 'build/windows/RailwayWarlords.exe'
    export = next(row for row in read(P / 'reports/export_results.json') if row['target'] == 'windows')
    require(export['export_verified'] and export['runtime_source_sha256'] == runtime
            and export['sha256'] == sha(exe), 'Current verified Windows export required')
    proof_path = P / 'reports/water_continuity_native_evidence.json'
    driver = sha(Path(__file__))
    if proof_path.exists():
        previous = read(proof_path)
        fixtures = previous.get('fixture_captures', [])
        if (previous.get('passed') and previous.get('version') == current_version()
                and previous.get('runtime_source_sha256') == runtime
                and previous.get('windows_exe_sha256') == export['sha256']
                and previous.get('fixture_driver_sha256') == driver and previous.get('checks') == 22
                and len(fixtures) == 3
                and all((P / previous[key]).is_file() and sha(P / previous[key]) == previous[key + '_sha256']
                        for key in ['report', 'log'])
                and all((P / row['file']).is_file() and sha(P / row['file']) == row['sha256'] for row in fixtures)):
            print('Current frozen-build twenty-two native water checks retained.', flush=True)
            return
    folder = P / 'reports/water_continuity_native'
    folder.mkdir(exist_ok=True)
    log = folder / 'native.log'
    with log.open('w', encoding='utf-8') as out:
        result = subprocess.run([str(exe), '--resolution', '1280x720', '--position', '-4000,-3000', '--',
            '--qa-session', '--water-continuity-test', '--water-continuity-output', str(folder)],
            cwd=P, stdout=out, stderr=subprocess.STDOUT, timeout=180)
    diagnostic = log.read_text(encoding='utf-8', errors='replace')
    require(result.returncode == 0 and 'SCRIPT ERROR:' not in diagnostic and '\nERROR:' not in diagnostic
            and 'SHADER ERROR:' not in diagnostic, 'Native water fixture failed')
    path = folder / 'validation.json'
    value = read(path)
    require(value['passed'] and value['build_version'] == current_version() and len(value['checks']) == 22,
            'Complete current water GPU evidence required')
    require(source_digest()[0] == runtime and sha(exe) == export['sha256'], 'Runtime identity changed')
    fixture_captures = []
    for kind in ['sea', 'river', 'inland']:
        image = folder / ('tile_water_' + kind + '_v0227_overview.png')
        require(image.is_file(), 'Raw continental fixture viewport missing: ' + kind)
        fixture_captures.append(dict(file=image.relative_to(P).as_posix(), sha256=sha(image)))
    proof = dict(passed=True, version=current_version(), runtime_source_sha256=runtime,
        windows_exe_sha256=export['sha256'], fixture_driver_sha256=driver, checks=len(value['checks']),
        report=path.relative_to(P).as_posix(), report_sha256=sha(path),
        log=log.relative_to(P).as_posix(), log_sha256=sha(log),
        fixture_captures=fixture_captures, created_at_utc=datetime.now(timezone.utc).isoformat(),
        synthetic_fixture_not_gameplay=True, physical_android_device_tested=False,
        formal_art_approval=False, source_images_modified=False, ew6_parity_claimed=False)
    proof_path.write_text(json.dumps(proof, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(proof), flush=True)


if __name__ == '__main__':
    main()
