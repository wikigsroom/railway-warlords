"""Check the exported review EXE itself, without a live-source --path override.

Every attempt has a new directory. Screenshots are complete native viewports;
this tool does not edit, crop or assemble any raster image.
"""
from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import json
import math
import subprocess
import time

P = Path(__file__).resolve().parents[1]
R = P / 'reports/geographic_relief_v0236'
STAGE = P.parents[1] / 'game/railway_warlords_review_0236'
CONTENT_HASH = '1f7e449dc80b289ab5274fda5636519d1e3a320062d04f95374669302b754256'
DEM_SHA = '4f6b4ba758715300e1793b22a28b2d41f1849f8bd618efbf518e5cfc680d7e3d'
ASIA_CAMERAS = {
    'osaka': (135.3, 34.9, 1.2), 'himalaya': (85.5, 29.2, .72),
    'manchuria': (121.3, 42.1, .92), 'asia': (101, 34, .17),
    'osaka_x30_dimensions': (135.3, 34.9, 1.2),
}


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def camera_arguments(name):
    lon, lat, zoom = ASIA_CAMERAS[name]
    data = json.loads((STAGE / 'content/maps/asia_strategic.json').read_bytes())
    west, _, _, north = data['geographic_bounds']
    x = (lon - west) / data['longitude_step_deg'] * 72
    y = (north - lat) / data['latitude_step_deg'] * math.sqrt(3) * 48
    return ['--scenario', 'asia_1927', '--focus-point', f'{x},{y}', '--capture-zoom', str(zoom)]


