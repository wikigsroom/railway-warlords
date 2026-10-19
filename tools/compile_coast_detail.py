"""Compile traceable marine geometry and its display mesh, never game rules.

GSHHG 2.3.7 L1 is a modern natural-coast reference, not a dated harbor survey.
Existing inland water/islands, historical administration and every rule field
are preserved from the immutable 0.2.25 baseline. No L2 reservoir is imported.
"""
from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import json
import math
import subprocess
import sys
import time
import warnings

P = Path(__file__).resolve().parents[1]
ROOT = P.parents[1]
sys.path.insert(0, str(ROOT / '.toolchain/python-libs'))
import numpy as np
import shapefile
import shapely
from shapely.geometry import shape, mapping, box, Polygon, LineString
from shapely.ops import transform, unary_union
from pyproj import Transformer
from fetch_coast_geodata import EXPECTED, sha

warnings.filterwarnings('ignore', category=DeprecationWarning, module=__name__)
SOURCE = ROOT / 'design/geodata/gshhg_2_3_7'
BASELINE_REF = '1d4a9c95d3d1cf214490dac69d166dab6f19e9a7'
BASELINE = P / 'presentation/data/coast_inland_baseline.json'
CATALOG = P / 'presentation/data/coast_geometry.json'
VISUAL_FIELDS = {'render_land', 'render_coast', 'physical_detail_source'}
PLAN = {'jingfeng': 'f', 'jingjin': 'f', 'conquest_china': 'h', 'asia_strategic': 'i'}
SOURCE_ID = 'gshhg_marine_2_3_7'


def encode(value):
    return (json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False)+'\n').encode('utf-8')


