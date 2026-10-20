"""Package the sourced commander expansion after native and dual-export gates."""
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
    receipt = P / 'reports/commander_pool_release_validation.json'
    if args.prepare_receipt:
        require(current_version() == '0.2.28', 'Unexpected receipt version')
        require(not receipt.exists(), 'Do not overwrite an existing receipt')
        write(receipt, dict(passed=False, version=current_version(),
            status='pending_strict_delivery_validation',
            note='Reserved link only. The full strict packager must replace this pending receipt.'))
        print(json.dumps(dict(prepared=True, release_validated=False)), flush=True)
        return
    summary, reports, captures, regression = validate('commander_pool')
    subprocess.run(['git', 'add', '--', str(receipt.relative_to(P))], cwd=P, check=True)
    subprocess.run([sys.executable, '-X', 'utf8', 'tools/verify_git_bytes.py'], cwd=P, check=True)
    subprocess.run(['git', 'add', '--', 'reports/git_byte_preservation.json'], cwd=P, check=True)
    checked, errors = inspect_git_bytes(include_receipt=True)
    require(checked > 0 and not errors, 'Final receipt differs from staged bytes')
    version = summary['version']
    require(version == '0.2.28' and summary['apk_version_code'] == 33, 'Commander release identity differs')
    out = ROOT / 'output/releases' / ('railway-warlords-' + version)
    out.mkdir(parents=True, exist_ok=True)
    exe = P / 'build/windows/RailwayWarlords.exe'
    apk = P / 'build/android/RailwayWarlords.apk'
    portable = out / 'Windows便携版'
    portable.mkdir(exist_ok=True)
    shutil.copyfile(exe, portable / exe.name)
    note = f'''# 铁道烽烟 {version} · 师旅级将领池与独立战役名册

Windows：解压Windows ZIP后运行RailwayWarlords.exe。Android：安装同版本APK，沿用既有签名，版本代码33。Godot：用4.7.2打开源码内game/railway_warlords/project.godot。全部工具在原生Windows运行。

军事人物从29名扩为324名，另保留4名政治背景人物，共328人。按登记职务，303人属于旅级及以上、海军指挥或历史同类统帅（含12名军及以上副职）；另有20名副师职及1名军级政治共同指挥，单独标记。资料来源148项；完整名册、职务、参考年份及出处在docs/data/commanders.csv。

61个剧本分别登记开局名册，共280条开局条目；10个自由世界入口另有89条可选后备条目。人数逐场逐阵营配置，没有统一3人或5人上限。总部名册每页12人，支持姓名、国别、军职与年代筛选。自由世界中，未受伤、未任职的本方后备将领可任命到本方无将领编队，规则层核对归属、伤病与重复任命。成功任命消耗所选编队本阶段的攻击机会。不会为了增加将领数量额外复制部队。

开局名册涉及68名不同人物，可选后备涉及65名，两者去重后114人有已编写的剧本玩法资格；另210人目前仅档案浏览与成长，具体年代部署待考证。324人入库不表示324人都已可在当前战场任命，CSV提供逐人可用状态。

新增295人的能力与战法仍使用未评级的指挥类别基础模板，已经接通成长与战斗加成，但逐人特色技能和长期平衡未完成。

328人均有四个生前阶段，肖像共1,315张，新增1,180张独立Sub2原图。原图、提示词、逐张完整查看记录与SHA256随源码保存，未拼接或加工PNG。早逝者使用生前后期，不虚构暮年。肖像为解释性游戏插画，脸部辨识度、部分轮廓彩边和四阶段一致性尚待改进，未取得独立历史肖似度或正式美术签核。

1860北线两场战役改为清军、英军、法军三方：英法同盟、清军与二者交战，目标按玩家阵营配置；游戏编队数不宣称真实兵力。其他已登记修正及仍待核实项目见docs/46_师旅级将领池与战役名册.md。全部亚洲合格将领、完整参战序列及所有任期尚未穷举；仍有{summary['non_training_sides_without_authored_commander']}个非训练剧本阵营位置没有有据开局将领，包含自由世界中立势力，不用随机人物填充。

每完整全阵营回合推进公历1天。schema2/ruleset11，名册和开局规则已改变；0.2.27及更早进行中战局请用原包继续，新规则需新开局。生涯档案和设置按其独立格式保留。原有地图地理、1,327张素材及3首YuE2纯器乐保留原字节；当前全部PNG为2,507张。

{summary['regression_groups']}组/{summary['regression_checks']}项回归与{summary['native_captures']}张专项原生视口证据随源码交付，包含三种布局的完整名册翻页、肖像加载与真实后备任命。APK核对签名、架构、版本和全部导入素材。截图生成与实际人工查看分别记录；2400×1080是桌面移动布局检查，Motorola X30尚未完成物理验收。

桌面静止战场180帧样本平均{summary['desktop_static_average_fps']:.2f} FPS，帧时p95为{summary['desktop_static_frame_ms_p95']:.2f}ms。窗口焦点与遮挡未记录、缺少同条件旧版基线，不能推断手机表现。完整每日长局平衡、全兵种动画、逐年代军事考证、商业美术和欧陆战争6整体品质仍未完成。

The military pool expands from 29 to 324 people, with four separate political-only figures retained. Of the 324, 303 have a brigade-or-higher, naval or historical equivalent command, including 12 army-or-higher deputies; 20 deputy-division officers and one army political co-commander are identified separately. All 328 people have four living-stage portraits, 1,315 originals in total. Every new original follows the requested Sub2 route with immutable bytes, prompts and individual source inspection. Historical likeness and final art approval are not claimed.

All 61 scenario rosters have independent dated side lists, 280 starting entries in total; free-world scenarios add 89 optional reserve entries. Twelve-card pagination, country/grade/era/search filters and actual appointments to eligible owned formations are implemented. Successful appointment consumes that formation's attack opportunity for the phase. Counts are not capped uniformly. Dated positions and gameplay progression grades are separate. This is not an exhaustive census of every eligible Asian commander, full service tenure or complete order of battle.

Authored starting rosters involve 68 distinct commanders and optional reserves involve 65; their union is 114. The remaining 210 catalogue entries support archive browsing and growth while sourced dated deployment remains pending. Catalogue size is not the number recruitable in current scenarios.

The 295 new military definitions currently use an unrated command-role baseline for abilities and skills; distinctive individual skills and long-term balance remain unfinished.

Windows and signed Android builds, source, documentation and native evidence are included. A full faction rotation advances one Gregorian day. New matches use ruleset 11; ongoing older matches require their original build. Existing map geography and original assets retain their bytes. Physical Motorola X30 testing, full daily balance, complete animation coverage and overall EW6 parity remain pending. See the release manifest for exact current hashes and checks.
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
    print('Packaging source, immutable portraits, sourced roster and native evidence.', flush=True)
    with zipfile.ZipFile(source, 'w', zipfile.ZIP_DEFLATED, compresslevel=1) as archive:
        for path in sorted(public | reports | captures):
            if not path.is_file():
                continue
            require(not any(part in {'.git', '.godot', '.toolchain', 'build', '__pycache__', 'signing'}
                for part in path.relative_to(P).parts), 'Private path in archive')
            archive.write(path, path.relative_to(ROOT).as_posix())
        add_tree(archive, ROOT / 'design', ROOT,
            allowed={'.md', '.json', '.py', '.csv', '.txt', '.png', '.shp', '.shx', '.dbf', '.prj', '.cpg', '.html', '.xml', '.zip', '.tif', '.pdf'})
    print('Verifying archive CRCs and tested binary identity.', flush=True)
    for path in [windows, source]:
        with zipfile.ZipFile(path) as archive:
            require(archive.testzip() is None, 'Corrupt archive: ' + path.name)
    with zipfile.ZipFile(windows) as archive:
        require(hashlib.sha256(archive.read(exe.name)).hexdigest() == sha(exe), 'Portable binary differs')
    require(sha(android) == sha(apk) and source_digest()[0] == summary['runtime_source_sha256'], 'Delivery identity changed')
    manifest = dict(**summary, created_at_utc=datetime.now(timezone.utc).isoformat(),
        release_kind='scoped_sourced_brigade_and_division_commander_pool_beta', regression=regression,
        artifacts=[dict(file=p.name, bytes=p.stat().st_size, sha256=sha(p)) for p in [windows, android, source]],
        reports=[dict(file=p.relative_to(P).as_posix(), sha256=sha(p)) for p in sorted(reports)],
        archive_integrity_verified=True, old_releases_modified=False)
    write(out / 'release_manifest.json', manifest)
    (out / '交付说明.md').write_text(note, encoding='utf-8')
    shutil.copyfile(P / 'docs/46_师旅级将领池与战役名册.md', out / '师旅级将领池与战役名册.md')
    print(json.dumps(dict(passed=True, release=str(out), artifacts=manifest['artifacts']), ensure_ascii=True), flush=True)


if __name__ == '__main__':
    main()
