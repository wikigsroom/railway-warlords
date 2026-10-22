"""Record whole native development views and actual river arrays per attempt."""
from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import time

P = Path(__file__).resolve().parents[1]
ENGINE = P.parents[1] / '.toolchain/godot/Godot_v4.7.2-stable_win64.exe'
EVIDENCE = P / 'reports/river_cartography_v0236'


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('case', choices=['geometry', 'river_rules', 'surface_rules', 'material_rules', 'mountains', 'village', 'coast', 'yangtze'])
    parser.add_argument('--phase', required=True, choices=['baseline', 'revised'])
    parser.add_argument('--attempt', default='01')
    args = parser.parse_args()
    out = EVIDENCE / args.phase / (args.case + args.attempt)
    out.mkdir(parents=True, exist_ok=False)
    command = [str(ENGINE), '--path', str(P), '--log-file', str(out / 'native.log')]
    if args.case == 'geometry':
        command += ['--headless', '--script', 'res://tests/river_corner_geometry_test.gd', '--',
                    '--report-output', str(out / 'geometry.json')]
        if args.phase == 'revised': command += ['--require-rounded-profile']
    elif args.case.endswith('_rules'):
        script = {'river_rules': 'river_surface_test', 'surface_rules': 'surface_geography_test',
                  'material_rules': 'map_material_continuity_test'}[args.case]
        command += ['--headless', '--script', 'res://tests/' + script + '.gd', '--',
                    '--report-output', str(out / 'validation.json')]
    else:
        scenario, focus, zoom = {
            'mountains': ('campaign_1924_03', ['--focus-point', '16848,7000'], '1.05'),
            'village': ('campaign_1924_03', ['--focus-place', 'place_dongjiakou'], '1.15'),
            'coast': ('campaign_1924_03', ['--focus-city', 'shanhaiguan'], '.88'),
            'yangtze': ('legion_08', ['--focus-point', '2772,3346.322265625'], '.8'),
        }[args.case]
        command += ['--resolution', '1920x1080', '--position', '0,0', '--', '--qa-session',
                    '--scenario', scenario, *focus, '--capture-zoom', zoom, '--ui-scale', '1.0',
                    '--capture', '--capture-path', str(out / 'viewport.png')]
    files = [P / 'project.godot'] + [P / 'tests' / (name + '.gd') for name in
             ['river_corner_geometry_test', 'river_surface_test', 'surface_geography_test', 'map_material_continuity_test']]
    for folder in ['app', 'content', 'domain', 'ai', 'presentation', 'persistence', 'audio']:
        files += [path for path in (P / folder).rglob('*') if path.is_file() and path.suffix in ['.gd', '.tscn', '.json', '.gdshader']]
    identity = {path.relative_to(P).as_posix(): sha(path) for path in sorted(files)}
    proof = dict(command=command, engine_sha256=sha(ENGINE), controller_sha256=sha(__file__),
                 code_and_data_sha256=identity, phase=args.phase, source_override_used=False,
                 scope='Normal native Windows development engine; no shipping or phone claim.')
    (out / 'command.json').write_text(json.dumps(proof, indent=2) + '\n', encoding='utf-8')
    started = time.monotonic()
    with (out / 'stdout.log').open('w', encoding='utf-8') as stream:
        child = subprocess.Popen(command, cwd=P, stdout=stream, stderr=subprocess.STDOUT)
        print('NATIVE_RIVER_PID ' + str(child.pid), flush=True)
        try:
            code = child.wait(timeout=360)
        except subprocess.TimeoutExpired:
            child.kill(); child.wait(timeout=15)
            raise
    text = (out / 'native.log').read_text(encoding='utf-8', errors='replace')
    assert code == 0 and not any(marker in text for marker in ['SCRIPT ERROR:', 'SHADER ERROR:', '\nERROR:']), text[-1500:]
    unchanged = all(sha(P / name) == value for name, value in identity.items())
    assert unchanged
    target = out / ('geometry.json' if args.case == 'geometry' else 'validation.json' if args.case.endswith('_rules') else 'viewport.png')
    assert target.is_file()
    if args.case == 'geometry' or args.case.endswith('_rules'):
        report = json.loads(target.read_bytes()); assert report['passed']
    else:
        metadata = json.loads(target.with_suffix('.json').read_bytes())
        assert metadata['raw_godot_capture'] and metadata['qa_save_isolated'] and not metadata['physical_android_device_tested']
        hydro = metadata['map_bank_visible']['hydrography']
        if args.case == 'yangtze': assert hydro['river_surface']['drawn_gradient_ribbons'] > 0
        else: assert hydro['visible_fine_reaches'] > 0
    result = dict(passed=True, native_exit_code=code, native_process_id=child.pid,
                  elapsed_seconds=round(time.monotonic() - started, 2), dependencies_unchanged=True,
                  completed_at_utc=datetime.now(timezone.utc).isoformat(), phase=args.phase,
                  file=target.relative_to(P).as_posix(), sha256=sha(target), shipping_exe=False,
                  physical_android_device_tested=False, formal_art_approval=False)
    if args.case != 'geometry' and not args.case.endswith('_rules'): result['metadata_sha256'] = sha(target.with_suffix('.json'))
    (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result), flush=True)


if __name__ == '__main__': main()
