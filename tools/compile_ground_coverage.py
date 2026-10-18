"""Compile source-clipped ground underlays, never new geographic/raster art.

The ordinary terrain catalogue deliberately excludes functional rule cells.
This separate presentation layer supplies their surveyed natural ground and
clips coastal material triangles instead of rejecting a whole texture square.
"""
from collections import Counter
from datetime import datetime, timezone
import argparse
import hashlib
import json
import gzip
import math
import time

from compile_terrain_surfaces import P, ROOT, SOURCE, family_for, load_regions, river_distances
import numpy as np
import shapely
from shapely.geometry import Point, Polygon, box
from shapely.ops import transform, unary_union
from shapely.strtree import STRtree
from pyproj import Transformer

TARGET = P / 'presentation/data/ground_coverage.json'
DIRECTIONS = [(1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1)]
RADIUS = 48.0


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def world(q, r):
    return np.array([72.0*q, math.sqrt(3)*RADIUS*(r+q*.5)])


def hexagon(center):
    return Polygon([center+RADIUS*np.array([math.cos(i*math.tau/6), math.sin(i*math.tau/6)]) for i in range(6)])


def polygons(geometry):
    if geometry.geom_type == 'Polygon':
        if geometry.area > 1e-10:
            yield geometry
    elif hasattr(geometry, 'geoms'):
        for part in geometry.geoms:
            yield from polygons(part)


def inverse_for(data):
    if data.get('strategic_scale'):
        xmin, _, _, ymax = data['geographic_bounds']
        sx = data['longitude_step_deg']/72.0
        sy = data['latitude_step_deg']/(math.sqrt(3)*RADIUS)
        return lambda x, y: (xmin+x*sx, ymax-y*sy)
    forward = Transformer.from_crs('EPSG:4326', data['projection'], always_xy=True)
    minx, _, _, maxy = transform(forward.transform, box(*data['geographic_bounds'])).bounds
    inverse = Transformer.from_crs(data['projection'], 'EPSG:4326', always_xy=True)
    scale = data['hex_radius_m']/RADIUS
    return lambda x, y: inverse.transform(minx+x*scale, maxy-y*scale)


def clipped_wedges(center, land):
    """Keep the original three-source basis when a coastline splits a wedge."""
    rows, rebuilt = [], []
    for direction, a_hex in enumerate(DIRECTIONS):
        a = world(*a_hex)
        b = world(*DIRECTIONS[(direction+1) % 6])
        corner = (a+b)/3.0
        # The basis is [centre, first neighbouring centre, second neighbour].
        inverse = np.linalg.inv(np.column_stack([a, b]))
        for offsets in [[np.zeros(2), a*.5, corner], [np.zeros(2), corner, b*.5]]:
            original = Polygon([center+offset for offset in offsets])
            for part in polygons(original.intersection(land)):
                for tri in shapely.constrained_delaunay_triangles(part).geoms:
                    # Overlaying adjacent floating-point wedges can return a
                    # collinear 1e-30-area triangle. Feeding that degenerate
                    # sliver into GEOS union can discard its real neighbour.
                    if tri.area<=1e-10:
                        continue
                    if not part.covers(tri):
                        raise ValueError('Ground triangle escaped its source shore')
                    rebuilt.append(tri)
                    for xy in list(tri.exterior.coords)[:3]:
                        wa, wb = inverse @ (np.array(xy)-center)
                        weights = [1.0-wa-wb, wa, wb]
                        if min(weights) < -1e-7 or max(weights) > 1+1e-7:
                            raise ValueError('Clipping changed the original material basis')
                        rows.append([float(xy[0]), float(xy[1]), float(weights[0]), float(weights[1]), direction])
    expected = hexagon(center).intersection(land)
    # Use a numerical grid for this validation ONLY: GEOS exact double union
    # can cancel a real neighbour when two wedge vertices differ by 1e-30.
    # Stored vertices remain the original unsnapped source intersections.
    actual = shapely.union_all(rebuilt,grid_size=1e-9)
    difference = actual.symmetric_difference(expected).area
    if difference > max(1e-6, expected.area*1e-9):
        raise ValueError(f'Ground clipping lost source land or filled source water at {center.tolist()}: expected={expected.area}, actual={actual.area}, difference={difference}')
    return rows


