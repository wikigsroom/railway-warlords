"""Independently audit native control triangles against source land and hexes."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import math
import sys

P=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(P.parents[1]/'.toolchain/python-libs'))
import numpy as np
import shapely
from shapely.geometry import Polygon, LineString
from shapely.ops import unary_union
from shapely.strtree import STRtree


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    output=P/'reports/ground_layers_v0238/source_audit01.json'
    if output.exists():raise FileExistsError('Immutable audit')
    paths=[P/'content/maps/asia_strategic.json',P/'presentation/data/control_land_clip.json',
           P/'presentation/data/coastal_control_asia.json']
    identity={p.relative_to(P).as_posix():sha(p) for p in paths}
    m=json.loads(paths[0].read_bytes())
    base=json.loads(paths[1].read_bytes())['maps']['asia_strategic']
    coast=json.loads(paths[2].read_bytes())
    assert base['field_radius']==48 and coast['field_radius']==48
    assert base['map_sha256']==identity['content/maps/asia_strategic.json']==coast['map_sha256']
    # Reload the source geometry at native float32 precision. No compiler
    # functions, serialized borders or derived land-query cache are imported.
    shapes=[Polygon(np.asarray(s['exterior'],dtype=np.float32),
                    [np.asarray(h,dtype=np.float32) for h in s['holes']]) for s in m['render_land']]
    assert all(s.is_valid for s in shapes)
    tree=STRtree(shapes)
    cells={f"{c['position']['q']},{c['position']['r']}":c for c in m['cells']}
    counts={'ordinary_partial_or_empty':0,'coastal':0};triangles=0;largest=0.;excess_max=0.;collapsed=[]
    for category,records in [('ordinary_partial_or_empty',base['field_clips']),('coastal',coast['field_clips'])]:
        for key,record in records.items():
            c=cells[key];q=c['position']['q'];r=c['position']['r']
            ordinary=c.get('render_land_covered',False) and c.get('natural_terrain_id',c['terrain_id'])!='sea'
            assert ordinary==(category=='ordinary_partial_or_empty')
            center=np.array([72*q,math.sqrt(3)*48*(r+q*.5)])
            angles=np.arange(6)*np.pi/3
            full=Polygon(center+48*np.column_stack([np.cos(angles),np.sin(angles)]))
            box=full.envelope.buffer(.01)
            local=unary_union([shapes[i].intersection(box) for i in tree.query(box)])
            expected=full.intersection(local)
            vertices=np.asarray(record['triangles'],dtype=np.float32).astype(np.float64)
            tris=shapely.polygons(vertices.reshape(-1,3,2)) if len(vertices) else []
            actual=shapely.union_all(tris)
            error=float(actual.symmetric_difference(expected).area)
            excess=float(actual.difference(local.buffer(.002)).area)
            assert error<=max(.02,expected.length*.002),(key,error)
            assert excess<1e-6,(key,excess)
            assert actual.difference(full.buffer(.002)).area<1e-6
            # A real source sliver can lose its altitude at float32 precision.
            # Such a primitive paints no pixels. Account for it explicitly,
            # bounded by the same native rounding budget; retain the separate
            # complete coverage/excess checks above instead of asserting that
            # every double-precision source triangle stays nondegenerate.
            for index,tri in enumerate(tris):
                if tri.area>0:continue
                raw=np.asarray(record['triangles'][index*3:index*3+3],dtype=np.float64)
                lengths=np.linalg.norm(raw-np.roll(raw,1,axis=0),axis=1)
                altitude=2*Polygon(raw).area/max(float(lengths.max()),1e-20)
                assert altitude<=.002,(key,'collapsed_source_altitude',altitude)
                collapsed.append(dict(category=category,cell=key,triangle=index,source_area=Polygon(raw).area,
                                      source_altitude_world=altitude,native_area=0.0))
            for direction in record['edges']:
                for segment in direction:
                    assert LineString(np.asarray(segment,dtype=np.float32)).difference(local.buffer(.002)).length<1e-7
            counts[category]+=1;triangles+=len(tris);largest=max(largest,error);excess_max=max(excess_max,excess)
            if sum(counts.values())%300==0:print('Audited boundary records',sum(counts.values()),flush=True)
    assert counts['coastal']==coast['supplement_cells']
    assert all(sha(P/name)==expected for name,expected in identity.items())
    result=dict(passed=True,completed_at_utc=datetime.now(timezone.utc).isoformat(),auditor_sha256=sha(__file__),
                input_sha256=identity,records_checked=counts,native_triangles_checked=triangles,
                maximum_symmetric_difference_area_world=largest,native_rounding_fringe_world=.002,
                maximum_area_beyond_source_fringe_world=excess_max,source_data_changed_during_audit=False,
                native_collapsed_triangles=collapsed,native_nonzero_triangles=triangles-len(collapsed),
                native_collapsed_primitives_paint_pixels=False,
                field_radius=48,operation_hex_radius=48,historical_frontiers_claimed=False,
                scope='Every stored ordinary and coastal boundary triangle/edge versus raw source land at native precision. Interior seam coverage is separately checked in actual native runtime meshes.',
                formal_art_approval=False,physical_android_device_tested=False)
    with output.open('x',encoding='utf-8',newline='\n') as stream:json.dump(result,stream,indent=2);stream.write('\n')
    print(json.dumps(result),flush=True)


if __name__=='__main__':main()
