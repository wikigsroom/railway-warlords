"""Archive the scoped, verified local-map preview without changing full release gates."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import shutil
import zipfile

from build_release import P, current_version, android_version_code, source_digest
from regression_dependencies import identities
from run_validation import CHECKS

ROOT = P.parents[1]
R = P / 'reports/local_map_refinement'
MAPS = P / 'reports/screenshots/local_map_refinement/v0234/verified_export_01'
HUD = P / 'reports/battle_hud_native_v0230/local_scale_v0234_02'
OUT = ROOT / 'output/releases/railway-warlords-0.2.34'


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def main():
    assert current_version() == '0.2.34' and android_version_code() == 39 and not OUT.exists()
    runtime = source_digest()[0]
    fingerprint = read(P / 'reports/sample_state_v2.json')['content_hash']
    exports = {row['target']: row for row in read(P / 'reports/export_results.json')}
    assert set(exports) == {'windows', 'android'}
    for row in exports.values():
        assert row['export_verified'] and row['runtime_source_sha256'] == runtime
        assert sha(row['path']) == row['sha256']
    seal = read(P / 'reports/regression_dependency_evidence.json')
    assert seal['passed'] and seal['game_version'] == '0.2.34' and seal['runtime_source_sha256'] == runtime
    assert len(seal['checks']) == len(CHECKS) == 30
    discovery = read(R / 'dependency_discovery_equivalence.json')
    assert discovery['passed'] and discovery['runtime_source_sha256'] == runtime
    assert discovery['current_tool_sha256'] == sha(P / 'tools/regression_dependencies.py')
    assert len(discovery['checks']) == 30 and all(row['same_legacy_dependency_paths'] for row in discovery['checks'])
    current = identities(CHECKS)
    count = 0
    for row in seal['checks']:
        assert row['passed'] and current[row['check']][0] == row['dependency_sha256_at_seal']
        assert sha(P / 'reports' / row['report']) == row['report_sha256']
        assert sha(P / 'reports' / row['log']) == row['log_sha256']
        report = read(P / 'reports' / row['report'])
        assert report.get('content_hash', fingerprint) == fingerprint
        assert not report.get('failed', 0) and not report.get('failures', [])
        count += len(report['checks'])
    local = read(P / 'reports/local_map_refinement_tests.json')
    assert local['passed'] and not local['candidate_only'] and local['content_hash'] == fingerprint
    assert len(local['checks']) == 86 and local['test_driver_sha256'] == sha(P / 'tests/local_map_refinement_test.gd')
    for mid, checksum in local['runtime_map_sha256'].items():
        assert sha(P / 'content/maps' / (mid+'.json')) == checksum
    scope, geography = read(R / 'scope.json'), read(R / 'geography_preinstall.json')
    assert scope['passed'] and len(scope['checks']) == 122
    assert geography['passed'] and len(geography['checks']) == 953
    settlement = read(P / 'reports/settlement_geography_validation.json')
    assert settlement['passed'] and len(settlement['checks']) == 207
    assert sha(P / 'reports/settlement_geography_validation.json') == scope['current_settlement_validation_sha256']
    assert sha(R / 'coastal_control_rebuild.json') == scope['coastal_control_receipt_sha256']
    hud, maps, shipping = read(HUD / 'validation.json'), read(MAPS / 'validation.json'), read(R / 'shipping_01/validation.json')
    assert hud['passed'] and hud['checks'] == 773 and len(hud['cases']) == 3
    assert hud['test_driver_sha256'] == sha(P / 'tests/battle_hud_test.gd')
    assert hud['controller_sha256'] == sha(P / 'tools/verify_battle_hud.py')
    assert maps['passed'] and maps['mode'] == 'verified_export' and len(maps['checks']) == 106
    assert maps['expected_content_hash'] == fingerprint
    assert len(maps['captures']) == 13
    for row in maps['captures']:
        metadata = read(row['metadata'])
        if row['name'].startswith('wuhan') or row['name'] in ['wuchang','hanyang']:
            assert metadata['relief']['source'] == 'SRTM90m_v3_five_point_samples'
        if row['name'].startswith('ningpu'):
            assert metadata['relief']['source'] == 'SRTM90m_v3_five_point_samples'
    assert shipping['passed'] and shipping['gpu_checks'] == 48 and shipping['ui_smoke_passed']
    assert all(proof['runtime_source_sha256'] == runtime for proof in [hud, maps, shipping])
    assert maps['capture_driver_sha256'] == sha(P / 'tools/capture_map_composition.py')
    assert shipping['capture_driver_sha256'] == sha(P / 'tools/verify_local_map_shipping.py')
    assert shipping['windows_exe_sha256'] == exports['windows']['sha256']
    review = read(R / 'visual_review.json')
    assert review['runtime_source_sha256'] == runtime and len(review['actually_viewed_complete_images']) == 16
    viewed = {row['path']: row['sha256'] for row in review['actually_viewed_complete_images']}
    for row in maps['captures'] + shipping['captures']:
        image = Path(row.get('image', row.get('path')))
        metadata = Path(row['metadata'])
        if not image.is_absolute():
            image = P / image
        if not metadata.is_absolute():
            metadata = P / metadata
        assert sha(image) == row['sha256'] == viewed[image.relative_to(P).as_posix()]
        assert sha(metadata) == row['metadata_sha256']
    for case in hud['cases']:
        assert case['passed'] and case['checks'] > 200
        assert sha(P / case['report']) == case['report_sha256']
        for row in case['images']:
            assert sha(P / row['path']) == row['sha256']
    resource = read(P / 'reports/resource_validation.json')
    assert resource['passed'] and resource['raster_count'] == 2509
    documentation = read(P / 'reports/repository_documentation_validation.json')
    assert documentation['passed'] and documentation['runtime_source_sha256'] == runtime
    assert not documentation['full_native_release_gates_checked']
    apk = read(P / 'reports/apk_content_validation.json')
    assert apk['passed'] and apk['artifact_sha256'] == exports['android']['sha256'] and not apk['private_files_detected']
    assert len(apk['raster_import_files_verified']) == 2509
    assert all(row['current_import_bytes_match'] for row in apk['raster_import_files_verified'])
    assert len(apk['instrumental_music_imports_verified']) == 3
    assert all(row['current_import_bytes_match'] for row in apk['instrumental_music_imports_verified'])
    signature = (P / 'reports/apk_signature.log').read_text(encoding='utf-8')
    assert all('Verified using v%d scheme (APK Signature Scheme v%d): true' % (n, n) in signature for n in [2, 3])
    badging = (P / 'reports/apk_badging.log').read_text(encoding='utf-8')
    assert "versionName='0.2.34'" in badging and "versionCode='39'" in badging
    assert "'arm64-v8a'" in badging and "'armeabi-v7a'" in badging
    assert 'uses-permission:' not in (P / 'reports/apk_permissions.log').read_text(encoding='utf-8')
    provenance = P / 'docs/geography-provenance/local-map-refinement-v0234'
    for row in read(provenance / 'manifest.json')['files']:
        assert sha(provenance / row['file']) == row['sha256']
    assert sha(provenance / 'srtm_original_responses.zip') == read(R / 'installation.json')['raw_archive_sha256']
    with zipfile.ZipFile(provenance / 'coastal_control_before.zip') as archive:
        assert archive.testzip() is None
        for row in read(R / 'coastal_control_rebuild.json')['maps']:
            assert hashlib.sha256(archive.read('coast_geometry_'+row['map_id']+'.json')).hexdigest() == row['previous_mesh_sha256']
    OUT.mkdir()
    evidence = OUT / 'evidence'
    files = {path for root in [R, MAPS, HUD, provenance] for path in root.rglob('*')
             if path.is_file() and path.suffix in ['.json', '.png', '.gd', '.py', '.md', '.zip']
             and '__pycache__' not in path.parts}
    files.update(P / name for name in ['README.md', 'README.en.md', 'docs/52_局部战区五倍比例与独立江岸.md',
        'docs/00_程序文档索引.md', 'docs/05_测试与验收.md', 'docs/06_双端构建与发布.md',
        'docs/23_当前完成度评估.md', 'docs/MEDIA.md', 'docs/media/manifest.json',
        'reports/local_map_refinement_tests.json', 'reports/settlement_geography_validation.json',
        'reports/regression_dependency_evidence.json', 'reports/export_results.json', 'reports/resource_validation.json',
        'reports/repository_documentation_validation.json', 'reports/apk_content_validation.json',
        'reports/apk_signature.log', 'reports/apk_badging.log', 'reports/apk_permissions.log',
        'reports/android_devices.log', 'reports/quality_goal_turn_v0234.json'])
    for row in seal['checks']:
        files.update([P / 'reports' / row['report'], P / 'reports' / row['log']])
    files.update((P / 'docs/media').glob('*v0234.*'))
    files.update(P / 'tools' / name for name in ['refine_local_maps.py', 'audit_local_map_refinement.py',
        'audit_local_map_runtime.py', 'refresh_local_map_presentation.py', 'refresh_coastal_control.py',
        'capture_map_composition.py', 'verify_local_map_shipping.py', 'refresh_local_map_media.py',
        'package_local_map_preview.py', 'regression_dependencies.py'])
    rows = []
    for source in sorted(files):
        target = evidence / source.relative_to(P)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        checksum = sha(source)
        assert sha(target) == checksum
        rows.append(dict(file=source.relative_to(P).as_posix(), bytes=source.stat().st_size, sha256=checksum))
    for row in exports.values():
        source = Path(row['path'])
        shutil.copyfile(source, OUT / source.name)
        assert sha(OUT / source.name) == row['sha256']
    receipt = dict(version='0.2.34', android_version_code=39,
        stage='local_map_scale_and_separate_river_banks_playable_preview',
        created_at_utc=datetime.now(timezone.utc).isoformat(), runtime_source_sha256=runtime,
        content_hash=fingerprint, full_thirty_group_regression_repeated=True, regression_checks=count,
        local_rule_checks=86, settlement_geometry_checks=207, scope_checks=122,
        native_hud_input_checks=773, shipping_map_layout_checks=106, shipping_gpu_checks=48,
        actual_full_shipping_images_viewed=16, new_raster_originals=0, registered_rasters=2509,
        new_music_generated=False, future_music_route='music-gen-remote-YuE2_RTX3080_instrumental',
        original_elevation_responses_archived=922, sampled_elevation_points=92120,
        physical_android_device_tested=False, ew6_parity_claimed=False, whole_goal_achieved=False,
        formal_art_approval=False, full_ai_combat_balance_claimed=False,
        old_in_progress_map_saves_automatically_migrated=False, old_release_archives_modified=False,
        manual_image_compositing=False, evidence=rows)
    write(OUT / 'scope_receipt.json', receipt)
    (OUT / 'START_HERE.md').write_text('# 铁道烽烟：军阀时代 0.2.34 / Railway Warlords\n\n'
        'Windows：解压运行RailwayWarlords.exe。Android：安装签名APK/code39。\n'
        'Windows: extract and run RailwayWarlords.exe. Android: install the signed APK/code39.\n\n'
        '本版细化汉口与宁浦战区，保留48单位操作蜂窝，分离城市中心和岸边港口，修复沿海控制色缺口。'
        '整体欧陆战争6品质仍未完成，无物理X30验收。\n'
        'This preview refines two local maps, separates inland cities and river-bank ports, and repairs coastal control coverage. '
        'Overall EW6 quality remains unfinished; there is no physical X30 acceptance.\n\n'
        '旧0.2.33进行中的对局不能直接加载到新版，请使用旧归档继续或新建对局。'
        '完整源码由Git仓库交付，来源与验收范围见scope_receipt.json和evidence。\n'
        'Existing 0.2.33 matches are not migrated. Continue them in the retained old release or start a new match. '
        'Full source is delivered through Git. See scope_receipt.json and evidence for source and verification scope.\n', encoding='utf-8')
    archives = [('RailwayWarlords-Windows-0.2.34.zip', [OUT / 'RailwayWarlords.exe', OUT / 'START_HERE.md', OUT / 'scope_receipt.json'], OUT),
                ('LocalMapEvidence-0.2.34.zip', sorted(path for path in evidence.rglob('*') if path.is_file()), evidence)]
    for name, paths, base in archives:
        with zipfile.ZipFile(OUT / name, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            for path in paths:
                archive.write(path, path.relative_to(base).as_posix())
        with zipfile.ZipFile(OUT / name) as archive:
            assert archive.testzip() is None
        print('ARCHIVED '+name, flush=True)
    manifest = dict(version='0.2.34', runtime_source_sha256=runtime, archive_directory=str(OUT),
        whole_goal_achieved=False, physical_android_device_tested=False, ew6_parity_claimed=False,
        artifacts=[dict(file=path.name, bytes=path.stat().st_size, sha256=sha(path))
                   for path in sorted(OUT.iterdir()) if path.is_file()])
    write(OUT / 'preview_manifest.json', manifest)
    write(P / 'reports/local_map_preview_v0234.json', manifest)
    print('LOCAL_MAP_PREVIEW_ARCHIVED '+str(OUT), flush=True)


if __name__ == '__main__':
    main()
