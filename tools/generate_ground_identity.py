"""Twenty material-identity originals via the mandated Sub2 route.

Original PNGs and prompts are immutable. New IDs supersede, rather than replace,
the stored v0.2.14 macro originals. This tool never writes image pixels.
"""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import argparse
import json
import shutil
import generate_map_bank as base

P=base.P
RAW=base.ROOT/'output/imagegen/warlord/terrain_identity_v0220/originals'
PLAN=P/'presentation/data/ground_identity_plan.json'
REPORT=P/'reports/ground_identity_generation.json'
CATALOG=P/'presentation/data/ground_macro_catalog.json'

def read(path):return json.loads(path.read_text(encoding='utf-8'))
def rows():
    value=read(PLAN)
    assert value['terrain_type_count']==len(value['assets'])==20
    assert value['source_route']=='sub2-image-gen/gpt-image-2.5/high'
    return value['assets']

def measured(row):
    result=base.measure(row)
    if result is not None:
        result.update(style_version='warlord_material_identity_v0220',revision='ground_identity_v0220_r001',
            era='representative_regional_material_not_historical_landuse_survey')
    return result

def install(items):
    review=read(P/'reports/ground_identity_source_review.json')
    assert review['all_twenty_originals_viewed'] and len(review['originals'])==20
    viewed={r['id']:r for r in review['originals']}
    values=[measured(row) for row in items]
    assert all(values) and len({r['source_sha256'] for r in values})==20
    previous=read(CATALOG)
    assert set(previous['records'])=={r['family'] for r in items}
    superseded=previous.get('superseded_asset_ids',[r['asset_id'] for r in previous['records'].values()])
    geography=P/'presentation/data/terrain_surface_regions.json';geo_sha=base.sha(geography)
    path=P/'assets/manifest.json';manifest=read(path);current={r['id']:r for r in manifest['assets']}
    records={}
    for row in values:
        assert row['source_sha256']==viewed[row['id']]['sha256']
        assert row['prompt_sha256']==viewed[row['id']]['prompt_sha256']
        target=P/row['engine_path'].removeprefix('res://')
        if target.exists():assert base.sha(target)==row['source_sha256'],'Immutable engine original differs'
        else:shutil.copyfile(base.ROOT/row['source_file'],target)
        portable=P/'docs/asset-prompts'/ (row['id']+'.txt')
        if portable.exists():assert base.sha(portable)==row['prompt_sha256']
        else:shutil.copyfile(base.ROOT/row['prompt_file'],portable)
        row.update(state='generated_scoped_source_review_complete',game_ready=False,
                   visual_review='All twenty whole originals inspected; integration and formal art approval tracked separately')
        if row['id'] in current:
            assert current[row['id']]['source_sha256']==row['source_sha256']
        current[row['id']]=row
        records[row['family']]=dict(asset_id=row['id'],source_sha256=row['source_sha256'],actual_dimensions=row['actual_dimensions'])
    assert len(superseded)==20 and set(superseded)<=set(current)
    manifest['assets']=sorted(current.values(),key=lambda r:r['id']);base.write_json(path,manifest)
    base.write_json(CATALOG,dict(format=1,version='0.2.20',independent_originals=20,
        source_plan_file=PLAN.relative_to(P).as_posix(),source_plan_sha256=base.sha(PLAN),world_repeat_period=128,
        source_images_modified=False,records=records,superseded_originals=20,superseded_asset_ids=sorted(superseded),
        original_pngs_retained=True,material_identity_revision='recognizable_material_motifs_r001'))
    assert base.sha(geography)==geo_sha
    base.write_json(P/'reports/ground_identity_installation.json',dict(passed=True,version='0.2.20',
        installed_new_originals=20,active_macro_originals=20,stored_superseded_originals=20,
        all_original_pngs_retained=True,source_images_modified=False,manual_compositing=False,
        geography_assignments_changed=False,geography_sha256=geo_sha,source_plan_sha256=base.sha(PLAN),
        total_registered_rasters=len(current),formal_art_approval=False))
    print('Installed 20 new identity originals; 20 previous originals retained unchanged.',flush=True)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--install',action='store_true');ap.add_argument('--workers',type=int,default=3)
    args=ap.parse_args();base.RAW=RAW;items=rows()
    if args.install:install(items);return
    complete={r['id']:v for r in items if (v:=measured(r)) is not None};failures=[]
    def report():base.write_json(REPORT,dict(version='0.2.20',created_at_utc=datetime.now(timezone.utc).isoformat(),
        passed=len(complete)==20 and not failures,completed=len(complete),requested=20,
        source_route='sub2-image-gen/gpt-image-2.5/high',source_images_modified=False,manual_compositing=False,
        formal_art_approval=False,source_plan_sha256=base.sha(PLAN),failures=failures,
        assets=sorted(complete.values(),key=lambda r:r['id'])))
    report()
    with ThreadPoolExecutor(max_workers=max(1,min(3,args.workers))) as pool:
        jobs={pool.submit(base.generate,r):r for r in items if r['id'] not in complete}
        for future in as_completed(jobs):
            row=jobs[future]
            try:future.result();complete[row['id']]=measured(row);print('GENERATED '+row['id'],flush=True)
            except Exception as exc:failures.append(dict(id=row['id'],error=str(exc)));print('FAILED '+row['id'],flush=True)
            report()
    print(json.dumps(dict(completed=len(complete),failures=len(failures))),flush=True)
    raise SystemExit(bool(failures))

if __name__=='__main__':main()
