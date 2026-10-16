"""Read original geographic polygons and PNGs; never generates raster pixels."""
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import json
import math
import sys

P=Path(__file__).resolve().parents[1];ROOT=P.parents[1]
sys.path.insert(0,str(ROOT/'.toolchain/python-libs'))
import numpy as np
import shapefile
import shapely
from shapely.geometry import shape,LineString
from PIL import Image

def read(path):return json.loads(path.read_text(encoding='utf-8'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--geography-only',action='store_true');args=parser.parse_args()
    checks=[]
    def check(name,ok,**details):checks.append(dict(name=name,passed=bool(ok),**details))
    geo=read(P/'presentation/data/terrain_surface_regions.json')
    plan=read(P/'presentation/data/terrain_surface_plan.json')
    source=ROOT/'design/geodata/surface_detail_sources/Ecoregions2017/Ecoregions2017.shp'
    check('geographic_original_bytes_preserved',all(sha(source.with_suffix(s))==v for s,v in geo['source_files_sha256'].items()))
    check('historical_precision_is_not_overclaimed',not geo['historical_landuse_survey'] and not geo['water_polygons_added'] and not geo['forest_boundaries_added'])
    wanted={int(row[1]) for rows in geo['maps'].values() for row in rows.values()}
    reader=shapefile.Reader(str(source),encoding='cp1252');polygons={};attrs={}
    for index,record in enumerate(reader.iterRecords()):
        row=record.as_dict();eco=int(row['ECO_ID'])
        if eco in wanted:
            attrs[eco]=row;polygons[eco]=shapely.make_valid(shape(reader.shape(index).__geo_interface__))
    totals=Counter();maps={}
    for map_id,records in geo['maps'].items():
        path=P/'content/maps'/f'{map_id}.json';data=read(path);cells={c['id']:c for c in data['cells']}
        grouped={};valid=True;valley_points=[];counts=Counter()
        for cell_id,(family,eco,gate) in records.items():
            cell=cells[cell_id];d=attrs[int(eco)];biome=int(d['BIOME_NUM']);name=d['ECO_NAME'].lower()
            grouped.setdefault(int(eco),[]).append(cell)
            natural=cell.get('natural_terrain_id',cell['terrain_id'])
            valid=valid and cell['terrain_id'] not in ['sea','river','road','city','port','ford']
            if family=='dune_sand':valid=valid and ('sand' in name or 'taklimakan' in name)
            elif family=='alpine_steppe':valid=valid and biome==10 and ('steppe' in name or 'desert' in name)
            elif family=='alpine_meadow':valid=valid and biome==10
            elif family=='saline_meadow':valid=valid and ('saline' in name or 'salt marsh' in name)
            elif family=='gravel_gobi':valid=valid and biome==13
            elif family=='desert_steppe':valid=valid and biome==13
            elif family in ['dry_steppe','temperate_meadow']:valid=valid and biome==8
            elif family=='tundra_moss':valid=valid and (biome==11 or int(eco)==0)
            elif family=='boreal_litter':valid=valid and biome==6
            elif family=='conifer_litter':valid=valid and biome in [3,5]
            elif family=='temperate_litter':valid=valid and biome==4
            elif family=='subtropical_humus':valid=valid and biome==4 and cell['lat_e6']<32000000 and cell['lon_e6']>70000000
            elif family=='tropical_moist_humus':valid=valid and biome in [1,14]
            elif family=='dry_woodland_litter':valid=valid and biome in [2,12]
            elif family=='savanna_red_soil':valid=valid and biome==7
            elif family=='flood_meadow':valid=valid and (biome==9 or natural=='wetland')
            elif family=='weathered_rock':valid=valid and natural in ['hill','mountain']
            elif family=='alpine_scree':valid=valid and natural=='peak'
            elif family=='alluvial_loam':
                valid=valid and any(word in name for word in ['plain','tarim','riparian'])
                coarse='nine_point_100km' in cell.get('terrain_source','')
                valid=valid and cell['relief_sample_m']<(400 if coarse else 56)
                q,r=cell['position']['q'],cell['position']['r'];valley_points.append([q*72,math.sqrt(3)*48*(r+q*.5)])
            else:valid=False
            counts[family]+=1
        membership=True
        for eco,group in grouped.items():
            points=shapely.points(np.array([[c['lon_e6']/1e6,c['lat_e6']/1e6] for c in group]))
            membership=membership and bool(np.all(shapely.covers(polygons[eco],points)))
        check('exact_original_polygon_membership:'+map_id,membership,cells=len(records))
        check('type_semantics_and_protected_features:'+map_id,valid)
        check('authoritative_rule_map_hash_preserved:'+map_id,sha(path)==geo['rule_maps_sha256'][path.name])
        if valley_points:
            lines=[LineString(row) for row in data['render_rivers'] if len(row)>=2]
            points=shapely.points(np.array(valley_points));tree=shapely.STRtree(lines)
            pairs,distances=tree.query_nearest(points,return_distance=True,all_matches=False)
            check('valley_material_is_near_an_existing_surveyed_river:'+map_id,len(distances)==len(valley_points) and np.max(distances)<=96.00001,maximum_world_distance=round(float(np.max(distances)),4))
        totals.update(counts);maps[map_id]=dict(counts)
    check('all_twenty_subtypes_are_present_in_real_maps',len(totals)==20 and set(totals)=={row['id'] for row in plan['types']})
    image_stats=[];old_contrast=[]
    if not args.geography_only:
        catalog=read(P/'presentation/data/terrain_surface_catalog.json')
        manifest={row['id']:row for row in read(P/'assets/manifest.json')['assets']}
        source_hashes=set();fingerprints=set()
        for row in plan['assets']:
            aid=row['id'];installed=manifest[aid];src=ROOT/installed['source_file'];engine=P/installed['engine_path'].removeprefix('res://')
            prompt=ROOT/installed['prompt_file']
            unchanged=sha(src)==sha(engine)==installed['source_sha256']==catalog['records'][aid]['source_sha256']
            check('source_engine_and_prompt_provenance:'+aid,unchanged and sha(prompt)==installed['prompt_sha256'] and prompt.read_text(encoding='utf-8')==row['prompt'])
            with Image.open(src) as image:
                rgb=np.asarray(image.convert('RGB').resize((128,128)),dtype=np.float32)
                alpha=image.getchannel('A').getextrema() if 'A' in image.getbands() else (255,255)
                luma=rgb@np.array([.2126,.7152,.0722]);std=float(luma.std())
                fingerprint=hashlib.sha256(rgb.astype(np.uint8).tobytes()).hexdigest()
                check('opaque_full_material_and_readable_reduced_grain:'+aid,alpha==(255,255) and min(image.size)>=1024 and std>5,contrast_128px=round(std,3))
                image_stats.append(dict(id=aid,type=row['family'],mean_rgb=[round(float(x),2) for x in rgb.mean(axis=(0,1))],luminance_std_128=round(std,3)))
                fingerprints.add(fingerprint);source_hashes.add(sha(src))
            import_path=engine.with_suffix('.png.import')
            text=import_path.read_text(encoding='utf-8') if import_path.exists() else ''
            check('mipmapped_budgeted_native_import:'+aid,'process/size_limit=256' in text and 'mipmaps/generate=true' in text)
        check('eighty_unique_originals_and_reduced_fingerprints',len(source_hashes)==80 and len(fingerprints)==80)
        for row in manifest.values():
            if row.get('family') not in ['meadow','dry_grass','rocky_ground','woodland_floor','wetland_ground','sandy_ground','arid_gravel','alluvial_soil'] or row['id'].startswith('tile_surface_'):continue
            with Image.open(P/row['engine_path'].removeprefix('res://')) as image:
                rgb=np.asarray(image.convert('RGB').resize((128,128)),dtype=np.float32)
                old_contrast.append(float((rgb@np.array([.2126,.7152,.0722])).std()))
    result=dict(passed=all(row['passed'] for row in checks),created_at_utc=datetime.now(timezone.utc).isoformat(),
        checks=checks,failures=[row['name'] for row in checks if not row['passed']],
        scope='Independent raw-polygon membership, type semantics, map immutability'+('' if args.geography_only else ', immutable PNGs, prompt provenance, native imports and reduced-size grain'),
        totals_by_type=dict(totals),assignments_by_map=maps,image_statistics=image_stats,
        old_material_median_luminance_std_128=float(np.median(old_contrast)) if old_contrast else None,
        new_material_median_luminance_std_128=float(np.median([row['luminance_std_128'] for row in image_stats])) if image_stats else None,
        raster_pixels_written=False,originals_modified=False,formal_art_approval=False,ew6_parity_claimed=False)
    output=P/'reports'/('terrain_surface_geography_audit.json' if args.geography_only else 'terrain_surface_asset_audit.json')
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(passed=result['passed'],checks=len(checks),failures=result['failures'])),flush=True)
    raise SystemExit(not result['passed'])


if __name__=='__main__':main()
