"""Cache real SRTM elevation samples using the public API, with its 1 req/s limit."""
from pathlib import Path
import json, math, time, urllib.request, urllib.parse
P=Path(__file__).resolve().parents[1];ROOT=P.parents[1]
OUT=ROOT/'design/geodata/srtm90m';OUT.mkdir(parents=True,exist_ok=True)
CACHE=OUT/'samples.json';API='https://api.opentopodata.org/v1/srtm90m'

def key(lat,lon):return f'{lat:.6f},{lon:.6f}'

def main():
 cache=json.loads(CACHE.read_text(encoding='utf-8')) if CACHE.exists() else {'dataset':'SRTM v3 90m','api':API,'source_url':'https://www.opentopodata.org/datasets/srtm/','samples':{}}
 requested={}
 for path in sorted((P/'content/maps').glob('*.json')):
  m=json.loads(path.read_text(encoding='utf-8'))
  if 'cells' not in m:continue
  for c in m['cells']:
   if c['terrain_id']=='sea' or c['region_id']=='restricted':continue
   lat=c['lat_e6']/1e6;lon=c['lon_e6']/1e6;delta=m['hex_radius_m']*.5/111320
   delta_lon=delta/math.cos(math.radians(lat))
   for y,x in [(lat,lon),(lat+delta,lon),(lat-delta,lon),(lat,lon+delta_lon),(lat,lon-delta_lon)]:requested[key(y,x)]=(y,x)
 missing=[v for k,v in requested.items() if k not in cache['samples']]
 print(f'Elevation points: requested={len(requested)}, uncached={len(missing)}',flush=True)
 for index in range(0,len(missing),100):
  batch=missing[index:index+100];url=API+'?'+urllib.parse.urlencode({'locations':'|'.join(key(*p) for p in batch),'interpolation':'bilinear'})
  for attempt in range(4):
   started=time.monotonic()
   try:
    with urllib.request.urlopen(url,timeout=40) as response:d=json.loads(response.read())
    if d.get('status')!='OK' or len(d.get('results',[]))!=len(batch):raise RuntimeError('unexpected elevation response')
    for (lat,lon),row in zip(batch,d['results']):cache['samples'][key(lat,lon)]=row['elevation']
    break
   except Exception:
    if attempt==3:raise
    time.sleep(3*(attempt+1))
   finally:time.sleep(max(0,1.1-(time.monotonic()-started)))
  CACHE.write_text(json.dumps(cache,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
  print(f'Elevation batch: {min(index+100,len(missing))}/{len(missing)}',flush=True)
 print('Real elevation cache complete.',flush=True)
if __name__=='__main__':main()
