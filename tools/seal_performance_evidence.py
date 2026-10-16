"""Seal current native capacity, semantic-equivalence and visual evidence."""
from pathlib import Path
import json
import hashlib
import argparse
from datetime import datetime,timezone
from build_release import current_version,source_digest,rule_dependencies_digest
from package_delivery import sha
from regression_dependencies import modified as regression_modified

P=Path(__file__).resolve().parents[1]

def read(name):return json.loads((P/'reports'/name).read_text(encoding='utf-8'))

def semantic_dependencies_digest():
    # Headless behavior comparisons depend on the real rule kernel and preserved
    # references, rather than rasterization or native presentation QA helpers.
    rule_hash,modified=rule_dependencies_digest()
    digest=hashlib.sha256(rule_hash.encode())
    paths=[P/'tests/performance_equivalence_test.gd',P/'tests/immutable_state_fingerprint.gd',P/'app/capacity_fixture.gd',
        P/'tests/fixtures/capacity_full_conquest.json']
    paths.extend(p for p in (P/'tests/fixtures').glob('reference_*') if p.suffix in ('.gd','.json'))
    for path in sorted(paths):
        digest.update(path.relative_to(P).as_posix().encode());digest.update(path.read_bytes())
        modified=max(modified,path.stat().st_mtime)
    return digest.hexdigest(),modified

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--allow-domain-timing-limited-beta',action='store_true')
    options=parser.parse_args()
    version=current_version();tag='v'+version.replace('.','');runtime,modified=source_digest()
    semantic_hash,semantic_modified=semantic_dependencies_digest()
    def evidence_modified(name):
        if name=='performance_equivalence.json':return semantic_modified
        if name=='capacity_domain_'+tag+'.json':return regression_modified('capacity_test')
        if name=='rules_worker_tests.json':return regression_modified('rules_worker_test')
        if name=='snapshot_optimization_tests.json':return regression_modified('snapshot_optimization_test')
        return modified
    domain=read('capacity_domain_'+tag+'.json');equivalence=read('performance_equivalence.json')
    snapshots=read('snapshot_optimization_tests.json')
    snapshot_reference=read('snapshot_reference_validation.json')
    pixels=read('unit_layer_pixel_validation.json')
    native=read('unit_layer_native.json')
    fixture_sha=sha(P/'tests/fixtures/capacity_full_conquest.json')
    images=[]
    for original,comparison in zip(native['cases'],pixels['cases']):
        if original['name']!=comparison['name']:raise SystemExit('Native pixel case order differs.')
        for key,expected in zip(('cached','direct'),comparison['native_images_sha256']):
            path=P/original[key].removeprefix('res://')
            if sha(path)!=expected:raise SystemExit('Native comparison capture changed: '+str(path))
            images.append({'file':path.relative_to(P).as_posix(),'sha256':expected})
    records=[]
    for profile in ('windows','x30'):
        name='capacity_'+profile+'_'+tag+'.json';value=read(name)
        stages={s['stage']:s for s in value['stages']}
        valid=value['game_version']==version and value['is_exported_executable'] and not value['physical_android_device_tested'] and value['fixture_file_sha256']==fixture_sha
        valid=valid and value['render_target_passed'] and value['cells']==74762 and value['usable_cells']==71386 and value['active_units']==240
        valid=valid and all(key in stages for key in ('atlas_static','atlas_pan','tactical_select','sustained_pan_zoom','battle_active'))
        if not valid:raise SystemExit('Incomplete current native render profile: '+name)
        valid=valid and stages['sustained_pan_zoom']['duration_seconds']>=59.5 and len(value['battle_commands'])>=1
        valid=valid and all(stages[key]['average_fps']>=60 for key in stages)
        valid=valid and all(stages[key]['initial_active_units']==240 and stages[key]['minimum_drawable_units']==240 and stages[key]['unit_layer_draw_count_min']>=240 for key in ('atlas_static','atlas_pan','sustained_pan_zoom'))
        if profile=='x30':valid=valid and value['mobile_layout_profile'] and value['ui_scale']==1.2
        records.append({'file':name,'sha256':sha(P/'reports'/name),'passed':valid,
            'stages':[{k:v for k,v in s.items() if k!='frame_ms_samples'} for s in value['stages']]})
    names=['capacity_domain_'+tag+'.json','performance_equivalence.json','snapshot_optimization_tests.json','snapshot_reference_validation.json','unit_layer_native.json','unit_layer_pixel_validation.json',*[r['file'] for r in records]]
    valid=domain['passed'] and domain['game_version']==version and len(domain['results'])==3
    valid=valid and not domain['baseline'] and not domain['production_map_baseline_only'] and all(row['cells']==74762 and row['usable_cells']==71386 and row['initial_active_units']==240 and len(row['phase_samples'])==3 for row in domain['results'])
    valid=valid and equivalence['failed']==0 and equivalence['passed']>=1544 and equivalence['game_version']==version
    valid=valid and len(equivalence.get('capacity_phase_traces',[]))==3
    valid=valid and snapshots['failed']==0 and snapshots['game_version']==version and snapshots['content_hash']==equivalence['content_hash'] and len(snapshots['traces'])==4 and snapshots['trace_commands']>=300
    valid=valid and snapshot_reference['passed'] and snapshot_reference['source_archive_sha256']==read('../tests/fixtures/reference_v023.json')['source_archive_sha256']
    valid=valid and pixels['passed'] and pixels['runtime_source_sha256']==runtime and all(r['passed'] for r in records)
    valid=valid and all((P/'reports'/name).stat().st_mtime>=evidence_modified(name) for name in names)
    valid=valid and equivalence['content_hash']==domain['production_content_hash']
    exports=read('export_results.json')
    valid=valid and all(row['export_verified'] and row['runtime_source_sha256']==runtime and sha(Path(row['path']))==row['sha256'] for row in exports)
    worker=read('rules_worker_tests.json')
    valid=valid and worker['game_version']==version and worker['failed']==0 and worker['passed']>=347 and worker['trace_commands']>=40
    response=[]
    for profile in ('windows','x30'):
        name='responsiveness_'+profile+'_'+tag+'.json';value=read(name)
        capture=P/'reports/screenshots'/('responsiveness_'+profile+'_'+tag+'.png')
        row_pass=value['passed'] and value['game_version']==version and value['runtime_source_sha256']==runtime
        row_pass=row_pass and value['is_exported_executable'] and not value['physical_android_device_tested']
        row_pass=row_pass and value['command_count']>=25 and value['end_phase_accepted'] and value['end_phase_changed'] and value['planning_frames']>0 and value['animation_frames']>0 and value['main_handoff_us_max']<=8000
        row_pass=row_pass and value['fixture_file_sha256']==fixture_sha and value['binary_sha256']==next(export['sha256'] for export in exports if export['target']=='windows') and value['native_capture_sha256']==sha(capture)
        row_pass=row_pass and value['initial_active_units']==240 and value['real_usable_cells']==71386
        if profile=='x30':row_pass=row_pass and value['mobile_layout_profile'] and value['ui_scale']==1.2
        valid=valid and row_pass
        response.append({'file':name,'passed':row_pass,'command_count':value['command_count'],'main_handoff_us_max':value['main_handoff_us_max'],'planning_frames':value['planning_frames'],'animation_frames':value['animation_frames']})
        images.append({'file':capture.relative_to(P).as_posix(),'sha256':sha(capture)})
        names.append(name)
    names.append('rules_worker_tests.json')
    valid=valid and all((P/'reports'/name).stat().st_mtime>=evidence_modified(name) for name in names)
    native_and_semantic_checks_passed=valid
    domain_targets_passed=domain['all_performance_targets_passed']
    valid=native_and_semantic_checks_passed and domain_targets_passed
    report={'passed':valid,'native_and_semantic_checks_passed':native_and_semantic_checks_passed,
        'domain_performance_targets_passed':domain_targets_passed,
        'unmet_domain_targets':[{'distribution':row['distribution'],'timings':row['timings']} for row in domain['results'] if not row['target_passed']],
        'version':version,'created_at_utc':datetime.now(timezone.utc).isoformat(),
        'runtime_source_sha256':runtime,'production_content_hash':domain['production_content_hash'],
        'semantic_dependency_sha256_at_seal':semantic_hash,
        'semantic_freshness_scope':'Behavior report completed after its unchanged rule/content/fixture/reference dependencies. Renderer-only changes are verified by fresh native pixel and exported performance checks.',
        'domain_results':domain['results'],'render_profiles':records,'semantic_checks':equivalence['passed'],
        'snapshot_semantic_checks':snapshots['passed'],'snapshot_comparison_commands':snapshots['trace_commands'],
        'pixel_comparisons':len(pixels['cases']),'physical_android_device_tested':False,
        'reports':[{'file':name,'sha256':sha(P/'reports'/name)} for name in names],
        'fixture_file_sha256':fixture_sha,'native_comparison_images':images,
        'ui_eight_millisecond_slice_verified':all(row['passed'] for row in response),
        'responsiveness_profiles':response,'worker_regression_checks':worker['passed'],
        'ui_slice_scope':'Measured active-play rule submission and atomic main-thread commit including signal listeners. Native serial background worker, cold first command retained. Does not cover startup/map construction, OS lifecycle or physical Android frames.',
        'scope':'Final exported Windows EXE, RTX 3060; 74762 actual production cells / 71386 usable cells / 240 units; two desktop layouts, real combat and sixty-second sustained pan/zoom. Domain includes three distributions and full legal AI phases. Not physical X30 GPU or human balance/history acceptance.'}
    (P/'reports/performance_evidence.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'passed':valid,'profiles':len(records),'semantic_checks':equivalence['passed'],'pixel_pairs':len(pixels['cases'])}))
    raise SystemExit(0 if valid or (options.allow_domain_timing_limited_beta and native_and_semantic_checks_passed) else 1)

if __name__=='__main__':main()
