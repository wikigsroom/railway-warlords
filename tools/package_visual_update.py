"""Package a scoped visual-fix beta with current evidence, without relaxing full-release gates.

The original package_delivery.py still requires full endurance/capacity evidence.
This entry point requires current native render capacity while explicitly
recording that the full AI endurance suite has not been rerun for this patch.
"""
from pathlib import Path
from datetime import datetime, timezone
import json
import shutil
import zipfile
from build_release import P, ROOT, current_version, source_digest
from run_validation import CHECKS
from regression_dependencies import modified
from package_delivery import read, sha, require, add_tree
from map_bank_inventory import ADDITIONAL_COUNT, MAP_COUNT, CATALOGS


def main():
    version=current_version(); tag='v'+version.replace('.','')
    runtime,changed=source_digest()
    fingerprint=read(P/'reports/sample_state_v2.json')['content_hash']
    out=ROOT/'output/releases'/('railway-warlords-'+version)
    out.mkdir(parents=True,exist_ok=True)
    reports=set(); regression=[]
    for check in CHECKS:
        name='rule_tests.json' if check=='run_tests' else check.removesuffix('_test')+'_tests.json'
        path=P/'reports'/name; log=P/'reports'/(check+'_'+tag+'.log'); value=read(path)
        require(not value.get('failed',0) and not value.get('failures',[]), 'Failing regression: '+check)
        require(min(path.stat().st_mtime,log.stat().st_mtime)>=modified(check), 'Stale regression: '+check)
        require(value.get('content_hash',fingerprint)==fingerprint, 'Wrong regression content: '+check)
        require(value.get('game_version',value.get('build_version',version))==version, 'Wrong regression version: '+check)
        diagnostic=log.read_text(encoding='utf-8',errors='replace')
        require('SCRIPT ERROR:' not in diagnostic and '\nERROR:' not in diagnostic, 'Native script errors: '+check)
        regression.append(dict(group=check,passed=True,report=name,sha256=sha(path)))
        reports.update([path,log])
    sealed=read(P/'reports/regression_dependency_evidence.json')
    require(sealed['passed'] and sealed['runtime_source_sha256']==runtime,'Current dependency seal is required')
    required=['resource_validation.json','atlas_v2_asset_audit.json','native_visual_evidence.json',
        'directional_native_tests.json','territory_visual_tests.json','visual_playtest.json',
        'support_playtest.json','hydrography_revision.json','terrain_direction_refinement.json',
        'terrain_visual_resolver_tests.json','unit_layer_pixel_validation.json','apk_content_validation.json',
        'unit_action_generation.json','unit_action_native_tests.json','facing_memory_tests.json','hud_native_tests.json',
        'relief_material_generation.json','map_bank_installation.json','map_bank_asset_audit.json',
        'map_bank_similarity_review.json','map_bank_visual_review.json','map_bank_native_evidence.json',
        'surface_geography_compilation.json','surface_geography_audit.json',
        'asia_relief_dem_revision.json','asia_relief_rebuild_verification.json','hydrography_fine_compilation.json']
    required.extend(filename for _,filename,_ in CATALOGS)
    for name in required:
        path=P/'reports'/name; value=read(path)
        require(value.get('passed') is True, 'Required current evidence failed: '+name)
        require(value.get('content_hash',fingerprint)==fingerprint,'Evidence content mismatch: '+name)
        reports.add(path)
    for name,driver in [('unit_action_native_tests.json','unit_action_native_test.gd'),
                        ('directional_native_tests.json','directional_native_test.gd'),
                        ('territory_visual_tests.json','territory_visual_test.gd')]:
        path=P/'reports'/name;value=read(path)
        require(value['build_version']==version and path.stat().st_mtime>=max(changed,(P/'tests'/driver).stat().st_mtime),
                'Current native driver evidence required: '+name)
    proof=read(P/'reports/native_visual_evidence.json')
    require(proof['runtime_source_sha256']==runtime,'Native visual source identity mismatch')
    require(proof['video']['sha256']==sha(P/proof['video']['file']),'Native recording bytes changed')
    require(read(P/'reports/terrain_direction_refinement.json')['requested']==14,'Four forests and ten corrected north views required')
    require(read(P/'reports/directional_native_tests.json')['unmodified_published_deployment'],'Legal published direction cases required')
    assets=read(P/'assets/manifest.json')['assets']
    installation=read(P/'reports/map_bank_installation.json')
    require(installation['installed']==ADDITIONAL_COUNT and installation['total_map_assets']==MAP_COUNT,
            'All 796 additional independent map sources must be installed')
    bank_proof=read(P/'reports/map_bank_native_evidence.json')
    require(bank_proof['runtime_source_sha256']==runtime and bank_proof['version']==version,
            'Current exported map-bank viewport proof required')
    capacity=[]
    for profile in ['windows','x30']:
        path=P/'reports'/f'capacity_{profile}_{tag}.json';value=read(path)
        require(value['render_target_passed'] and value['game_version']==version and
                value['runtime_source_sha256']==runtime and value['windows_exe_sha256']==sha(P/'build/windows/RailwayWarlords.exe'),
                'Current native capacity profile required: '+profile)
        require(path.stat().st_mtime>=changed,'Stale native capacity profile: '+profile)
        capacity.append(dict(profile=profile,report=path.relative_to(P).as_posix(),sha256=sha(path)))
        reports.add(path)
        for suffix in ['.log','_stdout.log']:
            candidate=path.with_name(path.stem+suffix)
            if candidate.exists():reports.add(candidate)
    provenance=[]
    for item in assets:
        require(sha(ROOT/item['source_file'])==sha(P/item['engine_path'].removeprefix('res://'))==item['source_sha256'],'Raster provenance mismatch: '+item['id'])
        prompt_sha=sha(ROOT/item['prompt_file'])
        if item.get('prompt_sha256'):require(prompt_sha==item['prompt_sha256'],'Prompt provenance mismatch: '+item['id'])
        provenance.append(dict(id=item['id'],source_file=item['source_file'],source_sha256=item['source_sha256'],prompt_file=item['prompt_file'],prompt_sha256_at_package=prompt_sha,prompt_sha_registered_previously=bool(item.get('prompt_sha256'))))
    exports=read(P/'reports/export_results.json')
    require({row['target'] for row in exports}=={'windows','android'},'Both exports required')
    for row in exports:
        require(row['export_verified'] and row['runtime_source_sha256']==runtime and row['sha256']==sha(Path(row['path'])),'Export identity mismatch: '+row['target'])
    apk=read(P/'reports/apk_content_validation.json')
    require(apk['artifact_sha256']==sha(P/'build/android/RailwayWarlords.apk'),'APK payload audit is stale')
    require(not apk['private_files_detected'] and len(apk['raster_import_files_verified'])==len(assets),'APK private-file / raster count mismatch')
    captures=set()
    source_review=read(P/'reports/map_bank_visual_review.json')
    require(source_review['version']==version and source_review['all_generated_sources_viewed'] and
            source_review['viewed_independent_sources']==ADDITIONAL_COUNT,
            'All independent map sources require actual whole-source visual inspection')
    for row in source_review['viewed_pages']:
        path=P/row['file']
        require(sha(path)==row['sha256'] and sha(path.with_suffix('.json'))==row['metadata_sha256'],
                'Inspected whole-source gallery changed: '+row['stem'])
        captures.update([path,path.with_suffix('.json')])
    for row in bank_proof['captures']:
        path=P/row['file'];require(sha(path)==row['sha256'],'Map-bank native image changed')
        captures.update([path,path.with_suffix('.json')]);reports.add(P/row['log'])
    for row in proof['captures']+proof['fivefold_map_captures']+proof['territory_color_evidence']['captures']:
        path=P/row['file'];require(sha(path)==row['sha256'],'Native image changed: '+row['file']);captures.add(path)
    for name in ['asia_forest_refined_'+tag,'asia_forest_x30_'+tag,'terrain_mountain_'+tag,'map_final_windows','map_x30_layout','map_large_text']:
        png=P/'reports/screenshots'/(name+'.png');meta=read(png.with_suffix('.json'))
        require(meta['build_version']==version and meta['content_hash']==fingerprint and meta['raw_godot_capture'],'Current exported capture required: '+name)
        captures.update([png,png.with_suffix('.json')])
    for path in (P/'reports/screenshots/directions').glob('*.png'):captures.add(path)
    require(len(list((P/'reports/screenshots/directions').glob('*.png')))==8,'Four moving/idle raw capture pairs required')
    for folder in ['hud_native','actions']:
        captures.update((P/'reports/screenshots'/folder).glob('*.png'))
    hud=read(P/'reports/hud_native_tests.json')
    require(hud['runtime_source_sha256']==runtime and hud['build_version']==version,'Current HUD evidence required')
    for row in hud['cases']:reports.add(P/row['report'])
    layers=read(P/'reports/unit_layer_native.json')
    for row in layers['cases']:
        for key in ['cached','direct']:captures.add(P/row[key].removeprefix('res://'))
    for path in list(captures):
        if path.with_suffix('.json').exists():captures.add(path.with_suffix('.json'))
    reports.update(P/'reports'/name for name in ['regression_dependency_evidence.json','visual_update_verification_summary.json','sample_state_v2.json','export_results.json','unit_layer_native.json','art_review.json','import_budgets.json','apk_signature.log','apk_badging.log','apk_permissions.log','android_devices.log','desktop_benchmark.json'])
    diagnostics=read(P/'reports/developer_tools_smoke.json')
    require(diagnostics['passed'], 'Current developer diagnostics must pass')
    reports.add(P/'reports/developer_tools_smoke.json')
    reports.update(P/name for name in diagnostics['source_reports'])
    for name in ['unit_action_native_test_'+tag+'.log','directional_native_'+tag+'.log','territory_native_'+tag+'.log']:
        path=P/'reports'/name
        if path.exists():reports.add(path)
    # Copy only public artifacts; this path never touches earlier releases.
    portable=out/'Windows便携版';portable.mkdir(exist_ok=True)
    exe=portable/'RailwayWarlords.exe';shutil.copyfile(P/'build/windows/RailwayWarlords.exe',exe)
    readme=f'''# 铁道烽烟 {version}\n\n运行 RailwayWarlords.exe，无需安装 Godot。\n本版为地图材质与素材扩充测试版：870 张地图素材，草土、沙地、砾地与湿土按来源区域选材，细支流有独立精度记录。\n本轮桌面双视口满载性能已复验；X30 真机与完整 AI 长局未完成本轮复验。\n操作：点选部队、选目标、确认移动/攻击；拖动平移、滚轮缩放；空格跳过演出。\n'''
    (portable/'README.md').write_text(readme,encoding='utf-8')
    legal_folder=portable/'licenses';legal_folder.mkdir(exist_ok=True)
    for path in (P/'assets/legal').glob('*.txt'):shutil.copyfile(path,legal_folder/path.name)
    windows=out/f'RailwayWarlords-Windows-{version}.zip'
    with zipfile.ZipFile(windows,'w',zipfile.ZIP_DEFLATED,compresslevel=1) as z:
        for path in portable.rglob('*'):
            if path.is_file():z.write(path,path.relative_to(portable).as_posix())
    android=out/f'RailwayWarlords-{version}.apk';shutil.copyfile(P/'build/android/RailwayWarlords.apk',android)
    movie=out/'实机战斗演示.mp4';shutil.copyfile(P/proof['video']['file'],movie)
    for document in sorted((P/'docs').glob('*.md')):
        text=document.read_text(encoding='utf-8')
        (out/document.name).write_text(text.replace('../reports/screenshots/','原生截图/'),encoding='utf-8')
    image_folder=out/'原生截图';image_folder.mkdir(exist_ok=True)
    for path in captures:
        rel=path.relative_to(P/'reports/screenshots');target=image_folder/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target)
    raw=set()
    for item in assets:
        for row in [item]+item.get('revision_history',[]):
            for key in ['source_file','prompt_file']:
                if row.get(key):raw.add(ROOT/row[key])
    # Preserve all accepted and superseded generation attempts for this pass.
    for path in (ROOT/'output/imagegen/warlord/ew6_v025/refinement_r002').rglob('*'):
        if path.is_file() and path.suffix.lower() in ['.png','.txt','.json']:raw.add(path)
    for path in (ROOT/'output/imagegen/warlord/ew6_v025/full_gameplay').rglob('*'):
        if path.is_file() and path.suffix.lower() in ['.png','.txt','.json']:raw.add(path)
    for name in ['output/imagegen/15_warlord_railways_full_gameplay.png',
                 'output/imagegen/prompts/15_warlord_railways_full_gameplay.txt']:
        if (ROOT/name).is_file():raw.add(ROOT/name)
    source=out/f'RailwayWarlords-Godot-{version}.zip'
    with zipfile.ZipFile(source,'w',zipfile.ZIP_DEFLATED,compresslevel=1) as z:
        for folder in ['app','content','domain','ai','presentation','persistence','audio','assets','schemas','tests','tools','docs']:
            add_tree(z,P/folder,ROOT)
        for name in ['project.godot','export_presets.cfg','README.md','README.en.md','SOUND_DESIGN.md','LICENSES.txt','LICENSE-NOTICE.md','AGENTS.md','.gitignore','.gitattributes','.editorconfig']:
            path=P/name
            if path.exists():z.write(path,path.relative_to(ROOT).as_posix())
        for path in sorted(reports|captures|raw):z.write(path,path.relative_to(ROOT).as_posix())
        z.writestr('game/railway_warlords/reports/.gdignore','')
        add_tree(z,ROOT/'design',ROOT,allowed={'.md','.json','.py','.csv','.txt','.png','.shp','.shx','.dbf','.prj','.cpg','.html','.xml','.zip','.tif','.pdf'})
        add_tree(z,ROOT/'output/research/european_war_6',ROOT,allowed={'.json','.html','.jpg','.png','.pdf'})
        for name in ['README.md','AGENTS.md']:
            if (ROOT/name).exists():z.write(ROOT/name,name)
    # Read every archive entry and verify each copied executable/package/source raster.
    for path in [windows,source]:
        with zipfile.ZipFile(path) as z:require(z.testzip() is None,'Corrupt archive: '+path.name)
    with zipfile.ZipFile(windows) as z:
        import hashlib
        require(hashlib.sha256(z.read('RailwayWarlords.exe')).hexdigest()==sha(exe),'Windows archive differs from tested EXE')
    require(sha(android)==sha(P/'build/android/RailwayWarlords.apk'),'Copied APK differs from tested APK')
    require(source_digest()[0]==runtime,'Source changed while packaging')
    manifest=dict(version=version,created_at_utc=datetime.now(timezone.utc).isoformat(),
        release_kind='scoped_map_material_bank_beta',runtime_source_sha256=runtime,content_hash=fingerprint,
        current_regression_groups=regression,raster_count=len(assets),refined_source_items=14,
        current_raster_provenance=provenance,
        action_pose_source_items=16,persistent_facing_ledger=True,native_hud_viewports=3,
        baseline_map_sources=74,additional_independent_map_sources=ADDITIONAL_COUNT,total_map_sources=MAP_COUNT,
        current_native_capacity_rerun=True,current_native_capacity_profiles=capacity,
        source_pngs_modified=False,manual_image_compositing=False,formal_art_release_approval=False,
        full_endurance_and_capacity_rerun=False,physical_android_device_tested=False,ew6_visual_parity_claimed=False,
        current_reports=[dict(file=p.relative_to(P).as_posix(),sha256=sha(p)) for p in sorted(reports)],
        native_captures=[dict(file=p.relative_to(P).as_posix(),sha256=sha(p)) for p in sorted(captures)],
        artifacts=[dict(file=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in [windows,android,source,movie]],
        archive_integrity_verified=True,older_releases_modified=False)
    (out/'release_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    instructions=f'''# 铁道烽烟 {version} 交付\n\n本轮交付为地图材质与素材扩充测试版。74 张地图素材基线上增加 796 张独立 Sub2 原图，合计 870 张；全部运行时栅格为 {len(assets)} 张。\n\n- Windows：解压 RailwayWarlords-Windows-{version}.zip 后运行 EXE；或直接运行 Windows便携版中的 EXE。\n- Android：安装 RailwayWarlords-{version}.apk，使用同一发布签名；X30 尚未实机验证。\n- Godot：解压工程 ZIP，打开 game/railway_warlords/project.godot。源图、提示词、地理来源和当前证据随包保留；不包含签名凭据。\n\n本轮 {len(CHECKS)} 组回归、地图原生视口、四向合法行军、领土像素、原生战斗回放和双端载荷核验的实际报告见 release_manifest.json。1920×1080 与 2400×1080 桌面满载性能本轮重跑，完整 AI 长局与物理 X30 尚未复验。\n\n亚洲大陆山地矩形旧分类已改用真实 DEM，内容指纹随之变化；旧内容指纹存档可能需要新开对局。生态区底材和细支流是已注明精度的物理地理参考，不是 1840—1940 每一年的土地利用与逐条历史河道测绘。详见 29_地表材质与细水系.md。\n\n本轮改进不代表已经达到 EW6 完整商业美术水准。\n'''
    (out/'交付说明.md').write_text(instructions,encoding='utf-8')
    print(json.dumps(dict(passed=True,release=str(out),artifacts=manifest['artifacts']),ensure_ascii=True),flush=True)


if __name__=='__main__':main()
