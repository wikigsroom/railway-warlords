"""Bind twenty presentation subtypes to archived ecological/DEM geography.

Exact source polygon membership; surveyed river proximity gates valley silt.
No rule-map, coastline, forest boundary, elevation or land-use data is edited.
"""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
import time
from compile_surface_regions import P, ROOT, SOURCE, sha
from generate_terrain_surfaces import TYPES
import numpy as np
import shapefile
import shapely
from shapely.geometry import box, shape, LineString
from shapely.strtree import STRtree

OUTPUT=P/'presentation/data/terrain_surface_regions.json'
SAND={810,838,843}
DESERT_STEPPE={808,813,824,825,826,827,828,829,834,835,841}
SALINE={312,742,747,748}
ALLUVIAL={238,287,657,667,673,684,818}
MEADOW_STEPPE={726,731,737,738}


def load_regions():
    rows=[];geometries=[];region=box(20,-10,180,80)
    reader=shapefile.Reader(str(SOURCE),encoding='cp1252')
    for item in reader.iterShapeRecords():
        if not box(*item.shape.bbox).intersects(region):continue
        attrs=item.record.as_dict();geometry=shapely.make_valid(shape(item.shape.__geo_interface__))
        if not geometry.intersects(region):continue
        if attrs['LICENSE']!='CC-BY 4.0':raise RuntimeError('Unexpected source license')
        rows.append(dict(id=int(attrs['ECO_ID']),name=attrs['ECO_NAME'],biome=int(attrs['BIOME_NUM']),license=attrs['LICENSE']))
        geometries.append(geometry)
    return rows,STRtree(geometries)


def xy(cell):
    q,r=cell['position']['q'],cell['position']['r']
    return q*72,math.sqrt(3)*48*(r+q*.5)


def river_distances(data,cells):
    lines=[LineString(points) for points in data.get('render_rivers',[]) if len(points)>=2]
    if not lines:return [math.inf]*len(cells)
    tree=STRtree(lines);points=shapely.points(np.array([xy(cell) for cell in cells]))
    indices,distances=tree.query_nearest(points,return_distance=True,all_matches=False)
    values=np.full(len(cells),np.inf);values[indices[0]]=distances
    return values


def family_for(region,cell,river_distance):
    eco=region['id'];biome=region['biome'];name=region['name'].lower()
    terrain=cell.get('natural_terrain_id',cell['terrain_id'])
    # These two mineral treatments are supported by actual DEM-derived relief,
    # but do not imply that we have mapped the rock type or a scree deposit.
    if terrain=='peak':return 'alpine_scree','dem_peak'
    if terrain in ['hill','mountain']:return 'weathered_rock','dem_relief'
    if terrain=='wetland':return 'flood_meadow','authored_wetland_rule'
    # Restrict a river-valley material to BOTH named ecological context and an
    # existing surveyed main river. A low elevation alone is not alluvium.
    if eco in ALLUVIAL:
        coarse='nine_point_100km' in cell.get('terrain_source','')
        elevation=cell.get('elevation_m');relief=cell.get('relief_sample_m')
        elevation_ok=eco in [684,818] or elevation is not None and elevation<=250
        relief_ok=relief is not None and relief<(400 if coarse else 56)
        if elevation_ok and relief_ok and river_distance<=96:
            return 'alluvial_loam','ecoregion_dem_surveyed_river_proximity'
    if eco in SALINE:return 'saline_meadow','named_saline_region'
    if eco in SAND:return 'dune_sand','named_sandy_desert_region'
    if eco in DESERT_STEPPE:return 'desert_steppe','named_desert_steppe_region'
    if biome==13:return 'gravel_gobi','xeric_region_representative_mineral_ground'
    if biome==9:return 'flood_meadow','flooded_grassland_region_not_water_extent'
    if biome==10:
        if 'steppe' in name or 'desert' in name:return 'alpine_steppe','named_alpine_steppe_region'
        return 'alpine_meadow','montane_meadow_region'
    if biome==11 or eco==0:return 'tundra_moss','tundra_region_no_seasonal_snow_claim'
    if biome==6:return 'boreal_litter','boreal_ground_reference_not_tree_cover'
    if biome in [3,5]:return 'conifer_litter','conifer_zone_ground_reference_not_tree_cover'
    if biome==4:
        if cell['lat_e6']<32000000 and cell['lon_e6']>70000000:
            return 'subtropical_humus','subtropical_ground_reference_not_tree_cover'
        return 'temperate_litter','temperate_ground_reference_not_tree_cover'
    if biome in [1,14]:return 'tropical_moist_humus','humid_tropical_ground_reference_no_mangrove_extent_claim'
    if biome in [2,12]:return 'dry_woodland_litter','dry_woodland_ground_reference_not_tree_cover'
    if biome==7:return 'savanna_red_soil','savanna_ground_reference_not_soil_survey'
    if biome==8:
        return ('temperate_meadow' if eco in MEADOW_STEPPE else 'dry_steppe'),'named_temperate_grassland_region'
    return '', ''


