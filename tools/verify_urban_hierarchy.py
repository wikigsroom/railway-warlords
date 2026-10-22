"""Capture untouched native city scenes or run the urban integration checks.

Every attempt has a new directory. No PNG processing or source override occurs.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json
import subprocess
import time

P = Path(__file__).resolve().parents[1]
ROOT = P.parents[1]
ENGINE = ROOT / '.toolchain/godot/Godot_v4.7.2-stable_win64.exe'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('case', choices=['rules', 'bank', 'wuhan', 'three_towns', 'nanjing', 'beijing'])
    parser.add_argument('--attempt', default='01')
    args = parser.parse_args()
    out = P / 'reports/urban_hierarchy_v0235' / (args.case + args.attempt)
    out.mkdir(parents=True, exist_ok=False)
    command = [str(ENGINE), '--path', str(P), '--resolution', '1920x1080', '--position', '0,0', '--log-file', str(out / 'native.log')]
    if args.case in ['rules', 'bank']:
        script = 'urban_hierarchy_test' if args.case == 'rules' else 'map_bank_test'
        command += ['--headless', '--script', 'res://tests/' + script + '.gd', '--', '--report-output', str(out / 'validation.json')]
    else:
        scenario, focus, zoom = {
            'wuhan': ('legion_07', ['--focus-city', 'hankou'], '1.05'),
            'three_towns': ('legion_07', ['--focus-point', '3492.0,4052.998889711173'], '.56'),
            'nanjing': ('legion_08', ['--focus-city', 'nanjing'], '1.05'),
            'beijing': ('campaign_1924_05', ['--focus-city', 'beijing'], '.9'),
        }[args.case]
        command += ['--', '--qa-session', '--scenario', scenario, '--ui-scale', '1.0', *focus,
                    '--capture-zoom', zoom, '--capture', '--capture-path', str(out / 'viewport.png')]
    dependencies = [P / 'project.godot', P / 'tests/urban_hierarchy_test.gd', P / 'tests/map_bank_test.gd',
                    P / 'assets/manifest.json', P / 'docs/asset-provenance/index.json']
    for folder in ['app', 'content', 'domain', 'ai', 'presentation', 'persistence', 'audio']:
        dependencies += [path for path in (P / folder).rglob('*') if path.is_file() and path.suffix in ['.gd', '.tscn', '.json']]
    for path in (P / 'assets/building').glob('building_bank_urban_*.png'):
        dependencies += [path, path.with_suffix('.png.import')]
    identity = {path.relative_to(P).as_posix(): sha(path) for path in sorted(dependencies)}
    proof = dict(scope='Native Windows development engine with the urban source extension. Not a shipping export or physical Android test.',
                 command=command, controller_sha256=sha(Path(__file__)), engine_sha256=sha(ENGINE),
                 code_content_urban_media_dependency_sha256=identity, source_override_used=False)
    (out / 'command.json').write_text(json.dumps(proof, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    started = time.monotonic()
    with (out / 'stdout.log').open('w', encoding='utf-8') as stream:
        child = subprocess.Popen(command, cwd=P, stdout=stream, stderr=subprocess.STDOUT)
        print('Native process ' + str(child.pid) + ': ' + args.case, flush=True)
        try:
            code = child.wait(timeout=600)
        except subprocess.TimeoutExpired:
            child.kill(); child.wait(timeout=15); code = -1
    log = (out / 'native.log').read_text(encoding='utf-8', errors='replace') if (out / 'native.log').exists() else ''
    passed = code == 0 and bool(log) and not any(marker in log for marker in ['SCRIPT ERROR:', 'SHADER ERROR:', '\nERROR:'])
    if args.case in ['rules', 'bank']:
        report = out / 'validation.json'
        passed = passed and report.exists() and json.loads(report.read_bytes())['passed']
    else:
        passed = passed and (out / 'viewport.png').exists() and (out / 'viewport.json').exists()
    unchanged = all(sha(P / name) == value for name, value in identity.items())
    result = dict(passed=passed and unchanged, native_exit_code=code, native_process_id=child.pid,
                  elapsed_seconds=round(time.monotonic() - started, 2), dependencies_unchanged=unchanged,
                  completed_at_utc=datetime.now(timezone.utc).isoformat(), shipping_exe=False,
                  physical_android_device_tested=False, ew6_parity_claimed=False)
    if (out / 'viewport.png').exists(): result['image_sha256'] = sha(out / 'viewport.png')
    (out / 'result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False), flush=True)
    raise SystemExit(0 if result['passed'] else 1)


if __name__ == '__main__':
    main()
