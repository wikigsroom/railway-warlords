"""Archive the verified 0.2.35 visual preview without changing old releases."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import shutil
import zipfile

from build_release import P, current_version, android_version_code, source_digest
from regression_dependencies import identities
from run_validation import CHECKS

R = P / 'reports/urban_hierarchy_v0235'
MAPS = R / 'composition_shipping01'
HUD = P / 'reports/battle_hud_native_v0230/map_visual_v0235_01'
OUT = P.parents[1] / 'output/releases/railway-warlords-0.2.35'


def read(path): return json.loads(Path(path).read_text(encoding='utf-8'))


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    assert current_version() == '0.2.35' and android_version_code() == 40 and not OUT.exists()
    runtime = source_digest()[0]
    fingerprint = read(P / 'reports/sample_state_v2.json')['content_hash']
    exports = {row['target']: row for row in read(P / 'reports/export_results.json')}
    assert set(exports) == {'windows', 'android'}
    for row in exports.values():
        assert row['export_verified'] and row['runtime_source_sha256'] == runtime and sha(row['path']) == row['sha256']
    seal = read(P / 'reports/regression_dependency_evidence.json')
    assert seal['passed'] and seal['game_version'] == '0.2.35' and seal['runtime_source_sha256'] == runtime
    assert len(seal['checks']) == len(CHECKS) == 30
    current = identities(CHECKS)
    count = 0
    for row in seal['checks']:
        assert row['passed'] and current[row['check']][0] == row['dependency_sha256_at_seal']
        assert sha(P / 'reports' / row['report']) == row['report_sha256']
        assert sha(P / 'reports' / row['log']) == row['log_sha256']
        report = read(P / 'reports' / row['report'])
        assert report.get('content_hash', fingerprint) == fingerprint and not report.get('failed', 0) and not report.get('failures', [])
        count += len(report['checks'])
    scope, audit = read(R / 'scope.json'), read(R / 'source_audit.json')
    assert scope['passed'] and not scope['historical_or_rule_changes'] and scope['current_rasters'] == 2521 and scope['new_originals'] == 12
    assert scope['driver_sha256'] == sha(P / 'tools/audit_map_visual_scope.py')
    assert audit['passed'] and audit['additional_independent_sources'] == 804 and audit['all_runtime_rasters'] == 2521
    urban = read(R / 'rules03/validation.json')
    urban_proof = read(R / 'rules03/command.json')
    assert urban['passed'] and len(urban['checks']) == 64 and read(R / 'rules03/result.json')['passed']
    assert urban_proof['controller_sha256'] == sha(P / 'tools/verify_urban_hierarchy.py')
    for name, checksum in urban_proof['code_content_urban_media_dependency_sha256'].items(): assert sha(P / name) == checksum
    edges = read(P / 'reports/ground_hierarchy_v0235/edgesshipping_source01/validation.json')
    assert edges['passed'] and len(edges['checks']) == 23
    assert read(P / 'reports/ground_hierarchy_v0235/edgesshipping_source01/result.json')['passed']
    hud, maps, shipping = read(HUD / 'validation.json'), read(MAPS / 'validation.json'), read(R / 'shipping01/validation.json')
    assert hud['passed'] and hud['checks'] == 773 and len(hud['cases']) == 3
    assert hud['test_driver_sha256'] == sha(P / 'tests/battle_hud_test.gd') and hud['controller_sha256'] == sha(P / 'tools/verify_battle_hud.py')
    assert maps['passed'] and maps['mode'] == 'verified_export' and len(maps['checks']) == 106 and len(maps['captures']) == 13
    assert maps['expected_content_hash'] == fingerprint and maps['capture_driver_sha256'] == sha(P / 'tools/capture_map_composition.py')
    assert shipping['passed'] and shipping['gpu_checks'] == 48 and shipping['ui_smoke_passed']
    assert shipping['capture_driver_sha256'] == sha(P / 'tools/verify_map_visual_shipping.py') and shipping['windows_exe_sha256'] == exports['windows']['sha256']
    assert all(proof['runtime_source_sha256'] == runtime for proof in [hud, maps, shipping])
    review = read(R / 'visual_review.json')
    assert review['runtime_source_sha256'] == runtime and len(review['actually_viewed_complete_images']) == 16
    viewed = {row['path']: row['sha256'] for row in review['actually_viewed_complete_images']}
    for row in maps['captures'] + shipping['captures']:
        image, metadata = Path(row.get('image', row.get('path'))), Path(row['metadata'])
        if not image.is_absolute(): image = P / image
        if not metadata.is_absolute(): metadata = P / metadata
        assert sha(image) == row['sha256'] == viewed[image.relative_to(P).as_posix()] and sha(metadata) == row['metadata_sha256']
    for case in hud['cases']:
        assert case['passed'] and case['checks'] > 200 and sha(P / case['report']) == case['report_sha256']
        for row in case['images']: assert sha(P / row['path']) == row['sha256']
    resource = read(P / 'reports/resource_validation.json')
    docs = read(P / 'reports/repository_documentation_validation.json')
    assert resource['passed'] and resource['raster_count'] == 2521
    assert docs['passed'] and docs['runtime_source_sha256'] == runtime and not docs['full_native_release_gates_checked']
    apk = read(P / 'reports/apk_content_validation.json')
    assert apk['passed'] and apk['artifact_sha256'] == exports['android']['sha256'] and not apk['private_files_detected']
    assert len(apk['raster_import_files_verified']) == 2521 and all(row['current_import_bytes_match'] for row in apk['raster_import_files_verified'])
    assert len(apk['instrumental_music_imports_verified']) == 3 and all(row['current_import_bytes_match'] for row in apk['instrumental_music_imports_verified'])
    signature = (P / 'reports/apk_signature.log').read_text(encoding='utf-8')
    assert all('Verified using v%d scheme (APK Signature Scheme v%d): true' % (n, n) in signature for n in [2, 3])
    badging = (P / 'reports/apk_badging.log').read_text(encoding='utf-8')
    assert "versionName='0.2.35'" in badging and "versionCode='40'" in badging and "'arm64-v8a'" in badging and "'armeabi-v7a'" in badging
    assert 'uses-permission:' not in (P / 'reports/apk_permissions.log').read_text(encoding='utf-8')
    OUT.mkdir()
    evidence = OUT / 'evidence'
    files = {path for root in [R, HUD, P / 'reports/ground_hierarchy_v0235', P / 'reports/control_borders_v0235']
             for path in root.rglob('*') if path.is_file() and path.suffix in ['.json', '.png', '.gd', '.py', '.md'] and '__pycache__' not in path.parts}
    files.update(P / name for name in ['README.md', 'README.en.md', 'docs/00_程序文档索引.md', 'docs/05_测试与验收.md',
        'docs/06_双端构建与发布.md', 'docs/23_当前完成度评估.md', 'docs/53_地表绘制层次修订.md',
        'docs/54_控制区共边与海岸描边修复.md', 'docs/55_城市建筑群层级与地图整合.md', 'docs/MEDIA.md', 'docs/media/manifest.json',
        'reports/regression_dependency_evidence.json', 'reports/export_results.json', 'reports/resource_validation.json',
        'reports/repository_documentation_validation.json', 'reports/apk_content_validation.json', 'reports/apk_signature.log',
        'reports/apk_badging.log', 'reports/apk_permissions.log', 'reports/android_devices.log', 'reports/quality_goal_turn_v0235.json'])
    for row in seal['checks']: files.update([P / 'reports' / row['report'], P / 'reports' / row['log']])
    files.update((P / 'docs/media').glob('*v0235.*'))
    files.update(P / 'tools' / name for name in ['generate_urban_assets.py', 'integrate_urban_hierarchy.py', 'verify_urban_hierarchy.py',
        'audit_map_visual_scope.py', 'capture_map_composition.py', 'verify_map_visual_shipping.py', 'package_map_visual_preview.py'])
    rows = []
    for source in sorted(files):
        target = evidence / source.relative_to(P); target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target); checksum = sha(source); assert sha(target) == checksum
        rows.append(dict(file=source.relative_to(P).as_posix(), bytes=source.stat().st_size, sha256=checksum))
    for row in exports.values():
        source = Path(row['path']); shutil.copyfile(source, OUT / source.name); assert sha(OUT / source.name) == row['sha256']
    receipt = dict(version='0.2.35', android_version_code=40, stage='urban_ground_and_control_border_playable_preview',
        created_at_utc=datetime.now(timezone.utc).isoformat(), runtime_source_sha256=runtime, content_hash=fingerprint,
        full_thirty_group_regression_repeated=True, regression_checks=count, urban_integration_checks=64,
        native_hud_input_checks=773, shipping_map_layout_checks=106, shipping_gpu_checks=48, source_edge_gpu_checks=23,
        actual_full_shipping_images_viewed=16, new_raster_originals=12, registered_rasters=2521,
        new_music_generated=False, future_music_route='music-gen-remote-YuE2_RTX3080_instrumental',
        physical_android_device_tested=False, formal_art_approval=False, ew6_parity_claimed=False, whole_goal_achieved=False,
        full_ai_combat_balance_claimed=False, old_release_archives_modified=False, manual_image_compositing=False, evidence=rows)
    write(OUT / 'scope_receipt.json', receipt)
    (OUT / 'START_HERE.md').write_text('# 铁道烽烟：军阀时代 0.2.35 / Railway Warlords\n\n'
        'Windows：解压运行RailwayWarlords.exe。Android：安装签名APK/code40。\n'
        'Windows: extract and run RailwayWarlords.exe. Android: install the signed APK/code40.\n\n'
        '本版包含四张地表底材、八张城市建筑群、城市层级与不同阵营共边修复。保持0.2.34历史规则与地理内容身份。'
        '整体欧陆战争6品质仍未完成，无物理X30验收。\n'
        'This preview adds four grounds and eight urban originals, preserves historical settlement rank and repairs control outlines. '
        'The 0.2.34 rule/geography content identity is preserved. Overall EW6 quality and physical X30 acceptance remain unfinished.\n\n'
        '源码通过Git仓库交付。来源、实际画面与验收范围见scope_receipt.json及evidence；旧版本归档独立保留。\n'
        'Source is delivered through Git. See scope_receipt.json and evidence for provenance, actual whole viewports and validation scope. '
        'Older archives remain separate.\n', encoding='utf-8')
    for name, paths, base in [
        ('RailwayWarlords-Windows-0.2.35.zip', [OUT / 'RailwayWarlords.exe', OUT / 'START_HERE.md', OUT / 'scope_receipt.json'], OUT),
        ('MapVisualEvidence-0.2.35.zip', sorted(path for path in evidence.rglob('*') if path.is_file()), evidence),
    ]:
        with zipfile.ZipFile(OUT / name, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            for path in paths: archive.write(path, path.relative_to(base).as_posix())
        with zipfile.ZipFile(OUT / name) as archive: assert archive.testzip() is None
        print('ARCHIVED ' + name, flush=True)
    manifest = dict(version='0.2.35', runtime_source_sha256=runtime, archive_directory=str(OUT), whole_goal_achieved=False,
                    physical_android_device_tested=False, ew6_parity_claimed=False,
                    artifacts=[dict(file=path.name, bytes=path.stat().st_size, sha256=sha(path)) for path in sorted(OUT.iterdir()) if path.is_file()])
    write(OUT / 'preview_manifest.json', manifest); write(P / 'reports/map_visual_preview_v0235.json', manifest)
    print('MAP_VISUAL_PREVIEW_ARCHIVED ' + str(OUT), flush=True)


if __name__ == '__main__': main()