def compile_map(data,regions,tree):
    cells=[cell for cell in data['cells'] if cell.get('render_land_covered',True)
        and cell['terrain_id'] not in ['sea','river','road','city','port','ford']]
    if not cells:return {},{}
    points=shapely.points(np.array([[cell['lon_e6']/1e6,cell['lat_e6']/1e6] for cell in cells]))
    pairs=tree.query(points,predicate='covered_by');distances=river_distances(data,cells)
    result={};counts=Counter()
    for point_index,region_index in pairs.T:
        index=int(point_index);cell=cells[index];region=regions[int(region_index)]
        family,gate=family_for(region,cell,float(distances[index]))
        if not family:continue
        row=[family,region['id'],gate]
        if cell['id'] in result and result[cell['id']]!=row:
            raise RuntimeError('Ambiguous geographical membership: '+cell['id'])
        result[cell['id']]=row;counts[family]+=1
    return result,dict(counts)


def main():
    started=time.monotonic();regions,tree=load_regions();maps={};counts={};hashes={};totals=Counter()
    for path in sorted((P/'content/maps').glob('*.json')):
        if path.name=='catalog.json':continue
        before=sha(path);data=json.loads(path.read_text(encoding='utf-8'))
        maps[data['id']],counts[data['id']]=compile_map(data,regions,tree)
        hashes[path.name]=before;totals.update(counts[data['id']])
        if before!=sha(path):raise RuntimeError('Authoritative map changed')
        print(json.dumps(dict(map=data['id'],assignments=len(maps[data['id']]),types=counts[data['id']])),flush=True)
    missing={row[0] for row in TYPES}-set(totals)
    if missing:raise RuntimeError('Registered types without actual map cells: '+','.join(sorted(missing)))
    source_hashes={suffix:sha(SOURCE.with_suffix(suffix)) for suffix in ['.shp','.shx','.dbf','.prj']}
    payload=dict(format=1,version='0.2.13',terrain_type_count=20,
        source_id='resolve_ecoregions_2017_and_archived_map_dem',source_year=2017,
        source_url='https://ecoregions.world/',source_files_sha256=source_hashes,
        attribution='Dinerstein et al. (2017), RESOLVE Ecoregions 2017, https://doi.org/10.1093/biosci/bix014',
        license='CC-BY 4.0',
        scope='Regional representative ground art; not dated historical land use, precise soil, rock lithology, actual tree cover or historical wetland extent',
        river_proximity='Alluvial material requires a named source ecological region, low DEM relief and <=96 world units to an archived map main river. Support follows each map scale, not a cadastral survey.',
        ecoregions={str(row['id']):row for row in regions},maps=maps,
        rule_maps_sha256=hashes,authored_rule_maps_modified=False,
        water_polygons_added=False,forest_boundaries_added=False,historical_landuse_survey=False)
    OUTPUT.write_text(json.dumps(payload,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    report=dict(passed=True,created_at_utc=datetime.now(timezone.utc).isoformat(),
        terrain_type_count=20,types_in_actual_maps=len(totals),assignments_by_map=counts,
        totals_by_type=dict(totals),source_files_sha256=source_hashes,
        output_sha256=sha(OUTPUT),rule_map_hashes=hashes,
        original_maps_modified=False,random_geography=False,historical_landuse_survey_claimed=False,
        elapsed_seconds=round(time.monotonic()-started,2))
    (P/'reports/terrain_surface_geography.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':main()
