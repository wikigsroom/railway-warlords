"""Deliver the verified atlas/office refinement with the existing strict gates."""
from datetime import datetime, timezone
import hashlib
import json
import shutil
import subprocess
import zipfile
from build_release import P, ROOT, source_digest
from package_delivery import read, sha, require, add_tree
from package_ui_refinement import validate, write


def main():
    summary, reports, captures, regression = validate('atlas_office')
    version = summary['version']
    require(version == '0.2.24', 'This delivery specification targets 0.2.24')
    out = ROOT / 'output/releases' / ('railway-warlords-' + version)
    out.mkdir(parents=True, exist_ok=True)
    exe = P / 'build/windows/RailwayWarlords.exe'
    apk = P / 'build/android/RailwayWarlords.apk'
    portable = out / 'Windows便携版'
    portable.mkdir(exist_ok=True)
    shutil.copyfile(exe, portable / exe.name)
    note = f'''# 铁道烽烟 {version} · 战区沙盘与外交事务

Windows：解压Windows ZIP，运行RailwayWarlords.exe。Android：安装同版本APK，沿用既有签名，版本代码29。Godot：用4.7.2打开源码内game/railway_warlords/project.godot。

- 选关沙盘复用战场的完整地表、高程、河流与独立地形素材；增加缩放、拖动、双指缩放与复位。城市和有来源的地方节点使用既有完整建筑原图，目标名称优先显示。没有新增或改写地理、疆界、河流、村镇或原始PNG。
- 铁路、地方节点按已登记的生效日期筛选。地图原始数据不可变；浏览器不生成战局，也不消耗游戏随机数。
- 外交页改为独立滚动的势力名册与选中对象详情，显示真实条约、期限日期、提案评分及本方已侦知编队。不会以全体敌军数代替本方情报。
- 外交命令继续通过现有工作线程与核心规则执行。已实测向选中有效势力付款50、建立在途援助、更新评分与冷却；撤离对象按现有规则退回未送达援助的一半。
- 将旧版征服定义表剩余的三条7天登记同步为1天，设计登记表同步。61个可玩剧本及每轮全阵营行动完成后推进公历1天的规则保持一致。
- 保留33人四阶段、135张独立肖像。李德胜1917年为青年，1947年为中年；当前可玩时间锚点仍止于1940，1947肖像属于素材准备。当前内容哈希已更新，旧战局需重开。

本轮29组/{summary['regression_checks']}项回归通过，专项证据共{summary['native_captures']}张未经编辑的Windows原生视口。APK核对签名、ARM64/ARMv7、1304张导入纹理及3首纯器乐。桌面手机比例和大字布局均以当前导出EXE检查；Motorola X30未连接，不宣称物理设备验收。

本轮新增栅格图片0张，全部沿用经指定Sub2路线生成的可追溯原图。完整地图的材质、山脚和河岸仍需美术深化，全部兵种动画、逐年代历史复核、每日制长局平衡、独立声音签核及X30触控/GPU验收仍未完成。不宣称已达到欧陆战争6整体品质。

The selection atlas now shares the shipping terrain renderer and supports zoom, pan, pinch and fit. Whole settlement art, dated places and railways are retained. Diplomacy uses a selected-counterparty office, actual treaty dates, visibility-limited intelligence, validated offers and real aid transactions. All 33 four-stage people and daily rounds are retained. Existing immutable Sub2 originals are reused; no new raster artwork is claimed. Physical X30 acceptance and overall EW6 parity remain pending.
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
    print('Packaging source, original art, dated design and current native evidence.', flush=True)
    with zipfile.ZipFile(source, 'w', zipfile.ZIP_DEFLATED, compresslevel=1) as archive:
        for path in sorted(public | reports | captures):
            if not path.is_file():
                continue
            require(not any(part in {'.git', '.godot', '.toolchain', 'build', '__pycache__', 'signing'}
                            for part in path.relative_to(P).parts), 'Private path in archive')
            archive.write(path, path.relative_to(ROOT).as_posix())
        add_tree(archive, ROOT / 'design', ROOT, allowed={'.md', '.json', '.py', '.csv', '.txt', '.png', '.shp', '.shx', '.dbf', '.prj', '.cpg', '.html', '.xml', '.zip', '.tif', '.pdf'})
    print('Verifying complete archive CRCs and tested binary identity.', flush=True)
    for path in [windows, source]:
        with zipfile.ZipFile(path) as archive:
            require(archive.testzip() is None, 'Corrupt archive: ' + path.name)
    with zipfile.ZipFile(windows) as archive:
        require(hashlib.sha256(archive.read(exe.name)).hexdigest() == sha(exe), 'Portable binary differs')
    require(sha(android) == sha(apk) and source_digest()[0] == summary['runtime_source_sha256'], 'Delivery identity changed')
    manifest = dict(**summary, created_at_utc=datetime.now(timezone.utc).isoformat(),
                    release_kind='scoped_selection_atlas_and_diplomacy_office_beta', regression=regression,
                    artifacts=[dict(file=p.name, bytes=p.stat().st_size, sha256=sha(p)) for p in [windows, android, source]],
                    reports=[dict(file=p.relative_to(P).as_posix(), sha256=sha(p)) for p in sorted(reports)],
                    archive_integrity_verified=True, old_releases_modified=False)
    write(out / 'release_manifest.json', manifest)
    (out / '交付说明.md').write_text(note, encoding='utf-8')
    shutil.copyfile(P / 'docs/42_战区沙盘与外交事务精修.md', out / '战区沙盘与外交事务精修.md')
    print(json.dumps(dict(passed=True, release=str(out), artifacts=manifest['artifacts']), ensure_ascii=True), flush=True)


if __name__ == '__main__':
    main()