def local_arguments(name):
    if name == 'shanhaiguan':
        return ['--scenario', 'campaign_1924_03', '--focus-point', '16920,8189.13623046875', '--capture-zoom', '.88']
    data = json.loads((STAGE / 'content/maps/jingjin.json').read_bytes())
    city = next(c for c in data['cities'] if c['id'] == 'tianjin')
    anchor = city['render_position']
    coast = min((v for line in data['render_coast'] for v in line),
                key=lambda v: (v[0]-anchor[0])**2 + (v[1]-anchor[1])**2)
    return ['--scenario', 'campaign_1920_01', '--focus-point', ','.join(map(str, coast)), '--capture-zoom', '.65']


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=['core', 'control', 'benchmark'])
    parser.add_argument('--attempt', default='01')
    parser.add_argument('--export-receipt', default='preview_export01.json',
                        help='Completed Windows export receipt; a partial-platform receipt is explicitly labelled.')
    args = parser.parse_args()
    export_path = R / args.export_receipt
    export = json.loads(export_path.read_bytes())
    windows = next(row for row in export['artifacts'] if row['target'] == 'windows')
    exe = Path(windows['path'])
    assert export['passed'] and export['version'] == '0.2.36'
    assert sha(exe) == windows['sha256']
    out = R / 'exported_windows' / (args.phase + args.attempt)
    out.mkdir(parents=True, exist_ok=False)
    names = (['menu', 'osaka', 'himalaya', 'manchuria', 'asia', 'shanhaiguan',
              'tianjin', 'osaka_x30_dimensions', 'ui_smoke'] if args.phase == 'core'
             else ['control'] if args.phase == 'control' else ['asia_idle'])
    proof = dict(version=export['version'], channel='development_review',
                 export_receipt=export_path.relative_to(P).as_posix(),
                 export_receipt_sha256=sha(export_path), exe_sha256=windows['sha256'],
                 runtime_source_merkle_sha256=export['runtime_source_merkle_sha256'],
                 controller_sha256=sha(__file__), shipping_exe=True,
                 live_source_override=False, production_presentation_overrides=False,
                 physical_android_device_tested=False, formal_art_approval=False,
                 both_platform_exports_complete_at_capture=all(any(a['target']==t for a in export['artifacts'])
                                                               for t in ['windows','android']),
                 captures_are_whole_native_viewports=True)
    with (out / 'identity.json').open('x', encoding='utf-8') as stream:
        json.dump(proof, stream, indent=2); stream.write('\n')
    cases = []
    for name in names:
        folder = out / name
        folder.mkdir(exist_ok=False)
        resolution = '2400x1080' if name.endswith('x30_dimensions') else '1920x1080'
        user_args = ['--qa-session', '--ui-scale', '1.2' if name.endswith('x30_dimensions') else '1.0']
        if name in ASIA_CAMERAS:
            user_args += camera_arguments(name)
        elif name in ['shanhaiguan', 'tianjin']:
            user_args += local_arguments(name)
        if name.endswith('x30_dimensions'):
            user_args.append('--mobile-ui-test')
        if name == 'control':
            user_args += ['--control-land-test', '--control-land-output', str(folder)]
        else:
            user_args += ['--capture-path', str(folder / 'viewport.png')]
            if name == 'ui_smoke':
                user_args += ['--scenario', 'campaign_1924_02', '--ui-test']
            elif name == 'asia_idle':
                user_args += ['--scenario', 'asia_1927', '--benchmark', '--benchmark-path', str(folder / 'benchmark.json')]
            else:
                user_args.append('--capture')
        command = [str(exe), '--resolution', resolution, '--position', '0,0',
                   '--log-file', str(folder / 'native.log'), '--', *user_args]
        assert '--path' not in command
        with (folder / 'command.json').open('x', encoding='utf-8') as stream:
            json.dump(dict(command=command, **proof), stream, indent=2); stream.write('\n')
        started = time.monotonic()
        with (folder / 'stdout.log').open('x', encoding='utf-8') as stream:
            child = subprocess.Popen(command, cwd=exe.parent, stdout=stream, stderr=subprocess.STDOUT)
            print(f'EXPORTED_PREVIEW {name} PID {child.pid}', flush=True)
            try:
                code = child.wait(timeout=420)
            except subprocess.TimeoutExpired:
                child.kill(); child.wait(timeout=15); raise
        diagnostic = (folder / 'native.log').read_text(encoding='utf-8', errors='replace')
        assert code == 0 and not any(marker in diagnostic for marker in ['SCRIPT ERROR:', 'SHADER ERROR:', '\nERROR:']), diagnostic[-1800:]
        row = dict(id=name, passed=True, process_id=child.pid, exit_code=code,
                   elapsed_seconds=round(time.monotonic()-started, 2),
                   log_sha256=sha(folder / 'native.log'), resolution=resolution)
        if name == 'control':
            validation = json.loads((folder / 'validation.json').read_bytes())
            assert validation['passed'] and validation['build_version'] == '0.2.36'
            assert validation['content_hash'] == CONTENT_HASH and validation['normal_shipping_renderer']
            assert validation['qa_save_isolated'] and not validation['physical_android_device_tested']
            row.update(checks=len(validation['checks']), validation_sha256=sha(folder / 'validation.json'),
                       water_view_samples=sum(case['water_pixels'] for case in validation['cases']),
                       maximum_water_channel_delta=max(case['water_max_channel_delta'] for case in validation['cases']),
                       hidden_minimap_cases=sum(case['minimap_pixel_check_status']=='skipped_hidden_by_production_hud'
                                                for case in validation['cases']))
            for capture in validation['captures']:
                assert Path(capture['path']).is_file() and Path(capture['metadata']).is_file()
        else:
            metadata = json.loads((folder / 'viewport.json').read_bytes())
            assert metadata['build_version'] == '0.2.36' and metadata['content_hash'] == CONTENT_HASH
            assert metadata['raw_godot_capture'] and metadata['qa_save_isolated']
            assert not metadata['physical_android_device_tested']
            if name in ASIA_CAMERAS or name == 'asia_idle':
                field = metadata['map_bank_visible']['terrain_surface_extension']['relief_lighting']['geographic_field']
                assert field['active'] and field['gpu_texture_available'] and field['shader_active']
                assert field['data_sha256'] == DEM_SHA and field['node_samples'] == 5765001
                row['geographic_field'] = field
            if name == 'ui_smoke':
                assert 'UI_SMOKE_PASS' in diagnostic
                row['ui_smoke_pass'] = True
            if name == 'asia_idle':
                bench = json.loads((folder / 'benchmark.json').read_bytes())
                assert bench['sample_frames'] == 180 and not bench['physical_android_device_tested']
                row['static_desktop_observation'] = bench
            row.update(viewport_sha256=sha(folder / 'viewport.png'), metadata_sha256=sha(folder / 'viewport.json'),
                       mobile_layout_profile=metadata['mobile_layout_profile'])
        cases.append(row)
        with (folder / 'result.json').open('x', encoding='utf-8') as stream:
            json.dump(row, stream, indent=2); stream.write('\n')
        print(json.dumps({k:v for k,v in row.items() if k not in ['geographic_field','static_desktop_observation']}), flush=True)
    assert sha(exe) == windows['sha256']
    result = dict(passed=True, **proof, completed_at_utc=datetime.now(timezone.utc).isoformat(), cases=cases,
                  binary_unchanged_during_checks=True, whole_images_automatically_generated_but_visual_review_recorded_separately=True)
    with (out / 'validation.json').open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2); stream.write('\n')


if __name__ == '__main__':
    main()
