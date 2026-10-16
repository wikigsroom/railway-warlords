"""Fivefold geographic board scale, native Python only; never edits game images."""
from pathlib import Path
import argparse, concurrent.futures, hashlib, io, json, math, sys, time, urllib.request

P=Path(__file__).resolve().parents[1]; ROOT=P.parents[1]
sys.path.insert(0,str(ROOT/'.toolchain/python-libs'))
import numpy as np
from PIL import Image
import compile_maps as compiler

WORK=ROOT/'output/map-scale-v023'
DEM=ROOT/'design/geodata/terrain_tiles'
SAMPLES=DEM/'scaled_samples.json'
SPECS=[('jingjin',(114.8,38.4,118.35,40.35),1000,9),
       ('jingfeng',(115.7,38.7,122.0,41.5),1000,9),
       ('conquest_china',(102.0,21.0,127.0,43.0),5400,8)]
BASE_URL='https://s3.amazonaws.com/elevation-tiles-prod/geotiff'
SOURCE_ID='Tilezen_TerrainTiles_geotiff'

def read(path):return json.loads(path.read_text(encoding='utf-8'))
def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def prepare():
    baseline_path=WORK/'baseline_v022.json'
    if not baseline_path.exists():
        records=[]
        for mid,_,_,_ in SPECS:
            path=P/'content/maps'/f'{mid}.json';m=read(path)
            if m.get('scale_revision'):raise RuntimeError('Missing preserved original scale baseline')
            records.append({k:m[k] for k in ['id','projection','geographic_bounds','hex_radius_m','hex_radius_px','cities']}|
                           {'cells':len(m['cells']),'source_sha256':sha(path)})
        write(baseline_path,{'version':'0.2.2','maps':records})
    for mid,bounds,radius,_ in SPECS:
        output=WORK/'pre_elevation'/f'{mid}.json'
        if output.exists():continue
        output.parent.mkdir(parents=True,exist_ok=True)
        print('Compiling surveyed grid:',mid,flush=True)
        compiler.compile_map(mid,bounds,radius,output_path=output,max_cells=98304,
                             land_source='ne_10m_land',elevation_samples={})
        print('Grid ready:',mid,len(read(output)['cells']),flush=True)

