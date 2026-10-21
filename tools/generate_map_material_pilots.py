"""Make two independent Sub2 ground candidates; do not install them implicitly."""
from datetime import datetime, timezone
import argparse
import json
import shutil
import generate_map_bank as base

RAW = base.ROOT / 'output/imagegen/warlord/ground_material_v0231/originals'
PLAN = base.P / 'reports/ground_material_v0231/production_plan.json'
REPORT = base.P / 'reports/ground_material_v0231/generation.json'

STYLE = '''Create ONE original opaque seamless painted terrain texture for a
historical strategy map, a complete continuous square viewed straight down.
The whole square will cover about three to four small hexes in the game; make
the ground read as a beautiful calm painted material at 224 screen pixels.
This is representative surface art, not a vegetation survey or a named place.
Use clear interlocking medium-sized brush planes, low clipped grass growth,
matte mineral earth and a few fine grouped grass strokes. Broad open shapes
must dominate, with enough structure to identify the material after reduction.
Soft sunlight from upper left, only shallow ground relief. The green should
look alive and natural, with warm light planes and cooler shaded strokes.
Avoid gray fog, beige paper, mottled photographic grit, tiny yellow freckles,
high-frequency fuzz, dark grass roots, regularly spaced tufts or tall plants.
No trees, bushes, flowers, crops, field parcels, paths, hills, standing rocks,
streams, lakes, shores, puddles, buildings, people, units, shadows of objects,
hexagons, UI, labels, borders, frame, vignette, letters, logo or watermark.
The full texture must reach all four edges, without a surrounding platform or
background. All edges should wrap seamlessly. Do not copy another game's art.
Material:
'''

SUBJECTS = {
    'temperate_meadow': '''Open temperate short-grass ground. The predominant
pigment is a living muted olive green #819751, with broad soft #9CAA70 lit
planes and #617C49 shaded brush accents. About 85 percent reads as connected
low green grass, 15 percent as softly exposed earth. Fine flat grass fans are
sparse, broad irregular blades grouped into a few readable flowing rhythms.
No isolated round grass balls. Keep it distinctly greener than gray sage soil,
yet subdued enough for soldiers and ownership colors to remain readable.''',
    'subtropical_humus': '''Warm humid lowland organic earth with an open low
ground-cover accent, not a forest floor or dense lawn. Warm olive green
#82915A and mossy #718150 are interwoven with warm brown #93835E humus and
ochre-gray #A89A72 fine earth. Green ground-cover occupies broad connected
patches; exposed humus is clearly visible between them. A few short flat
curved grass strokes rest in the same plane. No fallen leaf carpet, roots,
canopy shadows or presumed historic forest. Warm, cohesive and distinct from
the more fibrous temperate meadow; no dirty gray photographic cloud pattern.''',
}


