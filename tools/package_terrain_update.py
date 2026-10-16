"""Ship the scoped terrain/UI beta with current executable-bound evidence.

The complete commercial-release gate remains package_delivery.py. This scope
requires all regressions, native UI/material captures, native capacity and APK
payload verification; it does not certify EW6 parity or a physical X30 device.
"""
from datetime import datetime, timezone
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import zipfile
from build_release import P, ROOT, current_version, source_digest, android_version_code
from run_validation import CHECKS
from regression_dependencies import modified
from package_delivery import read, sha, require, add_tree


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--prepare-summary', action='store_true', help='Validate core evidence and write its summary without creating delivery artifacts')
    args = parser.parse_args()
    version = current_version()
    tag = 'v' + version.replace('.', '')
    runtime, changed = source_digest()
    out = ROOT / 'output/releases' / ('railway-warlords-' + version)
    require(not (out / 'release_manifest.json').exists(), 'Published version is immutable; select a new version')
    fingerprint = read(P / 'reports/sample_state_v2.json')['content_hash']
    reports = set()
    regression = []
    for check in CHECKS:
        path = P / 'reports' / ('rule_tests.json' if check == 'run_tests' else check.removesuffix('_test') + '_tests.json')
        log = P / 'reports' / (check + '_' + tag + '.log')
        value = read(path)
        require(not value.get('failed', 0) and not value.get('failures', []), 'Failing regression: ' + check)
        require(min(path.stat().st_mtime, log.stat().st_mtime) >= modified(check), 'Stale regression: ' + check)
        require(value.get('content_hash', fingerprint) == fingerprint, 'Wrong regression content: ' + check)
        diagnostic = log.read_text(encoding='utf-8', errors='replace')
        require('SCRIPT ERROR:' not in diagnostic and '\nERROR:' not in diagnostic, 'Regression diagnostic failure')
        regression.append(dict(group=check, passed_checks=len(value['checks']),
                               report=path.relative_to(P).as_posix(), sha256=sha(path)))
        reports.update([path, log])
    seal = read(P / 'reports/regression_dependency_evidence.json')
    require(seal['passed'] and seal['runtime_source_sha256'] == runtime and len(seal['checks']) == len(CHECKS),
            'Current complete dependency seal required')
    required = ['regression_dependency_evidence.json', 'resource_validation.json',
                'terrain_surface_generation.json', 'terrain_surface_installation.json',
                'terrain_surface_geography.json', 'terrain_surface_geography_audit.json',
                'terrain_surface_asset_audit.json', 'terrain_surface_source_review.json',
                'ground_macro_generation.json', 'ground_macro_asset_audit.json', 'ground_macro_source_review.json',
                'ground_identity_generation.json', 'ground_identity_source_review.json', 'ground_identity_installation.json',
                'ground_identity_native_review.json',
                'terrain_surface_native_evidence.json', 'river_surface_native_review.json', 'apk_content_validation.json',
                'control_land_clip_audit.json', 'control_land_native_evidence.json', 'control_land_native_review.json',
                'ground_continuity_native_evidence.json', 'relief_shade_native_evidence.json',
                'relief_shade_native_review.json', 'map_symbol_native_evidence.json', 'map_symbol_native_review.json',
                'unit_layer_native.json', 'unit_layer_pixel_validation.json']
    for name in required:
        path = P / 'reports' / name
        require(read(path).get('passed') is True, 'Required evidence failed: ' + name)
        reports.add(path)
    layers = read(P / 'reports/unit_layer_native.json')
    pixels = read(P / 'reports/unit_layer_pixel_validation.json')
    require(layers['version'] == pixels['version'] == version and layers['qa_save_isolated']
            and pixels['runtime_source_sha256'] == runtime and len(layers['cases']) == len(pixels['cases']) == 4,
            'Current native source-engine cache/direct comparison required')
    for case, comparison in zip(layers['cases'], pixels['cases']):
        paths = [P / case[key].removeprefix('res://') for key in ('cached', 'direct')]
        require(case['name'] == comparison['name'] and comparison['passed']
                and [sha(path) for path in paths] == comparison['native_images_sha256'],
                'Native cache/direct viewport changed')
    reports.add(P / 'reports/unit_layer_native.log')
    native = read(P / 'reports/terrain_surface_native_evidence.json')
    require(native['version'] == version and native['runtime_source_sha256'] == runtime and len(native['groups']) == 6,
            'Current complete native terrain/UI evidence required')
    river_review = read(P / 'reports/river_surface_native_review.json')
    require(river_review['version'] == version and river_review['runtime_source_sha256'] == runtime
            and river_review['windows_exe_sha256'] == native['windows_exe_sha256'], 'Current native river image review required')
    for row in river_review['images']:
        require(sha(P / row['file']) == row['sha256'], 'Reviewed river viewport changed: ' + row['file'])
    river_report = read(P / 'reports/river_surface_tests.json')
    require(river_report['passed'] and river_report['build_version'] == version
            and river_report['replacement_reaches_checked'] == 31, 'Current source river continuity regression required')
    captures = set()
    for group in native['groups']:
        require(group['passed'], 'Native profile failed')
        if 'report' in group:
            path = P / group['report']
            require(sha(path) == group['report_sha256'] and read(path)['passed'], 'Native profile report changed')
            reports.update([path, P / group['log']])
        for row in group['captures']:
            path = P / row['file']; metadata = P / row['metadata']
            require(sha(path) == row['sha256'] and sha(metadata) == row['metadata_sha256'], 'Native capture changed')
            require(read(metadata)['build_version'] == version, 'Old capture in current native proof')
            captures.update([path, metadata])
    require(len(captures) == 92 * 2, 'Complete current 92-view native evidence required')
    control = read(P / 'reports/control_land_native_evidence.json')
    clip_sha = sha(P / 'presentation/data/control_land_clip.json')
    require(control['version'] == version and control['runtime_source_sha256'] == runtime
            and control['windows_exe_sha256'] == native['windows_exe_sha256'] and control['clip_data_sha256'] == clip_sha
            and len(control['groups']) == 2, 'Current normal-renderer coastal control evidence required')
    clip_audit = read(P / 'reports/control_land_clip_audit.json')
    clip_test = read(P / 'reports/control_land_clip_tests.json')
    require(clip_audit['presentation_data_sha256'] == clip_sha and clip_audit['exact_triangle_coverage_verified']
            and clip_audit['disjoint_islands_and_water_holes_verified'] and not clip_audit['source_maps_modified']
            and clip_audit['clipped_city_zones'] == 61 and clip_audit['partial_field_cells'] == 617,
            'Real-source coastal vector audit required')
    require(clip_test['passed'] and clip_test['build_version'] == version and clip_test['timelines_checked'] == 7
            and clip_test['presentation_data_sha256'] == clip_sha, 'Current seven-timeline coastal regression required')
    review = read(P / 'reports/control_land_native_review.json')
    require(review['version'] == version and review['runtime_source_sha256'] == runtime
            and review['windows_exe_sha256'] == native['windows_exe_sha256'], 'Current native coastal image review required')
    for row in review['images']:
        require(sha(P / row['file']) == row['sha256'], 'Reviewed coastal viewport changed: ' + row['file'])
    for group in control['groups']:
        require(len(group['cases']) == 5 and len(group['captures']) == 10, 'Incomplete coast viewport set')
        require(all(row['water_max_channel_delta'] <= 2 and row['minimap_water_max_channel_delta'] <= 2
                    and row['water_pixels'] >= 9 and row['minimap_water_pixels'] >= 12 and row['land_changed_samples'] >= 3
                    for row in group['cases']), 'Coast pixels changed on actual water or land wash disappeared')
        report_path = P / group['report']
        require(sha(report_path) == group['report_sha256'] and read(report_path)['passed'], 'Coast report changed')
        reports.update([report_path, P / group['log']])
        for row in group['captures']:
            path = P / row['file']; metadata = P / row['metadata']
            require(sha(path) == row['sha256'] and sha(metadata) == row['metadata_sha256']
                    and read(metadata)['build_version'] == version, 'Coast viewport changed')
            captures.update([path, metadata])
    require(len(captures) == 112 * 2, 'Complete current 112-view terrain/UI/coast evidence required')
    symbols = read(P / 'reports/map_symbol_native_evidence.json')
    require(symbols['version'] == version and symbols['runtime_source_sha256'] == runtime
            and symbols['windows_exe_sha256'] == native['windows_exe_sha256'] and len(symbols['groups']) == 2
            and symbols['visible_formation_identity_verified'] and symbols['compact_counter_selection_verified']
            and symbols['small_zoom_cache_crossings_verified'], 'Current native map-symbol proof required')
    for group in symbols['groups']:
        path = P / group['report']; log = P / group['log']
        require(sha(path) == group['report_sha256'] and read(path)['passed']
                and sha(log) == group['log_sha256'], 'Map-symbol evidence changed')
        reports.update([path, log])
        require(len(group['captures']) == 16 and group['checks'] == 110, 'Both full native symbol profiles required')
        for row in group['captures']:
            path = P / row['file']; metadata = P / row['metadata']
            require(sha(path) == row['sha256'] and sha(metadata) == row['metadata_sha256']
                    and read(metadata)['build_version'] == version, 'Native symbol frame changed')
            captures.update([path, metadata])
    require(len(captures) == 144 * 2, 'Current 144-view terrain/UI/coast/symbol evidence required')
    symbols_review = read(P / 'reports/map_symbol_native_review.json')
    require(symbols_review['version'] == version and symbols_review['runtime_source_sha256'] == runtime
            and symbols_review['windows_exe_sha256'] == native['windows_exe_sha256'], 'Current symbol image review required')
    for row in symbols_review['images']:
        require(row['viewed_complete_native_frame'] and sha(P / row['file']) == row['sha256'], 'Reviewed symbol frame changed')
    ground = read(P / 'reports/ground_continuity_native_evidence.json')
    require(ground['version'] == version and ground['runtime_source_sha256'] == runtime
            and ground['windows_exe_sha256'] == native['windows_exe_sha256'] and ground['checks'] == 44
            and ground['twenty_whole_originals_verified'] and ground['same_family_coverage_verified']
            and ground['three_material_draw_order_verified'] and ground['world_phase_verified'],
            'Current complete native continuous-ground fixture proof required')
    for name, key in [('report', 'report_sha256'), ('log', 'log_sha256')]:
        path = P / ground[name]
        require(sha(path) == ground[key], 'Native material proof changed')
        reports.add(path)
    lighting = read(P / 'reports/relief_shade_native_evidence.json')
    require(lighting['version'] == version and lighting['runtime_source_sha256'] == runtime
            and lighting['windows_exe_sha256'] == native['windows_exe_sha256'] and lighting['checks'] == 11
            and lighting['independent_sixteen_weight_reference_verified']
            and lighting['triangle_diagonal_independence_verified'] and lighting['world_phase_verified']
            and lighting['new_dem_samples'] == 0 and len(lighting['captures']) == 4,
            'Current independent native relief-lighting proof required')
    for name, key in [('report', 'report_sha256'), ('log', 'log_sha256')]:
        path = P / lighting[name]
        require(sha(path) == lighting[key], 'Native lighting proof changed')
        reports.add(path)
    fixture_captures = set()
    for row in lighting['captures']:
        path = P / row['file']
        require(sha(path) == row['sha256'] and row['whole_native_viewport']
                and row['synthetic_fixture_not_gameplay'], 'Numerical fixture changed')
        fixture_captures.add(path)
    lighting_review = read(P / 'reports/relief_shade_native_review.json')
    require(lighting_review['version'] == version and lighting_review['runtime_source_sha256'] == runtime
            and lighting_review['windows_exe_sha256'] == native['windows_exe_sha256'],
            'Current whole-map lighting/river image review required')
    for row in lighting_review['images']:
        require(row['viewed_complete_native_frame'] and sha(P / row['file']) == row['sha256'],
                'Reviewed relief/river viewport changed')
    require(all(row['city_influence_fill_draws'] == 0 and row['field_fill_batches'] > 0
                and row['continuous_ground_shader_active'] for group in control['groups'] for row in group['cases']),
            'Continental controls must not stack city-influence fills over the field')
    details = next(group for group in native['groups'] if group['kind'] == 'details')
    detail_rows = {Path(row['file']).stem:row for row in details['captures']}
    for name in ['yangtze', 'nanjing', 'yangtze_x30']:
        require(name in detail_rows, 'Current source-linked river viewport required: ' + name)
        hydro = read(P / detail_rows[name]['metadata'])['map_bank_visible']['hydrography']
        require(hydro['source_endpoints_preserved'] and hydro['source_linked_endpoint_frames'] > 0
                and hydro['river_surface']['drawn_textured_ribbons'] > 0, 'Primary river render proof missing: ' + name)
    for name in ['mountain', 'tributaries', 'yangtze', 'nanjing', 'yangtze_x30']:
        meta = read(P / detail_rows[name]['metadata'])['map_bank_visible']
        require(meta['terrain_surface_extension']['relief_lighting']['shader_active']
                and meta['hydrography']['river_surface']['detail_banks_drawn_before_water'],
                'Normal-renderer continuous relief or river passes missing: ' + name)
    exports = read(P / 'reports/export_results.json')
    require({row['target'] for row in exports} == {'windows', 'android'}, 'Both verified exports required')
    for row in exports:
        require(row['export_verified'] and row['runtime_source_sha256'] == runtime and sha(Path(row['path'])) == row['sha256'],
                'Export identity mismatch: ' + row['target'])
    exe = P / 'build/windows/RailwayWarlords.exe'
    apk = P / 'build/android/RailwayWarlords.apk'
    require(native['windows_exe_sha256'] == sha(exe), 'Native capture EXE differs from current export')
    apk_proof = read(P / 'reports/apk_content_validation.json')
    assets = read(P / 'assets/manifest.json')['assets']
    require(apk_proof['artifact_sha256'] == sha(apk) and not apk_proof['private_files_detected']
            and len(apk_proof['raster_import_files_verified']) == len(assets), 'APK proof is stale or incomplete')
    require(all(row['current_import_bytes_match'] for row in apk_proof['raster_import_files_verified']), 'APK import mismatch')
    badging = (P / 'reports/apk_badging.log').read_text(encoding='utf-8')
    require(f"versionName='{version}'" in badging and f"versionCode='{android_version_code()}'" in badging, 'Wrong APK version')
    catalog = read(P / 'presentation/data/terrain_surface_catalog.json')
    require(len(catalog['types']) == 20 and len(catalog['records']) == 80, 'Twenty types and eighty originals required')
    provenance = read(P / 'docs/asset-provenance/index.json')
    require(provenance['count'] == len(assets) == 1176, 'Current portable provenance is incomplete')
    require(len({r['source_sha256'] for r in catalog['records'].values()}) == 80, 'Duplicate new originals')
    macros=read(P/'presentation/data/ground_macro_catalog.json')
    require(set(macros['records']) == set(catalog['types']) and len({row['source_sha256'] for row in macros['records'].values()})==20,
            'Twenty matching continuous-ground originals required')
    require(read(P/'reports/ground_macro_source_review.json')['all_twenty_originals_viewed'], 'New ground visual review missing')
    identity = read(P/'reports/ground_identity_generation.json')
    identity_review = read(P/'reports/ground_identity_source_review.json')
    installation = read(P/'reports/ground_identity_installation.json')
    active_ids = {row['asset_id'] for row in macros['records'].values()}
    retained_ids = set(macros['superseded_asset_ids'])
    stored_map_ids = {row['id'] for row in assets if row['category'] in {'building','scenery','tile'}}
    require(len(stored_map_ids) == 990 and len(stored_map_ids - retained_ids) == 970,
            'Stored and active map inventory must match the registered assets')
    require(identity['version'] == installation['version'] == identity_review['version'] == version
            and identity['completed'] == identity['requested'] == 20
            and identity['source_route'] == 'sub2-image-gen/gpt-image-2.5/high'
            and identity['source_plan_sha256'] == macros['source_plan_sha256']
                == sha(P / macros['source_plan_file'])
            and {row['id'] for row in identity['assets']} == active_ids
            and len({row['source_sha256'] for row in identity['assets']}) == 20,
            'Twenty current independent Sub2 material originals required')
    reviewed = {row['id']: row for row in identity_review['originals']}
    require(identity_review['all_twenty_originals_viewed'] and set(reviewed) == active_ids,
            'Complete individual source-image review required')
    registered = {row['id']: row for row in assets}
    for row in identity['assets']:
        require(row['source_sha256'] == reviewed[row['id']]['sha256']
                == registered[row['id']]['source_sha256']
                == sha(P / registered[row['id']]['engine_path'].removeprefix('res://')),
                'Material original changed: ' + row['id'])
    require(len(retained_ids) == 20 and retained_ids.isdisjoint(active_ids)
            and retained_ids <= set(registered) and macros['original_pngs_retained']
            and installation['installed_new_originals'] == installation['active_macro_originals'] == 20
            and installation['stored_superseded_originals'] == 20
            and installation['geography_sha256'] == sha(P/'presentation/data/terrain_surface_regions.json')
            and not installation['geography_assignments_changed']
            and read(P/'reports/ground_macro_asset_audit.json')['stored_superseded_originals_verified'] == 20,
            'Retained immutable originals and unchanged geographical assignments required')
    material_review = read(P/'reports/ground_identity_native_review.json')
    require(material_review['version'] == version and material_review['runtime_source_sha256'] == runtime
            and material_review['windows_exe_sha256'] == native['windows_exe_sha256']
            and set(material_review['active_material_ids']) == active_ids
            and material_review['world_repeat_period'] == macros['world_repeat_period'] == 128
            and material_review['all_twenty_material_cards_viewed'],
            'Current material-card and historical-map inspection required')
    for row in material_review['images']:
        require(row['viewed_complete_native_frame'] and sha(P/row['file']) == row['sha256'],
                'Reviewed material viewport changed')
    for row in provenance['assets']:
        require(sha(P / row['image']) == row['image_sha256'] and sha(P / row['prompt']) == row['prompt_sha256'],
                'Portable image or prompt changed: ' + row['id'])
    capacity = []
    for profile in ['windows', 'x30']:
        path = P / 'reports' / f'capacity_{profile}_{tag}.json'
        value = read(path)
        require(value['render_target_passed'] and value['game_version'] == version and value['runtime_source_sha256'] == runtime
                and value['windows_exe_sha256'] == sha(exe) and path.stat().st_mtime >= changed,
                'Current native capacity proof required: ' + profile)
        reports.add(path)
        capacity.append(dict(profile=profile, file=path.relative_to(P).as_posix(), sha256=sha(path)))
    reports.update(P / 'reports' / name for name in ['sample_state_v2.json', 'export_results.json', 'import_budgets.json',
                   'apk_signature.log', 'apk_badging.log', 'apk_permissions.log', 'android_devices.log', 'desktop_benchmark.json'])
    summary = dict(passed=True, version=version, runtime_source_sha256=runtime, content_hash=fingerprint,
                   regression_groups=len(regression), regression_checks=sum(int(r['passed_checks']) for r in regression),
                   terrain_types=20, detail_originals=80, macro_originals=20, new_independent_originals=20,
                   stored_superseded_macro_originals=20, material_identity_revision=macros['material_identity_revision'],
                   material_world_repeat_period=128, new_material_source_images_reviewed=20, native_material_cards_viewed=20,
                   river_replacement_reaches=31, source_linked_river_continuity_verified=True,
                   total_rasters=len(assets), total_map_assets=len(stored_map_ids - retained_ids), total_stored_map_assets=len(stored_map_ids),
                   native_groups=len(native['groups']), native_captures=92,
                   coastal_control_land_clipped=True, source_lake_islands_preserved=True,
                   continuous_ground_nonoverlapping=True, exclusive_continental_control_fill=True,
                   native_material_fixture_checks=ground['checks'],
                   native_relief_fixture_checks=lighting['checks'], native_relief_fixture_captures=4,
                   continuous_source_lighting_verified=True, layered_headwaters_verified=True,
                   native_map_symbol_checks=symbols['checks'], map_symbol_native_captures=32,
                   source_engine_cache_direct_native_pairs=4,
                   visible_individual_formations_preserved=True, compact_counter_selection_verified=True,
                   control_native_groups=len(control['groups']), control_native_captures=20, total_native_captures=len(captures)//2,
                   current_native_capacity=True, full_ai_endurance_rerun=False,
                   physical_android_device_tested=False, formal_art_approval=False, ew6_parity_claimed=False)
    write(P / 'reports/terrain_update_verification_summary.json', summary)
    reports.add(P / 'reports/terrain_update_verification_summary.json')
    if args.prepare_summary:
        print(json.dumps(summary), flush=True)
        return
    repository_path = P / 'reports/repository_validation.json'
    repository = read(repository_path)
    require(repository['passed'] and repository['version'] == version and repository['runtime_source_sha256'] == runtime,
            'Current repository validation is required')
    reports.add(repository_path)
    out.mkdir(parents=True, exist_ok=True)
    portable = out / 'Windows便携版'; portable.mkdir(exist_ok=True)
    shutil.copyfile(exe, portable / exe.name)
    (portable / 'README.md').write_text(f'''# 铁道烽烟 {version}

运行 RailwayWarlords.exe，无需安装 Godot。
20 类地域地表各有 1 张连续底材与 4 张细节原图；说明书内可打开地形图鉴。
本版启用 20 张新生成的连续底材：草叶、针叶、砂纹、砾石、苔藓等具有独立形态。旧 20 张底材保留归档。沿用连续光影、分层细河岸带与按缩放切换的城市/部队图符。
点选部队、选目标、再次点击确认；拖动平移、滚轮缩放、空格跳过战斗演出。
本版为可玩测试交付，X30 真机与完整 AI 长局尚未在本轮复验。
''', encoding='utf-8')
    legal = portable / 'licenses'; legal.mkdir(exist_ok=True)
    for path in (P / 'assets/legal').glob('*.txt'):
        shutil.copyfile(path, legal / path.name)
    windows = out / f'RailwayWarlords-Windows-{version}.zip'
    with zipfile.ZipFile(windows, 'w', zipfile.ZIP_DEFLATED, compresslevel=1) as archive:
        for path in sorted(portable.rglob('*')):
            if path.is_file(): archive.write(path, path.relative_to(portable).as_posix())
    android = out / f'RailwayWarlords-{version}.apk'; shutil.copyfile(apk, android)
    source = out / f'RailwayWarlords-Godot-Source-{version}.zip'
    with zipfile.ZipFile(source, 'w', zipfile.ZIP_DEFLATED, compresslevel=1) as archive:
        # Use exactly the public file set already inspected by verify_repository;
        # retain old versioned media references as well as current evidence.
        raw = subprocess.check_output(['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'], cwd=P)
        public = {P / name.decode('utf-8') for name in raw.split(b'\0') if name}
        for path in sorted(public | reports | captures | fixture_captures):
            if not path.is_file(): continue
            require(not any(part in {'.git','.godot','.toolchain','build','__pycache__','signing'} for part in path.relative_to(P).parts),
                    'Private or generated directory in source archive')
            archive.write(path, path.relative_to(ROOT).as_posix())
        add_tree(archive, ROOT / 'design', ROOT,
                 allowed={'.md', '.json', '.py', '.csv', '.txt', '.png', '.shp', '.shx', '.dbf', '.prj', '.cpg', '.html', '.xml', '.zip', '.tif', '.pdf'})
    for path in [windows, source]:
        with zipfile.ZipFile(path) as archive:
            require(archive.testzip() is None, 'Corrupt archive: ' + path.name)
    with zipfile.ZipFile(windows) as archive:
        require(hashlib.sha256(archive.read(exe.name)).hexdigest() == sha(exe), 'Windows archive differs from tested EXE')
    require(sha(android) == sha(apk) and source_digest()[0] == runtime, 'Delivery identity changed')
    manifest = dict(version=version, created_at_utc=datetime.now(timezone.utc).isoformat(),
                    release_kind='scoped_material_identity_terrain_beta', **{k:v for k,v in summary.items() if k not in ['version','passed']},
                    regression=regression, capacity=capacity, source_pngs_modified=False, manual_image_compositing=False,
                    source_image_location='game/railway_warlords/assets; byte-identical generated originals, portable prompt/provenance copies in docs',
                    original_production_tree_duplicated=False, old_releases_modified=False,
                    reports=[dict(file=p.relative_to(P).as_posix(), sha256=sha(p)) for p in sorted(reports)],
                    native_evidence_sha256=sha(P / 'reports/terrain_surface_native_evidence.json'),
                    artifacts=[dict(file=p.name, bytes=p.stat().st_size, sha256=sha(p)) for p in [windows, android, source]],
                    archive_integrity_verified=True)
    write(out / 'release_manifest.json', manifest)
    shutil.copyfile(P / 'docs/30_二十类地域地表与纹理整改.md', out / '二十类地域地表与纹理整改.md')
    shutil.copyfile(P / 'docs/31_连续地表与水系层次.md', out / '连续地表与水系层次.md')
    shutil.copyfile(P / 'docs/32_真实河段连续水面.md', out / '真实河段连续水面.md')
    shutil.copyfile(P / 'docs/33_真实海岸与控制区裁切.md', out / '真实海岸与控制区裁切.md')
    shutil.copyfile(P / 'docs/34_连续地表混合与控制色去重.md', out / '连续地表混合与控制色去重.md')
    shutil.copyfile(P / 'docs/35_地图缩放层次与精确点选.md', out / '地图缩放层次与精确点选.md')
    shutil.copyfile(P / 'docs/36_连续高程光影与细河岸带.md', out / '连续高程光影与细河岸带.md')
    shutil.copyfile(P / 'docs/37_二十类地表材质形态重制.md', out / '二十类地表材质形态重制.md')
    (out / '交付说明.md').write_text(f'''# 铁道烽烟 {version} · 地表与界面测试交付

Windows：解压 RailwayWarlords-Windows-{version}.zip，运行 RailwayWarlords.exe。
Android：安装 RailwayWarlords-{version}.apk，延续现有签名。目标样机 Motorola X30 尚未完成物理验收。
Godot：解压工程 ZIP，用 Godot 4.7.2 打开 game/railway_warlords/project.godot。

20 类地域地表的连续底材已全部重制：新增 20 张独立 Sub2 原图，各具草叶、针叶、砂纹、砾石、盐壳或岩板等结构。与既有 80 张细节原图合计 100 张启用专用地表原图。旧 20 张连续底材保留原始字节、ID、提示词及来源，未重复计入新增量或启用量。全部 PNG 共 1,176 张；存储的地图素材 990 张，其中当前启用 970 张。
新底材继续使用既有生态区、高程和河谷分配，不把示意材质当成逐年历史土地利用调查；规则地形仍为 12 类。沿用连续正权重高程光照及分层细河岸带，没有添加DEM采样或改写源地形。所有细河先画岸带再画水面，源河段端点与既有60米显示约束保持。沿用按缩放切换的独立城市/编队图符和精确点选。
沿用上一轮的不重叠地表网格和三种相邻来源连续混合；各地图总览仍显示地域底材。亚洲控制区不再重复叠加城市影响色。44项原生材质夹具检查核对20种完整导入纹理、连续覆盖、绘制顺序和平移稳定性；夹具不冒充历史地图画面。
沿用共享世界纹理的渐变主河水面；汉口、南京的31条替代主河使用既有60米有界显示圆角，上下游共用端点共享接头方向。河宽与岸带是制图符号，不是历史实测岸线。另有11项原生数值夹具检查核对GPU与独立16权重计算、三角方向和镜头平移；4张夹具画面单列，不作为实机地图画面。
沿用上一轮依据既有真实陆地裁切的亚洲战略层控制区：61个城市影响区和617个沿海控制格保留实际陆地部分，14个完全离岸候选格不绘制；主地图与缩略图共享裁切网格。里海水面扣除来源中独立的岛屿，保留真实湖中陆地。地理数据、历史归属和规则格未重写。
说明书与地格详情均可进入交互地形图鉴。材质按生态区、高程与既有河谷选取；不宣称逐年历史土地利用复原。

当前 {summary['regression_groups']} 组 / {summary['regression_checks']} 项回归通过；92张地表/UI及局部地图、20张海岸控制层开关和32张缩放/点选专项截图，共144张原生画面、双桌面视口容量与APK载荷已绑定本次EXE/源码哈希。五处海岸/总览的主图和缩略图水面像素均经开关对照。地图图符专项通过{symbols['checks']}项原生检查。
截图为 Windows 原生程序；README 的战斗 GIF 保留 0.2.12 原录像身份。本轮未重新宣称完整 AI 长局、正式美术/历史批准或《欧陆战争6》商业品质达标。

工程内的 PNG 即原始生成字节，提示词与便携来源索引位于 docs；原始 GIS 归档随 design 保留。不包含引擎缓存、签名、素材网关凭据或重复原图树。
完整校验值及实际范围见 release_manifest.json。旧版本交付保持不变。
''', encoding='utf-8')
    print(json.dumps(dict(passed=True, release=str(out), artifacts=manifest['artifacts']), ensure_ascii=True), flush=True)


if __name__ == '__main__':
    main()
