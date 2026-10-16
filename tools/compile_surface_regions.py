"""Compile geographical material references without modifying rule geography.

RESOLVE's potential biogeographic regions are a ground-art reference, not a
dated land-use/soil/wetland survey. They never add water, woodland, cities or
movement rules. Exact point membership and source IDs remain auditable.
"""
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import sys
import time

P=Path(__file__).resolve().parents[1];ROOT=P.parents[1]
sys.path.insert(0,str(ROOT/'.toolchain/python-libs'))
import numpy as np
import shapefile
import shapely
from shapely.geometry import box, shape
from shapely.strtree import STRtree

SOURCE=ROOT/'design/geodata/surface_detail_sources/Ecoregions2017/Ecoregions2017.shp'
OUTPUT=P/'presentation/data/surface_regions.json'
SAND={810,838,843}  # Explicit sandy regions, never the entire desert biome.
GRAVEL={808,824,825,826,835}  # Mixed stony/steppe ground, representative grain.
ALLUVIAL={238,287,657,667,673,684,818}
WET_SOIL={312,741,742,743,746,747,748}
LEGEND={
    'meadow':'温和草土底材（未确定历史土地利用）',
    'dry_grass':'草原／山地草甸区域底材',
    'sandy_ground':'沙质荒漠区域底材',
    'arid_gravel':'砾质荒漠／荒漠草原区域底材',
    'alluvial_soil':'低起伏平原／河谷土质底材',
    'wetland_ground':'盐生草甸／洪泛生态区湿土底材（非历史沼泽边界）',
}


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def load_regions():
    rows=[];geometries=[]
    reader=shapefile.Reader(str(SOURCE),encoding='cp1252')
    region=box(20,-10,180,80)
    for item in reader.iterShapeRecords():
        attrs=item.record.as_dict()
        if not box(*item.shape.bbox).intersects(region):continue
        eco=int(attrs['ECO_ID']);biome=int(attrs['BIOME_NUM'])
        mineral_desert=biome==13 and 'desert' in attrs['ECO_NAME'].lower()
        if eco not in SAND|GRAVEL|ALLUVIAL|WET_SOIL and biome not in [8,10] and not mineral_desert:continue
        geometry=shapely.make_valid(shape(item.shape.__geo_interface__))
        if not geometry.intersects(region):continue
        if attrs['LICENSE']!='CC-BY 4.0':raise RuntimeError('Unexpected geographic data license')
        rows.append(dict(id=eco,name=attrs['ECO_NAME'],biome=biome,license=attrs['LICENSE']))
        geometries.append(geometry)
    return rows,geometries,STRtree(geometries)


def family_for(region, cell):
    eco=region['id'];biome=region['biome']
    if eco in SAND:return 'sandy_ground'
    if eco in GRAVEL:return 'arid_gravel'
    if eco in WET_SOIL:
        # A regional ground-material reference is not a water polygon or a
        # historically verified marsh. Do not change terrain_id or add reeds.
        return 'wetland_ground'
    if eco in ALLUVIAL:
        elevation=cell.get('elevation_m');relief=cell.get('relief_sample_m')
        # Tarim/Central Asian river valleys can lie above 250 m. Continental
        # relief covers 100 km; tactical relief covers roughly one hex. Apply
        # the correct support, rather than comparing unlike sample distances.
        coarse='nine_point_100km' in cell.get('terrain_source','')
        elevation_ok=eco in [684,818] or elevation is None or elevation<=250
        if elevation_ok and (relief is None or relief<(400 if coarse else 56)):
            return 'alluvial_soil'
    if biome in [8,10]:return 'dry_grass'
    if biome==13 and 'desert' in region['name'].lower():return 'arid_gravel'
    return ''


def compile_map(data, regions, tree):
    cells=[cell for cell in data['cells'] if cell.get('render_land_covered',True)
           and cell['terrain_id'] not in ['sea','river','road','city','port','ford']
           and cell.get('natural_terrain_id',cell['terrain_id'])=='plain']
    positions=shapely.points(np.array([[cell['lon_e6']/1e6,cell['lat_e6']/1e6] for cell in cells]))
    pairs=tree.query(positions,predicate='covered_by')
    result={};counts=Counter()
    for point_index,region_index in pairs.T:
        cell=cells[int(point_index)];region=regions[int(region_index)]
        family=family_for(region,cell)
        if not family:continue
        row=[family,region['id']]
        if cell['id'] in result and result[cell['id']]!=row:
            raise RuntimeError('Ambiguous overlapping source regions: '+cell['id'])
        result[cell['id']]=row;counts[family]+=1
    return result,dict(counts)


def main():
    started=time.monotonic();regions,_,tree=load_regions();maps={};counts={};hashes={}
    for path in sorted((P/'content/maps').glob('*.json')):
        if path.name=='catalog.json':continue
        hashes[path.name]=sha(path);data=json.loads(path.read_text(encoding='utf-8'))
        maps[data['id']],counts[data['id']]=compile_map(data,regions,tree)
        print(json.dumps(dict(map=data['id'],assignments=len(maps[data['id']]),families=counts[data['id']])),flush=True)
        if hashes[path.name]!=sha(path):raise RuntimeError('Rule map changed during compile')
    original_files={suffix:sha(SOURCE.with_suffix(suffix)) for suffix in ['.shp','.shx','.dbf','.prj']}
    result=dict(format=1,source_id='resolve_ecoregions_2017',source_year=2017,
        source_url='https://ecoregions.world/',source_files_sha256=original_files,
        source_archive_sha256=sha(SOURCE.parent.parent/'Ecoregions2017.zip'),
        license='CC-BY 4.0',attribution='Dinerstein et al. (2017), RESOLVE Ecoregions 2017, https://doi.org/10.1093/biosci/bix014',
        scope='Potential biogeographic region used as a representative ground-material reference only; not dated land use, exact soil, actual forest or historical wetland extent',
        material_legend=LEGEND,ecoregions={str(row['id']):row for row in regions},maps=maps,
        authored_rule_maps_modified=False,water_polygons_added=False,forest_boundaries_added=False,
        historical_wetland_extent_claimed=False)
    OUTPUT.write_text(json.dumps(result,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    report=dict(passed=True,created_at_utc=datetime.now(timezone.utc).isoformat(),
        source_id=result['source_id'],source_files_sha256=original_files,
        output_sha256=sha(OUTPUT),rule_map_hashes=hashes,assignments_by_map=counts,
        elapsed_seconds=round(time.monotonic()-started,2),random_geography=False,
        source_files_modified=False,rule_maps_modified=False,historical_landuse_survey_claimed=False)
    (P/'reports/surface_geography_compilation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':main()
