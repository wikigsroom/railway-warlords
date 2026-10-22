"""Independently check native shore probes against the actual source land mesh."""
from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import json
import sys

P = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(P.parents[1] / '.toolchain/python-libs'))
import numpy as np
import shapely
from shapely.geometry import Polygon
from shapely.strtree import STRtree


def read(path):
    return json.loads(Path(path).read_bytes())


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def audit_ring_sides(tree, rings):
    """Resolve sides by GEOS containment, independently of native ring winding."""
    unresolved = dict(rings)
    resolved = {}
    for rank, scale in [(0, .001), (1, .001), (2, .001), (0, .00001), (3, .00001)]:
        if not unresolved:
            break
        probes, pending = [], []
        for line_index, (points, native_side, closed) in unresolved.items():
            delta = np.roll(points, -1, axis=0) - points if closed else points[1:] - points[:-1]
            lengths = np.linalg.norm(delta, axis=1)
            candidates = np.argsort(-lengths)
            segment = int(candidates[min(rank, len(candidates) - 1)])
            length = lengths[segment]
            if length <= 0:
                continue
            vector = delta[segment]
            normal = np.array([-vector[1], vector[0]]) / length
            midpoint = (points[segment] + points[(segment + 1) % len(points)]) * .5
            distance = min(length * scale, .02)
            left, right = midpoint + normal * distance, midpoint - normal * distance
            probes.extend([left, right])
            pending.append((line_index, native_side, segment, left, right))
        actual = np.zeros(len(probes), dtype=bool)
        if probes:
            hits = tree.query(shapely.points(probes), predicate='covered_by')
            actual[hits[0]] = True
        for index, (line_index, native_side, segment, left, right) in enumerate(pending):
            left_land, right_land = map(bool, actual[index * 2:index * 2 + 2])
            if left_land == right_land:
                continue
            independent_side = -1 if left_land else 1
            resolved[line_index] = dict(native_side=native_side, independent_side=independent_side,
                                        segment=segment, left=left.tolist(), right=right.tolist(),
                                        left_land=left_land, right_land=right_land)
            del unresolved[line_index]
    return resolved, sorted(unresolved)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--native', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists()
    native = read(args.native)
    catalog = read(P / 'presentation/data/coast_geometry.json')['maps']
    checks, records = [], []
    for row in native['maps']:
        mid = row['map_id']; source_path = P / 'content/maps' / (mid + '.json')
        source = read(source_path)
        assert sha(source_path) == row['map_sha256']
        if mid in catalog:
            data = read(P / catalog[mid]['file'])
            vertices = np.asarray(data['vertices'], dtype=np.float32).astype(np.float64)
            index = np.asarray(data['indices'], dtype=np.int64).reshape(-1, 3)
            triangles = shapely.polygons(vertices[index])
            polygons = triangles[shapely.area(triangles) > 0]
            reference = 'Actual archived source triangles at native float32 vertex coordinates; GEOS containment.'
        else:
            polygons = [Polygon(np.asarray(shape['exterior'], dtype=np.float32),
                                [np.asarray(hole, dtype=np.float32) for hole in shape['holes']])
                        for shape in source['render_land']]
            reference = 'Native float32 source rings, including existing inland holes; GEOS containment.'
        tree = STRtree(polygons)
        probes, expected, directions, rings = [], [], [], {}
        classified = 0
        for line in row['line_classification_probes']:
            raw = np.asarray(source['render_coast'][line['line_index']], dtype=np.float32).astype(np.float64)
            clean = [raw[0]]
            for point in raw[1:]:
                if np.dot(point - clean[-1], point - clean[-1]) > .00000001:
                    clean.append(point)
            closed = np.dot(clean[0] - clean[-1], clean[0] - clean[-1]) < .00000001
            if closed:
                clean.pop()
            clean = np.asarray(clean)
            if line['side']:
                classified += 1
            if line['reason'].startswith('exact_source_'):
                rings[line['line_index']] = (clean, line['side'], closed)
            for probe in line['probes']:
                probes += [probe['left'], probe['right']]
                expected += [probe['left_land'], probe['right_land']]
                a = clean[probe['segment']]; b = clean[(probe['segment'] + 1) % len(clean)]
                midpoint = (a + b) * .5; delta = b - a
                left = np.asarray(probe['left']) - midpoint
                right = np.asarray(probe['right']) - midpoint
                directions.append(bool(delta[0] * left[1] - delta[1] * left[0] > 0 and
                                       delta[0] * right[1] - delta[1] * right[0] < 0))
        actual = np.zeros(len(probes), dtype=bool)
        if probes:
            hits = tree.query(shapely.points(probes), predicate='covered_by')
            actual[hits[0]] = True
        mismatches = np.flatnonzero(actual != np.asarray(expected, dtype=bool)).tolist()
        invalid_normals = [i for i, valid in enumerate(directions) if not valid]
        ring_results, undetermined = audit_ring_sides(tree, rings)
        wrong_ring_sides = [index for index, proof in ring_results.items()
                            if proof['native_side'] != proof['independent_side']]
        checks += [dict(name=mid + ':all_native_land_probes_match_independent_GEOS', passed=not mismatches),
                   dict(name=mid + ':probe_normals_match_mesh_cross_sections', passed=not invalid_normals),
                   dict(name=mid + ':reported_classification_count_matches', passed=classified == row['source_land_classified_lines']),
                   dict(name=mid + ':exact_ring_sides_independently_match_actual_mesh_containment',
                        passed=not undetermined and not wrong_ring_sides and
                        len(rings) == row['exact_source_boundary_classified_lines'])]
        records.append(dict(map_id=mid, source_map_sha256=sha(source_path), reference=reference,
                            native_probe_points=len(probes), classified_lines=classified,
                            neutral_fallback_lines=row['neutral_fallback_lines'],
                            exact_native_centerline_vertices_checked=row['native_source_vertices_checked'],
                            mismatched_probe_indices=mismatches, invalid_normal_indices=invalid_normals,
                            independent_ring_side_method='GEOS paired edge probes on archived native-float triangles, without native winding classifier.',
                            independently_resolved_rings=len(ring_results),
                            undetermined_ring_lines=undetermined, wrong_ring_sides=wrong_ring_sides,
                            independent_ring_probes=ring_results))
    result = dict(passed=all(check['passed'] for check in checks),
                  created_at_utc=datetime.now(timezone.utc).isoformat(), controller_sha256=sha(__file__),
                  native_report_sha256=sha(args.native), native_report_passed=native['passed'],
                  production_classifier_imported=False, source_boundaries_modified=False,
                  historical_shore_survey_claimed=False, physical_android_device_tested=False,
                  development_only=True, checks=checks, maps=records,
                  failures=[check for check in checks if not check['passed']])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(passed=result['passed'], checks=len(checks),
                         probe_points=sum(row['native_probe_points'] for row in records), failures=result['failures'])), flush=True)
    raise SystemExit(0 if result['passed'] else 1)


if __name__ == '__main__':
    main()
