"""Produce 56 additional, immutable geographically gated ground originals.

Uses only the selected Sub2 CLI through the common producer. The native queue
waits for the existing 666+74 source jobs, keeping gateway concurrency at three.
"""
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import argparse
import time
import generate_map_bank as base
import generate_settlement_bank as settlements

P = base.P
PLAN = P / 'presentation/data/map_surface_extension_plan.json'
REPORT = P / 'reports/map_surface_extension_generation.json'
EXTRA_COUNT = 56
ADDITIONAL_COUNT = 796
MAP_COUNT = 870


def plan():
    original, extension = settlements.plan()
    prefix = next(row['prompt'].partition('Material specification:\n')[0] +
                  'Material specification:\n' for row in original if row['category'] == 'tile')
    specs = [
        ('sandy_ground', 24, '#B8AA82 muted pale ochre desert sand: delicate fine wind-shaped sand grain, broad very shallow low-contrast tonal sweeps; no raised dunes or stones',
         'sourced_sandy_desert_ecoregion_excluding_river_oases'),
        ('arid_gravel', 16, '#A69E86 subdued gray-tan arid gravel ground: fine embedded angular mineral chips, broad compacted mineral soil, occasional darker tiny flat pebbles; no golden sand-dune language',
         'sourced_stony_desert_or_xeric_shrubland_ecoregion'),
        ('alluvial_soil', 16, '#A4A184 restrained olive-tan alluvial soil: fine silt grain, faint soft earth clods and sparse short grass blades; no plowed field, field boundary or cultivation grid',
         'sourced_low_relief_alluvial_or_riparian_region'),
    ]
    grain = ['fine interrupted nearly horizontal grain', 'tiny loosely separated curved wisps',
             'sparse short diagonal brush flecks', 'delicate irregular mineral pin-grain']
    drift = ['one wide gentle diagonal tonal current', 'broad diffuse overlapping rounded drift',
             'quiet center with sparse dispersed edge grain', 'long soft shallow curved bands',
             'wide irregular interlocking tonal zones', 'several faint asymmetric oval tonal zones']
    rows = []
    for family, count, subject, gate in specs:
        for index in range(count):
            rows.append(dict(id=f'tile_bank_{family}_{index+1:03d}', category='tile',
                family=family, variant=index+1, axis='', region='', role='', gate=gate,
                visible_bounds=[140, 110], source_revision='r001', runtime_import_max_dimension=256,
                prompt=prefix+subject+'. Grain structure: '+grain[index%4]+
                       '. Distribution: '+drift[index//4]+
                       '. Keep a coherent calm surface and narrow muted tonal range. No isolated symbol, raised landform, vegetation clump, river channel, marsh pool, invented geography or large spot.'))
    assert len(rows) == EXTRA_COUNT and len({row['prompt'] for row in rows}) == EXTRA_COUNT
    assert not ({row['id'] for row in rows} & {row['id'] for row in original+extension})
    payload = dict(format=1, purpose='Geographically sourced sand, gravel and alluvial ground materials',
        additional_independent_sources=EXTRA_COUNT, total_additional_sources=ADDITIONAL_COUNT,
        total_map_sources=MAP_COUNT, original_images_modified=False,
        source_route='sub2-image-gen/gpt-image-2.5/high', assets=rows)
    if PLAN.exists():
        if settlements.read(PLAN) != payload:
            raise RuntimeError('Surface extension is immutable; make an explicit revision')
    else:
        base.write_json(PLAN, payload)
    return rows


def write_report(complete, failures, started, running=False, waiting=False):
    base.write_json(REPORT, dict(created_at_utc=datetime.now(timezone.utc).isoformat(),
        passed=len(complete)==EXTRA_COUNT and not failures, running=running,
        waiting_for_settlement_queue=waiting, requested=EXTRA_COUNT, completed=len(complete),
        elapsed_seconds=round(time.monotonic()-started, 1), catalog_sha256=base.sha(PLAN),
        source_route='sub2-image-gen/gpt-image-2.5/high', original_images_modified=False,
        manual_compositing=False, formal_art_approval=False, failures=failures,
        assets=sorted(complete.values(), key=lambda row: row['id'])))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--prepare-only', action='store_true')
    parser.add_argument('--after-settlements', action='store_true')
    parser.add_argument('--workers', type=int, default=3)
    args = parser.parse_args(); rows = plan(); started = time.monotonic()
    if args.prepare_only:
        print('56 additional ground originals planned; final map inventory 870', flush=True); return
    if args.after_settlements:
        write_report({}, [], started, waiting=True)
        while True:
            report = settlements.read(settlements.REPORT) if settlements.REPORT.exists() else {}
            if report.get('passed') and not report.get('running'):break
            if report and not report.get('running') and not report.get('waiting_for_base_queue'):
                raise RuntimeError('Settlement production did not pass; do not bypass the queue')
            if time.monotonic()-started > 28800:
                raise RuntimeError('Upstream production exceeded native queue deadline')
            time.sleep(10)
    complete = {row['id']: result for row in rows if (result:=base.measure(row)) is not None}
    grouped = defaultdict(deque)
    for row in rows:
        if row['id'] not in complete:grouped[row['family']].append(row)
    queue = []
    while any(grouped.values()):
        for family in grouped:
            if grouped[family]:queue.append(grouped[family].popleft())
    failures = []; write_report(complete, failures, started, bool(queue))
    with ThreadPoolExecutor(max_workers=max(1, min(3, args.workers))) as pool:
        futures = {pool.submit(base.generate,row):row['id'] for row in queue}
        for future in as_completed(futures):
            aid = futures[future]
            try:complete[aid] = future.result()
            except Exception as error:failures.append(dict(id=aid, reason=str(error)))
            write_report(complete, failures, started, True)
            print(f'{len(complete)}/56 ground originals; {len(failures)} failed; {aid}', flush=True)
    write_report(complete, failures, started)
    raise SystemExit(bool(failures))


if __name__ == '__main__':
    main()
