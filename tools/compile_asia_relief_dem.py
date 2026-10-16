"""Replace rectangular Asian relief guesses with archived physical DEM samples.

Downloads original GeoTIFF scientific data, never game-art rasters. City/rail,
political, coast, river geometry, hex positions and date content are preserved.
The old map is sealed separately before any change. Terrain rules intentionally
follow the corrected physical classification; the content fingerprint changes.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter
from copy import deepcopy
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json
import math
import sys

P=Path(__file__).resolve().parents[1];ROOT=P.parents[1]
sys.path.insert(0,str(ROOT/'.toolchain/python-libs'))
import numpy as np
from PIL import Image
import enlarge_maps as terrain

SOURCE=ROOT/'design/geodata/asia_relief_dem'
PATH=P/'content/maps/asia_strategic.json'
BASELINE=SOURCE/'asia_strategic_before_dem.json'
SAMPLES=SOURCE/'samples_v1.json'
ZOOM=4


def read(path):return json.loads(path.read_text(encoding='utf-8'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path,value):path.write_text(json.dumps(value,ensure_ascii=False,separators=(',',':')),encoding='utf-8')


def sample(data):
    requests={};cell_keys={}
    for cell in data['cells']:
        if cell.get('natural_terrain_id',cell['terrain_id'])=='sea':continue
        lat=cell['lat_e6']/1e6;lon=cell['lon_e6']/1e6
        # Nine points over a physical 100 km square within a coarse strategic
        # cell. This measures broad terrain, not 1 km local slope or land use.
        keys=[]
        for dy in [-50000,0,50000]:
            for dx in [-50000,0,50000]:
                y=lat+dy/111320;x=lon+dx/(111320*math.cos(math.radians(lat)))
                x=min(179.999999,max(-179.999999,x));y=min(84.9,max(-84.9,y))
                key=f'{y:.6f},{x:.6f}';keys.append(key);requests[key]=(y,x)
        cell_keys[cell['id']]=keys
    groups={}
    for key,(lat,lon) in requests.items():
        groups.setdefault(terrain.tile_for(lat,lon,ZOOM),[]).append((key,lat,lon))
    records=[]
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures={pool.submit(terrain.download,tile):tile for tile in groups}
        for future in as_completed(futures):
            records.append(future.result())
            print(f'Original continental DEM tiles {len(records)}/{len(groups)}',flush=True)
    values={};nodata=0
    for tile,points in groups.items():
        with Image.open(terrain.DEM/('%d_%d_%d.tif'%tile)) as im:
            grid=np.asarray(im).astype(float);scale=im.tag_v2[33550];tie=im.tag_v2[33922];keys=im.tag_v2[34735]
            tags={keys[index]:keys[index+3] for index in range(4,len(keys),4)}
            if tags.get(3072)!=3857:raise RuntimeError('Unexpected original DEM projection')
            offset=0 if tags.get(1025)==2 else .5
            missing=float(im.tag_v2.get(42113,'-32768'))
        lats=np.array([row[1] for row in points]);lons=np.array([row[2] for row in points])
        mx=np.radians(lons)*6378137;my=np.log(np.tan(np.pi/4+np.radians(lats)/2))*6378137
        px=np.clip((mx-tie[3])/scale[0]+tie[0]-offset,0,511)
        py=np.clip((tie[4]-my)/scale[1]+tie[1]-offset,0,511)
        x0=np.floor(px).astype(int);y0=np.floor(py).astype(int);x1=np.minimum(x0+1,511);y1=np.minimum(y0+1,511)
        fx=px-x0;fy=py-y0;total=np.zeros(len(points));weight=np.zeros(len(points))
        for xx,yy,w in [(x0,y0,(1-fx)*(1-fy)),(x1,y0,fx*(1-fy)),(x0,y1,(1-fx)*fy),(x1,y1,fx*fy)]:
            h=grid[yy,xx];valid=(h!=missing)&np.isfinite(h)
            total+=np.where(valid,h*w,0);weight+=np.where(valid,w,0)
        for index,row in enumerate(points):
            value=round(float(total[index]/weight[index]),3) if weight[index]>0 else None
            values[row[0]]=value;nodata+=value is None
    if nodata:raise RuntimeError('Continental DEM has missing samples; do not replace them with guesses')
    return dict(format=1,source_id='Tilezen_TerrainTiles_geotiff',zoom=ZOOM,
        sampling='Registered EPSG:3857 GeoTIFF, bilinear interpolation, point/area registration respected; nine points over a 100 km square centered at each strategic cell',
        horizontal_support_km=100,source_points=len(values),nodata_points=nodata,
        tiles=sorted(records,key=lambda row:row['id']),values=values,cell_keys=cell_keys)


def apply_samples(baseline,samples):
    result=deepcopy(baseline);changed=[];counts=Counter()
    protected={'sea','river','city','port','ford','road'}
    for cell in result['cells']:
        if cell['id'] not in samples['cell_keys']:
            if cell.get('natural_terrain_id',cell['terrain_id'])!='sea':
                raise RuntimeError('No archived physical relief samples for land cell '+cell['id'])
            continue
        heights=[samples['values'][key] for key in samples['cell_keys'][cell['id']]]
        elevation=round(heights[4]);relief=round(max(heights)-min(heights))
        kind='peak' if relief>=2800 and elevation>=2000 else 'mountain' if relief>=1200 else 'hill' if relief>=400 else 'plain'
        previous=cell['natural_terrain_id']
        # Water and existing route/site features retain their authored rule
        # role. Only the underlying physical land class is corrected.
        if previous not in ['sea','river','ford','port']:
            cell['natural_terrain_id']=kind
            if cell['terrain_id'] not in protected:cell['terrain_id']=kind
        cell['elevation_m']=elevation;cell['relief_sample_m']=relief
        cell['terrain_source']='Tilezen_TerrainTiles_geotiff_nine_point_100km'
        counts[cell['natural_terrain_id']]+=1
        if previous!=cell['natural_terrain_id']:changed.append(dict(id=cell['id'],old=previous,new=cell['natural_terrain_id']))
    result['terrain_classification']={**result.get('terrain_classification',{}),**dict(method=samples['sampling'],source_id=samples['source_id'],
        source_zoom=ZOOM,sample_cache_sha256=sha(SAMPLES),
        plain_relief_below_m=400,hill_relief_from_m=400,mountain_relief_from_m=1200,
        peak_relief_from_m=2800,peak_center_elevation_from_m=2000,
        precision='Broad physical relief at continental control-cell scale; not tactical local slope or period land use')}
    result['physical_relief_source']='Tilezen_TerrainTiles_geotiff_nine_point_100km'
    result['sources']=list(dict.fromkeys(result.get('sources',[])+['asia_relief_dem_v1']))
    result['geography_status']='real_natural_earth_geometry_and_archived_physical_dem_continental_relief'
    allowed={'terrain_id','natural_terrain_id','elevation_m','relief_sample_m','terrain_source'}
    for old,new in zip(baseline['cells'],result['cells']):
        if {k:v for k,v in old.items() if k not in allowed}!={k:v for k,v in new.items() if k not in allowed}:
            raise RuntimeError('Non-relief cell field changed')
    for key in baseline:
        if key not in ['cells','terrain_classification','physical_relief_source','sources','geography_status'] and baseline[key]!=result[key]:
            raise RuntimeError('Non-relief geography changed: '+key)
    return result,changed,counts


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--sample-only',action='store_true')
    args=parser.parse_args();SOURCE.mkdir(parents=True,exist_ok=True)
    if not BASELINE.exists():BASELINE.write_bytes(PATH.read_bytes())
    baseline=read(BASELINE)
    samples=read(SAMPLES) if SAMPLES.exists() else sample(baseline)
    if not SAMPLES.exists():write(SAMPLES,samples)
    if args.sample_only:return
    result,changed,counts=apply_samples(baseline,samples)
    write(PATH,result)
    source_path=P/'content/geography_sources.json';registry=read(source_path)
    record=dict(id='asia_relief_dem_v1',title='Asian continental relief: archived Terrain Tiles GeoTIFF samples',
        url='https://registry.opendata.aws/terrain-tiles/',
        attribution_url='https://github.com/tilezen/joerd/blob/master/docs/attribution.md',
        license='USGS SRTM / GMTED2010 and NOAA ETOPO1 public elevation data; retain provider attribution',
        attribution='Elevation: Mapzen / Tilezen. Underlying global sources: USGS SRTM, GMTED2010 and NOAA ETOPO1.',
        use='Physical continental relief sampled at nine points over a 100 km square; not historical land use, forest cover or military deployment',
        files=[SAMPLES.relative_to(ROOT).as_posix()],
        file_hashes={SAMPLES.relative_to(ROOT).as_posix():sha(SAMPLES)},
        raw_tile_manifest=SAMPLES.relative_to(ROOT).as_posix(),access_date='2026-10-16',nodata_points=0)
    registry['sources']=[row for row in registry['sources'] if row['id']!='asia_relief_dem_v1']+[record]
    write(source_path,registry)
    report=dict(passed=True,created_at_utc=datetime.now(timezone.utc).isoformat(),
        original_map_sha256=sha(BASELINE),corrected_map_sha256=sha(PATH),sample_cache_sha256=sha(SAMPLES),
        original_baseline=BASELINE.relative_to(ROOT).as_posix(),changed_terrain_cells=len(changed),changes=changed,
        natural_land_class_counts=dict(counts),source_tiles=len(samples['tiles']),source_points=samples['source_points'],
        city_coordinates_unchanged=True,water_geometry_unchanged=True,rail_and_political_fields_unchanged=True,
        hex_grid_unchanged=True,coarse_rectangle_relief_removed=True,
        content_fingerprint_changes_intentionally=True,original_dem_bytes_modified=False)
    (P/'reports/asia_relief_dem_revision.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='changes'}),flush=True)


if __name__=='__main__':main()
