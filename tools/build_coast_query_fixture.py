"""Independent GEOS truth for native float land queries, never imports the producer."""
from pathlib import Path
import hashlib
import json
import math
import sys

P = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(P.parents[1] / '.toolchain/python-libs'))
import numpy as np
import shapely
from shapely.geometry import Polygon
from shapely.ops import unary_union


def main():
    maps = {}
    for mid in ['jingjin', 'jingfeng', 'conquest_china', 'asia_strategic']:
        path = P / 'content/maps' / (mid + '.json')
        data = json.loads(path.read_text(encoding='utf-8'))
        polygons = [Polygon(np.asarray(s['exterior'], dtype=np.float32),
                           [np.asarray(h, dtype=np.float32) for h in s['holes']])
                    for s in data['render_land']]
        land = unary_union([shapely.make_valid(p) for p in polygons if p.area > 0])
        coordinates = []
        for cell in data['cells']:
            q, r = cell['position']['q'], cell['position']['r']
            coordinates.append((q * 72, math.sqrt(3) * 48 * (r + q * .5)))
        coast = [point for line in data['render_coast'] for point in line]
        for point in coast[::max(1, math.ceil(len(coast) / 2048))]:
            coordinates.extend([(point[0] + .75, point[1] + .75), (point[0] - .75, point[1] - .75)])
        xy = np.asarray(coordinates, dtype=np.float32).astype(np.float64)
        points = shapely.points(xy)
        # At most 0.008 world units around native float edges is deliberately
        # outside this point-classification fixture, not outside the separate
        # complete vertex/triangle/source geometry audits.
        distance = shapely.distance(points, land.boundary)
        keep = distance > .008
        expected = shapely.covers(land, points)
        rows = [[float(p[0]), float(p[1]), bool(value)] for p, value, retained in zip(xy, expected, keep) if retained]
        maps[mid] = dict(map_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                         rule_cell_centers=len(data['cells']), near_float_boundary_skipped=int((~keep).sum()),
                         points=rows)
        print(mid, 'independent points', len(rows), 'near-edge skipped', int((~keep).sum()), flush=True)
    result = dict(source='Independent GEOS coverage of registered native-float land polygons, including holes and islands',
        production_compiler_imported=False, pixel_art_generated=False, boundary_precision_exclusion_world=.008,
        geos_version=shapely.geos_version_string, maps=maps)
    target = P / 'tests/fixtures/coast_land_query_truth.json'
    raw = (json.dumps(result, ensure_ascii=False, separators=(',', ':')) + '\n').encode('utf-8')
    if '--check' in sys.argv:
        assert target.read_bytes() == raw, 'Independent fixture changed'
    else:
        target.write_bytes(raw)
    print(json.dumps(dict(passed=True, points=sum(len(r['points']) for r in maps.values()), sha256=hashlib.sha256(raw).hexdigest())))


if __name__ == '__main__':
    main()
