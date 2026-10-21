"""Archive the scoped 0.2.30 UI preview; leave full-release gates unchanged."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

from build_release import P, ROOT, android_version_code, current_version, source_digest


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def native_path(value):
    path = Path(value)
    return path if path.is_absolute() else P / path


def require(value, message):
    if not value:
        raise SystemExit(message)


def write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    require(current_version() == '0.2.30' and android_version_code() == 35,
            'This scoped preview is specific to version 0.2.30 / code 35.')
    runtime = source_digest()[0]
    content_hash = 'd9932b5aa389f0a482bf3def34201b14209071584bb4e06dc5f2c255dd010ef6'
    exports = read(P / 'reports/export_results.json')
    binaries = {}
    for target, relative in [('windows', 'build/windows/RailwayWarlords.exe'),
                             ('android', 'build/android/RailwayWarlords.apk')]:
        path = P / relative
        row = next(r for r in exports if r['target'] == target)
        require(row['export_verified'] and row['runtime_source_sha256'] == runtime
                and row['sha256'] == sha(path) and row['bytes'] == path.stat().st_size,
                'A current verified binary is required: ' + target)
        binaries[target] = dict(source=relative, sha256=row['sha256'], bytes=row['bytes'])

    roots = ['reports/battle_hud_native_v0230/final_04',
             'reports/battle_hud_cinema_v0230/final_02',
             'reports/screenshots/map_composition_native/v0230/verified_export_final_02',
             'reports/battle_hud_shipping_v0230/final_02']
    proofs = [read(P / root / 'validation.json') for root in roots]
    for proof in proofs:
        require(proof['passed'] and proof['runtime_source_sha256'] == runtime,
                'Every native report must match the current runtime.')
    hud, cinema, maps, media = proofs
    require(sum(c['checks'] for c in hud['cases']) == 668 and cinema['checks'] == 56
            and len(maps['checks']) == 58 and not maps['failures'], 'Incomplete native checks.')
    require(hud['source_unchanged_during_tests'] and cinema['source_unchanged_during_tests']
            and media['shipping_binary_unchanged'] and media['ui_smoke_passed'],
            'Source or shipping binary changed during a native run.')
    require(media['windows_exe_sha256'] == binaries['windows']['sha256']
            and maps['mode'] == 'verified_export', 'Shipping application evidence is required.')
    require(media['capture_driver_sha256'] == sha(P / 'tools/capture_battle_hud_media.py'),
            'Shipping media driver changed.')
    for proof, driver, controller in [
        (hud, 'tests/battle_hud_test.gd', 'tools/verify_battle_hud.py'),
        (cinema, 'tests/hud_native_test.gd', 'tools/verify_battle_cinema.py')]:
        require(proof['test_driver_sha256'] == sha(P / driver)
                and proof['controller_sha256'] == sha(P / controller), 'Native driver changed.')
        for case in proof['cases']:
            require(case['passed'] and sha(P / case['report']) == case['report_sha256'],
                    'Native case evidence changed.')
            for frame in case['images']:
                require(sha(P / frame['path']) == frame['sha256'], 'Native viewport changed.')
    require(maps['capture_driver_sha256'] == sha(P / 'tools/capture_map_composition.py'),
            'Shipping map driver changed.')
    for frame in maps['captures'] + media['captures']:
        require(sha(native_path(frame.get('image', frame.get('path', '')))) == frame['sha256']
                and sha(native_path(frame['metadata'])) == frame['metadata_sha256'],
                'Shipping viewport or metadata changed.')

    component_reports = ['rule_tests.json', 'ground_coverage_tests.json',
                         'surface_geography_tests.json', 'touch_scroll_tests.json', 'battle_summary_tests.json']
    for name, count in zip(component_reports, [102, 45, 39, 9, 10]):
        report = read(P / 'reports' / name)
        require(report['passed'] and not report.get('failed', 0)
                and not report.get('failures') and len(report['checks']) == count,
                'A scoped component regression failed: ' + name)
    require(read(P / 'reports/rule_tests.json')['content_hash'] == content_hash,
            'Core content identity changed.')
    require(read(P / 'reports/touch_scroll_tests.json')['touch_component_sha256']
            == sha(P / 'presentation/touch_scroll.gd'), 'Touch component evidence is stale.')
    require(read(P / 'reports/battle_summary_tests.json')['hud_source_sha256']
            == sha(P / 'presentation/battle_hud.gd'), 'Summary component evidence is stale.')
    apk = read(P / 'reports/apk_content_validation.json')
    require(apk['passed'] and apk['artifact_sha256'] == binaries['android']['sha256']
            and not apk['private_files_detected'] and apk['raster_manifest_byte_verified']
            and len(apk['raster_import_files_verified']) == 2507
            and all(r['current_import_bytes_match'] for r in apk['raster_import_files_verified'])
            and len(apk['instrumental_music_imports_verified']) == 3
            and all(r['current_import_bytes_match'] for r in apk['instrumental_music_imports_verified']),
            'Current APK content validation is required.')
    signature = (P / 'reports/apk_signature.log').read_text(encoding='utf-8')
    require(all(f'Verified using v{v} scheme (APK Signature Scheme v{v}): true' in signature
                for v in [2, 3]), 'APK v2/v3 signatures are required.')
    badging = (P / 'reports/apk_badging.log').read_text(encoding='utf-8')
    require("versionName='0.2.30'" in badging and "versionCode='35'" in badging
            and "'arm64-v8a'" in badging and "'armeabi-v7a'" in badging,
            'Android version or architecture mismatch.')
    require('uses-permission:' not in (P / 'reports/apk_permissions.log').read_text(encoding='utf-8'),
            'Unexpected Android permissions.')
    review_path = P / 'reports/battle_hud_visual_review_v0230.json'
    review = read(review_path)
    require(review['runtime_source_sha256'] == runtime and not review['formal_art_approval']
            and not review['ew6_parity_claimed'], 'A truthful visual review is required.')
    reviewed = {r['path'] for r in review['actually_viewed_complete_images']}
    required_views = {Path(r['image']).relative_to(P).as_posix() for r in maps['captures']}
    required_views.update(r['path'] for r in media['captures'])
    require(required_views <= reviewed, 'Open every shipping map and media frame before packaging.')
    for frame in review['actually_viewed_complete_images']:
        require(sha(P / frame['path']) == frame['sha256'], 'Reviewed image changed.')

    files = {P / 'reports' / name for name in component_reports}
    files.add(P / 'reports/battle_summary_cache_v0230/before_fix.json')
    files.update(P / 'reports' / name for name in ['export_results.json', 'apk_content_validation.json',
        'apk_signature.log', 'apk_badging.log', 'apk_permissions.log', 'android_devices.log'])
    files.add(review_path)
    for root in roots:
        files.update(f for f in (P / root).rglob('*') if f.is_file() and f.suffix in {'.json', '.png', '.log'})
    for relative in ['README.md', 'README.en.md', 'docs/23_当前完成度评估.md',
        'docs/48_战场浮动界面与直接触摸滚动.md', 'tests/battle_hud_test.gd',
        'tests/touch_scroll_test.gd', 'tests/battle_summary_test.gd', 'tests/hud_native_test.gd', 'tools/verify_battle_hud.py',
        'tools/verify_battle_cinema.py', 'tools/capture_map_composition.py',
        'tools/capture_battle_hud_media.py', 'tools/verify_exports.py',
        'tools/package_battle_hud_preview.py', 'presentation/battle_hud.gd',
        'presentation/touch_scroll.gd', 'presentation/map_details.gd', 'presentation/map_view.gd',
        'presentation/general_dossier.gd', 'presentation/command_button.gd', 'app/main.gd',
        'project.godot', 'export_presets.cfg', 'content/content_registry.gd']:
        files.add(P / relative)
    records = [dict(path=f.relative_to(P).as_posix(), sha256=sha(f), bytes=f.stat().st_size)
               for f in sorted(files)]
    receipt = dict(kind='scoped_battlefield_ui_preview', version='0.2.30', android_version_code=35,
        created_at_utc=datetime.now(timezone.utc).isoformat(), scope_passed=True,
        runtime_source_sha256=runtime, content_hash=content_hash, binaries=binaries,
        checks=dict(core_ground_scroll_summary=205, battlefield_input=668, combat_presentation=56,
                    shipping_map_composition=58, total=987), evidence_files=records,
        full_30_group_regression_repeated=False, full_release_approved=False,
        formal_art_approval=False, ew6_parity_claimed=False, physical_android_device_tested=False,
        performance_approval=False, source_pngs_modified=False, new_music_generated=False,
        source_delivery='Git repository; this preview has no standalone full-source ZIP.',
        source_repository='https://github.com/wikigsroom/railway-warlords')
    out = ROOT / 'output/releases/railway-warlords-0.2.30'
    require(not out.exists(), 'Keep the existing versioned preview immutable.')
    out.mkdir(parents=True)
    write(out / 'scope_receipt.json', receipt)
    quickstart = ('# Railway Warlords / 铁道烽烟 0.2.30 测试版\n\n'
        'Windows：解压后运行 RailwayWarlords.exe。Android：安装同目录签名APK。\n'
        'Windows: extract and run RailwayWarlords.exe. Android: install the signed APK.\n\n'
        '点选编队与目标，再确认移动或攻击；点左下摘要展开详情。右上图层与军令按需展开。\n'
        'Select a formation and target, then confirm the order. Open details from the lower-left summary.\n\n'
        '本包为战场UI专项测试交付，987项针对性检查通过；完整商业美术、史实、平衡与物理X30验收待完成。\n'
        'This is a scoped UI preview with 987 targeted checks, not full commercial or physical-phone acceptance.\n'
        '规则与内容兼容0.2.28/0.2.29进行中战局；手机升级需使用同一签名。\n'
        'Rules/content retain 0.2.28/0.2.29 match compatibility. Android updates require the same signature.\n\n'
        'Source and full bilingual manual: https://github.com/wikigsroom/railway-warlords\n')
    (out / 'START_HERE.md').write_text(quickstart, encoding='utf-8')
    for target, row in binaries.items():
        shutil.copyfile(P / row['source'], out / Path(row['source']).name)
        require(sha(out / Path(row['source']).name) == row['sha256'], 'Copied binary changed.')
    notices = [P / 'LICENSE-NOTICE.md', *sorted((P / 'assets/legal').glob('*.txt')),
               *sorted((P / 'assets/font').glob('OFL*.txt'))]
    windows_zip = out / 'railway-warlords-0.2.30-windows.zip'
    with zipfile.ZipFile(windows_zip, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=1) as archive:
        archive.write(out / 'RailwayWarlords.exe', 'RailwayWarlords.exe')
        archive.write(out / 'START_HERE.md', 'START_HERE.md')
        archive.write(out / 'scope_receipt.json', 'scope_receipt.json')
        for notice in notices:
            archive.write(notice, 'notices/' + notice.name)
    with zipfile.ZipFile(windows_zip) as archive:
        require(archive.testzip() is None, 'Windows ZIP CRC check failed.')
        with archive.open('RailwayWarlords.exe') as stream:
            require(hashlib.file_digest(stream, 'sha256').hexdigest() == binaries['windows']['sha256'],
                    'Archived EXE does not match the verified export.')
    evidence_zip = out / 'railway-warlords-0.2.30-ui-evidence.zip'
    with zipfile.ZipFile(evidence_zip, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=1) as archive:
        archive.write(out / 'scope_receipt.json', 'scope_receipt.json')
        for file in sorted(files):
            archive.write(file, 'project/' + file.relative_to(P).as_posix())
    with zipfile.ZipFile(evidence_zip) as archive:
        require(archive.testzip() is None, 'Evidence ZIP CRC check failed.')
        for row in records:
            require(hashlib.sha256(archive.read('project/' + row['path'])).hexdigest() == row['sha256'],
                    'Archived evidence differs from its verified bytes.')
    require(source_digest()[0] == runtime, 'Runtime changed during packaging.')
    manifest = dict(receipt, archive_checks_passed=True,
        scope_receipt_sha256=sha(out / 'scope_receipt.json'),
        artifacts=[dict(file=f.name, bytes=f.stat().st_size, sha256=sha(f))
                   for f in sorted(out.iterdir()) if f.is_file()])
    write(out / 'preview_manifest.json', manifest)
    write(P / 'reports/battle_hud_preview_v0230.json', manifest)
    print(json.dumps(dict(scope_passed=True, full_release_approved=False, output=str(out),
                          checks=987, evidence_files=len(records)), ensure_ascii=True), flush=True)


if __name__ == '__main__':
    main()
