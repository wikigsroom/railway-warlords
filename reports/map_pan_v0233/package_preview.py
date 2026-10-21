"""Archive the verified map-panning preview without changing full-release gates."""
from pathlib import Path
from datetime import datetime,timezone
import sys,json,hashlib,shutil,zipfile
P=Path(__file__).resolve().parents[2];sys.path.insert(0,str(P/'tools'))
from build_release import source_digest,current_version,android_version_code
R=P/'reports/map_pan_v0233';D=P.parents[1]/'output/releases/railway-warlords-0.2.33'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def write(p,d):Path(p).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def main():
 assert not D.exists() and current_version()=='0.2.33' and android_version_code()==38
 runtime=source_digest()[0];exports=read(P/'reports/export_results.json');binaries={}
 for row in exports:
  path=Path(row['path']);assert row['export_verified'] and row['runtime_source_sha256']==runtime and sha(path)==row['sha256']
  binaries[row['target']]=row
 assert set(binaries)=={'windows','android'}
 components=read(R/'final_components_02/runs.json');assert components['passed'] and len(components['runs'])==16
 checks=sum(o['checks'] for r in components['runs'] for o in r['outputs'])
 for r in components['runs']:
  assert sha(P/'tests'/(r['script']+'.gd'))==r['original_test_sha256']
  assert sha(R/'final_components_02'/(r['script']+'.gd'))==r['driver_sha256']
  for o in r['outputs']:
   proof=read(P/o['path']);assert not proof.get('failed',0) and not proof.get('failures') and len(proof['checks'])==o['checks']
 maps_root=P/'reports/screenshots/map_composition_native/v0233/verified_export_01'
 maps=read(maps_root/'validation.json');shipping=read(R/'shipping_01/validation.json')
 assert maps['passed'] and maps['mode']=='verified_export' and len(maps['checks'])==58
 assert shipping['passed'] and shipping['gpu_checks']==48 and shipping['ui_smoke_passed']
 assert maps['runtime_source_sha256']==shipping['runtime_source_sha256']==runtime
 assert shipping['windows_exe_sha256']==binaries['windows']['sha256']
 assert shipping['capture_driver_sha256']==sha(R/'verify_shipping.py') and maps['capture_driver_sha256']==sha(P/'tools/capture_map_composition.py')
 for frame in maps['captures']+shipping['captures']:
  for key,h in [('image' if 'image' in frame else 'path','sha256'),('metadata','metadata_sha256')]:
   path=Path(frame[key]);assert sha(path if path.is_absolute() else P/path)==frame[h]
 pixel=read(R/'renderer_comparison_02/pixel_comparison.json');assert pixel['passed'] and len(pixel['pairs'])==3
 assert read(R/'renderer_comparison_02/source_identity.json')['base_map_view_sha256']==sha(P/'presentation/map_view.gd'), 'The pixel-proven renderer source changed.'
 for pair in pixel['pairs']:
  assert pair['max_channel_delta']==0 and sha(P/pair['baseline'])==sha(P/pair['optimized'])==pair['optimized_sha256']
 pan=read(R/'abba_summary.json');assert pan['passed'] and pan['runtime_source_sha256']==runtime and len(pan['stages'])==4
 review=read(R/'visual_review.json');assert review['runtime_source_sha256']==runtime and len(review['actually_viewed_complete_images'])==10
 for row in review['actually_viewed_complete_images']:assert sha(P/row['path'])==row['sha256']
 scope=read(R/'scope.json');assert scope['passed'] and scope['unchanged_rule_and_geography_files']==158 and scope['asset_manifest_and_provenance_byte_identical']
 assert read(P/'reports/resource_validation.json')['passed'] and read(P/'reports/ground_macro_asset_audit.json')['passed']
 docs=read(P/'reports/repository_documentation_validation.json');assert docs['passed'] and docs['runtime_source_sha256']==runtime and not docs['full_native_release_gates_checked']
 apk=read(P/'reports/apk_content_validation.json');assert apk['passed'] and apk['artifact_sha256']==binaries['android']['sha256'] and not apk['private_files_detected']
 assert len(apk['raster_import_files_verified'])==2509 and all(r['current_import_bytes_match'] for r in apk['raster_import_files_verified'])
 assert len(apk['instrumental_music_imports_verified'])==3 and all(r['current_import_bytes_match'] for r in apk['instrumental_music_imports_verified'])
 signature=(P/'reports/apk_signature.log').read_text(encoding='utf-8',errors='replace');assert all('Verified using v%d scheme (APK Signature Scheme v%d): true'%(n,n) in signature for n in [2,3])
 badging=(P/'reports/apk_badging.log').read_text(encoding='utf-8',errors='replace');assert "versionName='0.2.33'" in badging and "versionCode='38'" in badging
 assert "'arm64-v8a'" in badging and "'armeabi-v7a'" in badging and 'uses-permission:' not in (P/'reports/apk_permissions.log').read_text(encoding='utf-8',errors='replace')
 D.mkdir();evidence=D/'evidence';rows=[]
 files=set(f for root in [R,maps_root] for f in root.rglob('*') if f.is_file() and f.suffix in ['.json','.png','.gd','.py','.md'] and '__pycache__' not in f.parts)
 files.update(P/x for x in ['README.md','README.en.md','docs/51_地图拖动预取与源线段缓存.md','docs/00_程序文档索引.md','docs/05_测试与验收.md','docs/06_双端构建与发布.md','docs/23_当前完成度评估.md','docs/MEDIA.md','docs/media/manifest.json','reports/export_results.json','reports/resource_validation.json','reports/ground_macro_asset_audit.json','reports/repository_documentation_validation.json','reports/apk_content_validation.json','reports/apk_signature.log','reports/apk_badging.log','reports/apk_permissions.log','reports/android_devices.log','reports/quality_goal_turn_v0233.json'])
 files.update((P/'docs/media').glob('*v0233.*'))
 for source in sorted(files):
  target=evidence/source.relative_to(P);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target);h=sha(source);assert sha(target)==h
  rows.append(dict(file=source.relative_to(P).as_posix(),bytes=source.stat().st_size,sha256=h))
 for target in ['windows','android']:
  source=Path(binaries[target]['path']);shutil.copyfile(source,D/source.name);assert sha(D/source.name)==binaries[target]['sha256']
 receipt=dict(version='0.2.33',android_version_code=38,stage='source_preserving_map_panning_playable_preview',created_at_utc=datetime.now(timezone.utc).isoformat(),runtime_source_sha256=runtime,component_checks=checks,current_targeted_checks=checks+106,pixel_pairs_identical=3,performance_stages=pan['stages'],new_raster_originals=0,registered_rasters=2509,physical_android_device_tested=False,ew6_parity_claimed=False,whole_goal_achieved=False,full_thirty_group_regression_repeated=False,formal_art_approval=False,old_release_archives_modified=False,manual_image_compositing=False,evidence=rows)
 write(D/'scope_receipt.json',receipt)
 (D/'START_HERE.md').write_text('# 铁道烽烟：军阀时代 0.2.33 / Railway Warlords\n\nWindows：解压后运行RailwayWarlords.exe。Android：安装签名APK/code38。\nWindows: extract and run RailwayWarlords.exe. Android: install the signed APK/code38.\n\n本版改善地图拖动的素材读取与重绘；沿用原图和地理，不代表整体欧陆战争6品质已完成。\nThis preview reduces panning stalls while preserving source artwork and geography. Overall EW6 quality remains unfinished.\n\n验收范围、开发性能复测和剩余缺口见scope_receipt.json及evidence。无物理X30验收；完整源码由Git仓库交付。\nSee scope_receipt.json and evidence for checks, development benchmarks and limits. No physical X30 acceptance; full source is delivered through Git.\n',encoding='utf-8')
 for name,files,root in [('RailwayWarlords-Windows-0.2.33.zip',[D/'RailwayWarlords.exe',D/'START_HERE.md',D/'scope_receipt.json'],D),('MapPanningEvidence-0.2.33.zip',sorted(f for f in evidence.rglob('*') if f.is_file()),evidence)]:
  with zipfile.ZipFile(D/name,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
   for f in files:z.write(f,f.relative_to(root).as_posix())
  with zipfile.ZipFile(D/name) as z:assert z.testzip() is None
  print('ARCHIVED '+name,flush=True)
 manifest=dict(version='0.2.33',runtime_source_sha256=runtime,archive_directory=str(D),whole_goal_achieved=False,physical_android_device_tested=False,ew6_parity_claimed=False,artifacts=[dict(file=f.name,bytes=f.stat().st_size,sha256=sha(f)) for f in sorted(D.iterdir()) if f.is_file()])
 write(D/'preview_manifest.json',manifest);write(P/'reports/map_pan_preview_v0233.json',manifest)
 print('MAP_PANNING_PREVIEW_ARCHIVED '+str(D),flush=True)
if __name__=='__main__':main()
