"""Wait for directly owned native Godot processes; never mistake launch for exit."""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json
import os
import subprocess
import time

HERE = Path(__file__).resolve().parent
P = HERE.parent
ROOT = P.parents[1]
ENGINE = Path(os.environ.get('GODOT_BIN', str(ROOT / '.toolchain/godot/Godot_v4.7.2-stable_win64.exe')))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('case', choices=['edges', 'continuity', 'wuhan', 'nanjing', 'coast'])
    parser.add_argument('--attempt', default='')
    args = parser.parse_args()
    out = P / 'reports/ground_hierarchy_v0235' / (args.case + args.attempt)
    out.mkdir(parents=True, exist_ok=False)
    command = [str(ENGINE), '--path', str(P), '--resolution', '1920x1080', '--position', '0,0', '--log-file', str(out / 'native.log')]
    if args.case == 'edges':
        command += ['--script', 'res://tests/ground_source_edges_gpu_test.gd', '--', '--output', str(out)]
    elif args.case == 'continuity':
        command += ['--', '--qa-session', '--ground-continuity-test', '--ground-continuity-output', str(out)]
    else:
        scenario, focus, zoom = {
            'wuhan': ('legion_07', ['--focus-point', '3492.0,4052.998889711173'], '.56'),
            'nanjing': ('legion_08', ['--focus-city', 'nanjing'], '1.05'),
            'coast': ('campaign_1924_03', ['--focus-city', 'shanhaiguan'], '.88'),
        }[args.case]
        command += ['--', '--qa-session', '--scenario', scenario, '--ui-scale', '1.0', *focus, '--capture-zoom', zoom,
                    '--capture', '--capture-path', str(out / 'viewport.png')]
    dependencies = ['presentation/ground_material_blend.gd', 'presentation/data/ground_macro_catalog.json',
                    'presentation/data/ground_material_plan_v0235.json', 'app/ground_continuity_qa.gd',
                    'tests/ground_source_edges_gpu_test.gd']
    proof = dict(controller_sha256=digest(Path(__file__)), scope='Native Windows development engine; source revision ahead of published 0.2.34. Not a shipping EXE or physical Android test.',
                 command=command, scoped_dependency_sha256={name: digest(P / name) for name in dependencies},
                 reference_published_commit='5fdd2de0348650307aec304d3175d334f62da610')
    (out / 'command.json').write_text(json.dumps(proof, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    started = time.monotonic()
    with (out / 'stdout.log').open('w', encoding='utf-8') as stream:
        process = subprocess.Popen(command, cwd=P, stdout=stream, stderr=subprocess.STDOUT)
        print('Native process ' + str(process.pid) + ': ' + args.case, flush=True)
        try:
            code = process.wait(timeout=600)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=15)
            code = -1
    log = (out / 'native.log').read_text(encoding='utf-8', errors='replace') if (out / 'native.log').exists() else ''
    passed = code == 0 and bool(log) and not any(marker in log for marker in ['SCRIPT ERROR:', 'SHADER ERROR:', '\nERROR:'])
    if args.case in ['edges', 'continuity']:
        validation = out / 'validation.json'
        passed = passed and validation.exists() and json.loads(validation.read_bytes())['passed']
    else:
        passed = passed and (out / 'viewport.png').exists() and (out / 'viewport.json').exists()
    unchanged = all(digest(P / name) == expected for name, expected in proof['scoped_dependency_sha256'].items())
    result = dict(passed=passed and unchanged, native_exit_code=code, native_process_id=process.pid,
                  elapsed_seconds=round(time.monotonic() - started, 2), dependencies_unchanged=unchanged,
                  completed_at_utc=datetime.now(timezone.utc).isoformat(), shipping_exe=False,
                  physical_android_device_tested=False, ew6_parity_claimed=False)
    if (out / 'viewport.png').exists(): result['image_sha256'] = digest(out / 'viewport.png')
    (out / 'result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False), flush=True)
    raise SystemExit(0 if result['passed'] else 1)


if __name__ == '__main__':
    main()
