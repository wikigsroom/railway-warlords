"""Scoped shipping EXE checks; source identity is rechecked by map capture and packaging."""
import json,sys,subprocess,hashlib,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from build_release import P,current_version
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8'))
out=P/'reports/ground_material_v0231/shipping_01'
assert not out.exists();out.mkdir()
exe=P/'build/windows/RailwayWarlords.exe'; exported=next(x for x in read(P/'reports/export_results.json') if x['target']=='windows')
identity=sha(exe);assert exported['export_verified'] and exported['sha256']==identity and current_version()=='0.2.31'
commands=[];captures=[]
for name,flags in [('gpu',['--ground-continuity-test','--ground-continuity-output',str(out/'gpu')]),('ui_smoke',['--scenario','campaign_1924_02','--ui-test','--capture-path',str(out/'ui_smoke.png')]),('home',['--capture','--capture-path',str(out/'home.png')])]:
 log=out/(name+'.log'); command=[str(exe),'--resolution','1920x1080','--position','0,0','--log-file',str(log),'--','--qa-session',*flags]
 started=time.time()
 with (out/(name+'.stdout.log')).open('w',encoding='utf-8') as f:
  run=subprocess.run(command,cwd=P,stdout=f,stderr=subprocess.STDOUT,timeout=360)
 text=log.read_text(encoding='utf-8',errors='replace')
 assert run.returncode==0 and 'SCRIPT ERROR:' not in text and '\nERROR:' not in text
 commands.append(dict(name=name,command=command,exit_code=run.returncode))
 if name=='gpu':
  result=read(out/'gpu/validation.json');assert result['passed'] and result['build_version']=='0.2.31' and len(result['checks'])==48 and len(result['samples'])==26
  assert all(x['maximum_channel_delta']<=2 and x['pixels']>=500 for x in result['samples'] if 'family' in x)
 else:
  if name=='ui_smoke':assert 'UI_SMOKE_PASS' in text
  path=out/(name+'.png');metadata=path.with_suffix('.json');d=read(metadata)
  assert path.stat().st_mtime>=started-2 and d['build_version']=='0.2.31' and d['qa_save_isolated'] and d['raw_godot_capture'] and not d['physical_android_device_tested']
  captures.append(dict(path=path.relative_to(P).as_posix(),sha256=sha(path),metadata=metadata.relative_to(P).as_posix(),metadata_sha256=sha(metadata)))
 print(name,'verified',flush=True)
assert sha(exe)==identity
report=dict(passed=True,version='0.2.31',mode='verified_shipping_exe',runtime_source_sha256=exported['runtime_source_sha256'],windows_exe_sha256=identity,shipping_binary_unchanged=True,capture_driver_sha256=sha(__file__),commands=commands,captures=captures,gpu_report='reports/ground_material_v0231/shipping_01/gpu/validation.json',gpu_report_sha256=sha(out/'gpu/validation.json'),gpu_checks=48,ui_smoke_passed=True,physical_android_device_tested=False,formal_art_approval=False,ew6_parity_claimed=False,manual_image_compositing=False)
(out/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('SHIPPING_MATERIAL_VERIFIED',flush=True)
