"""Package the continuous-water beta with all retained strict release gates."""
from datetime import datetime, timezone
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import zipfile
from build_release import P, ROOT, current_version, source_digest
from package_delivery import sha, require, add_tree
from package_ui_refinement import validate, write
from verify_git_bytes import inspect as inspect_git_bytes


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--prepare-receipt', action='store_true',
                        help='Reserve the documented receipt path with an explicit pending/failed state.')
    args = parser.parse_args()
    if args.prepare_receipt:
        require(current_version() == '0.2.27', 'Unexpected receipt version')
        path = P / 'reports/water_map_release_validation.json'
        require(not path.exists(), 'Do not overwrite an existing delivery receipt')
        write(path, dict(passed=False, version=current_version(),
                         status='pending_strict_delivery_validation',
                         note='Link destination reserved before repository checks. Only the complete strict packager can replace this with a passed receipt.'))
        print(json.dumps(dict(prepared=True, release_validated=False)), flush=True)
        return
    summary, reports, captures, regression = validate('water_map')
    # The validator owns this final receipt; stage it and rebind the index
    # without changing a source, image, capture or earlier test result.
    subprocess.run(['git', 'add', '--', 'reports/water_map_release_validation.json'], cwd=P, check=True)
    subprocess.run([sys.executable, '-X', 'utf8', 'tools/verify_git_bytes.py'], cwd=P, check=True)
    subprocess.run(['git', 'add', '--', 'reports/git_byte_preservation.json'], cwd=P, check=True)
    checked, errors = inspect_git_bytes(include_receipt=True)
    require(checked > 0 and not errors, 'Final release receipts differ from staged working bytes')
    version = summary['version']
    require(version == '0.2.27' and summary['apk_version_code'] == 32, 'Water release identity differs')
    out = ROOT / 'output/releases' / ('railway-warlords-' + version)
    out.mkdir(parents=True, exist_ok=True)
    exe = P / 'build/windows/RailwayWarlords.exe'
    apk = P / 'build/android/RailwayWarlords.apk'
    portable = out / 'Windows便携版'
    portable.mkdir(exist_ok=True)
    shutil.copyfile(exe, portable / exe.name)
    note = f'''# 铁道烽烟 {version} · 连续水纹与真实蜂窝显示

Windows：解压Windows ZIP，运行RailwayWarlords.exe。Android：安装同版本APK，沿用既有签名，版本代码32。Godot：用4.7.2打开源码内game/railway_warlords/project.godot。

海面、河面和内陆水面分别使用三张新的独立Sub2原图；世界坐标镜像取样、三路平移和mipmap过滤减轻接缝，远景采用整张原图的mipmap平均值去除重复亮点。删除总览三组轴线组成的三角网纹；可选规则蜂窝仍为48世界单位，缩放低于0.20隐藏。未加工任何PNG，未改变海岸、河道、历史行政、城市、铁路、规则或数值。

61个剧本每完整全阵营回合推进公历1天；33人四阶段、135张肖像保留。李德胜1917青年、1947中年；1947仍仅为素材准备。共1,327张PNG原图，地图资源存储1,013张，其中973张可用、40张旧底材保留。

29组/{summary['regression_checks']}项回归、61项原生海岸网格、48项地表GPU夹具、22项水面GPU夹具、{summary['native_captures']}张专项完整原生画面及18项配乐播放检查完成。既有独立GIS审计仍绑定同字节地图。人工查看范围与未解决问题见docs/45_连续水纹与真实蜂窝显示.md及实际查看记录；截图生成不等于所有画面人工通过。

schema2/ruleset10与0.2.26内容哈希一致；0.2.26进行中战局可沿用原有内容身份。更早包的兼容限制按原交付说明保留。源地理数据的LGPL通知、完整许可、可编辑区域源集与原始下载校验随包保留。

本次RTX 3060桌面静止战场180帧样本平均{summary['desktop_static_average_fps']:.2f} FPS、帧时p95为{summary['desktop_static_frame_ms_p95']:.2f}ms，未达到60帧目标。该样本未记录窗口焦点或遮挡，也没有同条件旧版基线，不能据此归因于水面改动或推算手机表现；原始报告、日志与完整视口随源码保留。受控前台、移动/战斗及物理手机性能仍需继续核验。

Motorola X30尚未完成物理验收，2400×1080仍是桌面移动布局检查。完整商业美术、全兵种动画、逐年代军史、每日长局平衡、独立声音签核和欧陆战争6整体品质对等仍待完成。

Three independent full Sub2 originals provide continuous sea, river and inland-water materials. World-anchored mirrored sampling and translated blends retain tactical waves; continental zoom fades to the complete source's mip average. The triangular overview guides are removed while actual optional 48-unit hexes remain. Delivered 0.2.26 geography, historical data, rules and original artwork retain their bytes and content identity. Complete all-faction rounds still advance one Gregorian day; all 33 people retain four living stages and 135 portraits. Li Desheng uses a youthful 1917 and middle-aged 1947 appearance; 1947 remains art preparation only. Current Windows/Android exports and scoped evidence are included. Physical Motorola X30 acceptance and overall EW6 parity remain pending.

The recorded RTX 3060 static sample averages {summary['desktop_static_average_fps']:.2f} FPS and misses the 60 FPS target. Window focus/occlusion were not recorded and no matched old-build baseline is available; this sample does not establish causality or phone performance. Raw evidence is retained for controlled follow-up.
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
    public = {P / name.decode('utf-8') for name in raw.split(b'\0') if name}
    print('Packaging source, immutable originals, dated design and native evidence.', flush=True)
    with zipfile.ZipFile(source, 'w', zipfile.ZIP_DEFLATED, compresslevel=1) as archive:
        for path in sorted(public | reports | captures):
            if not path.is_file():
                continue
            require(not any(part in {'.git', '.godot', '.toolchain', 'build', '__pycache__', 'signing'}
                            for part in path.relative_to(P).parts), 'Private path in archive')
            archive.write(path, path.relative_to(ROOT).as_posix())
        add_tree(archive, ROOT / 'design', ROOT,
                 allowed={'.md', '.json', '.py', '.csv', '.txt', '.png', '.shp', '.shx', '.dbf', '.prj', '.cpg', '.html', '.xml', '.zip', '.tif', '.pdf'})
    print('Verifying complete archive CRCs and tested binary identity.', flush=True)
    for path in [windows, source]:
        with zipfile.ZipFile(path) as archive:
            require(archive.testzip() is None, 'Corrupt archive: ' + path.name)
    with zipfile.ZipFile(windows) as archive:
        require(hashlib.sha256(archive.read(exe.name)).hexdigest() == sha(exe), 'Portable binary differs')
    require(sha(android) == sha(apk) and source_digest()[0] == summary['runtime_source_sha256'], 'Delivery identity changed')
    manifest = dict(**summary, created_at_utc=datetime.now(timezone.utc).isoformat(),
                    release_kind='scoped_continuous_water_and_actual_hex_grid_beta', regression=regression,
                    artifacts=[dict(file=p.name, bytes=p.stat().st_size, sha256=sha(p)) for p in [windows, android, source]],
                    reports=[dict(file=p.relative_to(P).as_posix(), sha256=sha(p)) for p in sorted(reports)],
                    archive_integrity_verified=True, old_releases_modified=False)
    write(out / 'release_manifest.json', manifest)
    (out / '交付说明.md').write_text(note, encoding='utf-8')
    shutil.copyfile(P / 'docs/45_连续水纹与真实蜂窝显示.md', out / '连续水纹与真实蜂窝显示.md')
    print(json.dumps(dict(passed=True, release=str(out), artifacts=manifest['artifacts']), ensure_ascii=True), flush=True)


if __name__ == '__main__':
    main()