def canonical_sha(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def rule_sha(data):
    return canonical_sha({k:v for k,v in data.items() if k not in VISUAL_FIELDS})


def parts(g, kind):
    if g is None or g.is_empty:
        return
    if g.geom_type == kind:
        yield g
    elif hasattr(g, 'geoms'):
        for part in g.geoms:
            yield from parts(part, kind)


def capture_baseline():
    if BASELINE.exists():
        record=json.loads(BASELINE.read_text(encoding='utf-8'))
        if 'preserved_content_files' in record:return record
    else:record={}
    maps = {}
    for mid in PLAN:
        raw = subprocess.check_output(['git','show',BASELINE_REF+f':content/maps/{mid}.json'],cwd=P)
        old = json.loads(raw)
        land = unary_union([Polygon(r['exterior'],r['holes']) for r in old['render_land']])
        holes = unary_union([Polygon(h) for r in old['render_land'] for h in r['holes']])
        maps[mid] = dict(map_sha256=hashlib.sha256(raw).hexdigest(), nonvisual_fields_sha256=rule_sha(old),
            old_land_polygons=len(old['render_land']), old_coast_vertices=sum(map(len,old['render_coast'])),
            old_land_area=land.area, inland_holes=mapping(holes),
            retained_lake_islands=mapping(land.intersection(holes)))
    files=subprocess.check_output(['git','ls-tree','-r','--name-only',BASELINE_REF,'content'],cwd=P).decode().splitlines()
    protected={}
    for name in files:
        if name.endswith('.json') and name not in ['content/geography_sources.json']+[f'content/maps/{mid}.json' for mid in PLAN]:
            raw=subprocess.check_output(['git','show',BASELINE_REF+':'+name],cwd=P)
            protected[name]=hashlib.sha256(raw).hexdigest()
    sources=json.loads(subprocess.check_output(['git','show',BASELINE_REF+':content/geography_sources.json'],cwd=P))
    record = dict(baseline_commit=BASELINE_REF, baseline_version='0.2.25', maps=maps,
                  preserved_content_files=protected, original_source_registry=sources,
                  purpose='Preserve existing inland water and all nonvisual fields, not new reservoir data.')
    BASELINE.write_bytes(encode(record))
    return record


def source_for(mid, resolution, data, check=False):
    path = P/f'docs/geography-sources/gshhg_{mid}.geojson'
    if path.exists():
        row = json.loads(path.read_text(encoding='utf-8'))
        if row['properties']['archive_sha256'] != EXPECTED or row['properties']['resolution'] != resolution:
            raise ValueError('Marine source identity differs: '+mid)
        return row, path
    if check:
        raise ValueError('Missing retained marine subset: '+mid)
    verification = json.loads((SOURCE/'download_verification.json').read_text(encoding='utf-8'))
    if not verification['passed'] or sha(SOURCE/'gshhg-shp-2.3.7.zip') != EXPECTED:
        raise ValueError('Original archive verification required')
    shp = SOURCE/f'GSHHS_shp/{resolution}/GSHHS_{resolution}_L1.shp'
    relevant = [f for f in verification['extracted'] if Path(f['file']).stem == shp.stem]
    if len(relevant) != 4 or any(sha(ROOT/f['file']) != f['sha256'] for f in relevant):
        raise ValueError('Original GIS members differ from verified archive')
    region = box(*data['geographic_bounds']).buffer(.10)
    reader = shapefile.Reader(str(shp))
    selected, ids = [], []
    for item in reader.iterShapeRecords(bbox=region.bounds):
        g = shape(item.shape.__geo_interface__)
        if not g.is_valid:
            raise ValueError('Invalid original source '+str(item.record['id'])+': '+shapely.is_valid_reason(g))
        if g.intersects(region):
            selected.append(g.intersection(region));ids.append(str(item.record['id']))
    marine = unary_union(selected)
    if not marine.is_valid:
        raise ValueError('Invalid marine subset')
    row = dict(type='Feature', properties=dict(source_id=SOURCE_ID, version='2.3.7', level=1,
        resolution=resolution, archive_sha256=EXPECTED, original_members=relevant,
        source_record_ids=ids, geographic_bounds=data['geographic_bounds'], clip_padding_deg=.10,
        crs='EPSG:4326', license='LGPL-3.0-or-later',
        changes='Geographic regional subset of L1 marine land; no political borders or L2 lakes.',
        historical_survey_claimed=False), geometry=mapping(marine))
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes(encode(row))
    return row, path


def forward_for(data):
    xmin, _, _, ymax = data['geographic_bounds']
    if data.get('strategic_scale'):
        sx = 72.0/data['longitude_step_deg']
        sy = math.sqrt(3)*48.0/data['latitude_step_deg']
        return lambda x,y,z=None: ((np.asarray(x)-xmin)*sx,(ymax-np.asarray(y))*sy)
    t = Transformer.from_crs('EPSG:4326',data['projection'],always_xy=True)
    ox, _, _, oy = transform(t.transform,box(*data['geographic_bounds'])).bounds
    scale = 48.0/data['hex_radius_m']
    def forward(x,y,z=None):
        px,py=t.transform(x,y)
        return ((np.asarray(px)-ox)*scale,(oy-np.asarray(py))*scale)
    return forward


def geometry_for(data, source, baseline):
    region=box(*data['geographic_bounds']);marine=shape(source['geometry']);forward=forward_for(data)
    # Densifying long clip-border chords before LAEA projection avoids artificial
    # self-intersections. Coast vertices are interpolated along the source line,
    # never jittered or bent to make decorative coves.
    land=transform(forward,shapely.segmentize(marine.intersection(region),.02)).simplify(.10,preserve_topology=True)
    coast=transform(forward,shapely.segmentize(marine.boundary.intersection(region),.02)).simplify(.10,preserve_topology=True)
    if not land.is_valid:raise ValueError('Projected source is invalid: '+shapely.is_valid_reason(land))
    holes=shape(baseline['inland_holes']);islands=shape(baseline['retained_lake_islands'])
    land=land.difference(holes).union(islands)
    def xy(line):return [[round(x,4),round(y,4)] for x,y in line.coords]
    rings=[dict(exterior=xy(p.exterior),holes=[xy(h) for h in p.interiors])
           for p in parts(land,'Polygon') if p.area>1e-10]
    polies=[Polygon(r['exterior'],r['holes']) for r in rings]
    if not all(p.is_valid for p in polies):raise ValueError('Rounded source polygon became invalid')
    # Retain the old inland lake edge and actual lake islands independently of
    # the marine source. We do not import modern L2 reservoir boundaries.
    inland=holes.difference(islands)
    coastline=[xy(line) for line in parts(coast,'LineString') if line.length>1e-6]
    for line in parts(inland.boundary,'LineString'):
        coastline.append(xy(line))
    return dict(render_land=rings,render_coast=coastline,physical_detail_source=SOURCE_ID),unary_union(polies)


def triangulate(land):
    vertices=[];indices=[];lookup={};triangles=[]
    for p in parts(land,'Polygon'):
        for tri in shapely.constrained_delaunay_triangles(p).geoms:
            if tri.area<=1e-10:continue
            if not p.covers(tri):raise ValueError('Triangle escaped its source land polygon')
            triangles.append(tri)
            for point in list(tri.exterior.coords)[:3]:
                key=tuple(point)
                if key not in lookup:
                    lookup[key]=len(vertices);vertices.append(list(point))
                indices.append(lookup[key])
    # Numerical snap only for this check, not stored data or geography.
    rebuilt=shapely.union_all(triangles,grid_size=1e-8)
    error=rebuilt.symmetric_difference(land).area
    if error>max(1e-5,land.area*1e-10):raise ValueError('Triangulation changed land/water: '+str(error))
    return dict(vertices=vertices,indices=indices,triangles=len(indices)//3,
                union_area_error=error,source_land_area=land.area)


def dependent_overlays(data,land):
    administration={}
    for year,regions in data.get('admin_layers',{}).items():
        clipped=[]
        for region in regions:
            for raw in region['lines']:
                if len(raw)<2:continue
                for line in parts(LineString(raw).intersection(land),'LineString'):
                    if line.length>1e-6:clipped.append([list(p) for p in line.coords])
        administration[year]=clipped
    settlements=P/'presentation/data/settlements_v023.json'
    source=json.loads(settlements.read_text(encoding='utf-8'))
    control={}
    for year,records in source.get('maps',{}).get(data['id'],{}).get('control_zones_by_year',{}).items():
        zones=[]
        for record in records:
            original=unary_union([Polygon(record['triangles'][i:i+3]) for i in range(0,len(record['triangles']),3)])
            clipped=original.intersection(land)
            mesh=triangulate(clipped)
            triangles=[mesh['vertices'][i] for i in mesh['indices']]
            # Keep only original influence edges on land. The land clip must
            # not manufacture an additional faction stroke along every coast.
            borders=[[list(p) for p in line.coords]
                     for line in parts(original.boundary.intersection(land),'LineString') if line.length>1e-6]
            zones.append(dict(city_id=record['city_id'],province=record['province'],triangles=triangles,
                borders=borders,bounds=list(clipped.bounds) if not clipped.is_empty else [],
                source_area=original.area,area=clipped.area,removed_water_area=original.difference(land).area))
        control[year]=zones
    return dict(administration_lines=administration,control_zones_by_year=control,
                settlement_source_sha256=sha(settlements),original_administration_modified=False)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--check',action='store_true');ap.add_argument('--overlays-only',action='store_true');args=ap.parse_args()
    if args.overlays_only:
        catalog=json.loads(CATALOG.read_text(encoding='utf-8'))
        for mid,entry in catalog['maps'].items():
            data=json.loads((P/f'content/maps/{mid}.json').read_text(encoding='utf-8'))
            path=P/entry['file'];row=json.loads(path.read_text(encoding='utf-8'))
            if sha(P/f'content/maps/{mid}.json')!=row['map_sha256']:raise ValueError('Land mesh must be current before clipping overlays')
            land=unary_union([Polygon(r['exterior'],r['holes']) for r in data['render_land']])
            row.update(dependent_overlays(data,land));path.write_bytes(encode(row));entry['data_sha256']=sha(path)
            print('COAST_OVERLAYS '+mid,flush=True)
        CATALOG.write_bytes(encode(catalog));return
    started=time.monotonic();baseline=capture_baseline();catalog={};reports=[]
    for mid,resolution in PLAN.items():
        print('COAST_BEGIN '+mid,flush=True)
        file=P/f'content/maps/{mid}.json';data=json.loads(file.read_text(encoding='utf-8'))
        old=baseline['maps'][mid]
        if rule_sha(data)!=old['nonvisual_fields_sha256']:
            raise ValueError('Rule/history fields differ from delivered baseline: '+mid)
        source,source_path=source_for(mid,resolution,data,args.check)
        visual,land=geometry_for(data,source,old)
        expected=dict(data,**visual)
        if args.check:
            if any(data.get(k)!=expected.get(k) for k in VISUAL_FIELDS):raise ValueError('Marine map is stale: '+mid)
        mesh=triangulate(land)
        mesh.update(dependent_overlays(expected,land))
        if not args.check:file.write_bytes(encode(expected).rstrip(b'\n'))
        mesh.update(map_id=mid,map_sha256=sha(file),source_subset_sha256=sha(source_path),
                    hex_radius=48,coast_vertices=sum(map(len,visual['render_coast'])),
                    source_land_polygons=len(visual['render_land']),
                    source_land_holes=sum(len(p['holes']) for p in visual['render_land']),
                    license='LGPL-3.0-or-later')
        mesh_path=P/f'presentation/data/coast_geometry_{mid}.json';encoded=encode(mesh)
        if args.check:
            if mesh_path.read_bytes()!=encoded:raise ValueError('Marine mesh is stale: '+mid)
        else:mesh_path.write_bytes(encoded)
        catalog[mid]=dict(file=mesh_path.relative_to(P).as_posix(),data_sha256=sha(mesh_path),
            map_sha256=sha(file),source_subset=source_path.relative_to(P).as_posix(),
            source_subset_sha256=sha(source_path),hex_radius=48)
        report=dict(map_id=mid,resolution=resolution,old_coast_vertices=old['old_coast_vertices'],
            new_coast_vertices=mesh['coast_vertices'],land_polygons=mesh['source_land_polygons'],
            holes=mesh['source_land_holes'],land_triangles=mesh['triangles'],
            triangle_union_area_error=mesh['union_area_error'],nonvisual_fields_preserved=True,
            existing_inland_water_preserved=True,new_l2_reservoirs_imported=False,
            map_sha256=sha(file),source_subset_sha256=sha(source_path))
        reports.append(report);print(json.dumps(report),flush=True)
    result=dict(schema=1,source_id=SOURCE_ID,source_version='2.3.7',archive_sha256=EXPECTED,
        historical_coast_survey_claimed=False,manually_invented_coast=False,new_rasters=0,
        map_fields_modified=sorted(VISUAL_FIELDS),maps=catalog)
    encoded=encode(result)
    if args.check:
        if CATALOG.read_bytes()!=encoded:raise ValueError('Marine catalog is stale')
    else:CATALOG.write_bytes(encoded)
    report=dict(passed=True,created_at_utc=datetime.now(timezone.utc).isoformat(),
        elapsed_seconds=round(time.monotonic()-started,2),baseline_commit=BASELINE_REF,
        source_archive_sha256=EXPECTED,independent_historical_approval=False,
        raw_rasters_modified=False,rule_fields_modified=False,maps=reports)
    (P/'reports/coast_detail_compilation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('COAST_COMPLETE '+str(round(time.monotonic()-started,2)),flush=True)


if __name__=='__main__':main()
