"""Clip presentation control geometry to the existing vector land, including holes.

No raster is created or modified. Cities, rule hexes and source coastlines stay
immutable. The output is independent of owners, so captures only change colors.
"""
from pathlib import Path
import argparse
import hashlib
import json
import math
import sys

P = Path(__file__).resolve().parents[1]
ROOT = P.parents[1]
sys.path.insert(0, str(ROOT / '.toolchain/python-libs'))
import shapely
from shapely.geometry import Polygon, LineString, Point
from shapely.ops import unary_union

SOURCE = P / 'content/maps/asia_strategic.json'
TARGET = P / 'presentation/data/control_land_clip.json'
RADIUS = 48.0
FIELD_RADIUS = RADIUS
INFLUENCE_FACTOR = 1.38


def world(position):
    q, r = position['q'], position['r']
    return 1.5 * RADIUS * q, math.sqrt(3) * RADIUS * (r + q * .5)


def ring(center, radius, rotation=0.0):
    x, y = center
    return Polygon([(x + radius * math.cos(rotation + math.tau * i / 6),
                     y + radius * math.sin(rotation + math.tau * i / 6)) for i in range(6)])


def polygons(geometry):
    if geometry.geom_type == 'Polygon':
        yield geometry
    elif hasattr(geometry, 'geoms'):
        for piece in geometry.geoms:
            yield from polygons(piece)


def segments(geometry):
    if geometry.geom_type in ('LineString', 'LinearRing'):
        coords = list(geometry.coords)
        for a, b in zip(coords, coords[1:]):
            if a != b:
                yield [list(a), list(b)]
    elif hasattr(geometry, 'geoms'):
        for piece in geometry.geoms:
            yield from segments(piece)


def mesh(geometry):
    triangles, borders, shapes = [], [], []
    for shape in polygons(geometry):
        if shape.area == 0:
            continue
        shapes.append(shape)
        borders.append([list(xy) for xy in shape.exterior.coords])
        borders.extend([[list(xy) for xy in hole.coords] for hole in shape.interiors])
        for tri in shapely.constrained_delaunay_triangles(shape).geoms:
            if not shape.covers(tri):
                raise ValueError('Control triangle escaped its source land intersection')
            triangles.extend([list(xy) for xy in list(tri.exterior.coords)[:3]])
    rebuilt = unary_union([Polygon(triangles[i:i+3]) for i in range(0, len(triangles), 3)])
    error = rebuilt.symmetric_difference(unary_union(shapes)).area
    if error > 1e-6:
        raise ValueError('Control mesh lost an island or filled a water hole')
    return dict(triangles=triangles, borders=borders, bounds=list(geometry.bounds) if not geometry.is_empty else [],
                area=geometry.area)


def compile_map(m):
    shapes = [Polygon(row['exterior'], row['holes']) for row in m['render_land']]
    if not all(shape.is_valid for shape in shapes):
        raise ValueError('Source land is invalid; do not silently repair historical geography')
    land = unary_union(shapes)
    shapely.prepare(land)
    # Hole polygons can contain separately sourced islands. The actual water
    # surface must exclude that land too, otherwise the lake hides its islands.
    inland_water = mesh(unary_union([Polygon(hole) for source in m['render_land'] for hole in source['holes']]).difference(land))
    field, city_zones, witnesses = {}, [], []
    eligible = [row for row in m['cells'] if row.get('render_land_covered', False)
                and row.get('natural_terrain_id', row.get('terrain_id', '')) != 'sea']
    empty = full = partial = 0
    for cell in eligible:
        polygon = ring(world(cell['position']), FIELD_RADIUS)
        if land.covers(polygon):
            full += 1
            continue
        clipped = polygon.intersection(land)
        record = mesh(clipped)
        # Shared political edges keep the original field orientation. Only
        # their source-land portions are inked; no line bridges a bay or lake.
        corners = list(polygon.exterior.coords)[:6]
        record['edges'] = [list(segments(LineString([corners[a], corners[b]]).intersection(land)))
                           for a, b in [(0, 1), (5, 0), (4, 5)]]
        field[f"{cell['position']['q']},{cell['position']['r']}"] = record
        if record['triangles']:
            partial += 1
        else:
            empty += 1
    clipped_cities = 0
    for city in m['cities']:
        original = ring(world(city['position']), city.get('control_radius_hex', 3) * RADIUS * INFLUENCE_FACTOR,
                        math.pi / 6)
        clipped = original.intersection(land)
        record = mesh(clipped)
        outside = original.difference(land)
        if outside.area > 1e-6:
            clipped_cities += 1
            # Independent native pixel probes: these were inside the old
            # influence hex but are outside the actual land, not new land.
            candidates = [piece.representative_point() for piece in polygons(outside)]
            center = world(city['position'])
            interior_corners = [Point(center[0]+.96*(x-center[0]), center[1]+.96*(y-center[1]))
                                for x, y in list(original.exterior.coords)[:6]]
            candidates.extend(point for point in interior_corners if not land.covers(point))
            candidates.sort(key=lambda point: land.distance(point), reverse=True)
            for point in candidates[:3]:
                clearance = land.distance(point)
                if clearance > 1:
                    witnesses.append(dict(city_id=city['id'], point=[point.x, point.y],
                                          source_land_clearance=clearance))
        record.update(city_id=city['id'], province=city.get('reference_bloc', '未核实'),
                      source_area=original.area, removed_water_area=outside.area)
        city_zones.append(record)
    return dict(map_id=m['id'], map_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                source_land_polygons=len(shapes), source_land_holes=sum(len(row['holes']) for row in m['render_land']),
                hex_radius=RADIUS, field_radius=FIELD_RADIUS, influence_factor=INFLUENCE_FACTOR,
                eligible_field_cells=len(eligible), full_field_cells=full, partial_field_cells=partial,
                empty_field_cells=empty, clipped_city_zones=clipped_cities,
                field_clips=field, city_zones=city_zones, water_witnesses=witnesses, inland_water=inland_water)