def compile_map(data, regions, tree, original):
    print(json.dumps(dict(map=data['id'], stage='source_land', cells=len(data['cells']))), flush=True)
    shapes = [Polygon(row['exterior'], row['holes']) for row in data['render_land']]
    if not all(shape.is_valid for shape in shapes):
        raise ValueError('Invalid source land: '+data['id'])
    land = unary_union(shapes)
    shapely.prepare(land)
    cells = data['cells']
    centers = np.array([world(c['position']['q'], c['position']['r']) for c in cells])
    rings = np.array([hexagon(p) for p in centers], dtype=object)
    intersects = shapely.intersects(land, rings)
    full = shapely.covers(land, rings)
    indices = [int(i) for i in np.flatnonzero(intersects)
               if full[i] or land.intersection(rings[i]).area > 1e-8]
    print(json.dumps(dict(map=data['id'], stage='land_intersections', cells=len(indices),
                          partial=sum(not bool(full[i]) for i in indices))), flush=True)
    eligible = [cells[i] for i in indices]
    distances = river_distances(data, eligible)
    inverse = inverse_for(data)
    samples = []
    pieces = {}
    for i in indices:
        center = Point(centers[i])
        if land.covers(center):
            samples.append([cells[i]['lon_e6']/1e6, cells[i]['lat_e6']/1e6])
        else:
            part = rings[i].intersection(land)
            pieces[i] = part
            sample = part.representative_point()
            samples.append(list(inverse(sample.x, sample.y)))
    memberships = tree.query(shapely.points(np.array(samples)), predicate='covered_by')
    references = {}
    for point_index, region_index in memberships.T:
        i = int(point_index)
        cell, region = eligible[i], regions[int(region_index)]
        family, gate = family_for(region, cell, float(distances[i]))
        if not family:
            continue
        value = [family, region['id'], gate]
        if i in references and references[i] != value:
            raise ValueError('Ambiguous underlay source: '+cell['id'])
        references[i] = value
    families, additions, clips, counts, unresolved = {}, {}, {}, Counter(), []
    source_rows = original.get(data['id'], {})
    for ordinal, i in enumerate(indices):
        cell = cells[i]
        key = f"{cell['position']['q']},{cell['position']['r']}"
        row = source_rows.get(cell['id']) or references.get(ordinal)
        if row is None:
            unresolved.append((ordinal, i, key))
            continue
        families[key] = row[0]
        if cell['id'] not in source_rows:
            additions[key] = dict(cell_id=cell['id'], family=row[0], ecoregion_id=row[1],
                source_gate=row[2], sample_lonlat=samples[ordinal],
                rule_terrain=cell['terrain_id'], natural_terrain=cell.get('natural_terrain_id', cell['terrain_id']))
        counts[row[0]] += 1
    # A source-coast discrepancy may leave a narrow strip outside the ecological
    # polygons. Continue an adjacent registered pigment for at most ONE source
    # neighbour distance, recording this as interpolation, not a new biome.
    supported_keys = list(families)
    if supported_keys:
        supported_points = np.array([world(*map(int, key.split(','))) for key in supported_keys])
        supported_tree = STRtree(shapely.points(supported_points))
        for ordinal, i, key in unresolved:
            point = Point(centers[i])
            nearest = int(supported_tree.nearest(point))
            distance = float(point.distance(Point(supported_points[nearest])))
            if distance > math.sqrt(3)*RADIUS+.00001:
                continue
            source_key = supported_keys[nearest]
            family = families[source_key]
            families[key] = family
            additions[key] = dict(cell_id=cells[i]['id'], family=family, source_gate='one_neighbour_pigment_interpolation',
                source_hex=source_key, distance_world=distance, ecoregion_id=None,
                rule_terrain=cells[i]['terrain_id'], natural_terrain=cells[i].get('natural_terrain_id', cells[i]['terrain_id']))
            counts[family] += 1
    area = 0.0
    for i in indices:
        key = f"{cells[i]['position']['q']},{cells[i]['position']['r']}"
        if key not in families:
            continue
        if full[i]:
            area += rings[i].area
        else:
            intersection = pieces.get(i, rings[i].intersection(land))
            # Intersect the continental geometry ONCE. All twelve material
            # wedges operate on this small local polygon, not the whole coast.
            clips[key] = clipped_wedges(centers[i], intersection)
            area += intersection.area
    return dict(map_sha256=sha(P/'content/maps'/f"{data['id']}.json"), hex_radius=RADIUS,
        families=families, supplements=additions, clips=clips,
        counts=dict(counts), land_intersecting_cells=len(indices), covered_cells=len(families),
        unclassified_cells=len(indices)-len(families), partial_cells=len(clips), ground_area=area,
        source_land_polygons=len(shapes), source_land_holes=sum(len(s['holes']) for s in data['render_land']),
        clipped_to_source_land=True, source_geometry_modified=False,
        functional_rules_unchanged=True, ecological_references_are_not_historical_landuse=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    started = time.monotonic()
    original_path = P/'presentation/data/terrain_surface_regions.json'
    original = json.loads(original_path.read_text(encoding='utf-8'))
    expected = original['source_files_sha256']
    for suffix, checksum in expected.items():
        if sha(SOURCE.with_suffix(suffix)) != checksum:
            raise ValueError('Archived ecological source differs: '+suffix)
    # Source-hash-bound numerical cache avoids re-running the expensive world
    # shapefile validity conversion during a local geometry/compiler repair.
    # It is not distributed, and the archived GIS and classifier stay canonical.
    cache_path=ROOT/'output/geodata/ground_coverage_ecoregions_cache.json.gz'
    classifier_sha=sha(P/'tools/compile_terrain_surfaces.py')
    cached={}
    if cache_path.exists():
        with gzip.open(cache_path,'rt',encoding='utf-8') as stream:cached=json.load(stream)
    if cached.get('sources')==expected and cached.get('classifier_sha256')==classifier_sha:
        regions=cached['regions'];tree=STRtree(shapely.from_wkb([bytes.fromhex(value) for value in cached['wkb']]))
    else:
        regions, tree = load_regions()
        cache_path.parent.mkdir(parents=True,exist_ok=True)
        with gzip.open(cache_path,'wt',encoding='utf-8') as stream:
            json.dump(dict(sources=expected,classifier_sha256=classifier_sha,regions=regions,wkb=[value.hex() for value in shapely.to_wkb(tree.geometries)]),stream,separators=(',',':'))
    maps = {}
    summaries = {}
    for path in sorted((P/'content/maps').glob('*.json')):
        data = json.loads(path.read_text(encoding='utf-8'))
        if not data.get('cells') or not data.get('render_land'):
            continue
        before = sha(path)
        row = compile_map(data, regions, tree, original['maps'])
        if sha(path) != before:
            raise ValueError('Authoritative map changed during compilation')
        map_path = TARGET.with_name('ground_coverage_'+data['id']+'.json')
        encoded_map = (json.dumps(row, ensure_ascii=False, separators=(',', ':'), allow_nan=False)+'\n').encode('utf-8')
        if args.check:
            if map_path.read_bytes() != encoded_map:
                raise ValueError('Ground coverage is stale: '+data['id'])
        else:
            map_path.write_bytes(encoded_map)
        summaries[data['id']] = {k:v for k,v in row.items() if k not in ['families','supplements','clips']}
        maps[data['id']] = dict(file=map_path.relative_to(P).as_posix(), data_sha256=sha(map_path),
                               map_sha256=before, hex_radius=RADIUS)
        print(json.dumps(dict(map=data['id'], covered=row['covered_cells'], partial=row['partial_cells'],
                              supplements=len(row['supplements']), unclassified=row['unclassified_cells'])), flush=True)
    result = dict(schema=2, source='existing_source_land_and_ecological_ground_reference',
        source_geography_sha256=sha(original_path), source_files_sha256=expected,
        numerical_vectors_only=True, source_rasters_modified=False, historical_landuse_claimed=False, maps=maps)
    encoded = (json.dumps(result, ensure_ascii=False, separators=(',', ':'), allow_nan=False)+'\n').encode('utf-8')
    if args.check:
        if TARGET.read_bytes() != encoded:
            raise ValueError('Ground coverage is stale')
    else:
        TARGET.write_bytes(encoded)
    report = dict(passed=True, data_sha256=sha(TARGET), source_geography_sha256=sha(original_path),
        source_maps_modified=False, source_rasters_modified=False, numerical_vectors_only=True,
        created_at_utc=datetime.now(timezone.utc).isoformat(), elapsed_seconds=round(time.monotonic()-started, 2),
        maps=summaries)
    (P/'reports/ground_coverage_compilation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()
