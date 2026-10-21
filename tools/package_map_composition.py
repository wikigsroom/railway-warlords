"""Package the map composition revision after all retained and new release gates."""
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
    parser.add_argument('--prepare-receipt', action='store_true')
    args = parser.parse_args()
    receipt = P / 'reports/map_composition_release_validation.json'
    require(current_version() == '0.2.29', 'Unexpected composition version')
    if args.prepare_receipt:
        require(not receipt.exists(), 'Do not overwrite an existing receipt')
        write(receipt, dict(passed=False, version=current_version(),
            status='pending_strict_delivery_validation',
            note='Reserved documentation link. Full strict packaging must replace this pending receipt.'))
        return
    summary, reports, captures, regression = validate('map_composition')
    subprocess.run(['git', 'add', '--', receipt.relative_to(P).as_posix()], cwd=P, check=True)
    subprocess.run([sys.executable, '-X', 'utf8', 'tools/verify_git_bytes.py'], cwd=P, check=True)
    subprocess.run(['git', 'add', '--', 'reports/git_byte_preservation.json'], cwd=P, check=True)
    checked, errors = inspect_git_bytes(include_receipt=True)
    require(checked > 0 and not errors, 'Final staged receipt differs from working bytes')
    version = summary['version']
    require(version == '0.2.29' and summary['apk_version_code'] == 34, 'Dual-platform release identity differs')
    out = ROOT / 'output/releases' / ('railway-warlords-' + version)
    out.mkdir(parents=True, exist_ok=True)
    # A terminal delivery is immutable. A failed/incomplete attempt can be rebuilt.
    require(not (out / 'release_manifest.json').exists(), 'Do not overwrite a completed release')
    exe = P / 'build/windows/RailwayWarlords.exe'
    apk = P / 'build/android/RailwayWarlords.apk'
    portable = out / 'Windows便携版'
    portable.mkdir(exist_ok=True)
    shutil.copyfile(exe, portable / exe.name)
    note = f'''# 铁道烽烟 {version} · 地图模型比例与统一标注布局

Windows：解压Windows ZIP后运行RailwayWarlords.exe。Android：安装本版APK，沿用既有签名，版本代码34。Godot：用4.7.2打开源码内game/railway_warlords/project.godot。全部构建及检查使用原生Windows。

村落、集镇、县城、城市、省城采用五级建筑显示尺度；普通编队76×68、驻城编队62×56世界单位。建筑、编队仍引用完整独立原图。城市、聚落和桥渡文字共享布局，避让实际显示的建筑轮廓、编队位置、朝向标识与HUD。移动和交战期间读取演出中的对象位置。原规则蜂窝半径48不变。

本轮没有新增或加工PNG。0.2.28的2,507张原图、全部地图地理、河流、铁路、人物、数值、编队坐标及提示词保留字节；内容哈希仍为{summary['content_hash']}，schema2/ruleset11。0.2.28进行中战局可沿用内容身份；更早版本请按原包兼容说明处理。原有地理源集、许可和通知随源码交付。

将领池仍为324名军事人物及4名政治背景人物。303名符合旅级及以上、海军或历史同类指挥职务；另外21名单独标明副师职或政治共同指挥。114名已有编写的剧本玩法资格，210名仍待逐年代部署；295名使用未评级指挥类别模板，不能将入库数当作已可招募人数。61个剧本采用独立阵营名册，人数没有统一上限。全部328人保留四个生前阶段和1,315张肖像。

本版通过{summary['regression_groups']}组/{summary['regression_checks']}项回归，地图布局另有7张完整导出视口和58项检查。保留原有肖像、将领任命、总部交互、地图材质、海岸、水面、APK内容/签名及音频播放检查，共{summary['native_captures']}张专项原生视口。截图生成数量与人工查看数量分开记录。

桌面静止战场180帧样本平均{summary['desktop_static_average_fps']:.2f} FPS、帧时p95为{summary['desktop_static_frame_ms_p95']:.2f}ms，60帧目标是否达到以原始报告为准。窗口焦点和遮挡未记录，也没有受控旧版基线；不能推断手机表现。2400×1080仅为桌面移动布局检查，Motorola X30尚未完成物理验收。

完整画面仍存在山脚接地、地表层次、细河岸、支流折线、区域取景、兵种全动作和整体UI精修等问题，详见docs/47_地图模型比例与统一标注布局.md及实际查看记录。亚洲起局还存在库伦1927/1940归属、晚期奥斯曼/卡扎尔身份、1940年1月维希标签及部分城市日期名称错误，详见docs/23_当前完成度评估.md；本轮保留原内容不代表这些史实已通过。逐年代军史、全部将领部署、每日长局平衡、独立完整曲目试听与欧陆战争6整体品质目标均未完成。

This revision introduces rank-based settlement display sizes and a shared label allocator for cities, villages and crossings. Labels account for the actual chosen building, unit position, facing markers and HUD during both static and animated scenes. All complete raster originals remain unchanged; no screenshot or bitmap was composited or repainted. Geography, the 48-unit operation hexes, ruleset 11 and the 0.2.28 content identity are preserved.

Both Windows and signed Android builds retain the prior commander, UI, material, coast, water, audio and payload gates, with seven additional full native map views and 58 composition checks. The 324-person military catalogue is not the recruitable count: 114 have authored scenario availability and 210 await dated deployment. Physical Motorola X30 testing, final art acceptance and overall EW6 parity remain pending. See the manifest and raw evidence for exact results and remaining limits.
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
    print('Packaging verified source, unchanged originals and complete native evidence.', flush=True)
    with zipfile.ZipFile(source, 'w', zipfile.ZIP_DEFLATED, compresslevel=1) as archive:
        for path in sorted(public | reports | captures):
            if not path.is_file():
                continue
            require(not any(part in {'.git', '.godot', '.toolchain', 'build', '__pycache__', 'signing'}
                for part in path.relative_to(P).parts), 'Private path in archive')
            archive.write(path, path.relative_to(ROOT).as_posix())
        add_tree(archive, ROOT / 'design', ROOT,
            allowed={'.md', '.json', '.py', '.csv', '.txt', '.png', '.shp', '.shx', '.dbf', '.prj', '.cpg', '.html', '.xml', '.zip', '.tif', '.pdf'})
    print('Checking complete ZIP CRCs and tested binary identity.', flush=True)
    for path in [windows, source]:
        with zipfile.ZipFile(path) as archive:
            require(archive.testzip() is None, 'Corrupt archive: ' + path.name)
    with zipfile.ZipFile(windows) as archive:
        require(hashlib.sha256(archive.read(exe.name)).hexdigest() == sha(exe), 'Portable executable differs')
    require(sha(android) == sha(apk) and source_digest()[0] == summary['runtime_source_sha256'], 'Delivery identity changed')
    manifest = dict(**summary, created_at_utc=datetime.now(timezone.utc).isoformat(),
        release_kind='scoped_map_model_scale_and_shared_annotation_beta', regression=regression,
        artifacts=[dict(file=p.name, bytes=p.stat().st_size, sha256=sha(p)) for p in [windows, android, source]],
        reports=[dict(file=p.relative_to(P).as_posix(), sha256=sha(p)) for p in sorted(reports)],
        archive_integrity_verified=True, old_releases_modified=False)
    write(out / 'release_manifest.json', manifest)
    (out / '交付说明.md').write_text(note, encoding='utf-8')
    shutil.copyfile(P / 'docs/47_地图模型比例与统一标注布局.md', out / '地图模型比例与统一标注布局.md')
    print(json.dumps(dict(passed=True, release=str(out), artifacts=manifest['artifacts']), ensure_ascii=True), flush=True)


if __name__ == '__main__':
    main()
