"""Audit independent Sub2 source bytes, actual dimensions and engine copies."""
from collections import Counter
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
from PIL import Image
from map_bank_inventory import ADDITIONAL_COUNT, CATEGORY_COUNTS, planned_rows, production_rows

P=Path(__file__).resolve().parents[1];ROOT=P.parents[1]


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):return json.loads(path.read_text(encoding='utf-8'))


def main():
    checks=[]
    def check(name,passed,**extra):checks.append(dict(name=name,passed=bool(passed),**extra))
    baseline=read(P/'reports/map_bank_baseline.json');production=read(P/'reports/map_bank_generation.json')
    plan=planned_rows();installed=read(P/'assets/manifest.json')['assets']
    extension_production=read(P/'reports/map_settlement_extension_generation.json')
    _, all_complete=production_rows()
    visuals=read(P/'presentation/data/map_bank_visuals.json');bank=[r for r in installed if '_bank_' in r['id']]
    check('source_production_complete',production['passed'] and not production['running'] and production['completed']==666 and not production['failures'])
    check('settlement_extension_complete',extension_production['passed'] and not extension_production['running'] and extension_production['completed']==74 and not extension_production['failures'])
    check('all_three_original_production_catalogs_complete',all_complete)
    check('immutable_74_item_baseline',baseline['count']==74 and len(baseline['assets'])==74)
    check('all_plan_ids_installed',{r['id'] for r in bank}=={r['id'] for r in plan}==set(visuals['records']))
    check('at_least_ten_times_baseline_map_assets',sum(r['category'] in ['tile','scenery','building'] for r in installed)>=baseline['count']*10)
    check('independent_additional_source_hashes',len({r['source_sha256'] for r in bank})==ADDITIONAL_COUNT)
    check('category_counts',Counter(r['category'] for r in bank)==CATEGORY_COUNTS)
    check('current_chinese_campaign_village_diversity',len(visuals['families']['village_north_china'])==26 and len(visuals['families']['village_south_china'])==10)
    check('all_runtime_families_addressable',set(visuals['records'])=={aid for ids in visuals['families'].values() for aid in ids})
    for row in bank:
        source=ROOT/row['source_file'];engine=P/row['engine_path'].removeprefix('res://');prompt=ROOT/row['prompt_file']
        check('provenance:'+row['id'],sha(source)==sha(engine)==row['source_sha256'] and sha(prompt)==row['prompt_sha256'] and not row['image_modified'] and not row['manual_compositing'])
        with Image.open(source) as im:
            actual=list(im.size);alpha=im.getchannel('A') if im.mode=='RGBA' else None
            corners=[alpha.getpixel(p) for p in [(0,0),(im.width-1,0),(0,im.height-1),(im.width-1,im.height-1)]] if alpha else [255]*4
            bounds=list(alpha.point(lambda value:255 if value>16 else 0).getbbox()) if alpha else [0,0,*im.size]
        # Some immutable originals have one alpha quantization step at a
        # corner (1/255). Preserve those bytes; an opaque exterior still fails.
        check('whole_source_metadata:'+row['id'],actual==row['actual_dimensions'] and bounds==row['alpha_bounds'] and (row['category']=='tile' or all(value<=1 for value in corners)),actual_dimensions=actual,maximum_corner_alpha_8bit=max(corners))
        import_file=engine.with_suffix('.png.import')
        text=import_file.read_text(encoding='utf-8') if import_file.exists() else ''
        check('native_import_budget:'+row['id'],f'process/size_limit={row["runtime_import_max_dimension"]}' in text and 'mipmaps/generate=true' in text)
    # Existing sources also remain unchanged; replacements were completed before
    # this baseline, and must not be silently counted as additional originals.
    current={r['id']:r for r in installed}
    for row in baseline['assets']:check('baseline_preserved:'+row['id'],current[row['id']]['source_sha256']==row['source_sha256'])
    result=dict(passed=all(r['passed'] for r in checks),created_at_utc=datetime.now(timezone.utc).isoformat(),
                baseline=74,additional_independent_sources=len(bank),total_map_assets=sum(r['category'] in ['tile','scenery','building'] for r in installed),
                all_runtime_rasters=len(installed),source_route='sub2-image-gen/gpt-image-2.5/high',
                source_pngs_modified=False,exterior_corner_alpha_ceiling_8bit=1,formal_art_approval=False,physical_android_device_tested=False,
                checks=checks,failures=[r['name'] for r in checks if not r['passed']])
    (P/'reports/map_bank_asset_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({key:result[key] for key in ['passed','baseline','additional_independent_sources','total_map_assets','all_runtime_rasters','failures']},ensure_ascii=False))
    raise SystemExit(0 if result['passed'] else 1)


if __name__=='__main__':main()
