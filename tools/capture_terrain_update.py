"""Bind terrain and war-room UI evidence to the verified native Windows export.

All images are untouched Godot viewports. Desktop mobile-size profiles do not
claim physical-phone acceptance. The QA save profile is isolated by the game.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
from PIL import Image
from build_release import P, current_version, source_digest
from package_delivery import sha, require, read
from capture_map_bank import tributary_point


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--section', choices=['all', 'terrain', 'war-room', 'details'], default='all')
    args = parser.parse_args()
    version = current_version()
    runtime = source_digest()[0]
    exe = P / 'build/windows/RailwayWarlords.exe'
    exported = next(row for row in read(P / 'reports/export_results.json') if row['target'] == 'windows')
    require(exported['export_verified'] and exported['sha256'] == sha(exe)
            and exported['runtime_source_sha256'] == runtime, 'Current verified native export required')
    groups = []
    cases = [('terrain', 'windows', '1920x1080', '1.0'),
             ('terrain', 'x30_layout', '2400x1080', '1.2'),
             ('war-room', 'windows', '1920x1080', '1.0'),
             ('war-room', 'x30_layout', '2400x1080', '1.2'),
             ('war-room', 'large_text', '1280x720', '1.5')]
    for kind, profile, resolution, scale in cases:
        if args.section != 'all' and args.section != kind:
            continue
        root = 'terrain_surfaces_native' if kind == 'terrain' else 'war_room_native'
        folder = P / 'reports/screenshots' / root / profile
        folder.mkdir(parents=True, exist_ok=True)
        report_path = folder / 'validation.json'
        log = P / 'reports' / f'{root}_{profile}_v{version.replace(".", "")}.log'
        stdout = log.with_name(log.stem + '_stdout.log')
        switch = '--terrain-surface' if kind == 'terrain' else '--war-room'
        command = [str(exe), '--resolution', resolution, '--position', '-4000,-3000',
                   '--log-file', str(log), '--', '--qa-session', '--ui-scale', scale,
                   switch + '-test', switch + '-output', str(folder)]
        if profile == 'x30_layout':
            command.append('--mobile-ui-test')
        started = datetime.now(timezone.utc).timestamp()
        with stdout.open('w', encoding='utf-8') as stream:
            result = subprocess.run(command, cwd=P, stdout=stream, stderr=subprocess.STDOUT, timeout=600)
        diagnostic = log.read_text(encoding='utf-8', errors='replace')
        require(result.returncode == 0 and not any(x in diagnostic for x in ('SCRIPT ERROR:', '\nERROR:', 'WARNING: ObjectDB')),
                'Native QA failed: ' + kind + '/' + profile + '; inspect ' + log.name)
        value = read(report_path)
        require(value['passed'] and value['build_version'] == version and report_path.stat().st_mtime >= started - 2,
                'Current native report required: ' + str(report_path))
        captures = []
        for row in value['captures']:
            path = P / row['path'].removeprefix('res://')
            metadata = path.with_suffix('.json')
            meta = read(metadata)
            if kind == 'terrain' and 'map_selection' in row:
                ground = row['map_selection']['terrain_surface_extension']['continuous_ground']
                require(ground['active'] and ground['source_layers'] == 20,
                        'Shipping continuous-ground shader unavailable: ' + path.name)
            require(meta['build_version'] == version and meta['raw_godot_capture'] and path.stat().st_mtime >= started - 2,
                    'Current raw Godot capture required: ' + path.name)
            with Image.open(path) as im:
                require(im.size == tuple(map(int, resolution.split('x'))), 'Viewport dimensions differ: ' + path.name)
            captures.append(dict(file=path.relative_to(P).as_posix(), sha256=sha(path),
                                 metadata=metadata.relative_to(P).as_posix(), metadata_sha256=sha(metadata)))
        expected = 3+value['rendered_map_types'] if kind == 'terrain' else 16
        if kind == 'terrain':
            withheld=set(value.get('withheld_without_dated_forest_source',[]))
            require(value['registered_library_types']==20 and withheld <= {'boreal_litter','temperate_litter','conifer_litter','dry_woodland_litter'}
                    and value['rendered_map_types']+len(withheld)==20,'Source-gated terrain coverage is incomplete')
        require(len(captures) == expected, 'Incomplete native capture set')
        groups.append(dict(kind=kind, profile=profile, resolution=resolution, ui_scale=scale,
                           checks=len(value['checks']), passed=True, report=report_path.relative_to(P).as_posix(),
                           report_sha256=sha(report_path), log=log.relative_to(P).as_posix(), captures=captures))
        print(json.dumps(dict(kind=kind, profile=profile, passed=True, checks=len(value['checks']), captures=len(captures))), flush=True)
    if args.section in ['all', 'details']:
        jobs = [('mountain', 'campaign_1924_03', ['--focus-point', '16848,7000', '--capture-zoom', '1.05']),
                ('coast', 'campaign_1924_03', ['--focus-city', 'shanhaiguan', '--capture-zoom', '.88']),
                ('village', 'campaign_1924_03', ['--focus-place', 'place_dongjiakou', '--capture-zoom', '1.15']),
                ('tributaries', 'campaign_1924_03', ['--focus-point', tributary_point('jingfeng'), '--capture-zoom', '1.15']),
                ('yangtze', 'legion_07', ['--focus-city', 'hankou', '--capture-zoom', '1.05']),
                ('nanjing', 'legion_08', ['--focus-city', 'nanjing', '--capture-zoom', '1.05']),
                ('yangtze_x30', 'legion_07', ['--focus-city', 'hankou', '--capture-zoom', '1.05',
                                           '--ui-scale', '1.2', '--mobile-ui-test'])]
        captures = []
        for name, scenario, extra in jobs:
            folder = P / 'reports/screenshots/terrain_surfaces_native/details'
            folder.mkdir(parents=True, exist_ok=True)
            path = folder / (name + '.png')
            log = P / 'reports' / ('terrain_detail_' + name + '.log')
            resolution = '2400x1080' if name.endswith('_x30') else '1920x1080'
            command = [str(exe), '--resolution', resolution, '--position', '-4000,-3000', '--',
                       '--qa-session', '--scenario', scenario, *extra, '--capture', '--capture-path', str(path)]
            started = datetime.now(timezone.utc).timestamp()
            with log.open('w', encoding='utf-8') as stream:
                result = subprocess.run(command, cwd=P, stdout=stream, stderr=subprocess.STDOUT, timeout=240)
            diagnostic = log.read_text(encoding='utf-8', errors='replace')
            meta = read(path.with_suffix('.json'))
            require(result.returncode == 0 and 'SCRIPT ERROR:' not in diagnostic and '\nERROR:' not in diagnostic,
                    'Native detail failed: ' + name)
            require(meta['build_version'] == version and meta['raw_godot_capture'] and meta['qa_save_isolated']
                    and path.stat().st_mtime >= started - 2, 'Current native detail required: ' + name)
            visible = meta['map_bank_visible']
            require(visible['current_total_map_assets'] == 970, 'Current complete map library required')
            with Image.open(path) as im:
                require(im.size == tuple(map(int, resolution.split('x'))), 'Wrong detail viewport: ' + name)
            rivers = visible['hydrography']['river_surface']
            if name == 'tributaries':
                require(visible['hydrography']['visible_fine_reaches'] > 0, 'Actual source tributaries must be visible')
                require(rivers['drawn_antialiased_headwaters'] > 0, 'Fine source streams must be drawn continuously')
            if name in ['yangtze', 'nanjing', 'yangtze_x30']:
                require(rivers['drawn_gradient_ribbons'] > 0 and rivers['drawn_textured_ribbons'] > 0,
                        'Primary gradient water and immutable water texture must be drawn')
                require(visible['hydrography']['source_linked_endpoint_frames'] > 0
                        and visible['hydrography']['source_endpoints_preserved']
                        and not rivers['measured_banks_claimed'], 'Source-linked symbolic river evidence required')
            if name == 'mountain':
                require(visible['distinct_scenery_originals_intersecting_view'] >= 30 and
                        visible['same_source_pairs_under_250_world_units'] == 0, 'Native scenery diversity regressed')
            captures.append(dict(file=path.relative_to(P).as_posix(), sha256=sha(path),
                                 resolution=resolution,
                                 metadata=path.with_suffix('.json').relative_to(P).as_posix(),
                                 metadata_sha256=sha(path.with_suffix('.json'))))
            print(json.dumps(dict(kind='details', profile=name, passed=True)), flush=True)
        groups.append(dict(kind='details', profile='windows_and_x30_layout', resolution='per-capture', passed=True, captures=captures))
    require(source_digest()[0] == runtime and sha(exe) == exported['sha256'], 'Native identity changed during capture')
    proof = dict(passed=True, version=version, created_at_utc=datetime.now(timezone.utc).isoformat(),
                 runtime_source_sha256=runtime, windows_exe_sha256=exported['sha256'],
                 source='Verified Windows release EXE; normal controls and published scenario geography',
                 groups=groups, raw_godot_captures=True, source_images_modified=False,
                 physical_android_device_tested=False, formal_art_approval=False, ew6_parity_claimed=False)
    suffix = '' if args.section == 'all' else '_' + args.section.replace('-', '_')
    path = P / 'reports' / ('terrain_surface_native_evidence' + suffix + '.json')
    path.write_text(json.dumps(proof, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
