"""Compile actual HydroRIVERS reaches into a separate, audited visual layer.

Small source reaches are limited to relief-adjacent natural valley contexts.
Flat lowland model branches are excluded: their historical/artificial status
cannot be inferred from this modern DEM product. Two small Yangtze maps receive
source main-channel presentation replacements, without editing rule geometry.
No endpoint snapping, fabricated branch, surveyed bank or historic-name claim.
"""
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import math
import sys
import time

P=Path(__file__).resolve().parents[1];ROOT=P.parents[1]
sys.path.insert(0,str(ROOT/'.toolchain/python-libs'))
import shapefile
import shapely
from shapely.geometry import box, shape, Polygon, LineString
from shapely.ops import transform, unary_union
from shapely.prepared import prep
from pyproj import Transformer
from build_asia_map import walk_lines, rounded_line

FOLDER=ROOT/'design/geodata/surface_detail_sources/HydroRIVERS_v10_as_shp'
OUTPUT=P/'presentation/data/hydrography_fine.json'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):return json.loads(path.read_text(encoding='utf-8'))


def rounded_hex(point):
    x,y=point;q=x/72;r=(-x/3+math.sqrt(3)*y/3)/48;s=-q-r
    rq,rr,rs=round(q),round(r),round(s);dq,dr,ds=abs(rq-q),abs(rr-r),abs(rs-s)
    if dq>dr and dq>ds:rq=-rr-rs
    elif dr>ds:rr=-rq-rs
    return rq,rr


def relief_adjacent(projected, cells):
    # The exact source line remains untouched. This only decides whether a
    # source reach can be displayed without implying historical lowland canals.
    for fraction in [.2,.5,.8]:
        point=projected.interpolate(fraction,normalized=True);q,r=rounded_hex((point.x,point.y))
        for dq,dr in [(0,0),(1,0),(0,1),(-1,1),(-1,0),(0,-1),(1,-1)]:
            if cells.get((q+dq,r+dr),{}).get('natural_terrain_id') in ['hill','mountain','peak']:
                return True
    return False


def contexts():
    result={}
    for path in sorted((P/'content/maps').glob('*.json')):
        if path.name=='catalog.json':continue
        data=read(path)
        if data.get('strategic_scale'):continue
        region=box(*data['geographic_bounds']);forward=Transformer.from_crs('EPSG:4326',data['projection'],always_xy=True)
        extent=transform(forward.transform,region);minx,_,_,maxy=extent.bounds;radius=data['hex_radius_m']
        def project(x,y,z=None,forward=forward,minx=minx,maxy=maxy,radius=radius):
            px,py=forward.transform(x,y);return ((px-minx)/radius*48,(maxy-py)/radius*48)
        land=unary_union([Polygon(row['exterior'],row.get('holes',[])) for row in data['render_land']])
        existing=[LineString(row) for row in data['render_rivers'] if len(row)>=2]
        original_minor=read(P/'presentation/data/hydrography_detail.json')['maps'].get(data['id'],[])
        existing.extend(LineString(row['points']) for row in original_minor if len(row['points'])>=2)
        existing_clearance=unary_union(existing).buffer(7) if existing else Polygon()
        result[data['id']]=dict(path=path,hash=sha(path),data=data,region=region,project=project,
            land=land,existing=existing_clearance,
            cells={(cell['position']['q'],cell['position']['r']):cell for cell in data['cells']},
            fine=[],major=[],excluded=Counter())
    return result


