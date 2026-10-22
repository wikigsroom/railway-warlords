"""Independent original-tile samples and immutable geometry/rule checks."""
from pathlib import Path
from datetime import datetime, timezone
import base64
import gzip
import hashlib
import json
import math
import random
import subprocess
import sys

P=Path(__file__).resolve().parents[1]; ROOT=P.parents[1]
sys.path.insert(0,str(ROOT/'.toolchain/python-libs'))
import numpy as np
from PIL import Image


def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def original_sample(lon,lat,records,cache):
    mx=math.radians(lon)*6378137
    my=math.log(math.tan(math.pi/4+math.radians(lat)/2))*6378137
    z=4;n=2**z
    tx=min(15,int((lon+180)/360*n))
    ty=int((1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2*n)
    def tile(x,y):
        key=f'{z}_{x}_{y}'
        if key not in cache:
            with Image.open(ROOT/records[key]['file']) as im:
                cache[key]=(np.array(im,dtype=np.int32),im.tag_v2[33550],im.tag_v2[33922])
        return cache[key]
    grid,scale,tie=tile(tx,ty)
    # Individual tile metadata, not the compiler's continental mosaic formula.
    x=(mx-tie[3])/scale[0]+tie[0]
    y=(tie[4]-my)/scale[1]+tie[1]
    x0=math.floor(x);y0=math.floor(y);fx=x-x0;fy=y-y0
    total=0.0;weight=0.0
    for xx,yy,w in [(x0,y0,(1-fx)*(1-fy)),(x0+1,y0,fx*(1-fy)),(x0,y0+1,(1-fx)*fy),(x0+1,y0+1,fx*fy)]:
        ox=math.floor(xx/512);oy=math.floor(yy/512)
        nx=min(15,max(8,tx+ox));ny=min(8,max(1,ty+oy))
        target,_,_=tile(nx,ny)
        cx=min(511,max(0,xx if nx==tx and tx+ox!=nx else xx-ox*512))
        cy=min(511,max(0,yy if ny==ty and ty+oy!=ny else yy-oy*512))
        value=int(target[cy,cx])
        if value!=-32768:total+=value*w;weight+=w
    if weight<=0:raise ValueError('No source sample support')
    return total/weight


def main():
    report_path=P/'reports/geographic_relief_v0236/independent_audit01.json'
    fixture_path=P/'reports/geographic_relief_v0236/source_probes01.json'
    if report_path.exists() or fixture_path.exists():raise FileExistsError('Immutable audit')
    source=P/'presentation/data/asia_presentation_dem.json'
    d=json.loads(source.read_bytes());w,h=d['dimensions']
    raw=gzip.decompress(base64.b64decode(d['data_base64']))
    heights=np.frombuffer(raw,dtype='>i2').reshape(h,w)
    assert hashlib.sha256(raw).hexdigest()==d['payload_sha256']
    records={r['id']:r for r in d['source_tiles']}
    assert all(sha(ROOT/r['file'])==r['sha256'] for r in records.values())
    rng=random.Random(23761022)
    locations={(0,0),(w-1,h-1),(0,h-1),(w-1,0)}
    locations.update((rng.randrange(w),rng.randrange(h)) for _ in range(8192))
    # Exercise original tile seams, including neighbouring-tile interpolation.
    for lon in np.arange(22.5,180.001,22.5):
        x=round((lon-20)/.05)
        for lat in [79,65,45,35,20,0,-9.95]:locations.add((x,round((80-lat)/.05)))
    places={'japan_alps':(137.65,36.25),'osaka_lowland':(135.5,34.65),
            'kanto_plain':(139.65,36.05),'korean_ridges':(128.5,37.8),
            'tibetan_plateau':(88.5,32.5),'himalayan_ridge':(86.9,28.05),
            'indo_gangetic_plain':(84.5,26.0),'sichuan_basin':(104.15,30.7)}
    for lon,lat in places.values():locations.add((round((lon-20)/.05),round((80-lat)/.05)))
    cache={};probes=[];max_error=0.0
    for x,y in sorted(locations):
        lon=20+x*.05;lat=80-y*.05
        expected=original_sample(lon,lat,records,cache)
        actual=int(heights[y,x]);error=abs(actual-expected)
        assert error<=.500001,(lon,lat,actual,expected)
        max_error=max(max_error,error)
        probes.append(dict(node=[x,y],lon=lon,lat=lat,original_bilinear_metres=expected,stored_metres=actual))
    parent='14f82090d521fb658ba3c1eba3304208767f15ef'
    git_names=subprocess.check_output(['git','ls-tree','-r','--name-only',parent],cwd=P,encoding='utf-8').splitlines()
    protected=[n for n in git_names if n.startswith(('content/','domain/','ai/','persistence/','assets/'))
               or n.startswith('presentation/data/')]
    changed=subprocess.check_output(['git','diff','--name-only',parent,'--','content','domain','ai',
                                     'persistence','assets','presentation/data'],cwd=P,encoding='utf-8').splitlines()
    assert not changed,changed
    named={k:int(heights[round((80-lat)/.05),round((lon-20)/.05)]) for k,(lon,lat) in places.items()}
    result=dict(passed=True,created_at_utc=datetime.now(timezone.utc).isoformat(),
                source_sha256=sha(source),auditor_sha256=sha(__file__),source_tiles_verified=len(records),
                independent_original_samples=len(probes),maximum_rounding_error_m=max_error,
                protected_parent_commit=parent,protected_tracked_files=len(protected),changed_protected_files=changed,
                protected_scope_method='Git tracked diff against parent; no new full byte rehash of the previously sealed art bank',
                original_tile_sample_method='Individual registered GeoTIFFs with cross-tile bilinear taps; independent of compilation mosaic',
                named_regional_samples_metres=named,scope='Physical DEM sampling and protected source identity, not historical landcover or art approval')
    fixture_path.write_text(json.dumps(dict(source_sha256=sha(source),probes=probes),indent=2)+'\n',encoding='utf-8')
    result['native_probe_fixture_sha256']=sha(fixture_path)
    report_path.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result),flush=True)


if __name__=='__main__':main()
