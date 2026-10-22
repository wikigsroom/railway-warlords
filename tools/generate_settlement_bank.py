"""Add 74 settlement originals to the immutable 666-source base production.

This explicit extension improves the actual Chinese campaign's diversity.
It does not alter any base prompt, original PNG or historical settlement.
The optional native wait starts after the base CLI queue has released its slots.
"""
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import argparse
import json
import shutil
import time
import generate_map_bank as base

P, ROOT = base.P, base.ROOT
PLAN = P / 'presentation/data/map_settlement_extension_plan.json'
REPORT = P / 'reports/map_settlement_extension_generation.json'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def plan():
    originals = base.initialize()
    templates = {row['family']: row for row in originals if row['category'] == 'building'}
    # Counts are additional originals; existing variants 001/002 are preserved.
    specs = [('village_north_china', 24), ('market_north_china', 12),
             ('county_north_china', 12), ('capital_north_china', 6),
             ('station_north_china', 8), ('dock_north_china', 4),
             ('village_south_china', 8)]
    layouts = [
        'a shallow crescent around an open foreground court, tallest roof at the left rear',
        'a narrow diagonal lane between two unequal staggered roof groups',
        'a broad open L-shaped courtyard, short annex projecting toward the lower right',
        'a compact offset T-shaped arrangement, one higher rear roof and two low wings',
        'two unequal interlocking courtyard groups, one visibly open corner',
        'a broken stepped silhouette rising from low left-front to taller right-rear',
        'a long shallow zigzag of connected roofs around a narrow unpaved passage',
        'an irregular triangular roof group with a clear open forecourt and short side wing',
    ]
    massing = [
        'broad long roof ridges, one low square annex; quiet light-gray masonry',
        'several short unequal roof ridges, one deeper courtyard; restrained warm-gray masonry',
        'one wide rear roof and several narrow lower roofs; muted dark-gray masonry',
    ]
    rows = []
    for family, count in specs:
        template = templates[family]
        role, region = template['role'], template['region']
        start = max(row['variant'] for row in originals if row['family'] == family) + 1
        prefix = template['prompt'].partition('Regional visual language: ')[0]
        for ordinal in range(count):
            number = start + ordinal
            row = {key: value for key, value in template.items() if key != 'prompt'}
            row['variant'] = number
            row['id'] = f'building_bank_{family}_{number:03d}'
            if role in ['village', 'market', 'county', 'capital']:
                size = {'village': 'four to six modest houses', 'market': 'eight to ten modest houses with two simple awnings',
                        'county': 'twelve to sixteen roof volumes with a restrained larger administrative courtyard',
                        'capital': 'twenty to twenty-four roofs with two restrained larger civic courtyards'}[role]
                subject = f'One {role} settlement SYMBOL, {size}. No surrounding walls, towers, temple, pagoda, monument or invented landmark.'
            elif role == 'station':
                subject = 'One modest late nineteenth/early twentieth-century railway station SYMBOL: low passenger building, one shallow platform canopy and a short freight shed. No visible tracks, locomotive, signs, clock lettering or modern infrastructure.'
            else:
                subject = 'One modest historical port warehouse SYMBOL: two or three low warehouses, one short simple timber pier finger and a small hand-operated hoist. No water rectangle, boats, ship, large modern crane or named port landmark.'
            row['prompt'] = (prefix + 'Regional visual language: ' + base.REGIONS[region] + '\n' + subject
                             + '\nDistinct whole-group silhouette: ' + layouts[ordinal % len(layouts)]
                             + '. Roof massing and material: ' + massing[ordinal // len(layouts)]
                             + '. Preserve clear large roof planes, grounded cast shadow and architectural depth. No detached specimen rows, opaque ground platform or decorative surrounding landscape.')
            rows.append(row)
    assert len(rows) == 74 and len({row['prompt'] for row in rows}) == 74
    assert not ({row['id'] for row in rows} & {row['id'] for row in originals})
    value = dict(format=1, purpose='Additional Chinese campaign settlement diversity; base catalog remains immutable',
                 base_catalog_sha256=base.sha(base.CATALOG), additional_independent_sources=74,
                 complete_additional_sources=740, baseline_map_assets=74, complete_map_assets=814,
                 source_route='sub2-image-gen/gpt-image-2.5/high', assets=rows)
    if PLAN.exists():
        if read(PLAN) != value:
            raise RuntimeError('Immutable settlement extension differs; use an explicit revision')
    else:
        base.write_json(PLAN, value)
    return originals, rows


def write_report(complete, failures, started, running, waiting=False):
    base.write_json(REPORT, dict(created_at_utc=datetime.now(timezone.utc).isoformat(),
        passed=len(complete) == 74 and not failures, running=running, waiting_for_base_queue=waiting,
        requested=74, completed=len(complete), elapsed_seconds=round(time.monotonic()-started, 1),
        base_catalog_sha256=base.sha(base.CATALOG), extension_catalog_sha256=base.sha(PLAN),
        source_route='sub2-image-gen/gpt-image-2.5/high', original_images_modified=False,
        manual_compositing=False, formal_art_approval=False, failures=failures,
        assets=sorted(complete.values(), key=lambda row: row['id'])))


def install(originals, extension):
    if (P/'presentation/data/map_urban_extension_plan.json').exists():
        raise RuntimeError('Urban extension is installed; preserve its reviewed originals and active family bindings. Do not rebuild the earlier catalog over this revision.')
    from map_bank_inventory import planned_rows, production_rows, ADDITIONAL_COUNT, MAP_COUNT
    production_rows(require_complete=True)
    measured = [base.measure(row) for row in planned_rows()]
    if any(row is None for row in measured) or len(measured) != ADDITIONAL_COUNT:
        raise RuntimeError('All 796 independent additional originals are required')
    if len({row['source_sha256'] for row in measured}) != ADDITIONAL_COUNT:
        raise RuntimeError('Duplicate originals are not counted or installed')
    path = P / 'assets/manifest.json'
    manifest = read(path); current = {row['id']: row for row in manifest['assets']}
    visuals = dict(format=1, baseline_count=74, base_additional_count=666,
                   settlement_extension_count=74, surface_extension_count=56,
                   additional_count=ADDITIONAL_COUNT, total_map_assets=MAP_COUNT,
                   original_images_modified=False, full_texture_draw=True, families={}, records={})
    for row in measured:
        target = P / row['engine_path'].removeprefix('res://')
        if target.exists() and base.sha(target) != row['source_sha256']:
            raise RuntimeError('Refuse to replace an existing original: ' + row['id'])
        if not target.exists():
            shutil.copyfile(ROOT / row['source_file'], target)
        current[row['id']] = row
        visuals['families'].setdefault(row['family'], []).append(row['id'])
        visuals['records'][row['id']] = {key: row[key] for key in
            ['category', 'family', 'variant', 'axis', 'region', 'role', 'gate', 'visible_bounds',
             'actual_dimensions', 'alpha_bounds', 'source_sha256']}
        visuals['records'][row['id']]['dimensions'] = visuals['records'][row['id']].pop('actual_dimensions')
    manifest['assets'] = sorted(current.values(), key=lambda row: row['id'])
    total = sum(row['category'] in ['tile', 'scenery', 'building'] for row in current.values())
    if total != MAP_COUNT:
        raise RuntimeError('Unexpected map inventory; baseline is not replaceable')
    base.write_json(path, manifest)
    base.write_json(P / 'presentation/data/map_bank_visuals.json', visuals)
    base.write_json(P / 'reports/map_bank_installation.json', dict(passed=True, installed=ADDITIONAL_COUNT,
        base_additional_sources=666, settlement_extension_sources=74, surface_extension_sources=56,
        baseline=74, total_map_assets=total,
        unique_new_original_hashes=ADDITIONAL_COUNT, source_pngs_modified=False, formal_art_approval=False,
        source_catalog_sha256=base.sha(base.CATALOG), extension_catalog_sha256=base.sha(PLAN),
        surface_catalog_sha256=base.sha(P / 'presentation/data/map_surface_extension_plan.json'),
        runtime_visuals_sha256=base.sha(P / 'presentation/data/map_bank_visuals.json')))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--workers', type=int, default=3)
    parser.add_argument('--prepare-only', action='store_true')
    parser.add_argument('--after-base', action='store_true')
    parser.add_argument('--install', action='store_true')
    args = parser.parse_args(); started = time.monotonic()
    originals, rows = plan()
    if args.prepare_only:
        print('Immutable 74-source settlement extension ready; final map inventory target 814', flush=True)
        return
    if args.install:
        install(originals, rows)
        print('796 independent unchanged originals installed; 870 total map assets', flush=True)
        return
    if args.after_base:
        write_report({}, [], started, False, waiting=True)
        while True:
            value = read(base.REPORT)
            if not value['running']:
                if not value['passed']:
                    raise RuntimeError('Base production failed; do not contend for its worker slots')
                break
            if time.monotonic()-started > 21600:
                raise RuntimeError('Base producer has not completed within the native queue deadline')
            time.sleep(10)
    complete = {row['id']: result for row in rows if (result := base.measure(row)) is not None}
    families = defaultdict(deque)
    for row in rows:
        if row['id'] not in complete:
            families[row['family']].append(row)
    pending_rows = []
    while any(families.values()):
        for family in families:
            if families[family]:
                pending_rows.append(families[family].popleft())
    failures = []; write_report(complete, failures, started, bool(pending_rows))
    with ThreadPoolExecutor(max_workers=max(1, min(3, args.workers))) as pool:
        pending = {pool.submit(base.generate, row): row['id'] for row in pending_rows}
        for future in as_completed(pending):
            aid = pending[future]
            try:
                complete[aid] = future.result()
            except Exception as error:
                failures.append(dict(id=aid, reason=str(error)))
            write_report(complete, failures, started, True)
            print(f'{len(complete)}/74 additional settlement originals; {len(failures)} failed; {aid}', flush=True)
    write_report(complete, failures, started, False)
    raise SystemExit(bool(failures))


if __name__ == '__main__':
    main()
