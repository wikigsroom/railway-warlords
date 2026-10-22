"""Capture unmodified gameplay through an owned native Windows Godot process."""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json
import os
import subprocess
import time

P = Path(__file__).resolve().parents[1]
ROOT = P.parents[1]
ENGINE = Path(os.environ.get('GODOT_BIN', str(ROOT / '.toolchain/godot/Godot_v4.7.2-stable_win64.exe')))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('case', choices=['rules', 'coast', 'wuhan', 'nanjing'])
    parser.add_argument('--attempt', default='01')
    args = parser.parse_args()
    out = P / 'reports/control_borders_v0235' / (args.case + args.attempt)
    out.mkdir(parents=True, exist_ok=False)
    command = [str(ENGINE), '--path', str(P), '--resolution', '1920x1080', '--position', '0,0', '--log-file', str(out / 'native.log')]
    if args.case == 'rules':
        command += ['--headless', '--script', 'res://tests/control_borders_test.gd', '--', '--output', str(out)]
    else:
        scenario, focus, zoom = {
            'coast': ('campaign_1924_03', ['--focus-city', 'shanhaiguan'], '.88'),
            'wuhan': ('legion_07', ['--focus-point', '3492.0,4052.998889711173'], '.56'),
            'nanjing': ('legion_08', ['--focus-city', 'nanjing'], '1.05'),
        }[args.case]
        command += ['--', '--qa-session', '--scenario', scenario, '--ui-scale', '1.0', *focus,
                    '--capture-zoom', zoom, '--capture', '--capture-path', str(out / 'viewport.png')]
    dependencies = [P / 'project.godot', P / 'tests/control_borders_test.gd']
    for folder in ['app', 'content', 'domain', 'ai', 'presentation', 'persistence', 'audio']:
        dependencies += [path for path in (P / folder).rglob('*') if path.is_file() and path.suffix in ['.gd', '.tscn', '.json']]
    identity = {path.relative_to(P).as_posix(): sha(path) for path in sorted(dependencies)}
    proof = dict(scope='Native Windows development engine after 0d78d69; source code and content dependencies below. Not a shipping export or physical Android test.',
                 command=command, controller_sha256=sha(Path(__file__)), engine_sha256=sha(ENGINE),
                 code_content_dependency_sha256=identity, source_override_used=False)
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
    if args.case == 'rules':
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
