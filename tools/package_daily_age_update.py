"""Deliver the daily-calendar/four-stage scope with current binary and media identity."""
from datetime import datetime,timezone
import hashlib,json,shutil,subprocess,zipfile
from pathlib import Path
from build_release import P,ROOT,current_version,source_digest,android_version_code
from package_delivery import read,sha,require,add_tree
from run_validation import CHECKS
from regression_dependencies import identity

def write(path,data):path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def validate():
 version=current_version();runtime=source_digest()[0]
 exports=read(P/'reports/export_results.json');exe=P/'build/windows/RailwayWarlords.exe';apk=P/'build/android/RailwayWarlords.apk'
 for target,path in [('windows',exe),('android',apk)]:
  row=next(r for r in exports if r['target']==target)
  require(row['export_verified'] and row['runtime_source_sha256']==runtime and row['sha256']==sha(path),'Current verified export required: '+target)
 deps=read(P/'reports/regression_dependency_evidence.json');require(deps['passed'] and deps['game_version']==version and deps['runtime_source_sha256']==runtime and len(deps['checks'])==29,'Current complete regression seal required')
 reports=set();regression=[]
 for row in deps['checks']:
  require(row['passed'] and identity(row['check'])[0]==row['dependency_sha256_at_seal'],'Regression dependency changed: '+row['check'])
  report=P/'reports'/row['report'];log=P/'reports'/row['log']
  require(sha(report)==row['report_sha256'] and sha(log)==row['log_sha256'],'Regression evidence changed')
  value=read(report);reports.update([report,log]);regression.append(dict(name=row['check'],checks=len(value['checks']),report=report.relative_to(P).as_posix(),sha256=sha(report)))
 require(read(P/'reports/calendar_tests.json')['passed'] and len(read(P/'reports/calendar_tests.json')['checks'])==83,'Calendar regression incomplete')
 portraits=read(P/'presentation/data/general_portraits.json');assets=read(P/'assets/manifest.json')['assets'];portrait_assets=[a for a in assets if a['category']=='portrait']
 require(portraits['production_complete'] and not portraits['missing_age_stages'] and len(portraits['generals'])==33 and len(portrait_assets)==135 and len(assets)==1299,'Four-stage production incomplete')
 require(len({a['source_sha256'] for a in portrait_assets})==135,'Independent portrait originals required')
 for gid,person in portraits['generals'].items():
  require({v['age_stage'] for v in person['variants']}=={'young','prime','middle','late'},'Missing stage: '+gid)
  require(all(person['birth_year']<=s['reference_year']<=person['death_year'] for s in person['stages']),'Posthumous stage: '+gid)
  for variant in person['variants']:
   asset=next(a for a in portrait_assets if a['id']==variant['asset_id'])
   require(sha(P/asset['engine_path'].removeprefix('res://'))==asset['source_sha256']==variant['asset_sha256'],'Portrait bytes changed')
 first=read(P/'reports/general_portrait_first_source_review.json');new=read(P/'reports/general_portrait_source_review.json')
 require(len(first['originals'])==26 and len(new['originals'])==97 and len(new['rejected_originals'])==20,'Individual source reviews incomplete')
 require(all(r['accepted'] and r['viewed_complete_original'] for r in first['originals']+new['originals']),'Unreviewed original included')
 captures=set();native_groups=[]
 for name,expected in [('general_portrait_native_evidence.json',3),('terrain_surface_native_evidence.json',6),('control_land_native_evidence.json',2),('map_symbol_native_evidence.json',2)]:
  path=P/'reports'/name;proof=read(path)
  require(proof['passed'] and proof['version']==version and proof['runtime_source_sha256']==runtime and proof['windows_exe_sha256']==sha(exe) and len(proof['groups'])==expected,'Current native proof required: '+name)
  reports.add(path)
  for group in proof['groups']:
   if group.get('report'):
    report=P/group['report'];require(sha(report)==group['report_sha256'],'Native report changed');reports.add(report)
   if group.get('log'):reports.add(P/group['log'])
   for row in group['captures']:
    image=P/row['file'];meta=P/row['metadata'];require(sha(image)==row['sha256'] and sha(meta)==row['metadata_sha256'],'Untouched native capture required')
    captures.update([image,meta])
  native_groups.append(dict(name=name,captures=sum(len(g['captures']) for g in proof['groups']),checks=sum(g.get('checks',0) for g in proof['groups'])))
 apk_report=read(P/'reports/apk_content_validation.json');require(apk_report['passed'] and apk_report['artifact_sha256']==sha(apk) and not apk_report['private_files_detected'] and len(apk_report['raster_import_files_verified'])==1299 and all(r['current_import_bytes_match'] for r in apk_report['raster_import_files_verified']),'Current APK payload proof required')
 require(len(apk_report['instrumental_music_imports_verified'])==3 and all(r['current_import_bytes_match'] for r in apk_report['instrumental_music_imports_verified']),'APK score payload required')
 signed=(P/'reports/apk_signature.log').read_text(encoding='utf-8');require('Verified using v2 scheme (APK Signature Scheme v2): true' in signed and 'Verified using v3 scheme (APK Signature Scheme v3): true' in signed,'APK signature required')
 music=read(P/'reports/music_native_tests.json');require(music['passed'] and music['runtime_source_sha256']==runtime and music['windows_exe_sha256']==sha(exe) and len(music['checks'])==18,'Current native music proof required')
 resources=read(P/'reports/resource_validation.json');require(resources['passed'] and resources['raster_count']==1299 and resources['scenarios']==61,'Source integrity required')
 repo=read(P/'reports/repository_validation.json');require(repo['passed'] and repo['version']==version and repo['runtime_source_sha256']==runtime and repo['verified_images_and_prompts']==1299,'Current repository audit required')
 text_audit=read(P/'reports/daily_age_text_audit.json');require(text_audit['passed'] and not text_audit['legacy_display_name_plaintext_files'],'Public display-name audit required')
 visual=read(P/'reports/general_portrait_native_review.json');require(visual['version']==version and visual['runtime_source_sha256']==runtime and visual['windows_exe_sha256']==sha(exe) and len(visual['viewed_complete_captures'])==8,'Current scoped visual inspection required')
 for row in visual['viewed_complete_captures']:require(sha(P/row['file'])==row['sha256'] and row['viewed_complete_original_capture'],'Inspected native capture changed')
 reports.update(P/'reports'/name for name in ['daily_age_text_audit.json','general_portrait_native_review.json'])
 reports.update(P/'reports'/name for name in ['regression_dependency_evidence.json','resource_validation.json','repository_validation.json','export_results.json','sample_state_v2.json','apk_content_validation.json','apk_signature.log','apk_badging.log','apk_permissions.log','android_devices.log','general_portrait_first_source_review.json','general_portrait_source_review.json','music_native_tests.json'])
 summary=dict(passed=True,version=version,runtime_source_sha256=runtime,content_hash=read(P/'reports/sample_state_v2.json')['content_hash'],ruleset=10,days_per_complete_round=1,scenarios=61,people=33,military_generals=29,political_only_people=4,living_age_stages_per_person=4,portrait_originals=135,new_portrait_originals=123,total_rasters=1299,regression_groups=29,regression_checks=sum(r['checks'] for r in regression),native_groups=native_groups,native_captures=len(captures)//2,native_music_checks=18,apk_version_code=android_version_code(),apk_data_and_notice_files=len(apk_report['files']),physical_android_device_tested=False,formal_art_approval=False,historical_likeness_approval=False,new_1947_scenario=False,full_daily_balance_acceptance=False,full_ai_endurance_rerun=False,ew6_parity_claimed=False,source_pngs_modified=False,manual_compositing=False)
 write(P/'reports/daily_age_release_validation.json',summary);reports.add(P/'reports/daily_age_release_validation.json')
 return summary,reports,captures,regression

def main():
 summary,reports,captures,regression=validate();version=summary['version'];out=ROOT/'output/releases'/('railway-warlords-'+version);out.mkdir(parents=True,exist_ok=True)
 exe=P/'build/windows/RailwayWarlords.exe';apk=P/'build/android/RailwayWarlords.apk';portable=out/'Windows便携版';portable.mkdir(exist_ok=True);shutil.copyfile(exe,portable/exe.name)
 note=f'''# 铁道烽烟 {version} · 每日历法与四阶段人物肖像

Windows：解压Windows ZIP，运行RailwayWarlords.exe。Android：安装同版本APK，沿用既有签名。Godot：用4.7.2打开源码内game/railway_warlords/project.godot。

- 全部61个剧本每完整回合推进公历1天，各阵营阶段不单独跳日；带日期事件按日期与条件触发。
- 33位人物（29位将领及4位仅作政治背景的角色）均有四张不同生前阶段原图；早逝者不虚构中老年。共135张肖像，本次新增123张，均通过指定Sub2路线直接生成。
- 对局自动按日期选图，指挥部及人物页可切换阶段。洪秀全已补全；游戏显示名使用李德胜，1917年选青年，1947年选中年。
- 1947与更晚图片属于素材准备，当前可玩时间锚点仍止于1940，没有新增1947战役。
- ruleset 9旧战局请新开游戏，不能按新每日规则读入。原有个人生涯及设置按自身格式保留。

本轮29组/{summary['regression_checks']}项回归通过；将领与政要四阶段人物页覆盖三种桌面布局，检查与画面数量见交付证据，另复验地图、UI、海岸、图符与配乐。完整证据和文件SHA256见release_manifest.json。

APK已核对签名、ARM64/ARMv7、版本与全部1299张导入纹理字节。Motorola X30没有连接，本轮未完成物理设备验收；桌面手机比例检查不能替代触摸、GPU、发热与续航实测。

每日制长局平衡、完整AI长局与独立历史肖似度、美术商业品质尚待继续验收。生日有分歧或只核实到年的情况明确标注；洪秀全为文献参照绘制，不称为已认证生前肖像。未宣称达到欧陆战争6商业完成度。

Daily calendar and four living age stages are implemented. Every complete faction rotation advances one Gregorian day. All 33 people have four independent living-stage originals; 135 portraits include 3 retained extra dates. Four political-only people are not added to the military roster. Post-1940 art is preparation, not a new1947 campaign. Old ruleset9 matches require a new match under ruleset10. Windows and signed Android builds are delivered; no physical Motorola X30 acceptance or complete daily-balance certification is claimed.
'''
 (portable/'README.md').write_text(note,encoding='utf-8');legal=portable/'licenses';legal.mkdir(exist_ok=True)
 for path in (P/'assets/legal').glob('*.txt'):shutil.copyfile(path,legal/path.name)
 windows=out/f'RailwayWarlords-Windows-{version}.zip'
 with zipfile.ZipFile(windows,'w',zipfile.ZIP_DEFLATED,compresslevel=1) as archive:
  for path in sorted(portable.rglob('*')):
   if path.is_file():archive.write(path,path.relative_to(portable).as_posix())
 android=out/f'RailwayWarlords-{version}.apk';shutil.copyfile(apk,android)
 source=out/f'RailwayWarlords-Godot-Source-{version}.zip'
 raw=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','-z'],cwd=P);public={P/n.decode('utf-8') for n in raw.split(b'\0') if n}
 print('Packaging Godot source, immutable art, documentation and native proof.',flush=True)
 with zipfile.ZipFile(source,'w',zipfile.ZIP_DEFLATED,compresslevel=1) as archive:
  for path in sorted(public|reports|captures):
   if not path.is_file():continue
   require(not any(part in {'.git','.godot','.toolchain','build','__pycache__','signing'} for part in path.relative_to(P).parts),'Private path in archive')
   archive.write(path,path.relative_to(ROOT).as_posix())
  add_tree(archive,ROOT/'design',ROOT,allowed={'.md','.json','.py','.csv','.txt','.png','.shp','.shx','.dbf','.prj','.cpg','.html','.xml','.zip','.tif','.pdf'})
 print('Verifying both archives and tested binary identity.',flush=True)
 for path in [windows,source]:
  with zipfile.ZipFile(path) as archive:require(archive.testzip() is None,'Corrupt archive: '+path.name)
 with zipfile.ZipFile(windows) as archive:require(hashlib.sha256(archive.read(exe.name)).hexdigest()==sha(exe),'Portable binary differs')
 require(sha(android)==sha(apk) and source_digest()[0]==summary['runtime_source_sha256'],'Delivery identity changed')
 manifest=dict(**summary,created_at_utc=datetime.now(timezone.utc).isoformat(),release_kind='scoped_daily_calendar_and_four_living_portrait_stages_beta',regression=regression,artifacts=[dict(file=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in [windows,android,source]],reports=[dict(file=p.relative_to(P).as_posix(),sha256=sha(p)) for p in sorted(reports)],archive_integrity_verified=True,old_releases_modified=False)
 write(out/'release_manifest.json',manifest);(out/'交付说明.md').write_text(note,encoding='utf-8');shutil.copyfile(P/'docs/40_每日历法与四阶段人物肖像.md',out/'每日历法与四阶段人物肖像.md')
 print(json.dumps(dict(passed=True,release=str(out),artifacts=manifest['artifacts']),ensure_ascii=True),flush=True)

if __name__=='__main__':main()
