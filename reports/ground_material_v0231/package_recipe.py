"""Archive this specific material preview; do not change full-release gates."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sys
import zipfile

P = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(P / 'tools'))
from build_release import source_digest, current_version, android_version_code

ROOT = P.parents[1]
REPORTS = P / 'reports/ground_material_v0231'
DEST = ROOT / 'output/releases/railway-warlords-0.2.31'


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    assert current_version() == '0.2.31' and android_version_code() == 36
    assert not DEST.exists(), 'Preserve every previous archive and partial attempt.'
    exports = read(P / 'reports/export_results.json')
    runtime = source_digest()[0]
    binaries = {}
    for target, relative in [('windows', 'build/windows/RailwayWarlords.exe'),
                             ('android', 'build/android/RailwayWarlords.apk')]:
        row = next(r for r in exports if r['target'] == target)
        path = P / relative
        assert row['export_verified'] and row['runtime_source_sha256'] == runtime
        assert row['bytes'] == path.stat().st_size and row['sha256'] == sha(path)
        binaries[target] = row
    maps_root = P / 'reports/screenshots/map_composition_native/v0231/verified_export_01'
    maps = read(maps_root / 'validation.json')
    shipping = read(REPORTS / 'shipping_01/validation.json')
    assert maps['passed'] and maps['mode'] == 'verified_export' and len(maps['checks']) == 58
    assert shipping['passed'] and shipping['gpu_checks'] == 48 and shipping['ui_smoke_passed']
    assert maps['runtime_source_sha256'] == shipping['runtime_source_sha256'] == runtime
    assert shipping['windows_exe_sha256'] == binaries['windows']['sha256']
    assert shipping['capture_driver_sha256'] == sha(REPORTS / 'verify_shipping.py')
    assert maps['capture_driver_sha256'] == sha(P / 'tools/capture_map_composition.py')
    gpu = read(P / shipping['gpu_report'])
    assert sha(P / shipping['gpu_report']) == shipping['gpu_report_sha256'] and gpu['passed']
    assert len(gpu['checks']) == 48 and len(gpu['samples']) == 26
    for frame in maps['captures'] + shipping['captures']:
        for key, checksum in [('image' if 'image' in frame else 'path', 'sha256'),
                              ('metadata', 'metadata_sha256')]:
            path = Path(frame[key])
            assert sha(path if path.is_absolute() else P / path) == frame[checksum]
    checks = {}
    for name, count in [('rule_tests', 102), ('map_material_continuity_tests', 39),
                        ('ground_coverage_tests', 45), ('surface_geography_tests', 39),
                        ('river_surface_tests', 48)]:
        data = read(P / 'reports' / (name + '.json'))
        assert data['passed'] and not data.get('failed', 0) and not data.get('failures')
        assert len(data['checks']) == count
        checks[name] = count
    assert read(P / 'reports/rule_tests.json')['content_hash'] == 'd9932b5aa389f0a482bf3def34201b14209071584bb4e06dc5f2c255dd010ef6'
    assert read(P / 'reports/ground_macro_asset_audit.json')['passed']
    assets = read(P / 'reports/resource_validation.json')
    assert assets['passed'] and assets['raster_count'] == 2509
    docs = read(P / 'reports/repository_documentation_validation.json')
    assert docs['passed'] and docs['runtime_source_sha256'] == runtime
    assert docs['scope'] == 'documentation_media_and_source_integrity'
    apk = read(P / 'reports/apk_content_validation.json')
    assert apk['passed'] and apk['artifact_sha256'] == binaries['android']['sha256']
    assert not apk['private_files_detected'] and len(apk['raster_import_files_verified']) == 2509
    assert all(r['current_import_bytes_match'] for r in apk['raster_import_files_verified'])
    assert len(apk['instrumental_music_imports_verified']) == 3
    assert all(r['current_import_bytes_match'] for r in apk['instrumental_music_imports_verified'])
    signature = (P / 'reports/apk_signature.log').read_text(encoding='utf-8')
    assert all(f'Verified using v{v} scheme (APK Signature Scheme v{v}): true' in signature for v in [2, 3])
    badging = (P / 'reports/apk_badging.log').read_text(encoding='utf-8')
    assert "versionName='0.2.31'" in badging and "versionCode='36'" in badging
    assert "'arm64-v8a'" in badging and "'armeabi-v7a'" in badging
    assert 'uses-permission:' not in (P / 'reports/apk_permissions.log').read_text(encoding='utf-8')
    review = read(REPORTS / 'visual_review.json')
    assert review['runtime_source_sha256'] == runtime and not review['formal_art_approval']
    assert not review['ew6_parity_claimed'] and len(review['actually_viewed_complete_images']) == 9
    for frame in review['actually_viewed_complete_images'] + review['normal_import_trial_complete_images']:
        assert frame['viewed_complete_image'] and sha(P / frame['path']) == frame['sha256']

    print('All current material-preview inputs verified.', flush=True)
    DEST.mkdir()
    shutil.copyfile(P / 'build/windows/RailwayWarlords.exe', DEST / 'RailwayWarlords.exe')
    shutil.copyfile(P / 'build/android/RailwayWarlords.apk', DEST / 'RailwayWarlords.apk')
    inputs = set()
    for folder in [REPORTS, maps_root]:
        inputs.update(f for f in folder.rglob('*') if f.is_file()
                      and f.suffix in ['.json', '.png', '.gd', '.py'] and '__pycache__' not in f.parts)
    inputs.update(P / f for f in ['README.md', 'README.en.md', 'docs/49_低地底纹与河岸材质调整.md',
        'docs/MEDIA.md', 'docs/media/manifest.json', 'assets/manifest.json', 'docs/asset-provenance/index.json',
        'presentation/data/ground_macro_catalog.json', 'presentation/data/ground_material_plan_v0231.json',
        'reports/resource_validation.json', 'reports/ground_macro_asset_audit.json',
        'reports/repository_documentation_validation.json', 'reports/export_results.json',
        'reports/apk_content_validation.json', 'reports/apk_signature.log',
        'reports/apk_badging.log', 'reports/apk_permissions.log'])
    inputs.update(P / 'reports' / (name + '.json') for name in checks)
    inputs.update(f for f in (P / 'docs/media').glob('*v0231.*'))
    inputs.update(f for f in (P / 'assets/tile').glob('tile_ground_painted_v0231_*'))
    inputs.update(f for f in (P / 'docs/asset-prompts').glob('tile_ground_painted_v0231_*.txt'))
    inputs.update(REPORTS / 'shipping_01' / (name + '.log') for name in ['gpu', 'ui_smoke', 'home'])
    evidence = DEST / 'evidence'
    evidence_rows = []
    for source in sorted(inputs):
        relative = source.relative_to(P)
        target = evidence / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        expected = sha(source)
        assert sha(target) == expected
        evidence_rows.append(dict(file=relative.as_posix(), sha256=expected, bytes=target.stat().st_size))
    receipt = dict(version='0.2.31', stage='targeted_map_material_playable_preview',
        created_at_utc=datetime.now(timezone.utc).isoformat(), runtime_source_sha256=runtime,
        base_commit='67797b494856662ec16d3007a25c477abb7ab59f',
        component_checks=checks, final_gpu_checks=48, final_map_layout_checks=58,
        current_targeted_checks=379, earlier_normal_import_trial_checks=24,
        final_shipping_images_actually_viewed=9, normal_import_trial_images_actually_viewed=6,
        new_independent_source_pngs=2, registered_source_pngs=2509,
        windows_exe_sha256=binaries['windows']['sha256'], android_apk_sha256=binaries['android']['sha256'],
        physical_android_device_tested=False, formal_art_approval=False, ew6_parity_claimed=False,
        full_thirty_group_regression_repeated=False, whole_goal_achieved=False,
        old_release_archives_modified=False, manual_image_compositing=False,
        evidence=evidence_rows, source_delivery='Git repository; no repeated full-project ZIP')
    write(DEST / 'scope_receipt.json', receipt)
    note = ('# 铁道烽烟：军阀时代 0.2.31 / Railway Warlords\n\n'
        'Windows：解压Windows包并运行RailwayWarlords.exe。Android：安装签名APK，保留相同应用签名。\n'
        'Windows: extract the Windows ZIP and run RailwayWarlords.exe. Android: install the signed APK.\n\n'
        '本版为低地底纹与河岸材质专项测试版。两张新Sub2原图已接入，20类材料保留；整体画质仍未达到欧陆战争6目标。\n'
        'This is a scoped map-material preview, with two new independent originals and twenty retained material families. Overall art parity remains unfinished.\n\n'
        '379项当前专项通过，24项早期正常导入试验另计；9张最终程序画面已实际查看。无物理X30验收，未重跑旧版30组完整套件。\n'
        '379 current targeted checks pass; 24 earlier import-trial checks are separate. Nine final-application images were viewed. No physical X30 acceptance or repeated full thirty-group suite.\n\n'
        '来源与范围见scope_receipt.json及evidence；双端与ZIP的SHA-256见preview_manifest.json。完整源码通过Git仓库交付。\n')
    (DEST / 'START_HERE.md').write_text(note, encoding='utf-8')
    archives = [('RailwayWarlords-Windows-0.2.31.zip',
                 [DEST / 'RailwayWarlords.exe', DEST / 'START_HERE.md', DEST / 'scope_receipt.json'], DEST),
                ('MapMaterialEvidence-0.2.31.zip', sorted(f for f in evidence.rglob('*') if f.is_file()), evidence)]
    for name, files, root in archives:
        with zipfile.ZipFile(DEST / name, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            for path in files:
                archive.write(path, path.relative_to(root).as_posix())
        with zipfile.ZipFile(DEST / name) as archive:
            assert archive.testzip() is None
        print('Archived and CRC-checked ' + name, flush=True)
    manifest = dict(version='0.2.31', runtime_source_sha256=runtime, stage=receipt['stage'],
        archive_directory=str(DEST), whole_goal_achieved=False, formal_art_approval=False,
        physical_android_device_tested=False, ew6_parity_claimed=False,
        artifacts=[dict(file=f.name, bytes=f.stat().st_size, sha256=sha(f))
                   for f in sorted(DEST.iterdir()) if f.is_file()])
    write(DEST / 'preview_manifest.json', manifest)
    write(P / 'reports/map_material_preview_v0231.json', manifest)
    print('MATERIAL_PREVIEW_ARCHIVED ' + str(DEST), flush=True)


if __name__ == '__main__':
    main()
