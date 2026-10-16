"""Twenty continuous painted grounds; the original eighty fine sources remain intact.

Only the mandated Sub2 CLI writes images. Runtime UVs repeat the complete
original; no derived PNG, atlas, recolor, crop or composite is produced here.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import argparse
import json
import shutil
import time
import generate_map_bank as base
from generate_terrain_surfaces import TYPES

P = base.P
RAW = base.ROOT / 'output/imagegen/warlord/ew6_v025/ground_macros_v0214'
PLAN = P / 'presentation/data/ground_macro_plan.json'
CATALOG = P / 'presentation/data/ground_macro_catalog.json'

STYLE = '''One original seamless opaque map-ground material for a premium
hand-painted historical turn-based strategy game. Exact top-down flat texture,
edge-to-edge. This covers a broad region on the game map, NOT a close-up
photograph of soil. Use calm broad painterly connected color planes, smooth
pigment transitions, subtle hand-painted brush direction and sparse distinct
medium-sized material marks. About 80 percent calm color, 20 percent clear
clustered identity. Medium brush shapes roughly 50-180 pixels wide in a 1024
image; fine marks should be very sparse. Reduce illustrative complexity to
the legible level of a painted strategy-game landscape. Soft shallow light
from upper left. Matte pigments, natural restrained saturation, moderate
value range without black speckles. Absolutely no sandpaper noise, photo
grain, dense leaf carpet, individual realistic leaves, micropebbles, gritty
freckles, stippling, repeated circular spots or camouflage shapes. No objects
casting long shadows, trees, bushes, cliffs, mountains, roads, buildings,
agricultural parcel lines, water channels, pools, coasts, labels, hexagons,
borders, UI, panels, frames, logos or watermark. Full continuous seamless
surface, never a swatch with margins. Do not copy another game's artwork.
The material is representative regional ground, not a historical land-use
survey. Subtle small organic/mineral marks describe this material:
'''

SUBJECTS = {
    'temperate_meadow': 'Quiet sage-green grass ground #98A478 with soft olive blade-shaped brush clusters, broad lighter grass openings and small warm loam touches; a green painted plain, never a realistic lawn photo.',
    'dry_steppe': 'Dry muted straw and sage ground #B0A47C. Broad broken wispy ochre brush currents with calm dry earth; distinctly drier and lighter than meadow.',
    'desert_steppe': 'Open taupe mineral ground #ABA18A, sparse desiccated straw brush marks in irregular groups. Large empty mineral planes, no dunes.',
    'dune_sand': 'Soft ochre sand #C6AF80, very gentle broad silky wind ripples in long interrupted curved brush strokes. Clean smooth sand planes, no speckles or raised dune silhouettes.',
    'gravel_gobi': 'Cool gray taupe desert pavement #A09D8A, sparse grouped broad flat angular slate brush chips. Calm stony ground, not sand ripples and not noisy gravel photography.',
    'saline_meadow': 'Pale gray sage #A2AC94 with sparse sedge-shaped brush traces and soft chalky silt streaks. Quiet mineral-organic ground; no salt lake or white salt polygons.',
    'alpine_meadow': 'Cool green #8CA68A low cushion-grass ground, connected soft velvet-like brush patches and a few shallow cool gray grit touches. No snow.',
    'alpine_steppe': 'Pale cool gray straw #B0B09A with open muted sage fibrous brush currents and broad calm gray mineral earth. No snow or frost polygons.',
    'tundra_moss': 'Olive moss and pale gray lichen #919B7C, shallow soft organic brush lobes with muted peat seams. No bushes, water or snow.',
    'boreal_litter': 'Cool muted olive humus #899371, a few soft rust needle-like brush currents and broad calm moss-earth planes. No dense needles, trees or leaf carpet.',
    'temperate_litter': 'Soft muted sage-ochre mineral and organic earth #A1A27B, a few broad decomposed olive brush patches with sparse warm straw marks. Ground of a temperate ecological region, NOT a forest leaf carpet; no recognizable leaves or trees.',
    'conifer_litter': 'Cool gray sage earth #929B81 with sparse quiet tan linear brush threads. Broad calm mineral humus; no dense needle carpet or branches.',
    'subtropical_humus': 'Muted warm loam #AA9B77, shallow olive organic brush patches and a few sienna clod-like brush touches. Ground without plants, cultivated parcels or individual leaves.',
    'tropical_moist_humus': 'Warm muted russet-earth #A18D70 with cool olive humus brush seams and broad soft dark loam planes, subtle shallow damp shading. No puddles or leaf carpet.',
    'dry_woodland_litter': 'Warm dry muted tan-olive earth #ADA17D, sparse broken straw brush wisps with broad calm sandy loam planes; no woodland silhouettes or leaves.',
    'savanna_red_soil': 'Subdued red ochre mineral earth #B49B75 with sparse dry olive grass-shaped brush wisps and connected warm clay planes. No trees, shrubs or fields.',
    'flood_meadow': 'Quiet gray-green ground #8F9E86, shallow broad sedge-shaped brush currents mixed with muted silt planes. No pools, river channels or marsh water extent.',
    'alluvial_loam': 'Soft muted warm gray-brown silt #AFA58B, wide shallow interrupted sediment-like brush bands and a few small loam clod marks. Dry flat material, no channels or agricultural furrows.',
    'weathered_rock': 'Muted sage-gray mineral earth #989D85 with sparse broad flat weathered stone brush planes and fine subdued strata-like direction. Flat surface, not raised boulders or a ridge.',
    'alpine_scree': 'Cool slate-gray mineral ground #A3A795, connected broad angular shallow brush planes and sparse small dark fissure marks. Flat representative scree, no peaks, snow or raised boulders.',
}


def plan():
    rows = [dict(id='tile_ground_macro_' + family, category='tile', family=family,
                 variant=1, axis='', region='', role='', gate=gate,
                 visible_bounds=[384, 384], source_revision='r001',
                 runtime_import_max_dimension=384, prompt=STYLE+SUBJECTS[family])
            for family, name, parent, subject, gate in TYPES]
    value = dict(format=1, version='0.2.14', independent_originals=20,
                 source_route='sub2-image-gen/gpt-image-2.5/high',
                 original_images_modified=False, manual_compositing=False, assets=rows)
    if PLAN.exists() and json.loads(PLAN.read_text(encoding='utf-8')) != value:
        raise RuntimeError('Immutable ground plan mismatch; create a new revision')
    if not PLAN.exists():base.write_json(PLAN,value)
    return rows


def install(rows):
    measured = [base.measure(row) for row in rows]
    if any(row is None for row in measured):raise RuntimeError('Twenty originals required')
    if len({row['source_sha256'] for row in measured}) != 20:raise RuntimeError('Duplicate original')
    path = P/'assets/manifest.json'
    manifest = json.loads(path.read_text(encoding='utf-8'))
    current = {row['id']:row for row in manifest['assets']}
    records = {}
    for row in measured:
        row.update(style_version='warlord_ew6_v025_ground_macros_v0214',
                   revision='ground_macros_v0214_r001',
                   era='representative_regional_ground_not_historical_landuse_survey')
        target = P/row['engine_path'].removeprefix('res://')
        if target.exists() and base.sha(target) != row['source_sha256']:raise RuntimeError('Immutable original differs')
        if not target.exists():shutil.copyfile(base.ROOT/row['source_file'],target)
        current[row['id']] = row
        records[row['family']] = dict(asset_id=row['id'],source_sha256=row['source_sha256'],
                                     actual_dimensions=row['actual_dimensions'])
    manifest['assets']=sorted(current.values(),key=lambda row:row['id'])
    base.write_json(path,manifest)
    base.write_json(CATALOG,dict(format=1,version='0.2.14',independent_originals=20,
        source_plan_sha256=base.sha(PLAN),world_repeat_period=384,
        source_images_modified=False,records=records))
    print('Installed twenty immutable macro originals',flush=True)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--only',default='');ap.add_argument('--workers',type=int,default=3)
    ap.add_argument('--install',action='store_true');ap.add_argument('--prepare-only',action='store_true')
    args=ap.parse_args();base.RAW=RAW;rows=plan()
    if args.prepare_only:return
    if args.install:install(rows);return
    complete={row['id']:value for row in rows if (value:=base.measure(row)) is not None}
    queue=[row for row in rows if row['id'] not in complete and (not args.only or row['family']==args.only)]
    failures=[];started=time.monotonic()
    def report():
        records=[]
        for row in complete.values():
            row=dict(row);row.update(style_version='warlord_ew6_v025_ground_macros_v0214',revision='ground_macros_v0214_r001',era='representative_regional_ground_not_historical_landuse_survey');records.append(row)
        base.write_json(P/'reports/ground_macro_generation.json',dict(passed=len(complete)==20 and not failures,version='0.2.14',
            created_at_utc=datetime.now(timezone.utc).isoformat(),requested=20,completed=len(complete),
            source_plan_sha256=base.sha(PLAN),source_route='sub2-image-gen/gpt-image-2.5/high',
            original_images_modified=False,formal_art_approval=False,failures=failures,
            assets=sorted(records,key=lambda row:row['id'])))
    report()
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        jobs={pool.submit(base.generate,row):row for row in queue}
        for future in as_completed(jobs):
            row=jobs[future]
            try:complete[row['id']]=future.result();print('GENERATED '+row['id'],flush=True)
            except Exception as exc:failures.append(dict(id=row['id'],error=str(exc)));print('FAILED '+row['id'],flush=True)
            report()
    print(json.dumps(dict(completed=len(complete),failures=failures,elapsed_seconds=round(time.monotonic()-started))),flush=True)
    if failures:raise SystemExit(1)


if __name__=='__main__':main()
