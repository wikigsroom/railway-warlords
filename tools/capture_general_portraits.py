"""Run four-stage roster controls in the exported Windows app, on three layouts."""
from datetime import datetime,timezone
import json,subprocess
from pathlib import Path
from PIL import Image
from build_release import P,current_version,source_digest
from package_delivery import read,sha,require

def main():
 version=current_version();runtime=source_digest()[0];exe=P/'build/windows/RailwayWarlords.exe'
 export=next(r for r in read(P/'reports/export_results.json') if r['target']=='windows')
 require(export['export_verified'] and export['sha256']==sha(exe) and export['runtime_source_sha256']==runtime,'Verified current Windows binary required')
 proof_path=P/'reports/general_portrait_native_evidence.json';driver=sha(Path(__file__))
 if proof_path.exists():
  previous=read(proof_path)
  if (previous.get('passed') and previous.get('version')==version
      and previous.get('runtime_source_sha256')==runtime and previous.get('windows_exe_sha256')==export['sha256']
      and previous.get('capture_driver_sha256')==driver and len(previous.get('groups',[]))==3
      and all(sha(P/g['report'])==g['report_sha256'] for g in previous['groups'])
      and all(sha(P/r['file'])==r['sha256'] and sha(P/r['metadata'])==r['metadata_sha256']
              for g in previous['groups'] for r in g['captures'])):
   print('Current frozen-build three-layout portrait evidence retained.',flush=True);return
 groups=[]
 for profile,resolution,scale in [('windows','1920x1080','1.0'),('x30_layout','2400x1080','1.2'),('large_text','1280x720','1.5')]:
  folder=P/'reports/screenshots/general_portraits_native'/profile;folder.mkdir(parents=True,exist_ok=True)
  log=P/'reports'/('general_portraits_native_'+profile+'.log');started=datetime.now(timezone.utc).timestamp()
  command=[str(exe),'--resolution',resolution,'--position','-4000,-3000','--','--qa-session','--ui-scale',scale,'--general-portrait-test','--general-portrait-output',str(folder)]
  if profile=='x30_layout':command.append('--mobile-ui-test')
  with log.open('w',encoding='utf-8') as out:result=subprocess.run(command,cwd=P,stdout=out,stderr=subprocess.STDOUT,timeout=600)
  diagnostic=log.read_text(encoding='utf-8',errors='replace')
  require(result.returncode==0 and 'SCRIPT ERROR:' not in diagnostic and '\nERROR:' not in diagnostic,'Native age UI failed: '+profile)
  report=folder/'validation.json';value=read(report)
  require(value['passed'] and value['build_version']==version and value['content_hash']==read(P/'reports/sample_state_v2.json')['content_hash'] and value['qa_save_isolated'],'Current native age report required')
  captures=[]
  for row in value['captures']:
   path=Path(row['path']);meta=path.with_suffix('.json');m=read(meta)
   require(path.stat().st_mtime>=started-2 and m['build_version']==version and m['raw_godot_capture'],'Fresh untouched viewport required')
   with Image.open(path) as im:require(im.size==tuple(map(int,resolution.split('x'))),'Viewport size mismatch')
   captures.append(dict(file=path.relative_to(P).as_posix(),sha256=sha(path),metadata=meta.relative_to(P).as_posix(),metadata_sha256=sha(meta)))
  require(len(captures)>=58,'Incomplete general and political four-stage native traversal')
  groups.append(dict(profile=profile,resolution=resolution,ui_scale=scale,checks=len(value['checks']),report=report.relative_to(P).as_posix(),report_sha256=sha(report),log=log.relative_to(P).as_posix(),captures=captures))
  print(json.dumps(dict(profile=profile,passed=True,checks=len(value['checks']),captures=len(captures))),flush=True)
 require(source_digest()[0]==runtime and sha(exe)==export['sha256'],'Source or binary changed during QA')
 result=dict(passed=True,version=version,runtime_source_sha256=runtime,windows_exe_sha256=export['sha256'],capture_driver_sha256=driver,groups=groups,raw_godot_captures=True,physical_android_device_tested=False,formal_art_approval=False,historical_likeness_approval=False)
 (P/'reports/general_portrait_native_evidence.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

if __name__=='__main__':main()
