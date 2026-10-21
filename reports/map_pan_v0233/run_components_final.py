"""Run source-preserving regression drivers sequentially, retaining old reports."""
from pathlib import Path
import subprocess,sys,json,re,hashlib
P=Path(__file__).resolve().parents[2]
engine=P.parents[1]/'.toolchain/godot/Godot_v4.7.2-stable_win64_console.exe'
root=P/'reports/map_pan_v0233/final_components_02';assert not root.exists();root.mkdir()
names=['map_ground_washes_test','relief_grounding_test','map_material_continuity_test','ground_coverage_test','relief_surface_test','terrain_surfaces_test','surface_geography_test','river_surface_test','run_tests','source_line_index_test','map_prefetch_test','fine_surface_cache_test','map_detail_boundary_motion_test','facing_memory_test','historical_places_test','input_test']
runs=[]
for name in names:
 original=P/'tests'/(name+'.gd');source=original.read_text(encoding='utf-8')
 paths=re.findall(r'res://reports/[^"\s]+\.json',source);assert paths,name
 for old in set(paths):source=source.replace(old,'res://reports/map_pan_v0233/final_components_02/'+Path(old).name)
 driver=root/(name+'.gd');driver.write_text(source,encoding='utf-8',newline='\n')
 with (root/(name+'.log')).open('w',encoding='utf-8') as log:
  result=subprocess.run([str(engine),'--headless','--path',str(P),'--script',driver.relative_to(P).as_posix()],cwd=P,stdout=log,stderr=subprocess.STDOUT,timeout=600)
 diagnostic=(root/(name+'.log')).read_text(encoding='utf-8',errors='replace');assert result.returncode==0 and 'SCRIPT ERROR:' not in diagnostic and '\nERROR:' not in diagnostic,name
 outputs=[]
 for old in set(paths):
  target=root/Path(old).name
  if target.exists():
   report=json.loads(target.read_text(encoding='utf-8'));assert not report.get('failed',0) and not report.get('failures'),name
   outputs.append(dict(path=target.relative_to(P).as_posix(),checks=len(report.get('checks',[]))))
 assert outputs,name
 row=dict(script=name,original_test_sha256=hashlib.sha256(original.read_bytes()).hexdigest(),driver_sha256=hashlib.sha256(driver.read_bytes()).hexdigest(),only_driver_change='Report destinations; original tests otherwise unchanged after line-ending normalization',outputs=outputs)
 runs.append(row);print('COMPONENT '+name+' '+str(outputs),flush=True)
(root/'runs.json').write_text(json.dumps(dict(passed=True,version='0.2.33',runs=runs,physical_android_device_tested=False),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('ALL_SCOPED_COMPONENTS_PASS',flush=True)
