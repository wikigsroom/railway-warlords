"""Reproject local catalogs, preserving every unrelated authored place and map."""
from datetime import datetime, timezone
import argparse
import json
from pathlib import Path
import subprocess
import sys

import refine_local_maps as local

P, WORK = local.P, local.WORK
REPORT = P / 'reports/local_map_refinement'
PROGRESS = WORK / 'presentation_progress.json'


def refresh_settlements():
    from compile_settlements import projector, control_zones
    from compile_coast_detail import encode
    path = P / 'presentation/data/settlements_v023.json'
    before_path = WORK / 'prior_catalogues' / path.name
    before = local.read(before_path)
    after = local.read(before_path)
    for mid in local.MAPS:
        map_path = P / 'content/maps' / (mid + '.json')
        data = local.read(map_path)
        world = projector(data)
        entry = after['maps'][mid]
        for marker in entry['markers']:
            marker['world'] = [round(v, 2) for v in world(marker['longitude'], marker['latitude'])]
        entry['control_zones_by_year'] = {year: control_zones(data, year) for year in ['1920', '1922', '1924']}
        entry['map_sha256'] = local.sha(map_path)
    unchanged = [mid for mid in before['maps'] if mid not in local.MAPS]
    assert all(before['maps'][mid] == after['maps'][mid] for mid in unchanged)
    assert all(before[key] == after[key] for key in before if key != 'maps')
    local.write(path, after)
    compilation = local.read(WORK / 'prior_settlement_compilation.json')
    compilation['presentation_data_sha256'] = local.sha(path)
    for mid in local.MAPS:
        compilation['immutable_gameplay_maps'][mid] = local.sha(P / 'content/maps' / (mid + '.json'))
    compilation['local_reprojection'] = dict(revision='0.2.34', maps=local.MAPS, unchanged_place_records=True,
        unchanged_other_map_entries=unchanged, surveyed_historical_county_or_wharf_boundaries_added=False)
    local.write(P / 'reports/settlement_compilation.json', compilation)
    # The four coastal meshes consume only their own unchanged control entries.
    # Rebind the containing file's hash only after proving those inputs identical;
    # numerical geometry is kept byte-for-byte in the decoded source structure.
    catalog_path = P / 'presentation/data/coast_geometry.json'
    catalog = local.read(WORK / 'prior_catalogues/coast_geometry.json')
    rebindings = []
    for mid, entry in catalog['maps'].items():
        assert before['maps'].get(mid) == after['maps'].get(mid)
        target = P / entry['file']
        old = local.read(WORK / 'prior_catalogues' / target.name)
        assert old['settlement_source_sha256'] == local.sha(before_path)
        new = dict(old, settlement_source_sha256=local.sha(path))
        assert {k:v for k,v in old.items() if k != 'settlement_source_sha256'} == {k:v for k,v in new.items() if k != 'settlement_source_sha256'}
        target.write_bytes(encode(new))
        rebindings.append(dict(map_id=mid, original_mesh_sha256=entry['data_sha256'],
            current_mesh_sha256=local.sha(target), all_geometry_values_unchanged=True,
            per_map_settlement_inputs_unchanged=True))
        entry['data_sha256'] = local.sha(target)
    catalog_path.write_bytes(encode(catalog))
    local.write(REPORT / 'settlement_reprojection.json', dict(passed=True, maps_reprojected=local.MAPS,
        no_settlements_invented=True, other_map_entries_unchanged=unchanged,
        previous_catalog_sha256=local.sha(before_path), current_catalog_sha256=local.sha(path),
        coastal_metadata_rebindings=rebindings, source_rasters_modified=False))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--settlements-only', action='store_true')
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    if args.settlements_only:
        refresh_settlements()
        return 0
    REPORT.mkdir(parents=True, exist_ok=True)
    maps = {path.name: local.sha(path) for path in (P / 'content/maps').glob('*.json')}
    steps = [('settlements', [sys.executable, '-X', 'utf8', __file__, '--settlements-only'])]
    steps += [(name, [sys.executable, '-X', 'utf8', str(P / 'tools' / (name + '.py'))]) for name in
        ['compile_hydrography', 'compile_fine_hydrography', 'compile_surface_regions', 'compile_terrain_surfaces']]
    steps.append(('compile_ground_coverage', [sys.executable, '-X', 'utf8', str(P / 'tools/compile_ground_coverage.py'), '--maps', *local.MAPS]))
    state = dict(terminal=False, passed=False, map_hashes=maps, stages=[], started_at_utc=datetime.now(timezone.utc).isoformat())
    first = 0
    if args.resume:
        previous = local.read(PROGRESS)
        assert previous['terminal'] and not previous['passed'] and previous['map_hashes'] == maps
        assert previous['stages'][-1]['exit_code'] != 0
        state = previous
        state.setdefault('terminal_attempts', []).append(previous['stages'][-1])
        state['stages'] = previous['stages'][:-1]
        state['terminal'] = False
        first = len(state['stages'])
    for name, command in steps[first:]:
        state['stage'] = name
        local.write(PROGRESS, state)
        print('LOCAL_PRESENTATION_BEGIN ' + name, flush=True)
        path = REPORT / (name + '.log')
        with path.open('w', encoding='utf-8') as output:
            result = subprocess.run(command, cwd=P, stdout=output, stderr=subprocess.STDOUT)
        state['stages'].append(dict(name=name, exit_code=result.returncode, log=path.relative_to(P).as_posix()))
        assert maps == {path.name: local.sha(path) for path in (P / 'content/maps').glob('*.json')}, 'Map changed during presentation compilation.'
        if result.returncode:
            state.update(terminal=True, passed=False)
            local.write(PROGRESS, state)
            print('LOCAL_PRESENTATION_FAILED ' + name, flush=True)
            return 1
        print('LOCAL_PRESENTATION_PASS ' + name, flush=True)
    state.update(terminal=True, passed=True, finished_at_utc=datetime.now(timezone.utc).isoformat())
    local.write(PROGRESS, state)
    local.write(REPORT / 'presentation_pipeline.json', state)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
