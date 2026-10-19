"""Generate three independent water originals using the mandated Sub2 CLI.

No image pixels are written by this tool. Installation copies original bytes;
the existing sources and every failed generation log remain untouched.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import argparse
import json
import shutil
import generate_map_bank as base

P = base.P
RAW = base.ROOT / 'output/imagegen/warlord/water_materials_v0227/originals'
PLAN = P / 'presentation/data/water_material_plan.json'
REPORT = P / 'reports/water_material_generation.json'

STYLE = '''ONE original seamless, opaque, edge-to-edge hand-painted water
material for a polished historical turn-based strategy map. Exact top-down
flat surface, no perspective and no horizon. Calm connected blue-green water,
subtle short irregular broken ripples with very low relief, restrained matte
painted realism and shallow upper-left illumination. The whole image must
remain visually calm when repeated across a large sea and reduced to 256 px.
Use small softly connected tonal variations, never large alternating light
and dark blotches. About ninety percent quiet water and ten percent delicate
broken surface strokes. Uniform overall value, no bright central focus, no
edge vignette. Small ripple marks are about 5-18 px wide at 1024 resolution.
Absolutely no land, grass, soil, algae patches, brown or ochre patches, islands,
rocks, coasts, riverbanks, channels, underwater terrain, pools, depth contours,
foam bands, surf, large waves, caustic cells, repeating circles, hexagons, grid,
stars, dots, paper weave, words, border, diagram, panels, UI or watermark.
No photographic speckle or noisy sandpaper. Do not copy existing game artwork.
This is a representative surface, not a claim of measured local water color.
WATER IDENTITY:
'''


def rows():
    subjects = [
        ('sea', 'tile_water_sea_v0227',
         'Muted deep teal-blue sea, base #3C6974 with quiet #497782 ripple strokes '
         'and very restrained #335E69 troughs. A continuous open sea, sparse '
         'short uneven near-horizontal ripple dashes, not a quilt or patches.'),
        ('river', 'tile_water_river_v0227',
         'Muted jade-teal river water, base #58878A with quiet #6A9898 surface '
         'strokes and #4D777E shallow shadows. Fine short flowing brush dashes, '
         'never brown silt bars, farmland, islands, a drawn channel or banks.'),
        ('inland', 'tile_water_inland_v0227',
         'Still inland water, muted cool sage-blue base #527D80 with quiet '
         '#638D8E sparse short ripple arcs and #487176 gentle troughs. '
         'No dark central basin, aquatic plants, shore or added water extent.'),
    ]
    return [dict(id=asset_id, category='tile', family=family, variant=1,
                 axis='', region='', role='', source_revision='r001',
                 visible_bounds=[256, 256], runtime_import_max_dimension=512,
                 gate='existing_sourced_' + family + '_geometry_only',
                 prompt=STYLE + subject) for family, asset_id, subject in subjects]


def install(items):
    review = json.loads((P / 'reports/water_material_source_review.json').read_text(encoding='utf-8'))
    viewed = {row['id']: row for row in review['images']}
    values = [base.measure(row) for row in items]
    assert len(values) == 3 and all(values)
    assert len({row['source_sha256'] for row in values}) == 3
    manifest_path = P / 'assets/manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    registered = {row['id']: row for row in manifest['assets']}
    for row in values:
        assert viewed[row['id']]['viewed_complete_original']
        assert viewed[row['id']]['sha256'] == row['source_sha256']
        assert row['alpha_min'] == 255, 'Water must not reveal a checkerboard'
        row.update(style_version='warlord_water_materials_v0227',
                   revision='water_materials_v0227_r001',
                   era='representative_water_surface_not_measured_historical_color',
                   state='generated_scoped_source_review_complete', game_ready=False,
                   visual_review='Whole original viewed; native integration and formal art approval tracked separately')
        for source, target in [
            (base.ROOT / row['source_file'], P / row['engine_path'].removeprefix('res://')),
            (base.ROOT / row['prompt_file'], P / 'docs/asset-prompts' / (row['id'] + '.txt')),
        ]:
            if target.exists():
                assert base.sha(target) == base.sha(source), 'Immutable bytes differ'
            else:
                shutil.copyfile(source, target)
        if row['id'] in registered:
            assert registered[row['id']]['source_sha256'] == row['source_sha256']
        registered[row['id']] = row
    manifest['assets'] = sorted(registered.values(), key=lambda row: row['id'])
    base.write_json(manifest_path, manifest)
    print('Installed three immutable Sub2 water originals.', flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--install', action='store_true')
    args = parser.parse_args()
    base.RAW = RAW
    items = rows()
    plan = dict(format=1, version='0.2.27', source_route='sub2-image-gen/gpt-image-2.5/high',
                original_images_modified=False, manual_compositing=False, assets=items)
    if PLAN.exists():
        assert json.loads(PLAN.read_text(encoding='utf-8')) == plan, 'Create a new immutable revision'
    else:
        base.write_json(PLAN, plan)
    if args.install:
        install(items)
        return
    completed = []
    failures = []
    with ThreadPoolExecutor(max_workers=3) as pool:
        jobs = {pool.submit(base.generate, row): row for row in items}
        for job in as_completed(jobs):
            row = jobs[job]
            try:
                value = job.result()
                assert value is not None
                completed.append(value)
                print('GENERATED ' + row['id'], flush=True)
            except Exception as exc:
                failures.append(dict(id=row['id'], error=str(exc)))
                print('FAILED ' + row['id'], flush=True)
            base.write_json(REPORT, dict(passed=len(completed) == 3 and not failures,
                version='0.2.27', created_at_utc=datetime.now(timezone.utc).isoformat(),
                source_route='sub2-image-gen/gpt-image-2.5/high', source_images_modified=False,
                manual_compositing=False, formal_art_approval=False,
                completed=len(completed), failures=failures, assets=completed))
    if failures:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
