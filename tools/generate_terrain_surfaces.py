"""Twenty regional terrain materials, four independent Sub2 originals each.

Never transforms or writes image pixels. Source bytes, prompts and provenance
are immutable. This catalog extends, rather than rewrites, the v0.2.12 bank.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
import argparse
import json
import shutil
import time
import generate_map_bank as base

P = base.P
RAW = base.ROOT / 'output/imagegen/warlord/ew6_v025/terrain_surfaces_v0213'
PLAN = P / 'presentation/data/terrain_surface_plan.json'
REPORT = P / 'reports/terrain_surface_generation.json'
CATALOG = P / 'presentation/data/terrain_surface_catalog.json'

# A material is an explicitly representative ground treatment, not a claim
# that an ecological polygon is an 1840 cadastral/forest/soil survey.
TYPES = [
    ('temperate_meadow', '温带草甸', 'plain',
     'Fresh temperate meadow ground. Interlocking patches of short sage-green grass blades, visible warm ochre loam in narrow irregular gaps. Broad blade groups with tiny cool green foot shadows; no flowers. Palette sage #88966A, loam #A69771, shadow #606F4E.',
     'temperate grassland and forest-steppe ecological regions'),
    ('dry_steppe', '旱生草原', 'plain',
     'Dry continental steppe ground. Short broken straw-gold blade fans, sparse olive grass and broad exposed compact tan earth between them. Distinct fibrous wisps, never lush meadow. Palette dusty straw #B4A375, dry olive #94906B, earth #95846C.',
     'temperate continental grassland ecological regions'),
    ('desert_steppe', '荒漠草原', 'plain',
     'Desert-steppe ground. Mostly dusty gray-brown mineral earth with widely spaced tiny desiccated grass stubble, thin embedded gravel and subdued interrupted wind streaks. Sparse plant fibers, no dunes or shrubs. Palette gray taupe #A69C86, slate pebbles #777B70, straw #B6AA83.',
     'named desert-steppe and semi-desert ecological regions'),
    ('dune_sand', '风成沙地', 'plain',
     'Fine wind-worked desert sand, clear silky curved ripple combs and shallow broad sweeping sand sheets. Fine ripple highlights and gentle trough shadows, completely flat material with no three-dimensional dune silhouette. Palette pale muted ochre #C1AC7E, sand highlight #D1BD91, trough #A58F67.',
     'explicit named sandy-desert ecological regions only'),
    ('gravel_gobi', '戈壁砾地', 'plain',
     'Stony desert pavement ground. Many small flat angular slate-gray and dusty umber chips embedded in compact buff mineral soil, unequal pebble sizes and coherent gravel-rich patches. Strongly different from sand: no ripple combs. Palette stone #7E827B, buff #ADA184, umber #8D806C.',
     'named stony and xeric-desert ecological regions'),
    ('saline_meadow', '盐生草甸地表', 'plain',
     'Representative saline-meadow surface. Muted gray-green fine sedge stubble crossing pale chalky silt seams, broad subdued mineral flats and small dark soil freckles. Thin chalk traces, not a white salt lake or salt polygon. Palette gray sage #8A9A88, pale silt #C0BDA5, damp earth #777B68.',
     'explicit named saline meadow and salt-marsh ecological regions; no water extent inferred'),
    ('alpine_meadow', '高山草甸', 'plain',
     'Alpine meadow ground. Tight low cushion-like grass mats and small velvety moss patches separated by visible cool fine gritty soil. Dense short radial fibers and occasional flat tiny gray chips, no flowers or snow. Palette cool sage #7F957D, moss #6C846B, grit #9B9A86.',
     'named alpine meadow ecological regions'),
    ('alpine_steppe', '高寒草原', 'plain',
     'Cold high plateau steppe surface. Pale short wiry grass fibers forming low open mats over gray tan coarse grit, clearly open soil channels between uneven grass patches. Cold dry matte finish, not snow or dunes. Palette gray straw #ADA991, dry sage #8F9680, grit #8E8B7D.',
     'named alpine steppe and alpine desert ecological regions'),
    ('tundra_moss', '苔原地表', 'plain',
     'Tundra ground material. Low dense olive moss and gray lichen crusts, tiny rusty brown organic flecks and broken dark peat grain between low mats. Organic close-to-ground texture, no shrubs, frost polygons, snow or water. Palette olive #858F69, lichen #ADAFA0, peat #686A56, muted rust #927A62.',
     'tundra ecological regions; no seasonal ice or permafrost boundary inferred'),
    ('boreal_litter', '寒带林带腐殖层', 'plain',
     'Representative boreal-zone floor material. Dark cool humus with fine rusty needle fibers and low olive moss crescents, sparse tiny dry bark chips. Distinct deep earthy organic texture; no trees, branches or trunks. Palette peat #666C57, moss #7F8D65, needle #A18B64.',
     'boreal ecological region ground reference, not an assertion of historical tree cover'),
    ('temperate_litter', '温带阔叶林带落叶层', 'plain',
     'Representative temperate mixed-forest-zone floor material. Small flat irregular ochre and muted copper leaf fragments woven into loose dark loam, soft olive decomposed patches. Readable broad leaf-shape fragments without large individual hero leaves. Palette loam #827B61, leaf ochre #B2A078, muted copper #A18A68, olive #858A67.',
     'temperate mixed and broadleaf ecological region ground reference, not historical tree cover'),
    ('conifer_litter', '针叶林带针叶层', 'plain',
     'Representative montane conifer-zone floor material. Clearly directional thin tan needle threads in overlapping fans over cool gray-green mineral humus, small isolated moss patches and tiny flat gray grit. More linear needle-rich than broadleaf litter; no branches or cones. Palette needles #B0A082, humus #7A806A, stone #979A89.',
     'temperate or tropical conifer ecological region ground reference, not historical tree cover'),
    ('subtropical_humus', '亚热带林带湿润土', 'plain',
     'Representative humid subtropical-zone floor material. Rich muted warm sienna loam threaded with short olive organic fibers, scattered small flat weathered leaf flakes and granular earth clods. Clearly warm brown mineral-organic surface with green touches; no roots or plants. Palette earth #A28A64, shade #7D7255, olive #8F986B, leaf #B6A078.',
     'low-latitude Asian temperate broadleaf ecological region ground reference'),
    ('tropical_moist_humus', '热带湿润林带腐土', 'plain',
     'Representative humid tropical-zone floor material. Deep warm brown crumbling organic soil, fine dark wet-looking grain with flattened russet leaf chips and small muted emerald moss stains. Matte, rich and dark, never glossy or muddy water. Palette earth #806C50, russet #A17D55, moss #6D825C, light clods #A49170.',
     'tropical moist broadleaf ecological region ground reference; no historical jungle boundary inferred'),
    ('dry_woodland_litter', '旱林灌丛带地表', 'plain',
     'Representative dry woodland and sclerophyll-zone floor material. Pale powdery warm soil with sparse curled small dry leaf flakes, thin short woody fibers and embedded chalk-gray mineral specks. Open dusty irregular organic grain, no standing scrub. Palette soil #B3A484, leaves #9C8A65, chalk #C3BEA5, shadow #8D826C.',
     'tropical dry broadleaf or Mediterranean woodland ecological region ground reference'),
    ('savanna_red_soil', '热带草原地表', 'plain',
     'Representative tropical grassland surface. Warm muted reddish-ochre granular ground with sparse short straw-gold grass fibers and flat rust-colored mineral flecks. Red-earth dominated ground with broad calm zones, no trees or termite mounds. Palette earth #AB8A64, rust #987653, straw #C2AD7C, olive #8F9166.',
     'tropical savanna and grassland ecological region ground reference; soil color is representative art'),
    ('flood_meadow', '洪泛草甸地表', 'plain',
     'Representative flood-meadow ground. Dark gray-green fine silt interwoven with flattened narrow sedge blades, quiet broad pale dried-silt traces and short moist organic fibers. Flat continuous ground with visibly different fine linear mat grain, no water, channels or pools. Palette silt #8E9989, sedge #7B8B69, pale #B1B59C, dark humus #6F7B68.',
     'named flooded grassland ecological region ground reference; not historical flooding or wetland extent'),
    ('alluvial_loam', '河谷冲积地表', 'plain',
     'Representative river-valley silt and loam ground. Broad warm fine-grained buff silt patches, uneven tiny earth clods and shallow irregular dried-soil lines, sparse soft grass fibers. Soft sediment-rich material, no farms, plow furrows, water channels or mud-crack polygons. Palette buff #B7A887, loam #9C8D6B, silt #C1B494, grass #919772.',
     'low-relief named alluvial ecological regions close to an archived surveyed river'),
    ('weathered_rock', '风化岩坡地表', 'hill',
     'Representative weathered mountain-ground material. Broad flat broken mineral flakes and embedded stratified stone chips, shallow irregular fracture grain interrupted by small muted olive soil pockets. Strong angular planar grain with restrained short contact shadows, no isolated boulder or mountain silhouette. Palette slate #8B9186, pale mineral #B0B09A, umber #979078, olive #81886B.',
     'DEM-classified hill and mountain cells; representative mineral grain, not a lithological survey'),
    ('alpine_scree', '峰岭碎岩地表', 'peak',
     'Representative high-relief peak-ground material. Dense unequal angular gray scree chips and coarse fine rock splinters, small connected shallow talus-like directional grain. Cool stony surface with light-facing tiny planes and dark crevices, no snow, boulder silhouette or actual raised peaks. Palette stone #9B9F95, highlight #C1C1B0, crevice #6E786D, mineral tan #A6A18B.',
     'DEM-classified peak cells; representative rock fragment grain, not a mapped scree deposit'),
]

STYLE = '''ONE original edge-to-edge hand-painted terrain GROUND MATERIAL for a
premium 2.5D historical turn-based strategy atlas. Exact top-down flat material,
seamless tiling edges, one continuous surface, opaque PNG. Authored visible
material identity that remains legible when the entire image is reduced to
128x128 pixels: use medium-sized grouped grain and finer secondary grain,
NOT a nearly blank beige wash or uniform sponge noise. Roughly sixty percent
calm broad material planes, forty percent readable natural microstructure.
Restrained painterly realism, matte mineral and organic pigments, consistent
soft upper-left illumination with shallow grain shading. Moderate local value
separation, unsaturated but distinct natural colors. No black outlines or
photographic grit. This is an original material, do not copy existing game art.
No landscape scene, sky, horizon, trees, standing bushes, large stones,
mountains, villages, buildings, roads, cultivated fields, rivers, lakes, pools,
coasts, grid, hexagon, borders, words, diagrams, collage, panels, UI or watermark.
Do not draw a specimen disc, object silhouette, rectangular material swatch
inside a margin, or transparent exterior: cover the whole image continuously.
The image is a representative atlas material, not a survey of a named site.
MATERIAL IDENTITY:
'''

ORGANIZATION = [
    'Broad uneven interlocking diagonal grain patches, larger calm opening offset toward upper-right; visible grain distributed asymmetrically across all edges.',
    'Two wide gently curving texture currents, grain-rich areas offset toward lower-left and upper-center; middle is quieter with fine secondary flecks.',
    'Loose unequal islands of connected material grain, separated by broad calm channels of the same ground; avoid evenly spaced spots or a cellular pattern.',
    'Several wide broken near-horizontal material bands, varied thickness and interrupted edges; subtle fine grain crosses between bands; no straight stripes.',
]


def plan():
    rows = []
    for family, name, parent, subject, gate in TYPES:
        for index, arrangement in enumerate(ORGANIZATION, 1):
            rows.append(dict(id=f'tile_surface_{family}_{index:02d}', category='tile',
                family=family, terrain_surface_id=family, variant=index, axis='', region='', role='',
                gate=gate, visible_bounds=[128,110], source_revision='r001',
                runtime_import_max_dimension=256,
                prompt=STYLE+subject+'\nSTRUCTURAL VARIANT: '+arrangement))
    payload = dict(format=1, version='0.2.13', terrain_type_count=20,
        independent_sources=80, originals_per_type=4, source_route='sub2-image-gen/gpt-image-2.5/high',
        original_images_modified=False, manual_compositing=False,
        classification_scope='Twenty regional presentation subtypes; existing twelve movement-rule terrains are retained',
        types=[dict(id=f,name=n,parent_terrain=p,source_gate=g) for f,n,p,s,g in TYPES], assets=rows)
    if PLAN.exists() and json.loads(PLAN.read_text(encoding='utf-8')) != payload:
        raise RuntimeError('Immutable terrain plan mismatch; create an explicit new revision')
    if not PLAN.exists():base.write_json(PLAN,payload)
    return rows


def write_report(rows, complete, failures, started, running=False):
    base.write_json(REPORT,dict(created_at_utc=datetime.now(timezone.utc).isoformat(),
        passed=len(complete)==len(rows) and not failures, running=running,
        requested=len(rows), completed=len(complete), terrain_type_count=20,
        elapsed_seconds=round(time.monotonic()-started,1), catalog_sha256=base.sha(PLAN),
        source_route='sub2-image-gen/gpt-image-2.5/high', original_images_modified=False,
        manual_compositing=False, formal_art_approval=False, failures=failures,
        assets=sorted(complete.values(),key=lambda row:row['id'])))


def install(rows):
    measured=[base.measure(row) for row in rows]
    if any(row is None for row in measured):raise RuntimeError('All 80 independent originals are required')
    if len({row['source_sha256'] for row in measured})!=80:raise RuntimeError('Duplicate original bytes')
    manifest_path=P/'assets/manifest.json';manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    current={row['id']:row for row in manifest['assets']}
    catalog=dict(format=1,version='0.2.13',terrain_type_count=20,originals_per_type=4,
        independent_sources=80,source_plan_sha256=base.sha(PLAN),
        original_images_modified=False,full_texture_draw=True,
        scope='Regional ground presentation, not new water/forest boundaries or movement barriers',types={},records={})
    for family,name,parent,subject,gate in TYPES:
        catalog['types'][family]=dict(id=family,name=name,parent_terrain=parent,source_gate=gate,
            assets=[row['id'] for row in rows if row['family']==family])
    for row in measured:
        row['style_version']='warlord_ew6_v025_terrain_surfaces_v0213'
        row['revision']='terrain_surfaces_v0213_r001'
        row['era']='representative_ground_material_not_historical_landuse_survey'
        target=P/row['engine_path'].removeprefix('res://')
        if target.exists() and base.sha(target)!=row['source_sha256']:
            raise RuntimeError('Existing original differs: '+row['id'])
        if not target.exists():shutil.copyfile(base.ROOT/row['source_file'],target)
        current[row['id']]=row
        catalog['records'][row['id']]={key:row[key] for key in ['family','variant','source_sha256','actual_dimensions']}
    manifest['assets']=sorted(current.values(),key=lambda row:row['id'])
    base.write_json(manifest_path,manifest);base.write_json(CATALOG,catalog)
    base.write_json(P/'reports/terrain_surface_installation.json',dict(passed=True,installed=80,
        terrain_type_count=20,total_raster_assets=len(current),
        total_map_assets=sum(row['category'] in ['tile','scenery','building'] for row in current.values()),
        unique_new_original_hashes=80,source_pngs_modified=False,formal_art_approval=False,
        catalog_sha256=base.sha(CATALOG)))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--prepare-only',action='store_true')
    parser.add_argument('--install',action='store_true');parser.add_argument('--workers',type=int,default=3)
    args=parser.parse_args();base.RAW=RAW;rows=plan();started=time.monotonic()
    if args.prepare_only:print('20 terrain subtypes; 80 immutable Sub2 source jobs planned',flush=True);return
    if args.install:install(rows);print('80 unchanged original PNGs installed',flush=True);return
    complete={row['id']:result for row in rows if (result:=base.measure(row)) is not None};failures=[]
    # Interleave types: review one of every material before producing its four variants.
    queue=[row for variant in range(1,5) for row in rows if row['variant']==variant and row['id'] not in complete]
    write_report(rows,complete,failures,started,bool(queue))
    print(f'Sub2 terrain production {len(complete)}/80; {len(queue)} queued',flush=True)
    with ThreadPoolExecutor(max_workers=max(1,min(3,args.workers))) as pool:
        jobs={pool.submit(base.generate,row):row['id'] for row in queue}
        for job in as_completed(jobs):
            aid=jobs[job]
            try:complete[aid]=job.result()
            except Exception as error:failures.append(dict(id=aid,reason=str(error)))
            write_report(rows,complete,failures,started,True)
            print(f'{len(complete)}/80 ready; {len(failures)} failed; {aid}',flush=True)
    write_report(rows,complete,failures,started)
    raise SystemExit(bool(failures))


if __name__=='__main__':main()
