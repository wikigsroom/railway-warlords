"""Derive shared control edges; never turn a coastline into a political stroke."""
from pathlib import Path
import argparse
import hashlib
import json
import sys

P = Path(__file__).resolve().parents[1]
ROOT = P.parents[1]
sys.path.insert(0, str(ROOT / '.toolchain/python-libs'))
from shapely import STRtree
from shapely.geometry import LineString, MultiLineString
from shapely.ops import unary_union, linemerge

TOLERANCE = .002  # Existing source rings are quantized to .001 world units.
MINIMUM = .01
MAPS = ['jingfeng', 'jingjin', 'conquest_china', 'hankou', 'ningpu']


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def lines(geometry):
    if geometry.is_empty:
        return
    if geometry.geom_type == 'LineString':
        yield geometry
    elif hasattr(geometry, 'geoms'):
        for part in geometry.geoms:
            yield from lines(part)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=P / 'presentation/data/control_border_graph.json')
    args = parser.parse_args()
    coast_catalog = read(P / 'presentation/data/coast_geometry.json')
    places_path = P / 'presentation/data/settlements_v023.json'
    places = read(places_path)
    result = dict(format=1, version='0.2.35-development',
                  purpose='One shared edge per adjacent pair of city influence areas; owner filtering occurs at runtime.',
                  tolerance_world=TOLERANCE, minimum_segment_world=MINIMUM,
                  source_geometry_modified=False, coast_and_frame_excluded=True,
                  historical_military_frontiers_claimed=False, maps={})
    for mid in MAPS:
        map_path = P / 'content/maps' / (mid + '.json')
        data = read(map_path)
        if mid in coast_catalog['maps']:
            entry = coast_catalog['maps'][mid]
            source_path = P / entry['file']
            assert sha(source_path) == entry['data_sha256']
            assert sha(map_path) == entry['map_sha256']
            source = read(source_path)
            assert source['settlement_source_sha256'] == sha(places_path)
        else:
            source_path = places_path
            source = places['maps'][mid]
            assert source['map_sha256'] == sha(map_path)
        coast = MultiLineString([line for line in data['render_coast'] if len(line) >= 2])
        extent = LineString(data['render_extent'] + [data['render_extent'][0]])
        excluded = unary_union([coast, extent]).buffer(TOLERANCE)
        periods = {}
        for year, rows in sorted(source['control_zones_by_year'].items()):
            by_city = {}
            for row in rows:
                by_city.setdefault(row['city_id'], []).extend(LineString(line) for line in row['borders'] if len(line) >= 2)
            ids = sorted(by_city)
            boundaries = [unary_union(by_city[identifier]) for identifier in ids]
            tree = STRtree(boundaries)
            edges = []
            claimed = MultiLineString([])
            junction_duplicate_length = 0.0
            for i, boundary in enumerate(boundaries):
                for j in sorted(int(index) for index in tree.query(boundary.buffer(TOLERANCE))):
                    if j <= i:
                        continue
                    # Retain points on the first original boundary. The narrow
                    # band only reconciles the existing milliworld rounding at
                    # shared vertices, including subdivided province segments.
                    shared = boundary.intersection(boundaries[j].buffer(TOLERANCE)).difference(excluded)
                    pieces = [line for line in lines(shared) if line.length >= MINIMUM]
                    if not pieces:
                        continue
                    merged = linemerge(unary_union(pieces)) if len(pieces) > 1 else pieces[0]
                    paths = [[[round(x, 6), round(y, 6)] for x, y in line.coords]
                             for line in lines(merged) if line.length >= MINIMUM]
                    # A milliworld tolerance may extend two different pairs a
                    # few thousandths past a three-way junction. Assign that
                    # exact shared fragment once, after output quantization.
                    rounded = unary_union([LineString(path) for path in paths])
                    unique = rounded.difference(claimed)
                    junction_duplicate_length += max(0.0, rounded.length - unique.length)
                    paths = [[[round(x, 6), round(y, 6)] for x, y in line.coords]
                             for line in lines(unique) if line.length >= MINIMUM]
                    if paths:
                        edges.append(dict(city_a=ids[i], city_b=ids[j], lines=paths,
                                          length_world=sum(LineString(line).length for line in paths)))
                        claimed = unary_union([claimed, MultiLineString(paths)])
            periods[year] = dict(zone_count=len(rows), city_count=len(ids),
                                 source_outline_length_world=sum(boundary.length for boundary in boundaries),
                                 junction_duplicate_length_removed_world=junction_duplicate_length,
                                 edge_pairs=len(edges), edges=edges)
        result['maps'][mid] = dict(map_sha256=sha(map_path), zone_source_file=source_path.relative_to(P).as_posix(),
                                   zone_source_sha256=sha(source_path), periods=periods)
        print(mid + ': ' + ', '.join(year + '=' + str(value['edge_pairs']) for year, value in periods.items()), flush=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes((json.dumps(result, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n').encode('utf-8'))
    print(json.dumps(dict(passed=True, maps=len(result['maps']), output=str(args.output), sha256=sha(args.output))), flush=True)


if __name__ == '__main__':
    main()
