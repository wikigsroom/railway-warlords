"""Freeze and validate the complete commander beta with native tools only."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import argparse, json, os, shutil, subprocess, sys
from build_release import P, ROOT, current_version, source_digest, ENGINE
from package_delivery import read, require, sha

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--resume-regressions',action='store_true')
    parser.add_argument('--reuse-current-regressions',action='store_true',
        help='Rerun stale dependency groups while retaining already sealed passing checks')
    args=parser.parse_args()
    require(current_version()=='0.2.28','This pipeline targets 0.2.28')
    require(not(args.resume_regressions and args.reuse_current_regressions),'Choose one regression recovery mode')
    if args.reuse_current_regressions:
        seal=read(P/'reports/regression_dependency_evidence.json')
        require(seal['passed'] and seal['game_version']==current_version() and len(seal['checks'])==30,
            'All thirty prior groups must already have a passing dependency seal')
    catalogue=read(P/'presentation/data/general_portraits.json')
    require(catalogue['production_complete'] and not catalogue['missing_age_stages']
        and len(catalogue['generals'])==328,'Do not export an unfinished portrait catalogue')
    progress=ROOT/'output/commander_pool_validation_progress.json'
    state=dict(version=current_version(),pid=os.getpid(),terminal=False,stages=[],
        started_at_utc=datetime.now(timezone.utc).isoformat())
    if args.resume_regressions:
        previous=read(progress)
        require(previous['version']==current_version() and previous['terminal']
            and not previous['passed'] and previous['current_stage']=='exports_and_regressions',
            'Resume is restricted to the interrupted export/regression phase')
        runtime=source_digest()[0]
        require(previous['runtime_source_sha256']==runtime,'Runtime changed; rerun the full export pipeline')
        exports=read(P/'reports/export_results.json')
        require({r['target'] for r in exports}=={'windows','android'} and all(
            r['export_verified'] and r['runtime_source_sha256']==runtime
            and sha(P/'build'/r['target']/('RailwayWarlords.exe' if r['target']=='windows' else 'RailwayWarlords.apk'))==r['sha256']
            for r in exports),'Both unchanged verified binaries are required to resume')
        archive=read(P/'docs/commander-production/index.json')
        require(archive['production_terminal'] and archive['generated_originals']==1180
            and all(sha(P/r['file'])==r['sha256'] for r in archive['files']),
            'Production archive changed; restart the pipeline')
        required={'build_commander_report','archive_commander_production','import_project','build_release'}
        completed=[r for r in previous['stages'] if r['exit_code']==0]
        require(required.issubset({r['name'] for r in completed}),'Incomplete import/export stages cannot be reused')
        retained=ROOT/'output/commander_pool_validation_previous_failure.json'
        retained.write_text(json.dumps(previous,indent=2)+'\n',encoding='utf-8')
        old_log=P/'reports/commander_validation_run_validation.log'
        if old_log.exists():shutil.copyfile(old_log,ROOT/'output/commander_pool_validation_previous_failure.log')
        state.update(stages=completed,runtime_source_sha256=runtime,
            resumed_from=retained.relative_to(ROOT).as_posix(),
            reused_binaries_verified_against_sha256=True,
            previous_failed_stages=[r for r in previous['stages'] if r['exit_code']])
    def save():
        pending=progress.with_suffix('.tmp');pending.write_text(json.dumps(state,indent=2)+'\n',encoding='utf-8');pending.replace(progress)
    def run(name,extra=(),native=False):
        log=P/'reports'/('coast_geometry_native.log' if native else 'commander_validation_'+name+'.log')
        if name=='import_project':command=[str(ENGINE),'--headless','--editor','--path',str(P),'--import']
        elif native:command=[str(ENGINE),'--headless','--path',str(P),'--script','res://tests/coast_geometry_test.gd']
        else:command=[sys.executable,'-X','utf8','tools/'+name+'.py',*extra]
        print('COMMANDER_VALIDATION_BEGIN '+name,flush=True);started=datetime.now(timezone.utc).isoformat()
        with log.open('w',encoding='utf-8') as out:result=subprocess.run(command,cwd=P,stdout=out,stderr=subprocess.STDOUT)
        print('COMMANDER_VALIDATION_'+('PASS ' if result.returncode==0 else 'FAILED ')+name,flush=True)
        return dict(name=name,exit_code=result.returncode,log=log.relative_to(P).as_posix(),
            started_at_utc=started,finished_at_utc=datetime.now(timezone.utc).isoformat())
    def finish(passed):
        state.update(terminal=True,passed=passed,finished_at_utc=datetime.now(timezone.utc).isoformat());save();return 0 if passed else 1
    if args.resume_regressions:
        state['current_stage']='exports_and_regressions';save()
        state['stages'].append(run('run_validation',('--stale-only',)));save()
    else:
        for name in ['build_commander_report','archive_commander_production','import_project']:
            state['current_stage']=name;save();state['stages'].append(run(name));save()
            if state['stages'][-1]['exit_code']:return finish(False)
        state['runtime_source_sha256']=source_digest()[0];state['current_stage']='exports_and_regressions';save()
        with ThreadPoolExecutor(max_workers=2) as pool:
            regression_args=('--stale-only',) if args.reuse_current_regressions else ()
            for job in as_completed([pool.submit(run,'build_release'),pool.submit(run,'run_validation',regression_args)]):
                state['stages'].append(job.result());save()
    if any(r['exit_code'] for r in state['stages']):return finish(False)
    steps=[('coast_geometry_test',True),('seal_coast_native_geometry',False),
        ('seal_regression_dependencies',False),('validate_project',False),
        ('audit_ground_macros',False),('verify_ground_continuity',False),
        ('verify_water_continuity',False),('run_final_ui_refinement_qa',False),
        ('capture_commander_roster',False),('capture_coast_detail',False),
        ('capture_water_maps',False),('audit_commander_scope',False),('record_commander_performance',False)]
    for name,native in steps:
        state['current_stage']=name;save();state['stages'].append(run(name,native=native));save()
        if state['stages'][-1]['exit_code']:return finish(False)
    if source_digest()[0]!=state['runtime_source_sha256']:
        state['failure']='Runtime source changed during validation';return finish(False)
    return finish(True)

if __name__=='__main__':raise SystemExit(main())