def install():
    """Install only reviewed originals; preserve the other eighteen families."""
    read = lambda path: json.loads(path.read_text(encoding='utf-8'))
    review = read(base.P / 'reports/ground_material_v0231/source_review.json')
    generation = read(REPORT)
    assert generation['source_plan_sha256'] == base.sha(PLAN)
    reviewed = {row['id']: row for row in review['originals']}
    values = generation['assets']
    assert len(values) == len(reviewed) == 2 and not review['formal_art_approval']
    catalog_path = base.P / 'presentation/data/ground_macro_catalog.json'
    catalog = read(catalog_path)
    parent_plan = read(base.P / 'presentation/data/ground_atlas_plan.json')
    incoming = {row['family']: row for row in read(PLAN)['assets']}
    active_plan_path = base.P / 'presentation/data/ground_material_plan_v0231.json'
    active_plan = dict(format=1, version='0.2.31', terrain_type_count=20,
        source_route=generation['source_route'],
        parent_plan_file='presentation/data/ground_atlas_plan.json',
        parent_plan_sha256=base.sha(base.P / 'presentation/data/ground_atlas_plan.json'),
        amendment_plan_file=PLAN.relative_to(base.P).as_posix(),
        amendment_plan_sha256=base.sha(PLAN),
        assets=[incoming.get(row['family'], row) for row in parent_plan['assets']],
        source_images_modified=False, manual_compositing=False,
        scope='Two replacement material originals; no historical land-cover or geography changes')
    if active_plan_path.exists():
        assert read(active_plan_path) == active_plan, 'Preserve the active source plan'
    else:
        base.write_json(active_plan_path, active_plan)
    manifest_path = base.P / 'assets/manifest.json'
    manifest = read(manifest_path)
    assets = {row['id']: row for row in manifest['assets']}
    superseded = set(catalog['superseded_asset_ids'])
    geography = base.P / 'presentation/data/terrain_surface_regions.json'
    geography_sha = base.sha(geography)
    for value in values:
        row = dict(value)
        note = reviewed[row['id']]
        assert note['viewed_complete_original'] and note['accepted_for_runtime_trial']
        assert note['sha256'] == row['source_sha256']
        assert note['prompt_sha256'] == row['prompt_sha256']
        for source, target, expected in [
            (base.ROOT / row['source_file'], base.P / row['engine_path'].removeprefix('res://'), row['source_sha256']),
            (base.ROOT / row['prompt_file'], base.P / 'docs/asset-prompts' / (row['id'] + '.txt'), row['prompt_sha256'])]:
            assert base.sha(source) == expected
            if target.exists():
                assert base.sha(target) == expected, 'Never overwrite an original'
            else:
                shutil.copyfile(source, target)
            assert base.sha(target) == expected
        old_id = catalog['records'][row['family']]['asset_id']
        if old_id != row['id']:
            superseded.add(old_id)
        row.update(state='generated_source_reviewed_runtime_trial', game_ready=False,
            visual_review='Complete source and native candidates viewed; normal imports and shipping acceptance recorded separately')
        assets[row['id']] = row
        catalog['records'][row['family']] = dict(asset_id=row['id'],
            source_sha256=row['source_sha256'], actual_dimensions=row['actual_dimensions'],
            world_repeat_period=384)
    assert len(catalog['records']) == 20 and len(superseded) == 42
    catalog.update(version='0.2.31', source_plan_file=active_plan_path.relative_to(base.P).as_posix(),
        source_plan_sha256=base.sha(active_plan_path), superseded_originals=42,
        superseded_asset_ids=sorted(superseded), material_identity_revision='painted_lowland_v0231_r001')
    manifest['assets'] = list(assets.values())
    assert len(assets) == 2509
    base.write_json(manifest_path, manifest)
    base.write_json(catalog_path, catalog)
    provenance_path = base.P / 'docs/asset-provenance/index.json'
    provenance = read(provenance_path)
    portable = {row['id']: row for row in provenance['assets']}
    for row in values:
        portable[row['id']] = dict(id=row['id'], category='tile',
            image=row['engine_path'].removeprefix('res://'), image_sha256=row['source_sha256'],
            prompt='docs/asset-prompts/' + row['id'] + '.txt', prompt_sha256=row['prompt_sha256'],
            source_kind=row['source_kind'], model=row['model'], quality=row['quality'],
            original_workspace_source=row['source_file'], image_modified=False, formal_art_approval=False)
    provenance.update(version='0.2.31', count=len(portable),
        image_bytes=sum((base.P / row['image']).stat().st_size for row in portable.values()),
        assets=list(portable.values()))
    base.write_json(provenance_path, provenance)
    assert base.sha(geography) == geography_sha
    base.write_json(base.P / 'reports/ground_material_v0231/installation.json', dict(
        passed=True, version='0.2.31', installed_new_originals=2, active_macro_originals=20,
        stored_superseded_originals=42, total_registered_rasters=len(assets),
        geography_sha256=geography_sha, geography_assignments_changed=False,
        source_images_modified=False, manual_compositing=False, formal_art_approval=False))
    print('Installed two byte-identical originals; twenty active families retained.', flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--install', action='store_true')
    if parser.parse_args().install:
        install()
        return
    rows = [dict(id='tile_ground_painted_v0231_' + family, category='tile',
                 family=family, variant=1, source_revision='r001',
                 runtime_import_max_dimension=384, visible_bounds=[384, 384],
                 gate='existing_' + family + '_material_only',
                 prompt=STYLE + subject) for family, subject in SUBJECTS.items()]
    plan = dict(version='0.2.31', source_route='sub2-image-gen/gpt-image-2.5/high',
                assets=rows, runtime_installed=False, historical_landcover_claimed=False)
    if PLAN.exists():
        assert json.loads(PLAN.read_text(encoding='utf-8')) == plan, 'Keep the production prompt immutable.'
    else:
        base.write_json(PLAN, plan)
    base.RAW = RAW
    values = []
    for row in rows:
        value = base.generate(row)
        value.update(style_version='warlord_painted_ground_v0231',
                     revision='painted_ground_v0231_r001',
                     era='representative_material_not_historical_landuse')
        values.append(value)
        base.write_json(REPORT, dict(recorded_at_utc=datetime.now(timezone.utc).isoformat(),
            source_plan_sha256=base.sha(PLAN), generated=len(values), requested=len(rows),
            source_route='sub2-image-gen/gpt-image-2.5/high', assets=values,
            source_images_modified=False, manual_compositing=False,
            runtime_installed=False, formal_art_approval=False))
        print('Generated and measured ' + row['id'], flush=True)


if __name__ == '__main__':
    main()
