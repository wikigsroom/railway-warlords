"""Independently read original GIS, map rules and actual compiled triangles.

No production coastline compiler is imported. The raw-source audit is separate
from aesthetic inspection and never certifies a nineteenth-century shoreline.
"""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import math
import sys
import time
import warnings
import zipfile

P=Path(__file__).resolve().parents[1];ROOT=P.parents[1]
sys.path.insert(0,str(ROOT/'.toolchain/python-libs'))
import numpy as np
import shapefile
import shapely
from shapely.geometry import Polygon,shape,box,LineString
from shapely.ops import transform,unary_union
from shapely.strtree import STRtree
from pyproj import Transformer
warnings.filterwarnings('ignore',category=DeprecationWarning,module=__name__)


def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def semantic_sha(value):return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def lines(g):
    if g is None or g.is_empty:return
    if g.geom_type in ['LineString','LinearRing']:yield g
    elif hasattr(g,'geoms'):
        for item in g.geoms:yield from lines(item)


def source_segments(rows):
    segments=[]
    for row in rows:
        points=np.asarray(row,dtype=float)
        if len(points)<2:continue
        pairs=np.stack([points[:-1],points[1:]],axis=1)
        pairs=pairs[np.sum((pairs[:,0]-pairs[:,1])**2,axis=1)>1e-16]
        segments.extend(shapely.linestrings(pairs))
    return STRtree(segments)


def greatest_source_distance(rows,tree):
    # Every source/display vertex and every segment midpoint is probed in both
    # directions. The spatial tree contains individual source segments, not a
    # single huge mainland line with quadratic nearest-point cost.
    greatest=0.0;count=0
    for start in range(0,len(rows),300):
        probes=[]
        for row in rows[start:start+300]:
            xy=np.asarray(row,dtype=float)
            if not len(xy):continue
            probes.extend(xy);probes.extend((xy[:-1]+xy[1:])*.5)
        if probes:
            _,distances=tree.query_nearest(shapely.points(probes),return_distance=True,all_matches=False)
            greatest=max(greatest,float(np.max(distances)));count+=len(probes)
    return greatest,count


