"""Check actual native river contacts without repeating the fillet algorithm."""
from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import json
import sys

P = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(P.parents[1] / '.toolchain/python-libs'))
from shapely.geometry import LineString
from shapely.strtree import STRtree


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def contacts(lines):
    pairs = STRtree(lines).query(lines, predicate='intersects')
    return {(int(a), int(b)) for a, b in zip(*pairs) if a < b}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--revised', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists()
    baseline = json.loads(args.baseline.read_bytes())
    revised = json.loads(args.revised.read_bytes())
    assert baseline['passed'] and revised['passed']
    assert baseline['native_content_hash'] == revised['native_content_hash']
    maps, checks = [], []
    for map_id in revised['map_fingerprints']:
        old = [row for row in baseline['rows'] if row['map'] == map_id and row['source_reach_id'] > 0]
        new = [row for row in revised['rows'] if row['map'] == map_id and row['source_reach_id'] > 0]
        assert len(old) == len(new)
        if not new:
            maps.append(dict(map_id=map_id, hydrorivers_reaches=0, applicable=False))
            continue
        assert all((a['source_reach_id'], a['source']) == (b['source_reach_id'], b['source']) for a, b in zip(old, new))
        source = [LineString(row['source']) for row in new]
        previous = [LineString(row['display']) for row in old]
        display = [LineString(row['display']) for row in new]
        source_pairs, old_pairs, new_pairs = contacts(source), contacts(previous), contacts(display)
        def describe(pairs):
            return [dict(a=dict(role=new[a]['role'], index=new[a]['index'], reach_id=new[a]['source_reach_id']),
                         b=dict(role=new[b]['role'], index=new[b]['index'], reach_id=new[b]['source_reach_id']))
                    for a, b in sorted(pairs)]
        added = new_pairs - source_pairs
        missing = source_pairs - new_pairs
        self_added = [i for i, (a, b) in enumerate(zip(source, display)) if a.is_simple and not b.is_simple]
        checks += [dict(name=map_id + ':no_new_source_contacts', passed=not added),
                   dict(name=map_id + ':no_lost_source_contacts', passed=not missing),
                   dict(name=map_id + ':no_new_self_intersections', passed=not self_added)]
        maps.append(dict(map_id=map_id, applicable=True, hydrorivers_reaches=len(new),
                         source_contact_pairs=len(source_pairs), previous_contact_pairs=len(old_pairs),
                         revised_contact_pairs=len(new_pairs), added_vs_source=describe(added),
                         missing_vs_source=describe(missing), added_vs_previous=describe(new_pairs - old_pairs),
                         removed_vs_previous=describe(old_pairs - new_pairs), new_self_intersections=self_added,
                         existing_source_non_simple=sum(not line.is_simple for line in source)))
        print(json.dumps(dict(map_id=map_id, reaches=len(new), source_contacts=len(source_pairs),
                              revised_contacts=len(new_pairs), added=len(added), missing=len(missing),
                              new_self_intersections=len(self_added))), flush=True)
    report = dict(passed=all(check['passed'] for check in checks),
                  created_at_utc=datetime.now(timezone.utc).isoformat(),
                  controller_sha256=sha(__file__), baseline_sha256=sha(args.baseline), revised_sha256=sha(args.revised),
                  native_content_hash=revised['native_content_hash'], development_only=True,
                  predicate='GEOS exact segment intersection; native float32 source and native display coordinates',
                  scope='Within HydroRIVERS only. No assumption that mixed Natural Earth lines form an identical graph.',
                  physical_android_device_tested=False, formal_art_approval=False, maps=maps, checks=checks,
                  failures=[check for check in checks if not check['passed']])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print('CONTACT_GRAPH ' + str(report['passed']), flush=True)
    raise SystemExit(0 if report['passed'] else 1)


if __name__ == '__main__':
    main()
