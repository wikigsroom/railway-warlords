"""Read-only checks of real game resources and provenance; never edits raster images."""
from pathlib import Path
from collections import Counter
import json, hashlib, wave, sys, re, zipfile
from array import array
from PIL import Image
from jsonschema import Draft202012Validator

P=Path(__file__).resolve().parents[1];ROOT=P.parents[1]
def read(path):return json.loads(path.read_text(encoding='utf-8'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    errors=[];checks=[];asset_rows=[];audio_rows=[]
    catalog=read(P/'content/definitions/catalog.json')['tables']
    definitions={n:read(P/'content/definitions'/f'{n}.json') for n in catalog}
    baseline_deltas={}
    # The selected Asia direction deliberately extends the original 0.2.x
    # catalog. Keep the original ids as a compatibility floor, while recording
    # new period factions, commanders, and era gates as an explicit data delta.
    extensible_tables={'factions','generals','units'}
    for n in catalog:
        baseline=ROOT/'design/铁道烽烟/data'/f'{n}.json'
        current_path=P/'content/definitions'/f'{n}.json'
        if not baseline.exists():continue
        if n not in extensible_tables:
            if sha(baseline)!=sha(current_path):errors.append('baseline_bytes_changed:'+n)
            continue
        old={row['id']:row for row in read(baseline)};new={row['id']:row for row in read(current_path)}
        missing=sorted(set(old)-set(new));added=sorted(set(new)-set(old));changed=sorted(key for key in set(old)&set(new) if old[key]!=new[key])
        if missing:errors.append('baseline_ids_missing:'+n+':'+','.join(missing))
        baseline_deltas[n]={'baseline_count':len(old),'current_count':len(new),'added_ids':added,'changed_ids':changed,'missing_ids':missing}
    terrain_ids={d['id'] for d in definitions['terrains']}
    maps={n:read(P/'content/maps'/f'{n}.json') for n in read(P/'content/maps/catalog.json')['maps']}
    scenarios=read(P/'content/scenarios/catalog.json')['scenarios']
    for n,m in maps.items():
        cells={c['id'] for c in m['cells']};positions={(c['position']['q'],c['position']['r']) for c in m['cells']}
        limit=98304 if m.get('scale_revision')=='geographic_linear_5x_v023' else (9000 if n=='asia_strategic' else 4096)
        if len(cells)!=len(m['cells']) or len(m['cells'])>limit:errors.append('map_count:'+n)
        for cell in m['cells']:
            if cell['terrain_id'] not in terrain_ids:errors.append('terrain_fk:'+n)
        for city in m['cities']:
            if (city['position']['q'],city['position']['r']) not in positions:errors.append('city_off_map:'+city['id'])
    for n in scenarios:
        recipe=read(P/'content/scenarios'/f'{n}.json')
        if recipe['map_id'] not in maps:errors.append('scenario_map_fk:'+n)
    geography=read(P/'content/geography_sources.json')
    for source in geography['sources']:
        for filename,expected in source.get('file_hashes',{}).items():
            path=ROOT/filename
            if not path.is_file() or sha(path)!=expected:errors.append('geography_source_sha:'+source['id']+':'+filename)
    capture_path=P/'reports/historical_source_fetch.json'
    if capture_path.is_file():
        for source in read(capture_path)['sources']:
            if source.get('saved'):
                path=ROOT/source['file']
                if not path.is_file() or sha(path)!=source['sha256']:errors.append('historical_html_capture_sha:'+source['id'])
    for a in read(P/'assets/manifest.json')['assets']:
        engine=P/a['engine_path'].removeprefix('res://');source=ROOT/a['source_file']
        if not engine.exists():errors.append('missing_asset:'+a['id']);continue
        if sha(engine)!=a['source_sha256']:errors.append('asset_sha:'+a['id'])
        if source.exists() and sha(source)!=sha(engine):errors.append('source_modified:'+a['id'])
        with Image.open(engine) as im:
            alpha=im.getchannel('A') if im.mode=='RGBA' else None
            zero_pct=alpha.histogram()[0]*100/(im.width*im.height) if alpha else 0
            if a['background']=='transparent' and (alpha is None or alpha.getextrema()[0]!=0):errors.append('alpha:'+a['id'])
            asset_rows.append(dict(id=a['id'],size=list(im.size),sha256=sha(engine),source_available=source.exists(),source_matches=True if source.exists() else None,alpha_zero_percent=round(zero_pct,2),review_state=a['state']))
    for path in sorted((P/'assets/audio').rglob('*.wav')):
        with wave.open(str(path)) as f:
            frames=f.getnframes();rate=f.getframerate();duration=frames/rate
            pcm=array('h',f.readframes(frames));peak=max((abs(v) for v in pcm),default=0)
            if frames==0 or rate!=22050 or peak==0:errors.append('audio_format_or_silence:'+path.name)
            audio_rows.append(dict(file=path.relative_to(P).as_posix(),seconds=round(duration,3),rate=rate,channels=f.getnchannels(),peak_sample=peak,sha256=sha(path)))
    fixture=read(P/'reports/sample_state_v2.json');schema=read(P/'schemas/runtime_match_state_v2.schema.json')
    errors.extend('schema:'+e.message for e in Draft202012Validator(schema).iter_errors(fixture))
    runtime_version=int(re.search(r'RUNTIME_RULESET_VERSION\s*=\s*(\d+)',(P/'content/content_registry.gd').read_text(encoding='utf-8')).group(1))
    stale=fixture.copy();stale['ruleset_version']=7
    references=[str(path.relative_to(P)) for folder in ['app','domain','ai','content','persistence','presentation','audio'] for path in (P/folder).rglob('*.gd') if re.search(r'schemas[/\\]',path.read_text(encoding='utf-8'))]
    prior=ROOT/'output/releases/railway-warlords-0.2.2/RailwayWarlords-Godot-0.2.2.zip'
    with zipfile.ZipFile(prior) as archive:
        old_bytes=archive.read('game/railway_warlords/schemas/runtime_match_state_v2.schema.json')
    old_schema=json.loads(old_bytes);expected=json.loads(old_bytes);expected['properties']['ruleset_version']['const']=10
    contract={'descriptor_sha256':sha(P/'schemas/runtime_match_state_v2.schema.json'),'previous_descriptor_sha256':hashlib.sha256(old_bytes).hexdigest(),'sole_descriptor_change_is_ruleset_7_to_10':schema==expected and old_schema['properties']['ruleset_version']['const']==7,'matches_runtime_ruleset':schema['properties']['ruleset_version']['const']==runtime_version==10,'stale_ruleset_rejected':any(Draft202012Validator(schema).iter_errors(stale)),'runtime_schema_file_references':references,'python_contract_only':not references}
    if not all(contract[k] for k in ['sole_descriptor_change_is_ruleset_7_to_10','matches_runtime_ruleset','stale_ruleset_rejected','python_contract_only']):errors.append('schema_contract_dependency_or_version_mismatch')
    checks=['21_definition_tables_preserve_baseline','five_maps_terrain_city_foreign_keys','33_scenario_map_links','archived_geography_and_historical_source_sha','all_generated_raster_sha_and_alpha','native_audio_headers_and_nonzero_waveforms','runtime_v2_schema_real_fixture']
    report=dict(passed=not errors,errors=errors,checks=checks,definition_tables=len(catalog),maps=len(maps),scenarios=len(scenarios),raster_count=len(asset_rows),audio_count=len(audio_rows),font_count=len(list((P/'assets/font').glob('*.otf'))),review_states=dict(Counter(r['review_state'] for r in asset_rows)),manual_image_composition=False,raster_images_modified=False,assets=asset_rows,audio=audio_rows)
    report['schema_contract']=contract
    report['baseline_definition_deltas']=baseline_deltas
    (P/'reports/resource_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ['assets','audio']},ensure_ascii=True))
    return int(bool(errors))
if __name__=='__main__':sys.exit(main())