def main():
    started=time.monotonic();checks=[];maps=[]
    def check(name,ok,**details):
        checks.append(dict(name=name,passed=bool(ok),**details))
        if not ok:print('AUDIT_FAILED '+name,flush=True)
    base=read(P/'presentation/data/coast_inland_baseline.json')
    for file,digest in base['preserved_content_files'].items():
        check('preserved_rule_content:'+file,sha(P/file)==digest)
    registry=read(P/'content/geography_sources.json');old=base['original_source_registry']
    newrows=[r for r in registry['sources'] if r['id']=='gshhg_marine_2_3_7']
    check('existing_geographic_source_records_preserved',dict(registry,sources=[r for r in registry['sources'] if r['id']!='gshhg_marine_2_3_7'])==old)
    check('one_explicit_marine_source_record',len(newrows)==1 and newrows[0]['license']=='LGPL-3.0-or-later')
    catalog=read(P/'presentation/data/coast_geometry.json');source=ROOT/'design/geodata/gshhg_2_3_7'
    archive=source/'gshhg-shp-2.3.7.zip'
    expected='8dbbe7e071e77e9e75f2d639239099ebca8d5c16d6a07df8169729d49f15cf41'
    check('publisher_original_archive_sha256',sha(archive)==expected==catalog['archive_sha256'])
    with zipfile.ZipFile(archive) as z:
        check('original_archive_crc',z.testzip() is None)
        for basename,local in [('LICENSE.TXT','GSHHG-LICENSE.txt'),('COPYING.LESSERv3','GSHHG-LGPL-3.0.txt')]:
            members=[n for n in z.namelist() if Path(n).name.upper()==basename.upper()]
            check('unmodified_source_notice:'+basename,bool(members) and z.read(members[0])==(P/'assets/legal'/local).read_bytes())
    check('full_gpl_text_in_distribution',(P/'assets/legal/GSHHG-GPL-3.0.txt').stat().st_size>30000)
    for mid,entry in catalog['maps'].items():
        print('AUDIT_BEGIN '+mid,flush=True)
        data=read(P/f'content/maps/{mid}.json');previous=base['maps'][mid]
        nonvisual={k:v for k,v in data.items() if k not in ['render_land','render_coast','physical_detail_source']}
        check('nonvisual_history_grid_cities_and_rules:'+mid,semantic_sha(nonvisual)==previous['nonvisual_fields_sha256'])
        subset_file=P/entry['source_subset'];subset=read(subset_file);props=subset['properties']
        check('marine_L1_only_no_historical_survey:'+mid,props['level']==1 and not props['historical_survey_claimed'] and props['license']=='LGPL-3.0-or-later')
        check('source_members_and_subset_hash:'+mid,sha(subset_file)==entry['source_subset_sha256'] and all(sha(ROOT/f['file'])==f['sha256'] for f in props['original_members']))
        resolution=props['resolution'];raw=shapefile.Reader(str(source/f'GSHHS_shp/{resolution}/GSHHS_{resolution}_L1.shp'))
        region=box(*data['geographic_bounds']);expanded=region.buffer(.10);selected=[];ids=[]
        for record in raw.iterShapeRecords(bbox=expanded.bounds):
            geometry=shape(record.shape.__geo_interface__)
            if geometry.intersects(expanded):
                selected.append(geometry.intersection(expanded));ids.append(str(record.record['id']))
        original=unary_union(selected);retained=shape(subset['geometry'])
        check('retained_subset_matches_original_vectors:'+mid,original.symmetric_difference(retained).area<1e-10 and ids==props['source_record_ids'])
        if data.get('strategic_scale'):
            west,_,_,north=data['geographic_bounds'];sx=72/data['longitude_step_deg'];sy=math.sqrt(3)*48/data['latitude_step_deg']
            def world(x,y,z=None):return ((np.asarray(x)-west)*sx,(north-np.asarray(y))*sy)
        else:
            t=Transformer.from_crs('EPSG:4326',data['projection'],always_xy=True)
            left,_,_,top=transform(t.transform,region).bounds;s=48/data['hex_radius_m']
            def world(x,y,z=None):
                xx,yy=t.transform(x,y);return ((np.asarray(xx)-left)*s,(top-np.asarray(yy))*s)
        raw_coast=transform(world,shapely.segmentize(original.boundary.intersection(region),.02))
        inland=shape(previous['inland_holes']);islands=shape(previous['retained_lake_islands'])
        source_rows=[list(g.coords) for g in lines(raw_coast)]+[list(g.coords) for g in lines(inland.difference(islands).boundary)]
        displayed=data['render_coast'];distance,n1=greatest_source_distance(displayed,source_segments(source_rows))
        reverse,n2=greatest_source_distance(source_rows,source_segments(displayed))
        check('all_displayed_coasts_follow_source_segments:'+mid,distance<=.151,max_world_deviation=distance,probes=n1)
        check('all_original_shore_segments_retained:'+mid,reverse<=.151,max_world_deviation=reverse,probes=n2)
        land=unary_union([Polygon(r['exterior'],r['holes']) for r in data['render_land']]);shapely.prepare(land)
        check('valid_source_land_and_preserved_inland_water:'+mid,land.is_valid and land.intersection(inland).symmetric_difference(islands).area<=1e-5)
        mesh_path=P/entry['file'];mesh=read(mesh_path)
        check('mesh_and_map_hashes_are_current:'+mid,sha(mesh_path)==entry['data_sha256'] and sha(P/f'content/maps/{mid}.json')==entry['map_sha256']==mesh['map_sha256'])
        xy=np.asarray(mesh['vertices']);indices=np.asarray(mesh['indices'],dtype=int).reshape(-1,3)
        tri=shapely.polygons(xy[indices]);valid=np.all(shapely.area(tri)>1e-10) and bool(np.all(shapely.covers(land,tri)))
        actual=shapely.union_all(tri,grid_size=1e-8);error=actual.symmetric_difference(land).area
        check('actual_triangles_cover_land_and_exclude_water:'+mid,valid and error<=max(1e-5,land.area*1e-10),triangles=len(tri),area_error=error)
        source_settlements=read(P/'presentation/data/settlements_v023.json')
        check('source_city_influence_catalog_preserved:'+mid,mesh['settlement_source_sha256']==sha(P/'presentation/data/settlements_v023.json'))
        administrative_clear=True;admin_error=0.0;admin_cache={}
        for year,regions in data.get('admin_layers',{}).items():
            expected_lines=unary_union([LineString(raw) for region in regions for raw in region['lines'] if len(raw)>1]).intersection(land)
            actual_lines=unary_union([LineString(raw) for raw in mesh['administration_lines'].get(year,[])])
            # A 1e-7-wide GEOS buffer over 300k-world-long borders can lose an
            # identical 0.1-world segment by roundoff. Test actual line-segment
            # distances at every vertex/midpoint instead, in both directions,
            # and independently compare total union length. No data is snapped.
            signature=hashlib.sha256(expected_lines.wkb+actual_lines.wkb).hexdigest()
            if signature not in admin_cache:
                expected_rows=[list(g.coords) for g in lines(expected_lines)]
                actual_rows=[list(g.coords) for g in lines(actual_lines)]
                deviation=0.0
                if bool(expected_rows)!=bool(actual_rows):deviation=math.inf
                elif expected_rows:
                    forward,_=greatest_source_distance(actual_rows,source_segments(expected_rows))
                    backward,_=greatest_source_distance(expected_rows,source_segments(actual_rows))
                    deviation=max(forward,backward)
                admin_cache[signature]=(deviation,abs(actual_lines.length-expected_lines.length))
            deviation,difference=admin_cache[signature]
            admin_error=max(admin_error,deviation,difference)
            administrative_clear=administrative_clear and deviation<=1e-7 and difference<1e-5
        check('display_administration_is_exact_source_land_intersection:'+mid,administrative_clear,max_length_error=admin_error)
        zones_clear=True;zone_error=0.0;zone_count=0;edges_clear=True
        originals=source_settlements.get('maps',{}).get(mid,{}).get('control_zones_by_year',{})
        for year,original_zones in originals.items():
            displayed_zones=mesh['control_zones_by_year'].get(year,[])
            zones_clear=zones_clear and len(original_zones)==len(displayed_zones)
            for previous_zone,zone in zip(original_zones,displayed_zones):
                zone_count+=1
                original=unary_union([Polygon(previous_zone['triangles'][i:i+3]) for i in range(0,len(previous_zone['triangles']),3)])
                actual_zone=shapely.union_all([Polygon(zone['triangles'][i:i+3]) for i in range(0,len(zone['triangles']),3)],grid_size=1e-8)
                difference=actual_zone.symmetric_difference(original.intersection(land)).area
                zone_error=max(zone_error,difference)
                zones_clear=zones_clear and difference<max(1e-5,original.area*1e-10) and zone['city_id']==previous_zone['city_id'] and zone['province']==previous_zone['province']
                expected_edges=original.boundary.intersection(land)
                actual_edges=unary_union([LineString(raw) for raw in zone['borders']])
                outside_edges=actual_edges.difference(expected_edges.buffer(1e-7)).length+expected_edges.difference(actual_edges.buffer(1e-7)).length
                edges_clear=edges_clear and outside_edges<1e-5 and abs(actual_edges.length-expected_edges.length)<1e-5
        check('display_city_influence_is_exact_source_land_intersection:'+mid,zones_clear,zones=zone_count,max_area_error=zone_error)
        check('city_edges_do_not_create_an_extra_coastal_frontier:'+mid,edges_clear)
        # Rules retain their geographic grid; display-shore precision must not
        # change movement, landing permission, city positions or DEM classes.
        check('original_hex_radius_preserved:'+mid,data['hex_radius_px']==48 and mesh['hex_radius']==48)
        maps.append(dict(map_id=mid,source_resolution=resolution,coast_vertices=sum(map(len,displayed)),
            source_polygons=len(data['render_land']),land_triangles=len(tri),
            max_display_to_source_world=distance,max_source_to_display_world=reverse,
            independent_source_probes=n1+n2,map_sha256=sha(P/f'content/maps/{mid}.json')))
    passed=all(r['passed'] for r in checks)
    report=dict(passed=passed,created_at_utc=datetime.now(timezone.utc).isoformat(),
        elapsed_seconds=round(time.monotonic()-started,2),checks=checks,maps=maps,
        baseline_commit=base['baseline_commit'],preserved_rule_content_files=len(base['preserved_content_files']),
        production_compiler_imported=False,source_rasters_modified=False,
        historical_coast_survey_approval=False,formal_art_approval=False)
    (P/'reports/coast_detail_geography_audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(passed=passed,checks=len(checks),maps=maps)),flush=True)
    raise SystemExit(0 if passed else 1)


if __name__=='__main__':main()
