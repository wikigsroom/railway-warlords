"""Archive ordinary native viewports and source dependencies; no raster editing."""
from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import json
import math
import subprocess
import time

P = Path(__file__).resolve().parents[1]
ENGINE = P.parents[1] / '.toolchain/godot/Godot_v4.7.2-stable_win64.exe'
R = P / 'reports/geographic_relief_v0236'
CASES = {'osaka': (135.3, 34.9, 1.2), 'himalaya': (85.5, 29.2, .72),
         'manchuria': (121.3, 42.1, .92), 'asia': (101, 34, .17)}


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('case', choices=[*CASES, 'rules', 'control'])
    parser.add_argument('--phase', required=True, choices=['baseline', 'revised'])
    parser.add_argument('--attempt', default='01')
    args = parser.parse_args()
    out = R / args.phase / (args.case + args.attempt)
    out.mkdir(parents=True, exist_ok=False)
    command = [str(ENGINE), '--path', str(P), '--log-file', str(out / 'native.log')]
    if args.case == 'control':
        command += ['--resolution', '1920x1080', '--position', '0,0', '--', '--qa-session',
                    '--control-land-test', '--control-land-output', str(out)]
    elif args.case == 'rules':
        script = 'geographic_relief_test'
        command += ['--headless', '--script', 'res://tests/' + script + '.gd', '--',
                    '--report-output', str(out / 'validation.json')]
    else:
        lon, lat, zoom = CASES[args.case]
        data = json.loads((P / 'content/maps/asia_strategic.json').read_bytes())
        west, _, _, north = data['geographic_bounds']
        x = (lon - west) / data['longitude_step_deg'] * 72
        y = (north - lat) / data['latitude_step_deg'] * math.sqrt(3) * 48
        command += ['--resolution', '1920x1080', '--position', '0,0', '--', '--qa-session',
                    '--scenario', 'asia_1927', '--focus-point', f'{x},{y}', '--capture-zoom', str(zoom),
                    '--ui-scale', '1.0', '--capture', '--capture-path', str(out / 'viewport.png')]
    files = [P / 'project.godot']
    for folder in ['app', 'content', 'domain', 'ai', 'presentation', 'persistence', 'audio']:
        files += [f for f in (P / folder).rglob('*') if f.is_file() and f.suffix in ['.gd', '.tscn', '.json', '.gdshader']]
    if args.case == 'rules':
        files.append(P / 'tests' / (script + '.gd'))
    identity = {f.relative_to(P).as_posix(): sha(f) for f in sorted(files)}
    proof = dict(command=command, controller_sha256=sha(__file__), engine_sha256=sha(ENGINE),
                 code_and_data_sha256=identity, phase=args.phase, production_overrides=False,
                 development_only=True, shipping_exe=False, physical_android_device_tested=False)
    (out / 'command.json').write_text(json.dumps(proof, indent=2) + '\n', encoding='utf-8')
    started = time.monotonic()
    with (out / 'stdout.log').open('w', encoding='utf-8') as stream:
        child = subprocess.Popen(command, cwd=P, stdout=stream, stderr=subprocess.STDOUT)
        print('NATIVE_GEOGRAPHIC_RELIEF_PID ' + str(child.pid), flush=True)
        try:
            code = child.wait(timeout=360)
        except subprocess.TimeoutExpired:
            child.kill(); child.wait(timeout=15); raise
    log = (out / 'native.log').read_text(encoding='utf-8', errors='replace')
    assert code == 0 and not any(m in log for m in ['SCRIPT ERROR:', 'SHADER ERROR:', '\nERROR:']), log[-1800:]
    assert all(sha(P / name) == checksum for name, checksum in identity.items())
    target = out / ('validation.json' if args.case in ['rules', 'control'] else 'viewport.png')
    result = dict(passed=True, native_exit_code=code, native_process_id=child.pid,
                  completed_at_utc=datetime.now(timezone.utc).isoformat(), elapsed_seconds=round(time.monotonic()-started, 2),
                  dependencies_unchanged=True, file=target.relative_to(P).as_posix(), sha256=sha(target),
                  development_only=True, shipping_exe=False, physical_android_device_tested=False, formal_art_approval=False)
    if args.case in ['rules', 'control']:
        assert json.loads(target.read_bytes())['passed']
    else:
        metadata = json.loads(target.with_suffix('.json').read_bytes())
        assert metadata['raw_godot_capture'] and metadata['qa_save_isolated']
        if args.phase == 'revised':
            field = metadata['map_bank_visible']['terrain_surface_extension']['relief_lighting']['geographic_field']
            assert field['active'] and field['gpu_texture_available'] and field['shader_active'], field
        result['metadata_sha256'] = sha(target.with_suffix('.json'))
    (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
