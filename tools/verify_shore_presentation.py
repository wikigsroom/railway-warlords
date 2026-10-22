"""Run ordinary native shore views with immutable per-attempt source receipts."""
from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import time

P = Path(__file__).resolve().parents[1]
ENGINE = P.parents[1] / '.toolchain/godot/Godot_v4.7.2-stable_win64.exe'
R = P / 'reports/shore_presentation_v0236'
CASES = {
    'shanhaiguan': ('jingfeng', 'campaign_1924_03', 'shanhaiguan', '.88'),
    'tianjin': ('jingjin', 'campaign_1920_01', 'tianjin', '.65'),
    'qingdao': ('conquest_china', 'conq_1924', 'qingdao', '.75'),
    'osaka': ('asia_strategic', 'asia_1927', 'osaka', '1.2'),
}


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('case', choices=[*CASES, 'coast_rules', 'shore_rules'])
    parser.add_argument('--phase', required=True, choices=['baseline', 'revised'])
    parser.add_argument('--attempt', default='01')
    args = parser.parse_args()
    out = R / args.phase / (args.case + args.attempt)
    out.mkdir(parents=True, exist_ok=False)
    command = [str(ENGINE), '--path', str(P), '--log-file', str(out / 'native.log')]
    if args.case.endswith('_rules'):
        script = 'coast_geometry_test' if args.case == 'coast_rules' else 'shore_presentation_test'
        command += ['--headless', '--script', 'res://tests/' + script + '.gd', '--',
                    '--report-output', str(out / 'validation.json')]
    else:
        mid, scenario, city_id, zoom = CASES[args.case]
        map_data = json.loads((P / 'content/maps' / (mid + '.json')).read_bytes())
        city = next(row for row in map_data['cities'] if row['id'] == city_id)
        if args.case == 'shanhaiguan':
            focus = [16920, 8189.13623046875]
        else:
            anchor = city['render_position']
            focus = min((point for line in map_data['render_coast'] for point in line),
                        key=lambda point: (point[0] - anchor[0]) ** 2 + (point[1] - anchor[1]) ** 2)
        command += ['--resolution', '1920x1080', '--position', '0,0', '--', '--qa-session',
                    '--scenario', scenario, '--focus-point', ','.join(map(str, focus)), '--capture-zoom', zoom,
                    '--ui-scale', '1.0', '--capture', '--capture-path', str(out / 'viewport.png')]
    files = [P / 'project.godot']
    for folder in ['app', 'content', 'domain', 'ai', 'presentation', 'persistence', 'audio']:
        files += [path for path in (P / folder).rglob('*') if path.is_file() and path.suffix in ['.gd', '.tscn', '.json', '.gdshader']]
    if args.case.endswith('_rules'):
        files.append(P / 'tests' / (script + '.gd'))
    identity = {path.relative_to(P).as_posix(): sha(path) for path in sorted(files)}
    proof = dict(command=command, engine_sha256=sha(ENGINE), controller_sha256=sha(__file__),
                 code_and_data_sha256=identity, phase=args.phase, production_overrides=False,
                 development_only=True, shipping_exe=False, physical_android_device_tested=False)
    (out / 'command.json').write_text(json.dumps(proof, indent=2) + '\n', encoding='utf-8')
    started = time.monotonic()
    with (out / 'stdout.log').open('w', encoding='utf-8') as stream:
        child = subprocess.Popen(command, cwd=P, stdout=stream, stderr=subprocess.STDOUT)
        print('NATIVE_SHORE_PID ' + str(child.pid), flush=True)
        try:
            code = child.wait(timeout=360)
        except subprocess.TimeoutExpired:
            child.kill(); child.wait(timeout=15); raise
    log = (out / 'native.log').read_text(encoding='utf-8', errors='replace')
    assert code == 0 and not any(marker in log for marker in ['SCRIPT ERROR:', 'SHADER ERROR:', '\nERROR:']), log[-1800:]
    assert all(sha(P / name) == checksum for name, checksum in identity.items())
    target = out / ('validation.json' if args.case.endswith('_rules') else 'viewport.png')
    result = dict(passed=True, native_exit_code=code, native_process_id=child.pid,
                  completed_at_utc=datetime.now(timezone.utc).isoformat(), elapsed_seconds=round(time.monotonic() - started, 2),
                  dependencies_unchanged=True, file=target.relative_to(P).as_posix(), sha256=sha(target),
                  development_only=True, shipping_exe=False, physical_android_device_tested=False, formal_art_approval=False)
    if args.case.endswith('_rules'):
        assert json.loads(target.read_bytes())['passed']
    else:
        metadata = json.loads(target.with_suffix('.json').read_bytes())
        assert metadata['raw_godot_capture'] and metadata['qa_save_isolated']
        hydro = metadata['map_bank_visible']['hydrography']
        assert hydro['actual_coast_band_draws'] == 1 and hydro['marine_geometry']['active']
        result['metadata_sha256'] = sha(target.with_suffix('.json'))
    (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
