"""Rebuild open river lines from the archived Natural Earth vector source.

Rule cells, cities, administrative borders, rail links and historical data are
untouched. Smaller source tributaries are a separate presentation catalogue.
"""
from pathlib import Path
import hashlib
import json
import sys
from datetime import datetime, timezone

P=Path(__file__).resolve().parents[1]
ROOT=P.parents[1]
sys.path.insert(0,str(ROOT/'.toolchain/python-libs'))
import shapefile
from shapely.geometry import shape, box
from shapely.ops import transform
from pyproj import Transformer
from build_asia_map import load_land_and_rivers, walk_lines, rounded_line, world

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    path=P/'content/maps/asia_strategic.json'
    data=json.loads(path.read_text(encoding='utf-8'))
    before={k:v for k,v in data.items() if k!='render_rivers'}
    source_before=digest(path)
    _,geometries,_=load_land_and_rivers()
    major=[]
    for geometry in geometries:
        projected=transform(lambda x,y,z=None:world(x,y),geometry)
        for line in walk_lines(projected):
            coords=rounded_line(line.simplify(.18).coords)
            if len(coords)>=2:major.append(coords)
    old=data['render_rivers']
    if len(major)!=len(old):raise AssertionError('Unexpected major river count change')
    removed=[]
    for index,(actual,previous) in enumerate(zip(major,old)):
        if previous==actual:continue
        if previous[:-1]!=actual or previous[-1]!=previous[0]:
            raise AssertionError(f'Change beyond erroneous closure: river {index}')
        a,b=previous[-2:]
        removed.append(dict(index=index,length_px=round(((a[0]-b[0])**2+(a[1]-b[1])**2)**.5,2)))
    data['render_rivers']=major
    assert before=={k:v for k,v in data.items() if k!='render_rivers'}
    if data['render_rivers']!=old:
        path.write_text(json.dumps(data,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    source=ROOT/'design/geodata/ne_10m_rivers_lake_centerlines/ne_10m_rivers_lake_centerlines.shp'
    reader=shapefile.Reader(str(source),encoding='utf-8')
    vectors=[(item.record.as_dict(),shape(item.shape.__geo_interface__)) for item in reader.iterShapeRecords()]
    maps={};counts={}
    for map_path in sorted((P/'content/maps').glob('*.json')):
        if map_path.name=='catalog.json':continue
        m=json.loads(map_path.read_text(encoding='utf-8'));region=box(*m['geographic_bounds'])
        strategic=m.get('strategic_scale',False)
        if strategic:
            project=lambda x,y,z=None:world(x,y)
            tolerance=.12
        else:
            forward=Transformer.from_crs('EPSG:4326',m['projection'],always_xy=True)
            extent=transform(forward.transform,region);minx,_,_,maxy=extent.bounds
            radius=m['hex_radius_m']
            def project(x,y,z=None):
                px,py=forward.transform(x,y)
                return ((px-minx)/radius*48,(maxy-py)/radius*48)
            tolerance=.40
        rows=[]
        # Existing major lines stay in the authoritative map. Only actual
        # additional source branches enter this detailed presentation layer.
        for attrs,geo in vectors:
            rank=int(attrs.get('scalerank') or 10)
            if rank<=4 or attrs.get('featurecla')=='Canal' or not geo.intersects(region):continue
            name=str(attrs.get('name') or attrs.get('name_en') or '')
            keywords=("yangtze","chang jiang","huang","yellow","ganges","brahmaputra","indus","mekong","amur","ob","irtysh","syr","amu","tigris","euphr") if strategic else ("yangtze","huang","hai","luan","han","huai","pearl")
            if any(word in name.lower() for word in keywords):continue
            for part,line in enumerate(walk_lines(geo.intersection(region))):
                projected=transform(project,line).simplify(tolerance)
                coords=rounded_line(projected.coords)
                if len(coords)<2 or projected.length<3.0:continue
                # A genuine source ring is retained as such; open lines are
                # never closed, joined to nearby cells, or randomly extended.
                if not line.is_closed and coords[0]==coords[-1]:continue
                rows.append(dict(id=f"ne_{attrs.get('ne_id',attrs.get('rivernum',len(rows)))}_{part}",
                    source_name=name,source_rank=rank,points=coords,
                    bounds=[min(p[0] for p in coords),min(p[1] for p in coords),max(p[0] for p in coords),max(p[1] for p in coords)],
                    source_closed=bool(line.is_closed)))
        maps[m['id']]=rows;counts[m['id']]=len(rows)
    detail=dict(schema_version=1,source_id='natural_earth_rivers_10m',source_sha256=digest(source),
        precision='generalized geographic centerlines; not surveyed historical banks or complete creeks',
        invented_connections=False,maps=maps)
    detail_path=P/'presentation/data/hydrography_detail.json'
    detail_path.write_text(json.dumps(detail,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    report=dict(passed=True,created_at_utc=datetime.now(timezone.utc).isoformat(),
        major_lines=len(major),removed_false_closures=len(removed),removed_segments=removed,
        rule_fields_unchanged=True,source_sha256=digest(source),map_sha256=digest(path),
        previous_map_sha256=source_before,detail_sha256=digest(detail_path),minor_lines_by_map=counts,
        manually_drawn_geography=False,original_source_changed=False)
    report_path=P/'reports/hydrography_revision.json'
    # Revalidation must not erase the original defect/correction audit trail.
    if report_path.exists() and not removed:
        previous=json.loads(report_path.read_text(encoding='utf-8'))
        for field in ('removed_false_closures','removed_segments','previous_map_sha256'):report[field]=previous[field]
    report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='removed_segments'},ensure_ascii=True))

if __name__=='__main__':main()
