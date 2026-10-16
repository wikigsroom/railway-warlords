"""Independent checks against original geographic vectors and the official point dump."""
from pathlib import Path
import hashlib
import json
import sys
P=Path(__file__).resolve().parents[1]
ROOT=P.parents[1]
sys.path.insert(0,str(ROOT/'.toolchain/python-libs'))
from pyproj import Transformer
from shapely.geometry import Polygon, Point, box
from shapely.ops import transform, unary_union
from compile_maps import ADMIN_LAYERS

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    path=P/'presentation/data/settlements_v023.json';data=json.loads(path.read_text(encoding='utf-8'))
    compilation=json.loads((P/'reports/settlement_compilation.json').read_text(encoding='utf-8'))
    checks=[];details=[]
    def verify(ok,name):checks.append({'name':name,'passed':bool(ok)})
    points={};wanted={p['location']['geonames_id'] for p in data['places'] if p['location']['geonames_id'] is not None}
    gazetteer=ROOT/'design/geodata/settlements/CN.txt'
    for line in gazetteer.open(encoding='utf-8'):
        row=line.rstrip('\n').split('\t')
        if int(row[0]) in wanted:points[int(row[0])]=row
    verify(sha(path)==compilation['presentation_data_sha256'],'current_presentation_matches_compilation')
    verify(sha(gazetteer)==compilation['gazetteer_sha256'],'official_point_dump_has_not_changed')
    verify(len(data['places'])==67 and len({p['id'] for p in data['places']})==67,'unique_67_place_records')
    verify(compilation['kinds']=={'village':9,'market':0,'county':56,'capital':2},'67_new_places_have_documented_rank_counts')
    for p in data['places']:
        loc=p['location'];row=points.get(loc['geonames_id'])
        verify(all(s in data['sources'] for s in p['sources']) and p['rank_period']=='1920—1924',p['id']+'_primary_historical_rank_source')
        verify((row is not None and row[6]=='P' and row[8]=='CN' and float(row[4])==p['latitude'] and float(row[5])==p['longitude'] and loc['gazetteer_sha256']==sha(gazetteer)) if loc['geonames_id'] is not None else p['kind']=='village' and loc['precision_m']>=1500,p['id']+'_real_populated_point_or_explicit_coarse_village')
    index={p['id']:p for p in data['places']}
    verify(index['place_baodi']['province']=='京兆地方' and index['place_jixian']['province']=='京兆地方' and index['place_chadao']['province']=='直隶','1914_jingzhao_membership_and_no_1928_province_anachronism')
    verify(index['place_qishui']['name']=='蕲水' and index['place_weixian']['name']=='潍县','period_county_names_are_preserved')
    verify(index['place_anqing']['kind']=='capital' and index['place_kaifeng']['kind']=='capital' and index['place_hefei']['kind']=='county' and data['role_overrides']['zhengzhou']['kind']=='county','historical_province_capitals_do_not_use_modern_seats')
    verify(set(p['id'] for p in compilation['omitted_unresolved'])=={'luoyang','xiangyang','xianning','wuhu'},'unverified_old_seat_coordinates_are_explicitly_omitted')
    for key,entry in data['maps'].items():
        map_path=P/'content/maps'/f'{key}.json';m=json.loads(map_path.read_text(encoding='utf-8'))
        verify(sha(map_path)==entry['map_sha256']==compilation['immutable_gameplay_maps'][key],key+'_authoritative_gameplay_map_unchanged')
        land=unary_union([Polygon(s['exterior'],s['holes']).buffer(0) for s in m['render_land']]).intersection(Polygon(m['render_extent']))
        projection=Transformer.from_crs('EPSG:4326',m['projection'],always_xy=True)
        origin=transform(projection.transform,box(*m['geographic_bounds'])).bounds
        factor=48/m['hex_radius_m']
        def xy(lon,lat):
            x,y=projection.transform(lon,lat);return ((x-origin[0])*factor,(origin[3]-y)*factor)
        verify(all(Point(n['world']).distance(Point(xy(n['longitude'],n['latitude'])))<.015 for n in entry['markers']),key+'_marker_world_points_match_real_projection_without_label_jitter')
        verify(all(Point(c['render_position']).distance(Point(xy(c['lon_e6']/1e6,c['lat_e6']/1e6)))<.08 for c in m['cities']),key+'_same_origin_as_existing_historical_cities')
        counts={}
        for year,zones in entry['control_zones_by_year'].items():
            regions={r['name']:transform(xy,r['geometry']).intersection(land) for r in ADMIN_LAYERS[year]}
            grouped={};triangle_count=0;leaks=0;area_error=0
            for zone in zones:
                vertices=zone['triangles'];triangles=[Polygon(vertices[i:i+3]) for i in range(0,len(vertices),3)]
                triangle_count+=len(triangles);expected=regions[zone['province']]
                # Three decimal vertex storage may shift a boundary by <0.001px.
                tolerance=expected.buffer(.002)
                leaks+=sum(not tolerance.covers(t) for t in triangles)
                grouped.setdefault(zone['province'],[]).extend(triangles)
                area_error=max(area_error,abs(sum(t.area for t in triangles)-zone['area_px2'])/max(1,zone['area_px2']))
            verify(leaks==0,key+'_'+year+'_all_control_triangles_stay_inside_real_province_and_land')
            verify(area_error<.00002,key+'_'+year+'_triangle_fill_preserves_zone_area')
            coverage=[]
            for province,triangles in grouped.items():
                filled=unary_union(triangles);expected=regions[province]
                error=filled.symmetric_difference(expected).area/max(1,expected.area)
                coverage.append(error)
            verify(all(error<.00002 for error in coverage),key+'_'+year+'_control_zones_cover_source_provinces_without_circular_islands')
            counts[year]={'zones':len(zones),'triangles':triangle_count,'outside_source':leaks,'max_relative_fill_error':max(coverage,default=0)}
        details.append({'map':key,'additional_markers':len(entry['markers']),'years':counts})
    report={'passed':all(c['passed'] for c in checks),'checks':checks,'failed':[c['name'] for c in checks if not c['passed']],'maps':details,'presentation_data_sha256':sha(path),'gazetteer_sha256':sha(gazetteer),'raster_editing':False,'historic_county_or_military_boundaries_claimed':False}
    (P/'reports/settlement_geography_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'checks':len(checks),'passed':report['passed'],'failed':report['failed']},ensure_ascii=False),flush=True)
    raise SystemExit(0 if report['passed'] else 1)
if __name__=='__main__':main()
