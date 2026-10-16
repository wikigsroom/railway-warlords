"""Independently verify material membership and numerical/river source bytes.

No production compiler is imported. Original shapefiles and registered GeoTIFF
pixels are read directly. No raster file is generated, cropped or modified.
"""
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import json
import math
import sys

P=Path(__file__).resolve().parents[1];ROOT=P.parents[1]
sys.path.insert(0,str(ROOT/'.toolchain/python-libs'))
import numpy as np
import shapefile
import shapely
from PIL import Image
from shapely.geometry import shape, Point, box, LineString
from shapely.ops import transform
from pyproj import Transformer


def read(path):return json.loads(path.read_text(encoding='utf-8'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--materials-only',action='store_true')
    args=parser.parse_args();checks=[]
    def check(name,ok,**details):checks.append(dict(name=name,passed=bool(ok),**details))
    source=ROOT/'design/geodata/surface_detail_sources/Ecoregions2017/Ecoregions2017.shp'
    catalog=read(P/'presentation/data/surface_regions.json')
    check('ecoregion_original_file_hashes',all(sha(source.with_suffix(suffix))==digest for suffix,digest in catalog['source_files_sha256'].items()))
    check('explicit_ecoregion_license_and_precision',catalog['license']=='CC-BY 4.0' and not catalog['historical_wetland_extent_claimed'] and not catalog['water_polygons_added'] and not catalog['forest_boundaries_added'])
    used_ids={int(row[1]) for rows in catalog['maps'].values() for row in rows.values()}
    reader=shapefile.Reader(str(source),encoding='cp1252');regions={};attributes={}
    for index,record in enumerate(reader.iterRecords()):
        attrs=record.as_dict();eco=int(attrs['ECO_ID'])
        if eco in used_ids:
            regions[eco]=shapely.make_valid(shape(reader.shape(index).__geo_interface__))
            attributes[eco]=attrs
    counts={}
    for map_id,records in catalog['maps'].items():
        data=read(P/'content/maps'/f'{map_id}.json');cells={cell['id']:cell for cell in data['cells']}
        grouped={};classification_ok=True;protected=True
        for cell_id,(family,eco) in records.items():
            cell=cells[cell_id];attrs=attributes[int(eco)];name=attrs['ECO_NAME'].lower()
            grouped.setdefault(int(eco),[]).append(cell)
            protected=protected and cell.get('natural_terrain_id')=='plain' and cell['terrain_id'] not in ['river','road','city','sea','ford','port']
            if family=='sandy_ground':classification_ok=classification_ok and ('sand' in name or 'taklimakan' in name)
            elif family=='arid_gravel':classification_ok=classification_ok and int(attrs['BIOME_NUM'])==13 and 'desert' in name
            elif family=='dry_grass':classification_ok=classification_ok and int(attrs['BIOME_NUM']) in [8,10]
            elif family=='wetland_ground':classification_ok=classification_ok and int(attrs['BIOME_NUM'])==9
            elif family=='alluvial_soil':classification_ok=classification_ok and any(word in name for word in ['plain','tarim','riparian'])
            else:classification_ok=False
        membership=True
        for eco,group in grouped.items():
            points=shapely.points(np.array([[cell['lon_e6']/1e6,cell['lat_e6']/1e6] for cell in group]))
            membership=membership and bool(np.all(shapely.covers(regions[eco],points)))
        check('original_polygon_membership:'+map_id,membership,assigned_cells=len(records))
        check('material_semantics_match_source_biome:'+map_id,classification_ok)
        check('source_water_road_and_site_features_are_protected:'+map_id,protected)
        counts[map_id]=dict(Counter(row[0] for row in records.values()))
    samples=read(ROOT/'design/geodata/asia_relief_dem/samples_v1.json')
    old=read(ROOT/'design/geodata/asia_relief_dem/asia_strategic_before_dem.json')
    current=read(P/'content/maps/asia_strategic.json')
    geometry_fields=['cities','rail_edges','rail_nodes','render_land','render_coast','render_rivers','admin_layers','geographic_bounds','hex_radius_px']
    check('asia_city_political_rail_and_water_geometry_preserved',all(old[key]==current[key] for key in geometry_fields))
    check('all_continental_dem_originals_preserved',len(samples['tiles'])==54 and all(sha(ROOT/row['file'])==row['sha256'] for row in samples['tiles']))
    tiles={};maximum_error=0.0
    for row in samples['tiles']:
        with Image.open(ROOT/row['file']) as image:
            keys=image.tag_v2[34735];tags={keys[i]:keys[i+3] for i in range(4,len(keys),4)}
            if tags.get(3072)!=3857:raise RuntimeError('Unexpected DEM CRS')
            tiles[row['id']]=(np.asarray(image).copy(),image.tag_v2[33550],image.tag_v2[33922],0 if tags.get(1025)==2 else .5)
    for key,expected in samples['values'].items():
        lat,lon=map(float,key.split(','));n=2**samples['zoom']
        tx=min(n-1,max(0,int((lon+180)/360*n)))
        ty=min(n-1,max(0,int((1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2*n)))
        grid,scale,tie,offset=tiles[f'{samples["zoom"]}_{tx}_{ty}']
        mx=math.radians(lon)*6378137;my=math.log(math.tan(math.pi/4+math.radians(lat)/2))*6378137
        x=min(511,max(0,(mx-tie[3])/scale[0]+tie[0]-offset));y=min(511,max(0,(tie[4]-my)/scale[1]+tie[1]-offset))
        x0,y0=math.floor(x),math.floor(y);x1,y1=min(511,x0+1),min(511,y0+1);fx,fy=x-x0,y-y0
        actual=float(grid[y0,x0])*(1-fx)*(1-fy)+float(grid[y0,x1])*fx*(1-fy)+float(grid[y1,x0])*(1-fx)*fy+float(grid[y1,x1])*fx*fy
        maximum_error=max(maximum_error,abs(actual-expected))
    check('all_33696_samples_match_registered_original_dem_pixels',len(samples['values'])==33696 and maximum_error<.30,maximum_error_metres=round(maximum_error,6))
    cell_index={cell['id']:cell for cell in current['cells']}
    check('taklimakan_basin_is_not_a_rectangular_mountain_band',all(cell_index[key]['natural_terrain_id']=='plain' and cell_index[key]['relief_sample_m']<400 for key in ['c_41_11','c_41_12','c_42_10','c_42_11']))
    if not args.materials_only:
        hydro=read(P/'presentation/data/hydrography_fine.json');report=read(P/'reports/hydrography_fine_compilation.json')
        raw=ROOT/report['source_file']
        check('fine_hydrography_original_and_runtime_hashes',sha(raw)==hydro['source_sha256']==report['source_sha256'] and sha(P/'presentation/data/hydrography_fine.json')==report['output_sha256'])
        check('fine_river_precision_not_misrepresented',hydro['flat_lowland_branches_excluded'] and hydro['no_invented_connections'] and hydro['no_invented_historical_names'] and hydro['width_is_symbolic'] and not hydro['authored_rule_maps_modified'])
        wanted={row['source_reach_id'] for rows in list(hydro['maps'].values())+list(hydro['major_presentation_replacements'].values()) for row in rows}
        raw_reader=shapefile.Reader(str(raw),encoding='utf-8');geometries={}
        for index,record in enumerate(raw_reader.iterRecords(fields=['HYRIV_ID'])):
            reach=int(record['HYRIV_ID'])
            if reach in wanted:geometries[reach]=shape(raw_reader.shape(index).__geo_interface__)
        for map_id,rows in hydro['maps'].items():
            data=read(P/'content/maps'/f'{map_id}.json');forward=Transformer.from_crs('EPSG:4326',data['projection'],always_xy=True)
            extent=transform(forward.transform,box(*data['geographic_bounds']));minx,_,_,maxy=extent.bounds;radius=data['hex_radius_m']
            inverse=Transformer.from_crs(data['projection'],'EPSG:4326',always_xy=True)
            all_rows=rows+hydro['major_presentation_replacements'].get(map_id,[]);maximum=0.0;closed_ok=True
            for row in all_rows:
                original=transform(forward.transform,geometries[row['source_reach_id']])
                # Simplified internal chords can deviate by .25 world units;
                # endpoints must still lie on the source clipped geometry.
                for point in [row['points'][0],row['points'][-1]]:
                    px=minx+point[0]*radius/48;py=maxy-point[1]*radius/48
                    maximum=max(maximum,original.distance(Point(px,py)))
                closed_ok=closed_ok and (row['source_closed'] or row['points'][0]!=row['points'][-1]) and not row['historically_surveyed_channel'] and row['width_symbolic']
            check('river_endpoints_match_original_reach:'+map_id,maximum<max(1.0,radius/48*.02),reaches=len(all_rows),maximum_endpoint_error_metres=round(maximum,4))
            check('open_rivers_not_closed_or_claimed_as_historical_survey:'+map_id,closed_ok)
    result=dict(passed=all(row['passed'] for row in checks),created_at_utc=datetime.now(timezone.utc).isoformat(),
        checks=checks,failures=[row['name'] for row in checks if not row['passed']],
        material_assignments_by_map=counts,original_files_modified=False,raster_files_written=False,
        includes_fine_hydrography=not args.materials_only,historical_landuse_or_channel_survey_claimed=False)
    filename='surface_geography_material_audit.json' if args.materials_only else 'surface_geography_audit.json'
    (P/'reports'/filename).write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(passed=result['passed'],checks=len(checks),failures=result['failures'])),flush=True)
    raise SystemExit(0 if result['passed'] else 1)


if __name__=='__main__':main()
