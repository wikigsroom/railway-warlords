"""Native Windows validation of the scoped coast/overlay release."""
from concurrent.futures import ThreadPoolExecutor,as_completed
from datetime import datetime,timezone
import json
import os
import subprocess
import sys
from build_release import P,ROOT,current_version,source_digest,ENGINE


def main():
    if current_version()!='0.2.26':raise SystemExit('This pipeline targets 0.2.26.')
    progress=ROOT/'output/coast_validation_progress.json'
    state=dict(version=current_version(),pid=os.getpid(),terminal=False,stages=[],
               runtime_source_sha256=source_digest()[0],started_at_utc=datetime.now(timezone.utc).isoformat())
    def save():
        tmp=progress.with_suffix('.tmp');tmp.write_text(json.dumps(state,indent=2)+'\n',encoding='utf-8');tmp.replace(progress)
    def run(name,extra=(),native=False):
        log=P/'reports'/('coast_geometry_native.log' if native else 'coast_validation_'+name+'.log')
        command=[str(ENGINE),'--headless','--path',str(P),'--script','res://tests/coast_geometry_test.gd'] if native else [sys.executable,'-X','utf8','tools/'+name+'.py',*extra]
        print('COAST_VALIDATION_BEGIN '+name,flush=True);start=datetime.now(timezone.utc).isoformat()
        with log.open('w',encoding='utf-8') as f:result=subprocess.run(command,cwd=P,stdout=f,stderr=subprocess.STDOUT)
        print('COAST_VALIDATION_'+('PASS ' if result.returncode==0 else 'FAILED ')+name,flush=True)
        return dict(name=name,exit_code=result.returncode,log=log.relative_to(P).as_posix(),started_at_utc=start,finished_at_utc=datetime.now(timezone.utc).isoformat())
    def finish(passed):
        state.update(terminal=True,passed=passed,finished_at_utc=datetime.now(timezone.utc).isoformat());save();return 0 if passed else 1
    state['current_stage']='exports_regressions_and_reproducible_coast';save()
    with ThreadPoolExecutor(max_workers=3) as pool:
        jobs=[pool.submit(run,'build_release'),pool.submit(run,'run_validation'),
              pool.submit(run,'compile_coast_detail',('--check',))]
        for job in as_completed(jobs):state['stages'].append(job.result());save()
    if any(r['exit_code'] for r in state['stages']):return finish(False)
    steps=[('coast_geometry_test',(),True),('seal_coast_native_geometry',(),False),('seal_regression_dependencies',(),False),
           ('audit_coast_detail',(),False),('audit_surface_geography',(),False),('verify_asia_geography_rebuild',(),False),
           ('validate_project',(),False),('audit_ground_macros',(),False),
           ('archive_native_review',('--review','ground_atlas_native_review.json'),False),
           ('verify_ground_continuity',(),False),('run_final_ui_refinement_qa',(),False),
           ('capture_coast_detail',(),False),
           ('audit_coast_scope',(),False)]
    for name,extra,native in steps:
        state['current_stage']=name;save();state['stages'].append(run(name,extra,native));save()
        if state['stages'][-1]['exit_code']:return finish(False)
    if source_digest()[0]!=state['runtime_source_sha256']:
        state['failure']='Runtime source changed during validation';return finish(False)
    return finish(True)


if __name__=='__main__':raise SystemExit(main())
