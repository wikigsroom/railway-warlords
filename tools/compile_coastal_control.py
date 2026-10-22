"""Restore source-clipped control wash on land inside sea-centred rule cells.

Scientific vector clipping only. Never change a cell's terrain or ownership.
The existing city-derived gameplay influence policy remains in the renderer.
"""
from datetime import datetime, timezone
import json
from pathlib import Path
import hashlib
from compile_control_land_clip import P,mesh,ring,world,segments
import shapely
from shapely.geometry import Polygon,LineString
from shapely.ops import unary_union

TARGET=P/'presentation/data/coastal_control_asia.json'
REPORT=P/'reports/geographic_relief_v0236/coastal_control_compile01.json'


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    if TARGET.exists() or REPORT.exists():raise FileExistsError('Immutable vector compilation')
    path=P/'content/maps/asia_strategic.json';before=sha(path)
    data=json.loads(path.read_bytes())
    land=unary_union([Polygon(s['exterior'],s['holes']) for s in data['render_land']])
    if not land.is_valid:raise ValueError('Invalid original land, do not repair it silently')
    shapely.prepare(land)
    cells={};area=0.0;triangles=0;water_centres=0
    for c in data['cells']:
        old_eligible=c.get('render_land_covered',False) and c.get('natural_terrain_id',c['terrain_id'])!='sea'
        if old_eligible:continue
        polygon=ring(world(c['position']),47.4)
        if not land.intersects(polygon):continue
        clipped=polygon.intersection(land)
        if clipped.area<=1e-8:continue
        record=mesh(clipped)
        record.pop('borders')
        corners=list(polygon.exterior.coords)[:6]
        record['edges']=[list(segments(LineString([corners[a],corners[b]]).intersection(land)))
                         for a,b in [(0,1),(5,0),(4,5)]]
        key=f"{c['position']['q']},{c['position']['r']}"
        cells[key]=record;area+=clipped.area;triangles+=len(record['triangles'])//3
        water_centres+=not land.covers(shapely.Point(world(c['position'])))
        if len(cells)%100==0:print(f'Clipped coastal control cells {len(cells)}',flush=True)
    assert sha(path)==before
    d=dict(format=1,map_id='asia_strategic',map_sha256=before,source='existing_render_land_exteriors_minus_holes',
           hex_radius=48,field_radius=47.4,field_clips=cells,supplement_cells=len(cells),
           source_land_area_world=area,source_land_triangles=triangles,sea_centre_land_fragments=water_centres,
           rule_cells_changed=False,ownership_changed=False,historical_military_frontiers_claimed=False)
    with TARGET.open('x',encoding='utf-8',newline='\n') as stream:
        json.dump(d,stream,ensure_ascii=False,separators=(',',':'));stream.write('\n')
    report={k:v for k,v in d.items() if k!='field_clips'}
    report.update(passed=True,created_at_utc=datetime.now(timezone.utc).isoformat(),
                  compiler_sha256=sha(__file__),output_sha256=sha(TARGET),output_bytes=TARGET.stat().st_size,
                  source_map_sha256_after=sha(path),raster_art_generated=False)
    with REPORT.open('x',encoding='utf-8',newline='\n') as stream:json.dump(report,stream,indent=2);stream.write('\n')
    print(json.dumps(report),flush=True)


if __name__=='__main__':main()
