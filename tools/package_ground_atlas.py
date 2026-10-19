"""Package quiet-ground beta exports with every retained strict release gate."""
from datetime import datetime, timezone
import hashlib
import json
import shutil
import subprocess
import zipfile
from build_release import P, ROOT, source_digest
from package_delivery import sha, require, add_tree
from package_ui_refinement import validate, write


def main():
    summary, reports, captures, regression = validate('ground_atlas')
    version = summary['version']
    out = ROOT / 'output/releases' / ('railway-warlords-' + version)
    out.mkdir(parents=True, exist_ok=True)
    exe = P / 'build/windows/RailwayWarlords.exe'
    apk = P / 'build/android/RailwayWarlords.apk'
    portable = out / 'Windows便携版'
    portable.mkdir(exist_ok=True)
    shutil.copyfile(exe, portable / exe.name)
    note = f'''# 铁道烽烟 {version} · 安静地表与山脚融合

Windows：解压Windows ZIP，运行RailwayWarlords.exe。Android：安装同版本APK，沿用既有签名，版本代码30。Godot：用4.7.2打开源码内game/railway_warlords/project.godot。

本版新增20张经指定Sub2路线直接生成的独立地表原图，降低草土与岩地的细碎反差，保留20类不同材质。完整原图逐张查看后接入，40张前批底材和提示词保留。世界坐标下三组平移取样减轻固定周期重复，近景细节层更克制，山脚轮廓底部平滑接入现有地面。原始PNG未裁切、补绘、拼图或叠字。

规则地图、年代地理、河流、高程、生态区分配及数值均与已交付0.2.24比较保留原字节。61个剧本每完整回合推进1天，33人四阶段和135张人物原图沿用；李德胜1917青年、1947中年，1947仍仅为素材准备。源图片共1,324张，地图存储1,010张、启用970张。

29组/{summary['regression_checks']}项回归、48项原生材质夹具、{summary['native_captures']}张当前专项原生画面和18项配乐播放检查完成。所有证据绑定实际导出EXE及运行源码SHA。APK检查签名、ARM64/ARMv7、1,324张导入纹理和3首纯器乐。完整来源、限制及人工查看范围见源码docs/43_安静地表与山脚融合.md和reports/ground_atlas_native_review.json。

Motorola X30未连接，桌面2400×1080仅为移动布局档案。完整商业美术、全兵种动画、逐年代史实、每日长局平衡、独立声音签核及X30触控/GPU验收仍未完成，不宣称达到欧陆战争6整体品质。旧版本和旧录像保留各自身份。

Twenty directly generated Sub2 ground originals replace the active base materials; forty earlier originals remain intact. World-anchored translated sampling reduces fixed wallpaper repetition, fine detail is restrained, and mountain feet blend into the existing ground. Dated geography and rule JSON retain the delivered 0.2.24 bytes. Daily rounds, all 33 four-stage people and 135 portraits remain. Windows and Android payloads are verified; physical X30 acceptance, full art approval and overall EW6 parity remain pending.
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
                    release_kind='scoped_quiet_ground_and_mountain_foot_beta', regression=regression,
                    artifacts=[dict(file=p.name, bytes=p.stat().st_size, sha256=sha(p)) for p in [windows, android, source]],
                    reports=[dict(file=p.relative_to(P).as_posix(), sha256=sha(p)) for p in sorted(reports)],
                    archive_integrity_verified=True, old_releases_modified=False)
    write(out / 'release_manifest.json', manifest)
    (out / '交付说明.md').write_text(note, encoding='utf-8')
    shutil.copyfile(P / 'docs/43_安静地表与山脚融合.md', out / '安静地表与山脚融合.md')
    print(json.dumps(dict(passed=True, release=str(out), artifacts=manifest['artifacts']), ensure_ascii=True), flush=True)


if __name__ == '__main__':
    main()
