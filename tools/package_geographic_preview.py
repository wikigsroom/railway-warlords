"""Package verified native preview binaries; preserve previous release folders."""
from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import zipfile

P = Path(__file__).resolve().parents[1]
R = P / 'reports/geographic_relief_v0236'
ROOT = P.parents[1]


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--attempt', default='01')
    args = parser.parse_args()
    receipt = R / ('package' + args.attempt + '.json')
    out = ROOT / 'output/development' / ('railway-warlords-0.2.36-preview' + args.attempt)
    if receipt.exists() or out.exists():
        raise FileExistsError('Refuse to replace a preview package or receipt')
    export = read(R / 'preview_export01.json')
    regression = read(R / 'regression01/validation.json')
    apk = read(R / 'apk01/validation.json')
    reviewed = read(R / 'visual_review01.json')
    validations = [read(R / 'exported_windows' / folder / 'validation.json')
                   for folder in ['core01', 'control01', 'benchmark01']]
    assert export['passed'] and regression['passed'] and apk['passed'] and reviewed['passed']
    assert all(v['passed'] and v['binary_unchanged_during_checks'] for v in validations)
    assert regression['groups'] == 30 and regression['checks'] > 14000
    assert export['version'] == '0.2.36' and export['android_version_code'] == 41
    for report in [regression, *validations]:
        assert report['runtime_source_merkle_sha256'] == export['runtime_source_merkle_sha256']
    windows = next(a for a in export['artifacts'] if a['target']=='windows')
    android = next(a for a in export['artifacts'] if a['target']=='android')
    assert apk['artifact_sha256'] == android['sha256']
    assert all(v['exe_sha256'] == windows['sha256'] for v in validations)
    expected_images = set()
    core = R / 'exported_windows/core01'
    for row in validations[0]['cases']:
        expected_images.add((core / row['id'] / 'viewport.png').relative_to(P).as_posix())
    control = read(R / 'exported_windows/control01/control/validation.json')
    for row in control['captures']:
        expected_images.add(Path(row['path']).relative_to(P).as_posix())
    expected_images.add('reports/geographic_relief_v0236/exported_windows/benchmark01/asia_idle/viewport.png')
    images = reviewed['exported_application_images']
    assert {row['file'] for row in images} == expected_images
    assert all(row['actually_viewed'] and sha(P / row['file']) == row['sha256'] for row in images)
    out.mkdir(parents=True, exist_ok=False)
    artifacts = []
    for item, filename in [(windows, 'RailwayWarlords-0.2.36-preview-windows-x64.exe'),
                           (android, 'RailwayWarlords-0.2.36-preview-android.apk')]:
        source = Path(item['path'])
        assert sha(source) == item['sha256'] and source.stat().st_size == item['bytes']
        target = out / filename
        shutil.copyfile(source, target)
        copied_sha = sha(target)
        assert copied_sha == item['sha256']
        artifacts.append(dict(target=item['target'], file=filename, bytes=target.stat().st_size, sha256=copied_sha))
    evidence = out / 'geographic-relief-verification.zip'
    with zipfile.ZipFile(evidence, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in sorted(R.rglob('*')):
            if path.is_file() and '__pycache__' not in path.parts:
                archive.write(path, path.relative_to(P).as_posix())
        for filename in ['58_亚洲细高程与沿海控制覆盖.md', '56_细水系圆角与水床显示.md', '57_源岸线方向与柔和海岸过渡.md']:
            archive.write(P / 'docs' / filename, 'docs/' + filename)
    evidence_row = dict(file=evidence.name, bytes=evidence.stat().st_size, sha256=sha(evidence))
    manifest = dict(passed=True, version='0.2.36', android_version_code=41,
                    channel='development_review', official_release=False,
                    created_at_utc=datetime.now(timezone.utc).isoformat(),
                    controller_sha256=sha(__file__), output_path=str(out),
                    runtime_source_merkle_sha256=export['runtime_source_merkle_sha256'],
                    runtime_identity_method=export['identity_method'], content_hash=regression['content_hash'],
                    export_receipt_sha256=sha(R / 'preview_export01.json'),
                    regression_receipt_sha256=sha(R / 'regression01/validation.json'),
                    visual_review_sha256=sha(R / 'visual_review01.json'),
                    apk_receipt_sha256=sha(R / 'apk01/validation.json'),
                    full_regression_groups=regression['groups'], full_regression_checks=regression['checks'],
                    exported_whole_viewports_individually_viewed=len(images),
                    artifacts=artifacts, evidence=evidence_row,
                    new_raster_art=0, new_music_tracks=0, existing_raster_png_count=2521,
                    future_music_route='music-gen-remote-YuE2 / remote native Windows RTX 3080 / instrumental',
                    previous_release_preserved='output/releases/railway-warlords-0.2.35',
                    formal_art_approval=False, physical_android_device_tested=False,
                    remaining=['coarse material boundaries', 'repeated terrain symbols', 'complete unit actions',
                               'historical timeline corrections', 'physical Motorola X30 acceptance'],
                    committed_source_identity_record='SOURCE_RECEIPT.json added after source commit/push; runtime Merkle already fixed')
    for path in [out / 'manifest.json', receipt]:
        with path.open('x', encoding='utf-8') as stream:
            json.dump(manifest, stream, ensure_ascii=False, indent=2); stream.write('\n')
    text = '''# 铁道烽烟 0.2.36 · 地图开发预览 / Map development preview

Windows：运行 RailwayWarlords-0.2.36-preview-windows-x64.exe，无需安装Godot。
Android：安装 RailwayWarlords-0.2.36-preview-android.apk，版本code41，ARM64/ARMv7，最低Android 7/API24。
这版包含亚洲连续高程、沿海控制补色及此前的细水系／海岸修订。0.2.35完整归档保持不变。

Windows: run the standalone EXE. Android: install the signed APK (code41, ARM64/ARMv7, API24+).
The preview includes continuous Asian relief, coastal control coverage, and earlier river/shore changes.

正式程序画面、原始失败尝试、来源和回归证据见 geographic-relief-verification.zip。
See manifest.json for exact checksums, scope and limitations; SOURCE_RECEIPT.json records the later committed source identity.

开发预览尚未达到《欧陆战争6》整体美术水准；粗材质块界、重复山体及完整兵种动作仍待修复。
Motorola X30尚未进行物理验收；桌面2400×1080布局检查不代表手机性能。
Art parity, complete unit actions and physical Motorola X30 acceptance remain unfinished.
后续新增配乐使用远端RTX 3080 YuE2纯器乐；本版未新增音乐，保留三首既有本地作品的实际来源。
'''
    (out / 'START_HERE.md').write_text(text, encoding='utf-8')
    print(json.dumps(manifest, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
