"""Bind all four living age stages; technical provenance is not art approval."""
import argparse,json
from generate_general_portraits import P,sha

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--allow-incomplete',action='store_true');args=parser.parse_args()
    life=json.loads((P/'presentation/data/general_lifespans.json').read_text(encoding='utf-8'))['generals']
    generals=json.loads((P/'content/definitions/generals.json').read_text(encoding='utf-8-sig'))
    military_ids={g['id'] for g in generals}
    figures=json.loads((P/'content/history/asia_timeline.json').read_text(encoding='utf-8'))['political_figures']
    people=generals+[dict(id=f['id'],name=f['name_zh']) for f in figures if f['id'] not in military_ids]
    assets=json.loads((P/'assets/manifest.json').read_text(encoding='utf-8'))['assets']
    records={};missing=[]
    for person in people:
        gid=person['id'];history=life[gid];variants=[]
        for asset in assets:
            if asset['category']!='portrait':continue
            aid=asset['id']
            if not (aid=='portrait_'+gid or aid.startswith('portrait_'+gid+'_')):continue
            year=int(asset.get('reference_year',1920));path=P/asset['engine_path'].removeprefix('res://')
            assert path.is_file() and sha(path)==asset['source_sha256'],aid
            stage=asset.get('age_stage','')
            if not stage:
                before=[s for s in history['stages'] if s['reference_year']<=year]
                stage=(before[-1] if before else history['stages'][0])['id']
            if (gid=='li_hongzhang' and year>=1890) or (gid=='yamagata_aritomo' and year>=1900):stage='late'
            if gid=='mao_zedong' and year==1940:stage='middle'
            variants.append(dict(reference_year=year,age_stage=stage,asset_id=aid,asset_sha256=asset['source_sha256'],illustration=True,exact_year_photograph_claimed=False))
        variants.sort(key=lambda r:r['reference_year'])
        for stage in history['stages']:
            if not any(v['age_stage']==stage['id'] for v in variants):missing.append(gid+':'+stage['id'])
        records[gid]=history|dict(name=person['name'],kind='portrait',variants=variants,military_deployable=gid in military_ids)
    if missing and not args.allow_incomplete:raise ValueError('Age-stage originals not yet installed: '+', '.join(missing))
    result=dict(schema=2,production_version='0.2.28',selection='Latest appropriate dated appearance; catalog previews permit an explicit living age stage.',likeness_policy='Interpretive game illustrations; age-stage art is not an archival photograph, verified same-year uniform or independent historical likeness approval.',missing_age_stages=missing,production_complete=not missing,generals=records)
    (P/'presentation/data/general_portraits.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(generals=len(records),originals=sum(len(r['variants']) for r in records.values()),missing_age_stages=len(missing),production_complete=not missing)))

if __name__=='__main__':main()
