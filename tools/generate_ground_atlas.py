"""Produce quiet, material-specific atlas grounds using the required Sub2 CLI.

Only that CLI writes raster pixels. Original files, prompts and earlier active
grounds are retained. Source inspection and in-game acceptance are separate.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import argparse
import json
import shutil
import generate_map_bank as base

P = base.P
RAW = base.ROOT / 'output/imagegen/warlord/ground_atlas_v0225/originals'
PLAN = P / 'presentation/data/ground_atlas_plan.json'
REPORT = P / 'reports/ground_atlas_generation.json'
REVIEW = P / 'reports/ground_atlas_source_review.json'
CATALOG = P / 'presentation/data/ground_macro_catalog.json'

STYLE = '''ONE original seamless opaque terrain material for a painted historical
strategy map. Entire square is one continuous flat ground surface, exact top
down, no margins. Design it to remain attractive when the WHOLE image is shown
at 180 screen pixels across, behind small military miniatures. Use broad quiet
matte pigment planes with restrained material-specific brush structure. Gentle
value variation, softly joined regions, readable medium scale structure, very
sparse fine detail. The surface must feel open and restful rather than busy.
No photographic grain, pointillism, sandpaper, freckles, harsh soil/plant
contrast, tiny yellow dots, dense individual grass blades, large clumps with
black roots, obvious camouflage blobs, evenly spaced motifs, discs or badges.
Retain the distinct material shape specified below; do not make generic noise.
Soft diffuse upper-left light, shallow surface relief only. No long shadows,
trees, standing reeds, bushes, raised rocks, mountain miniatures, field parcels,
furrows, paths, rivers, pools, coastlines, buildings, grid, hexagons, borders,
writing, paper background, UI, panels, frame, logo or watermark. No reference
game assets. All four edges wrap seamlessly. This is representative material
art; it does not define a real historical vegetation or soil boundary.
Material, palette and identifying structure:
'''

SUBJECTS = {
    'temperate_meadow': 'SAGE MEADOW. Muted gray-sage and olive ground, dominant #8D9B76 with soft #7F8F6C shade and #A2AB88 light. Broad connected grass surface. A few flat short curved grass-brush fans, softly interwoven into the same ground; almost no bare ochre earth. The grass is low and distant, no individual long leaves or tall tufts. Quiet green planes with sparse readable short wisps, not a lawn close-up.',
    'dry_steppe': 'DRY STEPPE. Pale straw-olive #ADA57F, shaded #969575, warm pale #BDB28D. Interrupted fine flat straw currents in loose sweeping arcs on calm compact earth; a small amount of faded olive. Broad open dry surface, distinct directional fibrous rhythm, no high-contrast clumps or dense blade carpet.',
    'desert_steppe': 'SPARSE DESERT STEPPE. Open gray-taupe mineral earth #ADA58E, lighter #BDB49C, a very few tiny soft straw-brush fans. About nine tenths visually quiet bare mineral ground. Sparse desiccated fibres, not a green mat, sand dunes or mottled camouflage.',
    'dune_sand': 'WIND-WORKED SAND. Pale warm ochre #C0AD86 with gentle #B6A47F troughs and #CDBB97 lips. Several long softly interrupted shallow curved ripple combs separated by broad smooth sand sheets. Coherent flowing ripple rhythm, no random granular speckles or raised dune silhouettes.',
    'gravel_gobi': 'GOBI GRAVEL PAVEMENT. Muted buff-gray #A29F8D with subdued slate #8E9289 and pale limestone #B9B5A2. Low-contrast flat angular chips in unequal loose groups, generous calm compact mineral ground between them. Small broken polygonal chip structure with soft shallow contacts, no black grit, giant boulders or sand ripples.',
    'saline_meadow': 'SALINE MEADOW GROUND. Quiet gray-green #94A497, soft silvery #B1B8A5 and muted cool olive #879583. A few pale irregular thin salt veils and sparse flat wiry grass traces; broad smooth moist mineral planes. No water, pools, channels, large white islands or ordinary green lawn.',
    'alpine_meadow': 'ALPINE MEADOW. Cool short grass ground #92A391, soft light #ADB6A0 and muted #7D9283. Short flat blade-brush cushions grouped loosely in broad open planes; a few tiny cool mineral flecks. Crisp cool short-grass structure, no flowers, snow or tall grass.',
    'alpine_steppe': 'ALPINE STEPPE. Cool pale straw-gray #AAA996, subtle #969E8C and #BAB9A5. Sparse close-cropped wiry straw brushwork and quiet exposed cool earth, broad open areas. Dry short directional fibres, no fresh green meadow or white snow.',
    'tundra_moss': 'TUNDRA MOSS AND LICHEN. Soft gray-sage #98A599, muted silver #B3B8AA and subdued slate-olive #87988D. Low flattened felt-like moss brush patches with tiny irregular lichen threads. Broad cool soft planes, no bright moss balls, black joints, leaves or rock carpet.',
    'boreal_litter': 'BOREAL FOREST FLOOR. Cool muted olive-brown #7E8C77, soft umber #8E937B and #6F806D shade. Thin fallen needles in very loose short directional fans, soft felted earth underneath. Quiet shallow fibrous floor, no trees, cones, giant leaves or a dense twig lattice.',
    'temperate_litter': 'TEMPERATE BROADLEAF FLOOR. Muted brown-olive #9A957B with #ABA18A light and #878C74 shade. A few recognizable small flat rounded lobed fallen-leaf brush shapes, separated by broad calm humus planes. Sparse leaves, gentle edges and no dark contacts, no grass tufts, bark or photographic leaf carpet.',
    'conifer_litter': 'CONIFER NEEDLE FLOOR. Restrained umber-sage #92917C with soft #A49E86 light and #7F8976 shade. Slender rust-brown needle-like marks in loose interrupted diagonal fans; calm compact dark earth. Fine linear material rhythm distinct from broadleaf shapes, no trees, sticks, cones or dense black crosshatching.',
    'dry_woodland_litter': 'DRY WOODLAND FLOOR. Warm dusty ochre-olive #A8A084, light #B9AE92, subdued #95957B. Sparse curled flat leaf fragments and a few broken straw fibres on broad dry mineral earth. Quiet open dry floor; distinct small leaf fragments, no lush lawn or pebbly sand.',
    'subtropical_humus': 'SUBTROPICAL HUMUS. Muted warm gray-umber #948E77, soft #A49C82 and #83866F. Broad smooth cohesive organic earth planes with occasional soft flattened rounded leaf fragments. Warm moist but matte and open, no puddles, black cracks, dense leaf carpet or green camouflage.',
    'tropical_moist_humus': 'TROPICAL MOIST HUMUS. Cool gray-brown #858E7D, gentle #98A08B and #748373. Smooth compact organic soil with sparse broad flat decaying leaf-brush fragments softly dissolving into the ground. Moist matte cohesive surface, no glossy water, living plants or deep black holes.',
    'savanna_red_soil': 'SAVANNA SOIL AND DRY GRASS. Muted clay-ochre #AF9A7E, gentle #BBA88A and #9F9279. Broad warm mineral earth planes with a few pale straw-brush fans and subdued fine clay seams. Warm, open and dry; no bright red earth, dunes, cracks or dense lush grass.',
    'flood_meadow': 'FLOOD MEADOW GROUND. Soft cool green-gray #90A49A, gentle #A7B6A5 and #7E998E. Low flattened long soft grass fibres swept into irregular gentle currents over quiet silty soil. Slightly moist matte structure; no channels, pools, tall reeds, crop rows or broad yellow gaps.',
    'alluvial_loam': 'ALLUVIAL SILT AND LOAM. Warm pale buff-gray #B2A58C, soft #C0B39B and #A39780. Broad smooth fine-sediment planes, a few long interrupted soft silt streaks and shallow rounded cohesive earth crumbs. Calm fine mineral structure, no sand ripples, cultivation rows, water channels, grass carpet or cracked-earth lattice.',
    'weathered_rock': 'WEATHERED BEDROCK. Quiet gray-green #929B8C, soft #AAB09C and muted #7F8C7E. Broad flattened uneven mineral planes, a few shallow softly broken angled fracture seams and faint narrow strata. Coherent slab material with gentle depth, no black cracks, loose gravel, moss islands, boulders or mountain shapes.',
    'alpine_scree': 'ALPINE ROCK CHIPS. Cool slate-gray #98A29D, soft silver #B0B7AC and #879590. Small flattened elongated angular shale strokes in loose uneven short fans, softly joined to a quiet cool mineral matrix. Recognizable elongated chip rhythm with subdued contacts; no dense black gravel, big raised rocks, plants or snow.',
}


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def prepare():
    previous = read(P / 'presentation/data/ground_identity_plan.json')
    assert set(SUBJECTS) == {r['family'] for r in previous['assets']}
    rows = []
    for old in previous['assets']:
        row = {k: v for k, v in old.items() if k not in {'id', 'prompt'}}
        row.update(id='tile_ground_quiet_v0225_' + old['family'], source_revision='r001',
                   prompt=STYLE + SUBJECTS[old['family']])
        rows.append(row)
    value = dict(format=1, version='0.2.25', terrain_type_count=20,
                 source_route='sub2-image-gen/gpt-image-2.5/high', assets=rows,
                 source_images_modified=False, manual_compositing=False,
                 scope='Twenty existing material families; no geographical or rule changes')
    if PLAN.exists():
        assert read(PLAN) == value, 'Existing production plan is immutable'
    else:
        base.write_json(PLAN, value)
    return rows


def measured(row):
    value = base.measure(row)
    if value is not None:
        value.update(style_version='warlord_quiet_atlas_v0225', revision='ground_atlas_v0225_r001',
                     era='representative_material_not_historical_landuse')
    return value


def install(rows):
    review = read(REVIEW)
    viewed = {r['id']: r for r in review['originals']}
    assert len(viewed) == 20 and review['all_twenty_originals_viewed']
    values = [measured(row) for row in rows]
    assert all(values) and len({r['source_sha256'] for r in values}) == 20
    old = read(CATALOG)
    incoming_ids = {r['id'] for r in values}
    superseded = sorted((set(old.get('superseded_asset_ids', [])) |
                         {r['asset_id'] for r in old['records'].values()}) - incoming_ids)
    assert len(superseded) == 40
    geography = P / 'presentation/data/terrain_surface_regions.json'
    geography_sha = base.sha(geography)
    path = P / 'assets/manifest.json'
    manifest = read(path)
    current = {r['id']: r for r in manifest['assets']}
    records = {}
    for row in values:
        note = viewed[row['id']]
        assert note['viewed_complete_original'] and note['accepted_for_runtime_trial']
        assert note['sha256'] == row['source_sha256'] and note['prompt_sha256'] == row['prompt_sha256']
        for source, target in [(base.ROOT / row['source_file'], P / row['engine_path'].removeprefix('res://')),
                               (base.ROOT / row['prompt_file'], P / 'docs/asset-prompts' / (row['id'] + '.txt'))]:
            if target.exists():
                assert base.sha(source) == base.sha(target), 'Existing original must remain unchanged'
            else:
                shutil.copyfile(source, target)
        row.update(state='generated_source_reviewed_runtime_trial', game_ready=False,
                   visual_review='Whole source inspected; in-game comparison and formal acceptance separate')
        current[row['id']] = row
        records[row['family']] = dict(asset_id=row['id'], source_sha256=row['source_sha256'],
                                     actual_dimensions=row['actual_dimensions'])
    manifest['assets'] = sorted(current.values(), key=lambda r: r['id'])
    base.write_json(path, manifest)
    base.write_json(CATALOG, dict(format=1, version='0.2.25', independent_originals=20,
        source_plan_file=PLAN.relative_to(P).as_posix(), source_plan_sha256=base.sha(PLAN),
        world_repeat_period=224, records=records, source_images_modified=False,
        superseded_originals=40, superseded_asset_ids=superseded, original_pngs_retained=True,
        material_identity_revision='quiet_material_shapes_v0225_r001'))
    assert base.sha(geography) == geography_sha
    base.write_json(P / 'reports/ground_atlas_installation.json', dict(passed=True, version='0.2.25',
        installed_new_originals=20, active_macro_originals=20, stored_superseded_originals=40,
        geography_sha256=geography_sha, geography_assignments_changed=False,
        source_images_modified=False, manual_compositing=False, total_registered_rasters=len(current),
        formal_art_approval=False))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--prepare-only', action='store_true')
    ap.add_argument('--install', action='store_true')
    ap.add_argument('--only', default='')
    ap.add_argument('--workers', type=int, default=3)
    args = ap.parse_args()
    base.RAW = RAW
    rows = prepare()
    if args.prepare_only:
        print('Twenty material-specific Sub2 prompts prepared.', flush=True)
        return
    if args.install:
        install(rows)
        return
    selected = [r for r in rows if not args.only or r['family'] in args.only.split(',')]
    assert selected, 'No matching families'
    complete = {r['id']: v for r in rows if (v := measured(r)) is not None}
    errors = []
    started = datetime.now(timezone.utc).isoformat()

    def report(terminal=False):
        base.write_json(REPORT, dict(version='0.2.25', phase='all' if len(selected) == 20 else 'pilot',
            terminal=terminal, run_passed=terminal and not errors,
            all_twenty_generated=len(complete) == 20, completed=len(complete), requested_this_run=len(selected),
            started_at_utc=started, updated_at_utc=datetime.now(timezone.utc).isoformat(),
            source_route='sub2-image-gen/gpt-image-2.5/high', source_plan_sha256=base.sha(PLAN),
            source_images_modified=False, manual_compositing=False, formal_art_approval=False,
            errors=errors, assets=sorted(complete.values(), key=lambda r: r['id'])))
    report()
    with ThreadPoolExecutor(max_workers=max(1, min(3, args.workers))) as pool:
        jobs = {pool.submit(base.generate, r): r for r in selected if r['id'] not in complete}
        for job in as_completed(jobs):
            row = jobs[job]
            try:
                job.result()
                complete[row['id']] = measured(row)
                print('GENERATED ' + row['id'], flush=True)
            except Exception as exc:
                errors.append(dict(id=row['id'], error=str(exc)))
                print('FAILED ' + row['id'], flush=True)
            report()
    report(terminal=True)
    raise SystemExit(bool(errors))


if __name__ == '__main__':
    main()
