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
                'terrain_surface_native_evidence.json', 'river_surface_native_review.json', 'apk_content_validation.json']
    for name in required:
        path = P / 'reports' / name
        require(read(path).get('passed') is True, 'Required evidence failed: ' + name)
        reports.add(path)
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
    details = next(group for group in native['groups'] if group['kind'] == 'details')
    detail_rows = {Path(row['file']).stem:row for row in details['captures']}
    for name in ['yangtze', 'nanjing', 'yangtze_x30']:
        require(name in detail_rows, 'Current source-linked river viewport required: ' + name)
        hydro = read(P / detail_rows[name]['metadata'])['map_bank_visible']['hydrography']
        require(hydro['source_endpoints_preserved'] and hydro['source_linked_endpoint_frames'] > 0
                and hydro['river_surface']['drawn_textured_ribbons'] > 0, 'Primary river render proof missing: ' + name)
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
    require(provenance['count'] == len(assets) == 1156, 'Current portable provenance is incomplete')
    require(len({r['source_sha256'] for r in catalog['records'].values()}) == 80, 'Duplicate new originals')
    macros=read(P/'presentation/data/ground_macro_catalog.json')
    require(set(macros['records']) == set(catalog['types']) and len({row['source_sha256'] for row in macros['records'].values()})==20,
            'Twenty matching continuous-ground originals required')
    require(read(P/'reports/ground_macro_source_review.json')['all_twenty_originals_viewed'], 'New ground visual review missing')
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
                   terrain_types=20, detail_originals=80, macro_originals=20, new_independent_originals=0,
                   river_replacement_reaches=31, source_linked_river_continuity_verified=True,
                   total_rasters=len(assets), total_map_assets=970,
                   native_groups=len(native['groups']), native_captures=len(captures)//2,
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
本版细化来源河段的连续水面、河岸和水纹，保留原始端点及规则地图。
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
        for path in sorted(public | reports | captures):
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
                    release_kind='scoped_regional_terrain_and_war_room_ui_beta', **{k:v for k,v in summary.items() if k not in ['version','passed']},
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
    (out / '交付说明.md').write_text(f'''# 铁道烽烟 {version} · 地表与界面测试交付

Windows：解压 RailwayWarlords-Windows-{version}.zip，运行 RailwayWarlords.exe。
Android：安装 RailwayWarlords-{version}.apk，延续现有签名。目标样机 Motorola X30 尚未完成物理验收。
Godot：解压工程 ZIP，用 Godot 4.7.2 打开 game/railway_warlords/project.godot。

保留 20 类地域地表、80 张细节原图和 20 张连续底材，共 100 张专用地表原图；地图素材共 970 张，全部 PNG 共 1,156 张。本版未增加栅格原图。
本版将主河改为共享世界纹理的渐变水面；汉口、南京的31条替代主河使用既有60米有界显示圆角，上下游共用端点共享接头方向。细支流使用抗锯齿线，水陆纹理和地格规则保持来源约束。河宽是制图符号，不是历史实测岸线。
说明书与地格详情均可进入交互地形图鉴。材质按生态区、高程与既有河谷选取；不宣称逐年历史土地利用复原。

当前 {summary['regression_groups']} 组 / {summary['regression_checks']} 项回归通过；85 张地表/UI及7张局部地图原生截图、双桌面视口容量与 APK 载荷已绑定本次 EXE/源码哈希。
截图为 Windows 原生程序；README 的战斗 GIF 保留 0.2.12 原录像身份。本轮未重新宣称完整 AI 长局、正式美术/历史批准或《欧陆战争6》商业品质达标。

工程内的 PNG 即原始生成字节，提示词与便携来源索引位于 docs；原始 GIS 归档随 design 保留。不包含引擎缓存、签名、素材网关凭据或重复原图树。
完整校验值及实际范围见 release_manifest.json。旧版本交付保持不变。
''', encoding='utf-8')
    print(json.dumps(dict(passed=True, release=str(out), artifacts=manifest['artifacts']), ensure_ascii=True), flush=True)


if __name__ == '__main__':
    main()
