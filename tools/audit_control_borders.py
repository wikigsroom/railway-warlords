"""Check political strokes against both immutable source rings and natural shores."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import sys

P = Path(__file__).resolve().parents[1]
ROOT = P.parents[1]
sys.path.insert(0, str(ROOT / '.toolchain/python-libs'))
from shapely.geometry import LineString, MultiLineString
from shapely.ops import unary_union


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit('Preserve the previous audit; choose a new output path.')
    graph_path = P / 'presentation/data/control_border_graph.json'
    graph = read(graph_path)
    checks = []
    rows = []

    def verify(value, name):
        checks.append(dict(name=name, passed=bool(value)))

    for mid, entry in graph['maps'].items():
        source_path = P / entry['zone_source_file']
        verify(sha(source_path) == entry['zone_source_sha256'], mid + ':zone_source_hash')
        map_path = P / 'content/maps' / (mid + '.json')
        verify(sha(map_path) == entry['map_sha256'], mid + ':map_source_hash')
        geometry = read(map_path)
        source = read(source_path)
        if 'maps' in source:
            source = source['maps'][mid]
        coast_frame = unary_union([MultiLineString(geometry['render_coast']),
                                   LineString(geometry['render_extent'] + [geometry['render_extent'][0]])])
        for year, period in entry['periods'].items():
            boundaries = {}
            for row in source['control_zones_by_year'][year]:
                boundaries.setdefault(row['city_id'], []).extend(LineString(line) for line in row['borders'] if len(line) >= 2)
            boundaries = {key: unary_union(value) for key, value in boundaries.items()}
            seen = set()
            all_lines = []
            source_supported = True
            shore_clear = True
            unique_pairs = True
            length_correct = True
            minimum_clearance = float('inf')
            for edge in period['edges']:
                key = (edge['city_a'], edge['city_b'])
                unique_pairs = unique_pairs and key[0] < key[1] and key not in seen
                seen.add(key)
                a = boundaries[key[0]]
                b = boundaries[key[1]]
                lines = [LineString(line) for line in edge['lines']]
                all_lines.extend(lines)
                for line in lines:
                    # The first ring must support the entire output line, not
                    # merely its endpoints. The second ring allows only the
                    # documented milliworld source quantization tolerance.
                    source_supported = source_supported and line.difference(a.buffer(.000002)).length < .00001
                    source_supported = source_supported and line.difference(b.buffer(.002002)).length < .00001
                    clearance = line.distance(coast_frame)
                    minimum_clearance = min(minimum_clearance, clearance)
                    shore_clear = shore_clear and clearance >= .001998
                length_correct = length_correct and abs(sum(line.length for line in lines) - edge['length_world']) < .000001
            total = sum(line.length for line in all_lines)
            combined = unary_union(all_lines)
            unique = combined.length
            # An independent exact intersection supplies a lower bound on
            # required shared borders. Do not let duplicate removal erase
            # legitimate boundaries just to make the overdraw check pass.
            ids = sorted(boundaries)
            missing_exact_length = 0.0
            covered = combined.buffer(.00201)
            excluded = coast_frame.buffer(.002)
            for i, a in enumerate(ids):
                for b in ids[i + 1:]:
                    exact = boundaries[a].intersection(boundaries[b]).difference(excluded)
                    missing_exact_length += exact.difference(covered).length
            prefix = mid + ':' + year
            verify(source_supported, prefix + ':entire_strokes_supported_by_both_real_source_boundaries')
            verify(shore_clear, prefix + ':natural_coast_and_map_frame_have_no_political_stroke')
            verify(unique_pairs and abs(total - unique) < .01, prefix + ':no_duplicated_pair_or_overdrawn_line')
            verify(length_correct and period['edge_pairs'] == len(period['edges']), prefix + ':stored_geometry_metrics_match_lines')
            verify(missing_exact_length < .1, prefix + ':exact_source_shared_boundaries_are_retained')
            rows.append(dict(map_id=mid, year=year, pairs=len(seen), shared_length_world=total,
                             original_whole_outline_length_world=period['source_outline_length_world'],
                             missing_exact_shared_length_world=missing_exact_length,
                             minimum_coast_or_frame_clearance_world=minimum_clearance))
    diff = subprocess.run(['git', 'diff', '--name-only', '0d78d6910239eab49733c78f1b9882155a7915ed', '--',
                           'content', 'domain', 'ai', 'persistence', 'assets', 'audio'],
                          cwd=P, check=True, capture_output=True, text=True).stdout.splitlines()
    verify(not diff, 'rules_geography_media_and_economy_sources_unchanged_from_0d78d69')
    report = dict(passed=all(row['passed'] for row in checks), checks=checks, maps_and_periods=rows,
                  graph_sha256=sha(graph_path), code_sha256=sha(Path(__file__)),
                  compared_source_commit='0d78d6910239eab49733c78f1b9882155a7915ed', source_changes=diff,
                  source_geometry_modified=False, historical_military_frontiers_claimed=False,
                  shipping_exe=False, physical_android_device_tested=False)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    failed = [row['name'] for row in checks if not row['passed']]
    print(json.dumps(dict(passed=report['passed'], checks=len(checks), failures=failed)), flush=True)
    raise SystemExit(0 if report['passed'] else 1)


if __name__ == '__main__':
    main()
