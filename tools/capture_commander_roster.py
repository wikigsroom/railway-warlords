"""Exercise the complete commander archive and a real reserve appointment."""
from datetime import datetime,timezone
from pathlib import Path
import json,subprocess
from PIL import Image
from build_release import P,current_version,source_digest
from package_delivery import read,sha,require

def main():
 version=current_version();runtime=source_digest()[0];exe=P/'build/windows/RailwayWarlords.exe'
 export=next(r for r in read(P/'reports/export_results.json') if r['target']=='windows')
 require(export['export_verified'] and export['sha256']==sha(exe) and export['runtime_source_sha256']==runtime,'Verified current Windows binary required')
 proof_path=P/'reports/commander_roster_native_evidence.json';driver=sha(Path(__file__))
 if proof_path.exists():
  previous=read(proof_path);old_groups=previous.get('groups',[])
  if (previous.get('passed') and previous.get('version')==version
      and previous.get('runtime_source_sha256')==runtime and previous.get('windows_exe_sha256')==export['sha256']
      and previous.get('capture_driver_sha256')==driver and len(old_groups)==3
      and {g['profile'] for g in old_groups}=={'windows','x30_layout','large_text'}
      and all((P/g['report']).is_file() and sha(P/g['report'])==g['report_sha256']
          and (P/g['log']).is_file() and sha(P/g['log'])==g.get('log_sha256')
          and len(g['captures'])==6 for g in old_groups)
      and all((P/r[k]).is_file() and sha(P/r[k])==r['sha256' if k=='file' else 'metadata_sha256']
          for g in old_groups for r in g['captures'] for k in ['file','metadata'])
      and all(read(P/g['report'])['passed'] and read(P/g['report'])['all_portraits_complete']
          and read(P/g['report'])['military_commanders']==324
          and read(P/g['report'])['people_with_four_registered_portraits']==328 for g in old_groups)):
   print('Current frozen-build three-layout commander browsing and actual appointment evidence retained.',flush=True)
   return
 groups=[]
 for profile,resolution,scale in [('windows','1920x1080','1.0'),('x30_layout','2400x1080','1.2'),('large_text','1280x720','1.5')]:
  folder=P/'reports/screenshots/commander_roster_native'/profile;folder.mkdir(parents=True,exist_ok=True)
  log=P/'reports'/('commander_roster_native_'+profile+'.log');started=datetime.now(timezone.utc).timestamp()
  command=[str(exe),'--resolution',resolution,'--position','0,0','--','--qa-session','--ui-scale',scale,'--commander-roster-test','--commander-roster-output',str(folder)]
  if profile=='x30_layout':command.append('--mobile-ui-test')
  with log.open('w',encoding='utf-8') as out:result=subprocess.run(command,cwd=P,stdout=out,stderr=subprocess.STDOUT,timeout=900)
  diagnostic=log.read_text('utf-8',errors='replace');require(result.returncode==0 and 'SCRIPT ERROR:' not in diagnostic and '\nERROR:' not in diagnostic,'Native commander archive failed: '+profile)
  report=folder/'validation.json';value=read(report)
  require(value['passed'] and value['version']==version and value['qa_save_isolated'] and value['all_portraits_complete'],'Current complete archive/portrait report required')
  require(value['military_commanders']==len(read(P/'content/definitions/generals.json')),'Roster cardinality differs')
  captures=[]
  for row in value['captures']:
   path=Path(row['path']);meta=path.with_suffix('.json');m=read(meta)
   require(path.stat().st_mtime>=started-2 and m['build_version']==version and m['raw_godot_capture'],'Fresh untouched viewport required')
   require(m['content_hash']==value['content_hash'],'Capture content differs from the report')
   with Image.open(path) as im:require(im.size==tuple(map(int,resolution.split('x'))),'Viewport size differs')
   captures.append(dict(surface=row['surface'],file=path.relative_to(P).as_posix(),sha256=sha(path),metadata=meta.relative_to(P).as_posix(),metadata_sha256=sha(meta)))
  require({'commander_catalogue','commander_last_page','japanese_division_commanders','live_name_search','scenario_reserve_appointment','reserve_appointed'}=={r['surface'] for r in captures},'Incomplete actual archive and appointment captures')
  groups.append(dict(profile=profile,resolution=resolution,ui_scale=scale,checks=len(value['checks']),report=report.relative_to(P).as_posix(),report_sha256=sha(report),log=log.relative_to(P).as_posix(),log_sha256=sha(log),captures=captures))
  print(json.dumps(dict(profile=profile,passed=True,checks=len(value['checks']),captures=len(captures))),flush=True)
 require(source_digest()[0]==runtime and sha(exe)==export['sha256'],'Source or binary changed during QA')
 proof=dict(passed=True,version=version,runtime_source_sha256=runtime,windows_exe_sha256=export['sha256'],capture_driver_sha256=driver,groups=groups,raw_godot_captures=True,physical_android_device_tested=False,formal_art_approval=False,historical_likeness_approval=False)
 proof_path.write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

if __name__=='__main__':main()