def verify_fixture():
    # A concave shore, two disjoint islands and a lake must survive triangulation.
    mainland = Polygon([(0, 0), (24, 0), (24, 9), (15, 9), (15, 24), (0, 24)],
                       [[(3, 3), (3, 7), (7, 7), (7, 3)]])
    island = Polygon([(27, 4), (31, 4), (31, 8), (27, 8)])
    lake_island = Polygon([(4, 4), (6, 4), (6, 6), (4, 6)])
    land = unary_union([mainland, island, lake_island])
    record = mesh(land.intersection(Polygon([(-2, -2), (35, -2), (35, 30), (-2, 30)])))
    rebuilt = unary_union([Polygon(record['triangles'][i:i+3]) for i in range(0, len(record['triangles']), 3)])
    assert rebuilt.symmetric_difference(land).area <= 1e-6
    assert not rebuilt.covers(Point(3.5, 3.5)) and not rebuilt.covers(Point(25, 6))
    assert rebuilt.covers(Point(5, 5))
    assert rebuilt.covers(Point(29, 6)) and not rebuilt.covers(Point(20, 15))
    edge = list(segments(LineString([(-1, 5), (33, 5)]).intersection(land)))
    assert len(edge) == 4 and sum(LineString(piece).length for piece in edge) == 26
    assert mesh(Polygon())['triangles'] == []


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true', help='Recompute source intersections and check published vector bytes')
    args = parser.parse_args()
    verify_fixture()
    m = json.loads(SOURCE.read_text(encoding='utf-8'))
    source_sha = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    row = compile_map(m)
    result = dict(schema=1, source='existing_render_land_exteriors_minus_holes',
                  historical_military_frontiers_claimed=False, rule_maps_modified=False,
                  maps={m['id']: row})
    encoded = json.dumps(result, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n'
    encoded_bytes = encoded.encode('utf-8')
    if args.check:
        if TARGET.read_bytes() != encoded_bytes:
            raise SystemExit('Control clip data is stale or was edited independently of its source')
    else:
        TARGET.write_bytes(encoded_bytes)
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == source_sha
    summary = dict(passed=True, map_id=m['id'], source_map_sha256=source_sha,
                   presentation_data_sha256=hashlib.sha256(TARGET.read_bytes()).hexdigest(),
                   shapely=shapely.__version__, geos=shapely.geos_version_string,
                   source_land_polygons=row['source_land_polygons'], source_land_holes=row['source_land_holes'],
                   eligible_field_cells=row['eligible_field_cells'], full_field_cells=row['full_field_cells'],
                   partial_field_cells=row['partial_field_cells'], empty_field_cells=row['empty_field_cells'],
                   city_zones=len(row['city_zones']), clipped_city_zones=row['clipped_city_zones'],
                   water_witnesses=len(row['water_witnesses']), exact_triangle_coverage_verified=True,
                   disjoint_islands_and_water_holes_verified=True, source_maps_modified=False, raster_editing=False)
    (P / 'reports/control_land_clip_audit.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=True), flush=True)


if __name__ == '__main__':
    main()
