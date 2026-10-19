"""Deliver the scoped military UI update without weakening prior release gates."""
from datetime import datetime, timezone
import hashlib
import json
import shutil
import subprocess
import zipfile
from build_release import P, ROOT, current_version, source_digest, android_version_code
from package_delivery import read, sha, require, add_tree
from regression_dependencies import identity
from verify_git_bytes import inspect as inspect_git_bytes


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def validate(scope='dossier'):
    require(scope in {'dossier', 'atlas_office', 'ground_atlas', 'coast_detail'}, 'Unknown scoped delivery')
    atlas_scope = scope in {'atlas_office', 'ground_atlas', 'coast_detail'}
    ground_scope = scope in {'ground_atlas', 'coast_detail'}
    expected_rasters = 1324 if ground_scope else 1304
    version = current_version()
    runtime = source_digest()[0]
    exe = P / 'build/windows/RailwayWarlords.exe'
    apk = P / 'build/android/RailwayWarlords.apk'
    exports = read(P / 'reports/export_results.json')
    for target, path in [('windows', exe), ('android', apk)]:
        row = next(r for r in exports if r['target'] == target)
        require(row['export_verified'] and row['runtime_source_sha256'] == runtime
                and row['sha256'] == sha(path), 'Current verified export required: ' + target)
    deps = read(P / 'reports/regression_dependency_evidence.json')
    require(deps['passed'] and deps['game_version'] == version
            and deps['runtime_source_sha256'] == runtime and len(deps['checks']) == 29,
            'Complete current regression seal required')
    reports = set()
    regression = []
    for row in deps['checks']:
        require(row['passed'] and identity(row['check'])[0] == row['dependency_sha256_at_seal'],
                'Regression dependency changed: ' + row['check'])
        report = P / 'reports' / row['report']
        log = P / 'reports' / row['log']
        require(sha(report) == row['report_sha256'] and sha(log) == row['log_sha256'], 'Regression evidence changed')
        value = read(report)
        require(not value.get('failed', 0) and not value.get('failures', []), 'Failed regression report')
        reports.update([report, log])
        regression.append(dict(name=row['check'], checks=len(value['checks']), report=report.relative_to(P).as_posix(), sha256=sha(report)))
    calendar = read(P / 'reports/calendar_tests.json')
    calendar_checks = 88 if atlas_scope else 85
    require(calendar['passed'] and len(calendar['checks']) == calendar_checks, 'Complete daily-calendar registrations required')
    portraits = read(P / 'presentation/data/general_portraits.json')
    assets = read(P / 'assets/manifest.json')['assets']
    portrait_assets = [a for a in assets if a['category'] == 'portrait']
    require(portraits['production_complete'] and not portraits['missing_age_stages']
            and len(portraits['generals']) == 33 and len(portrait_assets) == 135 and len(assets) == expected_rasters,
            'Retained four-stage portraits or UI asset count differs')
    require(len({a['source_sha256'] for a in portrait_assets}) == 135, 'Independent portrait originals required')
    for gid, person in portraits['generals'].items():
        require({v['age_stage'] for v in person['variants']} == {'young', 'prime', 'middle', 'late'}, 'Missing stage: ' + gid)
        require(all(person['birth_year'] <= s['reference_year'] <= person['death_year'] for s in person['stages']), 'Posthumous stage: ' + gid)
        for variant in person['variants']:
            asset = next(a for a in portrait_assets if a['id'] == variant['asset_id'])
            require(sha(P / asset['engine_path'].removeprefix('res://')) == asset['source_sha256'] == variant['asset_sha256'],
                    'Retained portrait bytes changed')
    first = read(P / 'reports/general_portrait_first_source_review.json')
    age = read(P / 'reports/general_portrait_source_review.json')
    require(len(first['originals']) == 26 and len(age['originals']) == 97 and len(age['rejected_originals']) == 20,
            'Retained individual portrait source review incomplete')
    require(all(r['accepted'] and r['viewed_complete_original'] for r in first['originals'] + age['originals']), 'Unreviewed portrait included')
    art = read(P / 'reports/ui_refinement_source_review.json')
    expected_ui = {'ui_officer_sheet_v023', 'ui_command_plate_v023', 'icon_medal_marksmanship_v023',
                   'icon_medal_steadfast_v023', 'icon_medal_logistics_v023'}
    reviewed_ui_version = '0.2.23' if atlas_scope else version
    require(art['version'] == reviewed_ui_version and {r['id'] for r in art['originals']} == expected_ui
            and not art['source_images_modified'] and not art['manual_compositing'], 'Five direct Sub2 originals required')
    for row in art['originals']:
        asset = next(a for a in assets if a['id'] == row['id'])
        require(row['accepted'] and row['viewed_complete_original']
                and asset['source_kind'] == 'sub2_image_gen'
                and sha(P / asset['engine_path'].removeprefix('res://')) == row['sha256'] == asset['source_sha256'],
                'Unreviewed or modified UI original')
    captures = set()
    native_groups = []
    for name, expected in [('general_portrait_native_evidence.json', 3), ('terrain_surface_native_evidence.json', 6),
                           ('control_land_native_evidence.json', 2), ('map_symbol_native_evidence.json', 2),
                           ('ui_refinement_native_evidence.json', 3)]:
        path = P / 'reports' / name
        proof = read(path)
        require(proof['passed'] and proof['version'] == version and proof['runtime_source_sha256'] == runtime
                and proof['windows_exe_sha256'] == sha(exe) and len(proof['groups']) == expected, 'Current native proof required: ' + name)
        reports.add(path)
        for group in proof['groups']:
            if group.get('report'):
                report = P / group['report']
                require(sha(report) == group['report_sha256'], 'Native report changed')
                reports.add(report)
            else:
                require(name == 'terrain_surface_native_evidence.json' and group['kind'] == 'details'
                        and group['passed'], 'Unexpected native group without an aggregate report')
            if group.get('log'):
                reports.add(P / group['log'])
            for row in group['captures']:
                image = P / row['file']
                meta = P / row['metadata']
                require(sha(image) == row['sha256'] and sha(meta) == row['metadata_sha256'], 'Untouched native capture required')
                captures.update([image, meta])
        native_groups.append(dict(name=name, captures=sum(len(g['captures']) for g in proof['groups']),
                                  checks=sum(g.get('checks', 0) for g in proof['groups'])))
    dossier = read(P / 'reports/ui_refinement_native_evidence.json')
    require(dossier['actual_profile_transactions'] and not dossier['physical_android_device_tested'], 'Scoped real UI transaction evidence required')
    for group in dossier['groups']:
        require(read(P / group['report'])['isolated_profile_restored'], 'QA profile not restored')
    apk_report = read(P / 'reports/apk_content_validation.json')
    require(apk_report['passed'] and apk_report['artifact_sha256'] == sha(apk) and not apk_report['private_files_detected']
            and len(apk_report['raster_import_files_verified']) == expected_rasters
            and all(r['current_import_bytes_match'] for r in apk_report['raster_import_files_verified']), 'Current APK payload proof required')
    require(len(apk_report['instrumental_music_imports_verified']) == 3
            and all(r['current_import_bytes_match'] for r in apk_report['instrumental_music_imports_verified']), 'APK score payload required')
    signed = (P / 'reports/apk_signature.log').read_text(encoding='utf-8')
    require('Verified using v2 scheme (APK Signature Scheme v2): true' in signed
            and 'Verified using v3 scheme (APK Signature Scheme v3): true' in signed, 'APK signature required')
    music = read(P / 'reports/music_native_tests.json')
    require(music['passed'] and music['runtime_source_sha256'] == runtime
            and music['windows_exe_sha256'] == sha(exe) and len(music['checks']) == 18, 'Current native music proof required')
    resources = read(P / 'reports/resource_validation.json')
    require(resources['passed'] and resources['raster_count'] == expected_rasters and resources['scenarios'] == 61, 'Source integrity required')
    repo = read(P / 'reports/repository_validation.json')
    require(repo['passed'] and repo['version'] == version and repo['runtime_source_sha256'] == runtime
            and repo['verified_images_and_prompts'] == expected_rasters, 'Current repository audit required')
    git_bytes = read(P / 'reports/git_byte_preservation.json')
    require(git_bytes['passed'] and git_bytes['version'] == version
            and git_bytes['runtime_source_sha256'] == runtime, 'Current Git byte-preservation receipt required')
    git_count, git_errors = inspect_git_bytes(include_receipt=True)
    require(git_count > 0 and not git_errors, 'Staged Git blobs differ from tested working files')
    audit = read(P / 'reports/daily_age_text_audit.json')
    require(audit['passed'] and audit['version'] == version and audit['runtime_source_sha256'] == runtime
            and not audit['legacy_display_name_plaintext_files'], 'Current display-name audit required')
    visual_name = {'coast_detail': 'coast_detail_native_review.json', 'ground_atlas': 'ground_atlas_native_review.json', 'atlas_office': 'atlas_office_native_review.json',
                   'dossier': 'ui_refinement_native_review.json'}[scope]
    visual = read(P / 'reports' / visual_name)
    require(visual['version'] == version and visual['runtime_source_sha256'] == runtime
            and visual['windows_exe_sha256'] == sha(exe) and len(visual['viewed_complete_captures']) >= 8,
            'Current scoped visual inspection required')
    for row in visual['viewed_complete_captures']:
        require(sha(P / row['file']) == row['sha256'] and row['viewed_complete_original_capture'], 'Inspected native capture changed')
    if atlas_scope:
        terrain_proof = read(P / 'reports/terrain_surface_native_evidence.json')
        offices = [g for g in terrain_proof['groups'] if g['kind'] == 'war-room']
        require(len(offices) == 3, 'Three current office/atlas layouts required')
        for group in offices:
            proof = read(P / group['report'])
            by_surface = {r['surface']: r for r in proof['captures']}
            require(len(by_surface) == 16 and {'campaign_detail', 'multi_diplomacy', 'aid_pending'} <= by_surface.keys(),
                    'Full atlas interaction and diplomacy transaction captures required')
            preview = by_surface['campaign']['atlas_preview']
            require(preview['renderer'] == 'shipping_MapView_static_atlas' and preview['source_map_immutable']
                    and preview['ground']['active'] and preview['material_cells_drawn'] > 0
                    and preview['scenery_drawn'] > 0, 'Shipping preview ground and whole scenery must actually be drawn')
            require(by_surface['campaign_detail']['atlas_preview']['zoom_multiplier'] > 2,
                    'Actual zoomed native preview required')
            require(all(row['passed'] for row in proof['checks']), 'Office interaction/transaction checks failed')
    if ground_scope:
        require(version == ('0.2.26' if scope == 'coast_detail' else '0.2.25'), 'Scoped map specification/version mismatch')
        catalog = read(P / 'presentation/data/ground_macro_catalog.json')
        source_review = read(P / 'reports/ground_atlas_source_review.json')
        require(catalog['world_repeat_period'] == 224 and catalog['superseded_originals'] == 40
                and len(catalog['records']) == 20, 'Twenty quiet grounds and forty preserved originals required')
        reviewed = {r['id']: r for r in source_review['originals']}
        plan = read(P / catalog['source_plan_file'])
        require(source_review['all_twenty_originals_viewed'] and len(reviewed) == len(plan['assets']) == 20,
                'Complete individual quiet-source reviews required')
        for item in plan['assets']:
            original = next(a for a in assets if a['id'] == item['id'])
            viewed = reviewed[item['id']]
            require(viewed['viewed_complete_original'] and viewed['accepted_for_runtime_trial']
                    and original['source_kind'] == 'sub2_image_gen'
                    and original['source_sha256'] == viewed['sha256']
                    and sha(P / original['engine_path'].removeprefix('res://')) == viewed['sha256']
                    and original['prompt_sha256'] == viewed['prompt_sha256'], 'Quiet source differs from its review')
        audit = read(P / 'reports/ground_macro_asset_audit.json')
        require(audit['passed'] and audit['version'] == version and audit['sources'] == 20
                and audit['stored_superseded_originals_verified'] == 40, 'Current immutable-ground audit required')
        material = read(P / 'reports/ground_continuity_native_evidence.json')
        require(material['passed'] and material['version'] == version
                and material['runtime_source_sha256'] == runtime and material['windows_exe_sha256'] == sha(exe)
                and material['checks'] == 48 and material['production_quad_vs_hex_verified']
                and material['fixed_texture_period_removed'], 'Current native production-material proof required')
        if scope == 'ground_atlas':
            scope_audit = read(P / 'reports/ground_atlas_scope_audit.json')
            require(scope_audit['passed'] and scope_audit['version'] == version
                    and scope_audit['runtime_source_sha256'] == runtime and not scope_audit['changed_files']
                    and scope_audit['verified_preserved_json_files'] > 100, 'Dated geography and rules must match the baseline')
        else:
            scope_audit = read(P / 'reports/coast_detail_scope_audit.json')
            require(scope_audit['passed'] and scope_audit['version'] == version
                    and scope_audit['runtime_source_sha256'] == runtime
                    and not scope_audit['unexpected_changed_files'] and scope_audit['preserved_json_files'] > 100
                    and scope_audit['independent_raw_geography_audit_bound'], 'Coast changes exceeded the documented map scope')
            coast = read(P / 'reports/coast_detail_geography_audit.json')
            require(coast['passed'] and not coast['production_compiler_imported'] and len(coast['maps']) == 4
                    and not coast['historical_coast_survey_approval'], 'Independent original-GIS audit required')
            for row in coast['maps']:
                require(row['map_sha256'] == sha(P / ('content/maps/' + row['map_id'] + '.json')),
                        'Raw source audit is stale: ' + row['map_id'])
            native = read(P / 'reports/coast_geometry_tests.json')
            seal = read(P / 'reports/coast_detail_native_geometry_evidence.json')
            require(native['passed'] and native['build_version'] == version
                    and native['content_hash'] == calendar['content_hash'] and len(native['checks']) == 61,
                    'Current native precompiled coast/mesh checks required')
            require(seal['passed'] and seal['version'] == version and seal['runtime_source_sha256'] == runtime
                    and seal['dependency_sha256'] == identity('coast_geometry_test')[0]
                    and seal['report_sha256'] == sha(P / seal['report']) and seal['log_sha256'] == sha(P / seal['log']),
                    'Current geometry dependency seal required')
            coast_frames = read(P / 'reports/coast_detail_native_capture_evidence.json')
            require(coast_frames['passed'] and coast_frames['version'] == version
                    and coast_frames['runtime_source_sha256'] == runtime
                    and coast_frames['windows_exe_sha256'] == sha(exe)
                    and coast_frames['capture_driver_sha256'] == sha(P / 'tools/capture_coast_detail.py')
                    and len(coast_frames['captures']) == 4
                    and {r['map_id'] for r in coast_frames['captures']} ==
                        {'jingjin', 'jingfeng', 'conquest_china', 'asia_strategic'},
                    'All four changed maps require current exported viewport evidence')
            for row in coast_frames['captures']:
                require(row['actual_coast_band_draws'] == 1
                        and row['map_sha256'] == sha(P / ('content/maps/' + row['map_id'] + '.json'))
                        and sha(P / row['file']) == row['sha256']
                        and sha(P / row['metadata']) == row['metadata_sha256']
                        and sha(P / row['log']) == row['log_sha256'], 'Coast viewport evidence changed')
                captures.update([P / row['file'], P / row['metadata']])
                reports.add(P / row['log'])
            reports.update(P / 'reports' / name for name in ['coast_detail_scope_audit.json',
                'coast_detail_geography_audit.json', 'coast_detail_compilation.json', 'coast_geometry_tests.json',
                'coast_geometry_native.log', 'coast_detail_native_geometry_evidence.json', 'coast_detail_native_capture_evidence.json',
                'map_surface_geography_audit.json', 'asia_relief_rebuild_verification.json'])
        details = read(P / 'reports/screenshots/terrain_surfaces_native/details/mountain.json')
        ground = details['map_bank_visible']['terrain_surface_extension']['continuous_ground']
        require(ground['active'] and ground['grounded_scenery_draws'] > 0
                and ground['source_sampling'] == 'world_anchored_three_translations_with_explicit_mip_gradients'
                and not ground['fixed_wallpaper_period'], 'Shipping ground and mountain feet must actually be drawn')
        reports.update(P / 'reports' / name for name in ['ground_atlas_generation.json', 'ground_atlas_source_review.json',
            'ground_atlas_installation.json', 'ground_macro_asset_audit.json', 'ground_continuity_native_evidence.json',
            'ground_continuity_native/validation.json', 'ground_continuity_native/native.log'])
        if scope == 'ground_atlas':reports.add(P / 'reports/ground_atlas_scope_audit.json')
    names = ['daily_age_text_audit.json', 'git_byte_preservation.json', visual_name, 'ui_refinement_source_review.json',
             'regression_dependency_evidence.json', 'resource_validation.json', 'repository_validation.json',
             'export_results.json', 'sample_state_v2.json', 'apk_content_validation.json', 'apk_signature.log',
             'apk_badging.log', 'apk_permissions.log', 'android_devices.log', 'general_portrait_first_source_review.json',
             'general_portrait_source_review.json', 'music_native_tests.json']
    reports.update(P / 'reports' / name for name in names)
    summary = dict(passed=True, version=version, runtime_source_sha256=runtime,
                   content_hash=read(P / 'reports/sample_state_v2.json')['content_hash'], ruleset=10,
                   days_per_complete_round=1, scenarios=61, people=33, military_generals=29, political_only_people=4,
                   living_age_stages_per_person=4, portrait_originals=135, new_portrait_originals=0,
                   new_ui_originals=0 if atlas_scope else 5, total_rasters=expected_rasters, regression_groups=29,
                   calendar_checks=len(calendar['checks']),
                   regression_checks=sum(r['checks'] for r in regression), native_groups=native_groups,
                   native_captures=len(captures) // 2, native_music_checks=18, apk_version_code=android_version_code(),
                   apk_data_and_notice_files=len(apk_report['files']), physical_android_device_tested=False,
                   formal_art_approval=False, historical_likeness_approval=False, new_1947_scenario=False,
                   full_daily_balance_acceptance=False, full_ai_endurance_rerun=False, ew6_parity_claimed=False,
                   source_pngs_modified=False, manual_compositing=False, git_working_bytes_preserved=True)
    if ground_scope:
        summary.update(new_ground_originals=20 if scope == 'ground_atlas' else 0, stored_map_originals=1010, active_map_originals=970,
                       preserved_superseded_ground_originals=40, native_material_checks=48)
    if scope == 'coast_detail':
        summary.update(refined_marine_maps=4, new_raster_originals=0, native_coast_checks=61,
                       independent_geography_checks=len(coast['checks']), historical_coast_survey_approval=False,
                       additional_coast_native_captures=len(coast_frames['captures']))
    validation_name = {'coast_detail': 'coast_detail_release_validation.json', 'ground_atlas': 'ground_atlas_release_validation.json', 'atlas_office': 'atlas_office_release_validation.json',
                       'dossier': 'ui_refinement_release_validation.json'}[scope]
    write(P / 'reports' / validation_name, summary)
    reports.add(P / 'reports' / validation_name)
    return summary, reports, captures, regression