def tile_for(lat,lon,z):
    n=2**z
    return z,min(n-1,max(0,int((lon+180)/360*n))),min(n-1,max(0,int((1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2*n)))

def download(tile):
    z,x,y=tile;path=DEM/f'{z}_{x}_{y}.tif';url=f'{BASE_URL}/{z}/{x}/{y}.tif'
    for attempt in range(3):
        try:
            if not path.exists():
                raw=urllib.request.urlopen(url,timeout=25).read()
                with Image.open(io.BytesIO(raw)) as im:
                    if im.size!=(512,512) or im.tag_v2.get(33550) is None:raise ValueError('Invalid DEM tile')
                    im.load()
                path.write_bytes(raw)
            with Image.open(path) as im:
                im.load()
                if im.size!=(512,512):raise ValueError('Invalid cached DEM tile')
                resolution=list(im.tag_v2[33550])[:2]
            return {'id':f'{z}_{x}_{y}','url':url,'file':path.relative_to(ROOT).as_posix(),
                    'sha256':sha(path),'bytes':path.stat().st_size,'projected_pixel_size_m':resolution}
        except Exception:
            if attempt==2:raise
            time.sleep(1+attempt)

def sample():
    DEM.mkdir(parents=True,exist_ok=True)
    points={}
    for mid,_,radius,z in SPECS:
        m=read(WORK/'pre_elevation'/f'{mid}.json')
        for c in m['cells']:
            if c['terrain_id']=='sea' or c['region_id']=='restricted':continue
            lat=c['lat_e6']/1e6;lon=c['lon_e6']/1e6;delta=radius*.5/111320
            delta_lon=delta/math.cos(math.radians(lat))
            for a,b in [(lat,lon),(lat+delta,lon),(lat-delta,lon),(lat,lon+delta_lon),(lat,lon-delta_lon)]:
                key=f'{a:.6f},{b:.6f}'
                if key not in points or z>points[key][2]:points[key]=(round(a,6),round(b,6),z)
    groups={}
    for key,(lat,lon,z) in points.items():groups.setdefault(tile_for(lat,lon,z),[]).append((key,lat,lon))
    print('DEM points / tiles:',len(points),len(groups),flush=True)
    tiles=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        tasks={pool.submit(download,tile):tile for tile in sorted(groups)}
        for index,future in enumerate(concurrent.futures.as_completed(tasks),1):
            tiles.append(future.result())
            if index%20==0 or index==len(tasks):print('DEM cached:',index,'/',len(tasks),flush=True)
    values={};nodata=0;registration=[]
    for tile,records in sorted(groups.items()):
        z,x,y=tile;path=DEM/f'{z}_{x}_{y}.tif'
        with Image.open(path) as im:
            grid=np.asarray(im).astype(np.float64)
            scale=im.tag_v2[33550];tie=im.tag_v2[33922];keys=im.tag_v2[34735]
            key_values={keys[i]:keys[i+3] for i in range(4,len(keys),4)}
            if key_values.get(3072)!=3857:raise ValueError('Unexpected DEM projection')
            point_pixels=key_values.get(1025)==2
            offset=0 if point_pixels else .5
            nodata_value=float(im.tag_v2.get(42113,'-32768'))
        lats=np.array([v[1] for v in records]);lons=np.array([v[2] for v in records])
        mx=np.radians(lons)*6378137;my=np.log(np.tan(np.pi/4+np.radians(lats)/2))*6378137
        px=np.clip((mx-tie[3])/scale[0]+tie[0]-offset,0,511)
        py=np.clip((tie[4]-my)/scale[1]+tie[1]-offset,0,511)
        x0=np.floor(px).astype(int);y0=np.floor(py).astype(int);x1=np.minimum(x0+1,511);y1=np.minimum(y0+1,511)
        fx=px-x0;fy=py-y0
        total=np.zeros(len(records));weight=np.zeros(len(records))
        for xx,yy,w in [(x0,y0,(1-fx)*(1-fy)),(x1,y0,fx*(1-fy)),(x0,y1,(1-fx)*fy),(x1,y1,fx*fy)]:
            h=grid[yy,xx];valid=(h!=nodata_value)&np.isfinite(h)
            total+=np.where(valid,h*w,0);weight+=np.where(valid,w,0)
        for i,record in enumerate(records):
            value=round(float(total[i]/weight[i]),3) if weight[i]>0 else None
            values[record[0]]=value;nodata+=value is None
        registration.append({'tile':f'{z}_{x}_{y}','point_pixels':point_pixels,'sample_count':len(records)})
    tiles.sort(key=lambda v:v['id'])
    write(SAMPLES,{'dataset':SOURCE_ID,'source_url':'https://registry.opendata.aws/terrain-tiles/',
                   'sampling':'GeoTIFF registered pixel coordinates; bilinear interpolation; tile-edge clamping; declared no-data kept null',
                   'points':len(values),'nodata_points':nodata,'tiles':tiles,'samples':values})
    write(WORK/'dem_sampling.json',{'passed':len(values)==len(points),'points':len(values),'nodata_points':nodata,
                                  'tiles':tiles,'registrations':registration,'sample_cache_sha256':sha(SAMPLES)})
    print('DEM sampled:',len(values),'points; no-data:',nodata,flush=True)

def compile_final():
    data=read(SAMPLES);samples=data['samples'];baseline_path=WORK/'baseline_v022.json'
    if not baseline_path.exists():baseline_path=P/'tests/fixtures/map_scale_baseline_v022.json'
    baseline=read(baseline_path);rows=[]
    for mid,bounds,radius,z in SPECS:
        print('Building final fivefold map:',mid,flush=True)
        compiler.compile_map(mid,bounds,radius,max_cells=98304,land_source='ne_10m_land',
                             elevation_samples=samples,elevation_source=SOURCE_ID)
        path=P/'content/maps'/f'{mid}.json';m=read(path);old=next(v for v in baseline['maps'] if v['id']==mid)
        m.update(scale_revision='geographic_linear_5x_v023',scale_baseline_version='0.2.2',
                 geographic_linear_scale=old['hex_radius_m']/radius,
                 physical_grid_source='natural_earth_land_10m_v5_1_1',elevation_detail_zoom=z)
        for cell in m['cells']:
            lon=cell['lon_e6']/1e6;lat=cell['lat_e6']/1e6
            inside=bounds[0]<=lon<=bounds[2] and bounds[1]<=lat<=bounds[3]
            cell['render_land_covered']=inside and cell['natural_terrain_id']!='sea'
            if not inside:cell['region_id']='restricted'
        m['sources']=[v for v in m['sources'] if v not in ['natural_earth_land_50m','SRTM90m_v3']]+['natural_earth_land_10m_v5_1_1',SOURCE_ID]
        m['terrain_classification']['method']='Real Terrain Tiles DEM at declared zoom; center and four cardinal half-radius samples. No-data stays null.'
        errors=[]
        for c in m['cities']:
            before=next(v for v in old['cities'] if v['id']==c['id'])
            if any(c[k]!=before[k] for k in ['lon_e6','lat_e6','name','reference_owner']):errors.append('Historical city changed: '+c['id'])
            error=max(abs(c['render_position'][i]-before['render_position'][i]*5) for i in [0,1])
            if error>.04:errors.append('City scale mismatch: '+c['id'])
        if errors:raise ValueError(errors)
        write(path,m)
        rows.append({'id':mid,'old_radius_m':old['hex_radius_m'],'new_radius_m':radius,'hex_radius_px':m['hex_radius_px'],
                     'linear_scale':m['geographic_linear_scale'],'old_cells':old['cells'],'new_cells':len(m['cells']),
                     'geographic_bounds_unchanged':list(bounds)==old['geographic_bounds'],'historical_city_data_unchanged':not errors})
    source={'id':SOURCE_ID,'title':'Terrain Tiles: Mapzen / Tilezen GeoTIFF digital elevation model',
            'url':'https://registry.opendata.aws/terrain-tiles/','attribution_url':'https://github.com/tilezen/joerd/blob/master/docs/attribution.md',
            'license':'USGS SRTM / GMTED2010 public-domain global elevation sources; retain provider attribution.',
            'attribution':'Elevation: Mapzen / Tilezen. Underlying global datasets: USGS SRTM and GMTED2010; NOAA ETOPO1.',
            'use':'Physical relief samples, not period forest, farmland, buildings or historical military deployments.',
            'access_date':'2026-10-11','files':[SAMPLES.relative_to(ROOT).as_posix()],
            'file_hashes':{SAMPLES.relative_to(ROOT).as_posix():sha(SAMPLES)},'raw_tile_manifest':(DEM/'scaled_samples.json').relative_to(ROOT).as_posix(),
            'nodata_points':data['nodata_points']}
    path=P/'content/geography_sources.json';geo=read(path)
    geo['sources']=[v for v in geo['sources'] if v['id']!=SOURCE_ID]+[source];write(path,geo)
    write(P/'reports/map_scale_v023.json',{'passed':all(v['linear_scale']>=5 and v['hex_radius_px']==48 for v in rows),
           'basis':'Width and height each fivefold at the same camera zoom; gameplay hex radius remains 48 pixels.',
           'maps':rows,'dem_sample_sha256':sha(SAMPLES),'baseline_sha256':sha(baseline_path)})
    print('Final map scale:',rows,flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=['prepare','sample','compile'])
    stage=parser.parse_args().stage
    {'prepare':prepare,'sample':sample,'compile':compile_final}[stage]()
