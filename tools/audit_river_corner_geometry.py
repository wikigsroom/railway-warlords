"""Independently compare native river display geometry with archived sources."""
from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import json
import math
import sys

P = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(P.parents[1] / '.toolchain/python-libs'))
import shapely
from shapely.geometry import LineString, Point


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path): return json.loads(Path(path).read_bytes())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--revised', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists()
    baseline, revised = read(args.baseline), read(args.revised)
    assert baseline['passed'] and revised['passed'] and revised['revised_profile_required']
    assert baseline['native_content_hash'] == revised['native_content_hash']
    assert baseline['map_fingerprints'] == revised['map_fingerprints']
    assert len(baseline['rows']) == len(revised['rows'])
    checks, measurements = [], []
    def check(ok, name, **extra): checks.append(dict(name=name, passed=bool(ok), **extra))
    fine = read(P / 'presentation/data/hydrography_fine.json')
    detail = read(P / 'presentation/data/hydrography_detail.json')
    maps = {path.stem: read(path) for path in (P / 'content/maps').glob('*.json') if path.stem != 'catalog'}
    max_forward = 0.0; max_hausdorff = 0.0; changed = 0; refined = 0
    for old, row in zip(baseline['rows'], revised['rows']):
        identity = f"{row['map']}:{row['role']}:{row['index']}"
        check(all(old[key] == row[key] for key in ['map', 'role', 'index', 'source', 'source_reach_id', 'radius_m', 'budget_m']),
              'source_topology_and_budget_preserved:' + identity)
        mid = row['map']; index = row['index']
        raw_rows = fine.get('major_presentation_replacements', {}).get(mid, []) if row['role'] == 'major_rows' else []
        if row['role'] == 'major_rows':
            archived = raw_rows[index]['points'] if raw_rows else maps[mid]['render_rivers'][index]
        else:
            raw_rows = detail.get('maps', {}).get(mid, []) + fine.get('maps', {}).get(mid, [])
            archived = raw_rows[index]['points']
        check(all(math.dist(a, b) <= .003 for a, b in zip(archived, row['source'])) and len(archived) == len(row['source']),
              'native_original_matches_archived_array:' + identity)
        # Use the archived JSON's double coordinates, independently of the
        # engine's float32 original array, for the geographic-distance gate.
        source = LineString(archived); display = LineString(row['display'])
        budget = row['budget_m'] * 48 / row['radius_m']; tolerance = .004
        forward = max(source.distance(Point(point)) for point in row['display'])
        # The sampled metric is descriptive. Continuous containment of BOTH
        # complete lines in the other line's round buffer is the actual gate.
        # GEOS's circular buffer approximation is inscribed, so coverage cannot
        # pass merely by overshooting the allowed Euclidean-distance budget.
        hd = float(shapely.hausdorff_distance(source, display, densify=.0625))
        check(row['source'][0] == row['display'][0] and row['source'][-1] == row['display'][-1],
              'exact_endpoints:' + identity)
        within = (source.equals_exact(display, tolerance) if budget == 0 else
                  source.buffer(budget, quad_segs=32).covers(display) and
                  display.buffer(budget, quad_segs=32).covers(source))
        check(within and forward <= (budget if budget > 0 else tolerance) and hd <= (budget if budget > 0 else tolerance),
              'continuous_two_way_geos_buffers_within_60m:' + identity,
              continuous_bidirectional_containment=within, sampled_hausdorff_world=hd, budget_world=budget)
        if row['source_reach_id'] <= 0:
            check(row['source'] == row['display'] == old['display'], 'non_hydrorivers_lines_remain_exact:' + identity)
        if row['display'] != old['display']: changed += 1
        if len(row['display']) > len(old['display']): refined += 1
        if budget > 0:
            max_forward = max(max_forward, forward * row['radius_m'] / 48)
            max_hausdorff = max(max_hausdorff, hd * row['radius_m'] / 48)
        measurements.append(dict(identity=identity, source_reach_id=row['source_reach_id'],
            source_vertices=len(row['source']), old_vertices=len(old['display']), new_vertices=len(row['display']),
            forward_world=forward, sampled_hausdorff_world=hd, budget_world=budget,
            continuous_bidirectional_containment=within))
    fixtures = []
    for row in revised['fixtures']:
        source, display = LineString(row['source']), LineString(row['display'])
        hd = float(shapely.hausdorff_distance(source, display, densify=.01))
        check(hd <= row['budget_world'] + .0001, 'all_angle_bidirectional_fixture:' + str(row['angle_degrees']),
              sampled_hausdorff_world=hd)
        fixtures.append(dict(angle_degrees=row['angle_degrees'], sampled_hausdorff_world=hd,
                             maximum_turn_degrees=row['maximum_turn_degrees']))
    check(revised['right_angle_maximum_turn_degrees'] < 16 < baseline['right_angle_maximum_turn_degrees'],
          'actual_native_right_angle_tessellation_is_smoother_than_baseline')
    check(changed > 1000 and refined > 1000, 'actual_geographic_reaches_receive_revised_geometry')
    result = dict(passed=all(row['passed'] for row in checks), created_at_utc=datetime.now(timezone.utc).isoformat(),
        development_only=True, controller_sha256=sha(__file__), baseline_sha256=sha(args.baseline),
        revised_sha256=sha(args.revised), native_content_hash=revised['native_content_hash'],
        actual_reaches_checked=len(measurements), actual_display_reaches_changed=changed,
        actual_reaches_with_more_curve_vertices=refined, maximum_curve_vertex_deviation_m=max_forward,
        maximum_sampled_symmetric_hausdorff_m=max_hausdorff,
        source_geometry_modified=False, rule_geometry_modified=False, source_endpoints_preserved=True,
        historic_channel_survey_claimed=False, measured_river_width_claimed=False,
        checks=checks, failures=[row for row in checks if not row['passed']], measurements=measurements, fixtures=fixtures)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({key: result[key] for key in ['passed','actual_reaches_checked','actual_display_reaches_changed',
        'maximum_curve_vertex_deviation_m','maximum_sampled_symmetric_hausdorff_m']}) + '; checks=' + str(len(checks)), flush=True)
    raise SystemExit(0 if result['passed'] else 1)


if __name__ == '__main__': main()