def main():
    summary, reports, captures, regression = validate()
    version = summary['version']
    out = ROOT / 'output/releases' / ('railway-warlords-' + version)
    out.mkdir(parents=True, exist_ok=True)
    exe = P / 'build/windows/RailwayWarlords.exe'
    apk = P / 'build/android/RailwayWarlords.apk'
    portable = out / 'Windows便携版'
    portable.mkdir(exist_ok=True)
    shutil.copyfile(exe, portable / exe.name)
    note = f'''# 铁道烽烟 {version} · 军事界面与将领档案精修

Windows：解压Windows ZIP，运行RailwayWarlords.exe。Android：安装同版本APK，沿用既有签名。Godot：用4.7.2打开源码内game/railway_warlords/project.godot。

- 统一钢灰/冷银控件，新增两张面板材质和三枚游戏成长图标，全部由指定Sub2路线直接生成、逐张查看并保留原始字节。成长图标不代表真实历史授勋。
- 将领档案放大完整肖像；左右独立滚动，年代选择与关闭固定；29位将领与17条政要档案支持姓名查找。
- 晋升、战法和勋章读取实际费用及经验条件；不足时显示原因并禁用。装备/卸下走真实生涯事务，保持选中的肖像阶段。
- 保留0.2.22每日历法和33人四阶段/135张独立肖像。每轮全部阵营行动结束推进公历1天，默认规则登记也同步为1天。
- 1947及更晚肖像仍为素材准备，当前可玩时间锚点止于1940。ruleset9旧战局需新开；本版继续使用ruleset10。

本轮29组/{summary['regression_checks']}项回归通过，专项证据共{summary['native_captures']}张未经编辑的Windows原生视口。完整证据与SHA256见release_manifest.json。APK核对签名、ARM64/ARMv7、版本、1304张导入纹理及3首纯器乐。三布局中2400×1080仅为桌面移动比例检查，Motorola X30未连接；没有宣称物理设备验收。

完整每日长局平衡、完整AI长局、独立历史肖似度、所有兵种动画及商业美术品质仍待继续验收。人物年代存在生卒资料精度边界；不宣称与欧陆战争6完全同等品质。旧版本发布目录及历史录像不改写。

Military UI and general dossiers are refined with five independently generated Sub2 originals. Whole portraits, independent scrolling, roster search and actual progression requirements are implemented. All payments use the existing profile transaction layer. Daily rounds and all 33 four-stage people are retained. Windows and signed Android builds and native evidence are delivered; physical Motorola X30 acceptance, full daily-balance certification and EW6 parity are not claimed.
'''
    (portable / 'README.md').write_text(note, encoding='utf-8')
    legal = portable / 'licenses'
    legal.mkdir(exist_ok=True)
    for path in (P / 'assets/legal').glob('*.txt'):
        shutil.copyfile(path, legal / path.name)
    windows = out / f'RailwayWarlords-Windows-{version}.zip'
    with zipfile.ZipFile(windows, 'w', zipfile.ZIP_DEFLATED, compresslevel=1) as archive:
        for path in sorted(portable.rglob('*')):
            if path.is_file():
                archive.write(path, path.relative_to(portable).as_posix())
    android = out / f'RailwayWarlords-{version}.apk'
    shutil.copyfile(apk, android)
    source = out / f'RailwayWarlords-Godot-Source-{version}.zip'
    raw = subprocess.check_output(['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'], cwd=P)
    public = {P / n.decode('utf-8') for n in raw.split(b'\0') if n}
    print('Packaging Godot source, immutable art, documentation and native proof.', flush=True)
    with zipfile.ZipFile(source, 'w', zipfile.ZIP_DEFLATED, compresslevel=1) as archive:
        for path in sorted(public | reports | captures):
            if not path.is_file():
                continue
            require(not any(part in {'.git', '.godot', '.toolchain', 'build', '__pycache__', 'signing'}
                            for part in path.relative_to(P).parts), 'Private path in archive')
            archive.write(path, path.relative_to(ROOT).as_posix())
        add_tree(archive, ROOT / 'design', ROOT, allowed={'.md', '.json', '.py', '.csv', '.txt', '.png', '.shp', '.shx', '.dbf', '.prj', '.cpg', '.html', '.xml', '.zip', '.tif', '.pdf'})
    print('Verifying both archives and tested binary identity.', flush=True)
    for path in [windows, source]:
        with zipfile.ZipFile(path) as archive:
            require(archive.testzip() is None, 'Corrupt archive: ' + path.name)
    with zipfile.ZipFile(windows) as archive:
        require(hashlib.sha256(archive.read(exe.name)).hexdigest() == sha(exe), 'Portable binary differs')
    require(sha(android) == sha(apk) and source_digest()[0] == summary['runtime_source_sha256'], 'Delivery identity changed')
    manifest = dict(**summary, created_at_utc=datetime.now(timezone.utc).isoformat(),
                    release_kind='scoped_military_ui_and_general_dossier_beta', regression=regression,
                    artifacts=[dict(file=p.name, bytes=p.stat().st_size, sha256=sha(p)) for p in [windows, android, source]],
                    reports=[dict(file=p.relative_to(P).as_posix(), sha256=sha(p)) for p in sorted(reports)],
                    archive_integrity_verified=True, old_releases_modified=False)
    write(out / 'release_manifest.json', manifest)
    (out / '交付说明.md').write_text(note, encoding='utf-8')
    shutil.copyfile(P / 'docs/41_军事界面与将领档案精修.md', out / '军事界面与将领档案精修.md')
    print(json.dumps(dict(passed=True, release=str(out), artifacts=manifest['artifacts']), ensure_ascii=True), flush=True)


if __name__ == '__main__':
    main()
