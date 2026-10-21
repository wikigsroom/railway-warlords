"""Capture complete native water/grid views; never edit any captured pixels."""
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
from PIL import Image
from build_release import P, current_version, source_digest
from package_delivery import read, require, sha


def main():
    version = current_version()
    runtime = source_digest()[0]
    exe = P / 'build/windows/RailwayWarlords.exe'
    export = next(row for row in read(P / 'reports/export_results.json') if row['target'] == 'windows')
    require(version in ['0.2.27', '0.2.28', '0.2.29'] and export['export_verified'] and export['runtime_source_sha256'] == runtime
            and export['sha256'] == sha(exe), 'Frozen current Windows executable required')
    cases = [
        ('china_overview', 'conq_1922', ['--atlas-view', '--inspect-city', 'qingdao']),
        ('asia_overview', 'asia_1927', ['--atlas-view']),
        ('bohai', 'campaign_1924_03', ['--focus-city', 'shanhaiguan', '--capture-zoom', '.88']),
        ('japan', 'asia_1927', ['--focus-city', 'osaka', '--capture-zoom', '1.2']),
        ('caspian', 'asia_1840', ['--focus-city', 'baku', '--capture-zoom', '.9']),
        ('yangtze', 'legion_07', ['--focus-city', 'hankou', '--capture-zoom', '1.05']),
        ('nanjing', 'legion_08', ['--focus-city', 'nanjing', '--capture-zoom', '1.05']),
        ('yangtze_x30', 'legion_07', ['--focus-city', 'hankou', '--capture-zoom', '1.05']),
        ('china_overview_x30', 'conq_1922', ['--atlas-view', '--inspect-city', 'qingdao']),
        ('grid_below_readable', 'campaign_1924_03', ['--focus-city', 'shanhaiguan', '--capture-zoom', '.19', '--capture-grid']),
        ('grid_readable', 'campaign_1924_03', ['--focus-city', 'shanhaiguan', '--capture-zoom', '.21', '--capture-grid']),
    ]
    proof_path = P / 'reports/water_map_native_capture_evidence.json'
    driver = sha(Path(__file__))
    if proof_path.exists():
        previous = read(proof_path)
        rows = previous.get('captures', [])
        if (previous.get('passed') and previous.get('version') == version
                and previous.get('runtime_source_sha256') == runtime
                and previous.get('windows_exe_sha256') == export['sha256']
                and previous.get('capture_driver_sha256') == driver
                and len(rows) == len(cases) and {row['name'] for row in rows} == {case[0] for case in cases}
                and all((P / row[key]).is_file() and sha(P / row[key]) == row['sha256' if key == 'file' else key + '_sha256']
                        for row in rows for key in ['file', 'metadata', 'log'])):
            print('Current frozen-build eleven water/grid viewports retained.', flush=True)
            return
    captures = []
    for name, scenario, extra in cases:
        mobile = name.endswith('_x30')
        resolution = '2400x1080' if mobile else '1920x1080'
        folder = P / 'reports/screenshots/water_map_native'
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / (name + '.png')
        log = P / 'reports' / ('water_map_capture_' + name + '.log')
        args = [str(exe), '--resolution', resolution, '--position', '0,0', '--',
                '--qa-session', '--scenario', scenario, *extra, '--capture', '--capture-path', str(target)]
        if mobile:
            args += ['--ui-scale', '1.2', '--mobile-ui-test']
        started = datetime.now(timezone.utc).timestamp()
        with log.open('w', encoding='utf-8') as out:
            result = subprocess.run(args, cwd=P, stdout=out, stderr=subprocess.STDOUT, timeout=300)
        diagnostic = log.read_text(encoding='utf-8', errors='replace')
        require(result.returncode == 0 and 'SCRIPT ERROR:' not in diagnostic and '\nERROR:' not in diagnostic,
                'Native water/grid capture failed: ' + name)
        meta = read(target.with_suffix('.json'))
        require(meta['build_version'] == version and meta['raw_godot_capture'] and meta['qa_save_isolated']
                and meta['scenario_id'] == scenario and target.stat().st_mtime >= started - 2,
                'Fresh complete native viewport required: ' + name)
        visible = meta['map_bank_visible']
        water = visible['hydrography']['water_materials']
        grid = visible['hydrography']['operation_grid']
        require(visible['current_total_map_assets'] == 973 and water['independent_originals'] == 3
                and water['mipmapped_minification_active'] and not water['legacy_per_cell_water_stamps']
                and not water['geographic_water_extent_changed'], 'Continuous sourced water pipeline missing')
        for kind in ['sea', 'river', 'inland']:
            require(water['bound_' + kind + '_resource'] == 'res://assets/tile/tile_water_' + kind + '_v0227.png',
                    'Actual bound resource differs: ' + kind)
        require(grid['hex_radius_world'] == 48 and grid['axial_guide_lines'] == 0,
                'Unchanged hex grid must not gain axial guide replacements')
        if visible['zoom'] < .20:
            require(grid['drawn_hexes'] == 0, 'Subpixel operation grid must be hidden')
        if name == 'grid_readable':
            require(grid['drawn_hexes'] > 0, 'Actual optional operation hexes must remain available')
        if name.startswith('yangtze') or name == 'nanjing':
            rivers = visible['hydrography']['river_surface']
            require(rivers['drawn_textured_ribbons'] > 0 and rivers['water_texture_id'] == 'tile_water_river_v0227',
                    'Real river material must be issued on the source channel')
        with Image.open(target) as image:
            require(image.size == tuple(map(int, resolution.split('x'))), 'Full native viewport required')
        captures.append(dict(name=name, file=target.relative_to(P).as_posix(), sha256=sha(target),
            metadata=target.with_suffix('.json').relative_to(P).as_posix(),
            metadata_sha256=sha(target.with_suffix('.json')), log=log.relative_to(P).as_posix(),
            log_sha256=sha(log), resolution=resolution, water=water, grid=grid))
        print('WATER_MAP_NATIVE_PASS ' + name, flush=True)
    require(source_digest()[0] == runtime and sha(exe) == export['sha256'], 'Frozen source/export changed')
    proof = dict(passed=True, version=version, runtime_source_sha256=runtime,
        windows_exe_sha256=export['sha256'], capture_driver_sha256=driver,
        captures=captures, created_at_utc=datetime.now(timezone.utc).isoformat(),
        raw_godot_captures=True, physical_android_device_tested=False,
        source_images_modified=False, formal_art_approval=False, ew6_parity_claimed=False)
    proof_path.write_text(
        json.dumps(proof, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
