"""Rebuild a gapless control wash, still clipped to existing source land."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import shutil

from compile_control_land_clip import P, SOURCE, FIELD_RADIUS, compile_map, mesh, ring, world, segments, verify_fixture
import shapely
from shapely.geometry import Polygon, LineString
from shapely.ops import unary_union


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    out=P/'reports/ground_layers_v0238/vector_rebuild01'
    out.mkdir(parents=True,exist_ok=False)
    targets=[P/'presentation/data/control_land_clip.json', P/'presentation/data/coastal_control_asia.json']
    previous={p.name:sha(p) for p in targets}
    for p in targets:shutil.copyfile(p,out/p.name)
    shutil.copyfile(__file__,out/'controller.py.txt')
    shutil.copyfile(P/'tools/compile_control_land_clip.py',out/'clip_compiler.py.txt')
    before=sha(SOURCE);data=json.loads(SOURCE.read_bytes())
    verify_fixture()
    row=compile_map(data)
    main_data=dict(schema=1,source='existing_render_land_exteriors_minus_holes',
                   historical_military_frontiers_claimed=False,rule_maps_modified=False,maps={data['id']:row})
    land=unary_union([Polygon(s['exterior'],s['holes']) for s in data['render_land']])
    if not land.is_valid:raise ValueError('Invalid source land; never repair geography silently')
    shapely.prepare(land)
    cells={};area=0.0;triangles=0;water_centres=0
    for cell in data['cells']:
        if cell.get('render_land_covered',False) and cell.get('natural_terrain_id',cell['terrain_id'])!='sea':continue
        polygon=ring(world(cell['position']),FIELD_RADIUS)
        if not land.intersects(polygon):continue
        clipped=polygon.intersection(land)
        if clipped.area<=1e-8:continue
        record=mesh(clipped);record.pop('borders')
        corners=list(polygon.exterior.coords)[:6]
        record['edges']=[list(segments(LineString([corners[a],corners[b]]).intersection(land)))
                         for a,b in [(0,1),(5,0),(4,5)]]
        cells[f"{cell['position']['q']},{cell['position']['r']}"]=record
        area+=clipped.area;triangles+=len(record['triangles'])//3
        water_centres+=not land.covers(shapely.Point(world(cell['position'])))
    coast=dict(format=1,map_id='asia_strategic',map_sha256=before,
               source='existing_render_land_exteriors_minus_holes',hex_radius=48,field_radius=FIELD_RADIUS,
               field_clips=cells,supplement_cells=len(cells),source_land_area_world=area,
               source_land_triangles=triangles,sea_centre_land_fragments=water_centres,
               rule_cells_changed=False,ownership_changed=False,historical_military_frontiers_claimed=False)
    assert sha(SOURCE)==before
    for path,value in zip(targets,[main_data,coast]):
        pending=path.with_suffix('.json.pending')
        with pending.open('x',encoding='utf-8',newline='\n') as stream:
            json.dump(value,stream,ensure_ascii=False,separators=(',',':'),allow_nan=False);stream.write('\n')
        pending.replace(path)
    report=dict(passed=True,created_at_utc=datetime.now(timezone.utc).isoformat(),
                compiler_sha256=sha(__file__),helper_sha256=sha(P/'tools/compile_control_land_clip.py'),
                source_map_sha256=before,source_map_unchanged=sha(SOURCE)==before,
                previous_vector_sha256=previous,current_vector_sha256={p.name:sha(p) for p in targets},
                field_radius_before=47.4,field_radius_after=FIELD_RADIUS,operation_hex_radius=48,
                full_field_cells=row['full_field_cells'],partial_field_cells=row['partial_field_cells'],
                empty_field_cells=row['empty_field_cells'],coastal_cells=len(cells),coastal_triangles=triangles,
                city_zones_unchanged=main_data['maps']['asia_strategic']['city_zones']==json.loads((out/targets[0].name).read_bytes())['maps']['asia_strategic']['city_zones'],
                source_pngs_modified=False,rule_or_city_ownership_changes=False,
                historical_frontier_claimed=False,formal_art_approval=False)
    with (out/'validation.json').open('x',encoding='utf-8',newline='\n') as stream:
        json.dump(report,stream,indent=2);stream.write('\n')
    print(json.dumps(report),flush=True)


if __name__=='__main__':main()