def main():
    started=time.monotonic();paths=list(FOLDER.rglob('*as.shp'))
    if len(paths)!=1:raise RuntimeError('One original, extracted Asia HydroRIVERS shapefile required')
    source=paths[0];reader=shapefile.Reader(str(source),encoding='utf-8')
    ctx=contexts();overall=unary_union([value['region'] for value in ctx.values()]).bounds
    seen=0
    for item in reader.iterShapeRecords(bbox=overall):
        attrs=item.record.as_dict();order=int(attrs['ORD_STRA']);upstream=float(attrs['UPLAND_SKM'])
        candidates=[value for value in ctx.values() if box(*item.shape.bbox).intersects(value['region'])]
        if not candidates:continue
        geometry=shape(item.shape.__geo_interface__);seen+=1
        for value in candidates:
            map_id=value['data']['id'];major=map_id in ['hankou','ningpu'] and order>=6
            if not major and (order>4 or upstream>5000):
                value['excluded']['large_channel_already_in_primary_layer']+=1;continue
            if not major and value['data']['hex_radius_m']>=5000 and (order<3 or upstream<400):
                # A 5.4 km control grid cannot read the same headwater density
                # as a 1 km campaign. Preserve the real small channels in the
                # campaign maps; use an appropriate source hierarchy here.
                value['excluded']['below_readable_hierarchy_at_coarser_control_grid']+=1;continue
            for part,line in enumerate(walk_lines(geometry.intersection(value['region']))):
                projected=transform(value['project'],line)
                if projected.length<2.0:continue
                if not major and not relief_adjacent(projected,value['cells']):
                    value['excluded']['flat_lowland_branch_not_historically_verified']+=1;continue
                clipped=projected.intersection(value['land'])
                if not major:clipped=clipped.difference(value['existing'])
                for section,piece in enumerate(walk_lines(clipped)):
                    simplified=piece.simplify(.25,preserve_topology=True)
                    coords=rounded_line(simplified.coords)
                    if len(coords)<2 or simplified.length<2.0:continue
                    if not piece.is_closed and coords[0]==coords[-1]:continue
                    row=dict(id=f'hyriv_{int(attrs["HYRIV_ID"])}_{part}_{section}',
                        source_reach_id=int(attrs['HYRIV_ID']),next_down=int(attrs['NEXT_DOWN']),
                        stream_order=order,upstream_area_km2=upstream,
                        source_name='',source_closed=bool(piece.is_closed),
                        points=coords,bounds=[min(p[0] for p in coords),min(p[1] for p in coords),max(p[0] for p in coords),max(p[1] for p in coords)],
                        min_zoom=.80 if order==1 else .64 if order==2 else .48,
                        width_symbolic=True,historically_surveyed_channel=False)
                    value['major' if major else 'fine'].append(row)
        if seen%5000==0:print(f'Source reaches inspected: {seen}',flush=True)
    maps={};major={};counts={}
    for map_id,value in ctx.items():
        if sha(value['path'])!=value['hash']:raise RuntimeError('Rule geography changed during compile')
        maps[map_id]=sorted(value['fine'],key=lambda row:row['id'])
        if value['major']:major[map_id]=sorted(value['major'],key=lambda row:row['id'])
        rows=maps[map_id]+major.get(map_id,[])
        counts[map_id]=dict(reaches=len(rows),fine_reaches=len(maps[map_id]),
            main_presentation_replacement_reaches=len(major.get(map_id,[])),
            segments=sum(len(row['points'])-1 for row in rows),exclusions=dict(value['excluded']))
        print(json.dumps(dict(map=map_id,**counts[map_id])),flush=True)
    payload=dict(format=1,source_id='hydrorivers_v10_as',source_url='https://www.hydrosheds.org/products/hydrorivers',
        source_sha256=sha(source),source_archive_sha256=sha(FOLDER.parent/'HydroRIVERS_v10_as_shp.zip'),
        source_support='15 arc-second DEM-derived river network; threshold 10 km2 upstream area or 0.1 m3/s estimated natural discharge; not every creek',
        temporal_scope='Modern physical reference; not a dated 1840-1940 channel survey',
        license='HydroSHEDS License Agreement; original technical documents and license archived',
        attribution='Lehner and Grill (2013), https://doi.org/10.1002/hyp.9740',
        no_invented_connections=True,no_invented_historical_names=True,width_is_symbolic=True,
        authored_rule_maps_modified=False,flat_lowland_branches_excluded=True,
        display_hierarchy='1 km campaign grids retain source orders 1-4 with zoom LOD; grids >=5 km retain orders 3-4 and upstream area >=400 km2. Continental overview uses its existing primary source network.',
        maps=maps,major_presentation_replacements=major)
    OUTPUT.write_text(json.dumps(payload,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    report=dict(passed=True,created_at_utc=datetime.now(timezone.utc).isoformat(),
        source_file=source.relative_to(ROOT).as_posix(),source_sha256=payload['source_sha256'],
        output_sha256=sha(OUTPUT),maps=counts,inspected_source_reaches=seen,
        eligible_scope='Tactical-map relief-adjacent tributaries; main-channel presentation in the two small Yangtze maps. Continental overview retains Natural Earth. Flat lowland model branches are excluded.',
        source_files_modified=False,rule_map_files_modified=False,no_endpoint_snapping=True,
        historical_channel_survey_claimed=False,measured_river_width_claimed=False,
        rule_map_sha256={key:value['hash'] for key,value in ctx.items()},elapsed_seconds=round(time.monotonic()-started,2))
    (P/'reports/hydrography_fine_compilation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':main()
