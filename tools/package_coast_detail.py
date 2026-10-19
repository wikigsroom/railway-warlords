"""Package source-coast beta exports with every retained strict release gate."""
from datetime import datetime, timezone
import hashlib
import json
import shutil
import subprocess
import sys
import zipfile
from build_release import P, ROOT, source_digest
from package_delivery import sha, require, add_tree
from package_ui_refinement import validate, write
from verify_git_bytes import inspect as inspect_git_bytes


def main():
    summary, reports, captures, regression = validate('coast_detail')
    # Validation writes its final receipt after inspecting the index. Stage
    # only that owned receipt, then bind all staged bytes again, including it.
    # No runtime, artwork, capture or test result is changed by this step.
    subprocess.run(['git', 'add', '--', 'reports/coast_detail_release_validation.json'], cwd=P, check=True)
    subprocess.run([sys.executable, '-X', 'utf8', 'tools/verify_git_bytes.py'], cwd=P, check=True)
    subprocess.run(['git', 'add', '--', 'reports/git_byte_preservation.json'], cwd=P, check=True)
    checked, errors = inspect_git_bytes(include_receipt=True)
    require(checked > 0 and not errors, 'Final release receipts differ from staged working bytes')
    version = summary['version']
    out = ROOT / 'output/releases' / ('railway-warlords-' + version)
    out.mkdir(parents=True, exist_ok=True)
    exe = P / 'build/windows/RailwayWarlords.exe'
    apk = P / 'build/android/RailwayWarlords.apk'
    portable = out / 'Windows便携版'
    portable.mkdir(exist_ok=True)
    shutil.copyfile(exe, portable / exe.name)
    note = f'''# 铁道烽烟 {version} · 细海岸与沿岸图层统一

Windows：解压Windows ZIP，运行RailwayWarlords.exe。Android：安装同版本APK，沿用既有签名，版本代码31。Godot：用4.7.2打开源码内game/railway_warlords/project.godot。

京津、京奉、中国东部、亚洲战略层使用经原始GIS核对的GSHHG 2.3.7 L1自然海岸，配合离线三角网和窄渐隐岸带。地表、行政线和城市影响区统一按真实陆地裁切；城市控制边仅保留原边在陆地上的部分，减少沿海重复描边。原PNG、提示词、日期规则、规则格、历史行政资料、城市、铁路、渡点和经济数值不变。

61个剧本每完整全阵营回合推进公历1天；33人四阶段、135张肖像和1,324张PNG原图保留。李德胜1917青年、1947中年；1947仍仅为素材准备。

29组/{summary['regression_checks']}项回归、61项原生海岸网格检查、{summary['independent_geography_checks']}项独立GIS审计、48项原生材质夹具、{summary['native_captures']}张专项原生画面及18项配乐播放检查完成。完整人工查看范围与剩余问题见docs/44_细海岸与沿岸图层统一.md。源数据的LGPL通知、完整许可、可编辑区域源集和原始下载校验随包保留。海岸资料不代表1840—1940港区及填海的逐年实测。

schema2/ruleset10保留；地理绘制数据导致内容哈希改变，0.2.25进行中战局请使用保留的0.2.25包继续，本版新开战局。生涯档案沿用既有格式。

Motorola X30尚未完成物理验收，2400×1080仍是桌面移动布局检查。完整商业美术、全兵种动画、逐年代军史、每日长局平衡、独立声音签核和欧陆战争6整体品质对等仍待完成。

Four maps use traceable GSHHG 2.3.7 L1 marine drawing geometry, offline triangulation and a narrow fading shoreline batch. Ground, administrative display lines and city influence meshes use the same land boundary; influence edges preserve only their original land portions. Rule fields, daily rounds, all 33 four-stage people and 135 portraits remain unchanged. Existing inland water is preserved; no modern L2 reservoir or political border is imported. This is a natural reference, not a dated harbor survey. Editable subsets and LGPL notices accompany the source. Start a fresh 0.2.26 match; retained 0.2.25 builds continue their existing matches. Physical Motorola X30 acceptance and overall EW6 parity remain pending.
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
                    release_kind='scoped_sourced_coast_and_land_clipped_overlay_beta', regression=regression,
                    artifacts=[dict(file=p.name, bytes=p.stat().st_size, sha256=sha(p)) for p in [windows, android, source]],
                    reports=[dict(file=p.relative_to(P).as_posix(), sha256=sha(p)) for p in sorted(reports)],
                    archive_integrity_verified=True, old_releases_modified=False)
    write(out / 'release_manifest.json', manifest)
    (out / '交付说明.md').write_text(note, encoding='utf-8')
    shutil.copyfile(P / 'docs/44_细海岸与沿岸图层统一.md', out / '细海岸与沿岸图层统一.md')
    print(json.dumps(dict(passed=True, release=str(out), artifacts=manifest['artifacts']), ensure_ascii=True), flush=True)


if __name__ == '__main__':
    main()
