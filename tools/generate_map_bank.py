"""Produce the 666-source map expansion through the required Sub2 CLI only.

Every PNG is an independent generation, preserved byte-for-byte. PIL is used
only to measure source dimensions/alpha and inspect low-resolution statistics.
There is no crop, recolor, compositing, atlas packing, or image-writing code.
The catalog and baseline are immutable; a restart resumes completed sources.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import time
from PIL import Image, ImageStat

P = Path(__file__).resolve().parents[1]
ROOT = P.parents[1]
RAW = ROOT / 'output/imagegen/warlord/ew6_v025/map_bank_v0212'
CLI = Path('C:/Users/carzy/.codex/skills/sub2-image-gen/scripts/sub2_image_gen.py')
CATALOG = P / 'presentation/data/map_bank_plan.json'
BASELINE = P / 'reports/map_bank_baseline.json'
REPORT = P / 'reports/map_bank_generation.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temp.replace(path)


STYLE = '''ONE original isolated terrain miniature for a premium historical
turn-based strategy game, intended to read clearly at 100-170 screen pixels.
Restrained painterly 2.5D cartographic realism: broad coherent light planes,
substantial sculptural volume, crisp irregular silhouette and soft fine edges.
Fixed elevated orthographic camera at 55 degrees, image top is north.
Consistent upper-left sunlight, softly shaded lower-right faces. Matte muted
olive-sage grass #929D72, gray-green stone #7D8676, cool slate-olive shadow
#53644F, subdued warm highlights #BDC19A. Ground should harmonize with a quiet
sage-olive map; no saturated emerald, neon, glossy plastic, black ink hatching
or photorealistic texture noise. No visible ground rectangle or circular base.
One connected terrain group, no detached specimen rows, sheet, panels or props.
Zero-alpha transparent exterior, generous empty margins, complete subject fits
inside 78 percent of canvas. No sky, horizon, backdrop, grid, hexagon, labels,
letters, logo, UI, frame or watermark. Do not draw an existing game's artwork.
This is an unnamed terrain symbol, not a claim about a particular real place.
'''

REGIONS = {
    'north_china': 'North Chinese vernacular: muted gray-tile shallow pitched roofs, low gray-brick courtyard houses, restrained earth-toned walls; avoid pagodas and invented monuments',
    'south_china': 'southern Chinese vernacular: closely spaced gray-tile pitched roofs, pale limewashed walls, narrow lanes and simple courtyards; avoid iconic monuments and elaborate pagodas',
    'japan': 'Japanese vernacular: low timber-and-plaster houses, subdued gray tiled or thatched pitched roofs, compact irregular lanes; no invented castle or torii landmark',
    'korea': 'Korean vernacular: modest low timber/plaster courtyard houses, gently curved gray-tile roofs and a few thatched small roofs; no Japanese castle, torii or invented palace',
    'south_asia': 'a generic South Asian settlement symbol: low warm plaster or brick courtyard blocks, restrained flat and gently pitched roofs, shaded porches; no invented temple, religious monument or palace',
    'southeast_asia': 'a generic mainland Southeast Asian settlement symbol: low timber houses with pitched brown roofs, modest plaster market structures and raised porches; no invented temple or pagoda landmark',
    'north_eurasia': 'a generic northern Eurasian settlement symbol: low timber houses with steep muted slate-brown roofs, a few modest masonry civic buildings; no onion-dome church, invented monument or modern tower',
    'west_central_asia': 'a generic West/Central Asian settlement symbol: low ochre brick and plaster courtyard blocks, quiet flat roofs, enclosed shaded lanes; no invented mosque, minaret, monumental dome or palace',
}


def plan():
    rows = []

    def add(category, family, n, subject, *, axis='', region='', role='', gate='', dimensions=(140, 110)):
        aid = f'{category}_bank_{family}_{n:03d}'
        if category == 'tile':
            prompt = '''ONE opaque seamless hand-painted ground material for an
original historical strategy atlas. Exact top-down flat view, edge-to-edge
continuous material, seamless edges. Quiet matte low contrast color and fine
readable natural brushwork. Ninety percent calm continuous surface, with broad
soft tonal drift and sparse subtle detail. No raised objects or cast shadows,
buildings, fields, roads, rivers, shorelines, hexagons, map boundaries, words,
frames, UI, paper, camouflage, panels or grid. No photography or noisy sponge
brush. Do not reproduce any existing game's image. Material specification:
''' + subject
        elif category == 'building':
            prompt = '''ONE original small settlement miniature for a premium
historical strategy map. Restrained hand-painted 2.5D volume, fixed 55-degree
elevated orthographic view, north at image top, upper-left sunlight, soft cool
lower-right shading. Readable large roof planes and coherent grouped buildings
at 100-150 screen pixels. Quiet gray, umber, ivory and sage palette, harmonious
with muted olive ground. Generic representative architecture before 1940,
not an exact reconstruction of any named landmark. Complete single group inside
78 percent of canvas with generous margins and zero-alpha transparent exterior.
No landscape rectangle or disc base, sky, horizon, people, soldiers, flags,
readable writing, labels, UI, grid, panels, logo, frame or watermarks. No modern
cars, skyscrapers, power pylons or modern concrete roads. No copy of existing
game assets. Regional visual language: ''' + REGIONS[region] + '\n' + subject
        else:
            prompt = STYLE + subject
        rows.append(dict(id=aid, category=category, family=family, variant=n,
                         axis=axis, region=region, role=role, gate=gate,
                         visible_bounds=list(dimensions), prompt=prompt,
                         runtime_import_max_dimension=384 if category == 'building' else 256,
                         source_revision='r001'))

    # 120 low-contrast materials. Variation is in brush structure and visible
    # grain/patch organization, never merely a copy with a new tint.
    materials = [
        ('meadow', 36, '#9BA67D quiet sage-olive meadow', 'plain'),
        ('dry_grass', 24, '#A5A17D subdued dry grass with tiny straw flecks, no sand dunes or desert', 'plain'),
        ('rocky_ground', 16, '#939A80 weathered muted gray-olive mineral ground with tiny embedded flat stone flecks, no raised boulders', 'hill_mountain_peak'),
        ('woodland_floor', 16, '#7D8D69 cool olive earth with tiny quiet leaf litter, no trees or branches', 'source_forest'),
        ('wetland_ground', 16, '#829A88 muted gray-green moist soil with tiny reed-stubble flecks, no water channels or invented pools', 'source_wetland'),
        ('sea_water', 12, '#587D84 subdued blue-gray open water with very fine soft water ripples, no coastline or objects', 'source_water'),
    ]
    grain = ['sparse fine short diagonal strokes', 'tiny irregular separated flecks',
             'very fine crosswise broken wisps', 'faint long soft brush filaments',
             'small curved interrupted grain', 'delicate scattered pin-point grain']
    distribution = ['broad very faint overlapping oval drift', 'wide quiet gently curving streaks',
                    'loosely spaced fine islands of grain', 'one calm center with sparse edge grain',
                    'soft broad interlocking rounded patches', 'long shallow diagonal tonal currents']
    for family, count, color, gate in materials:
        for index in range(count):
            add('tile', family, index + 1, f'{color}. Grain: {grain[index % 6]}.\nDistribution: {distribution[index // 6]}. Keep all changes within a very narrow tonal range. No obvious large speckles.', gate=gate)

    # 144 woodland silhouettes, differentiated by canopy topology, species
    # language, density and opening. Only source forest cells/dated sites use them.
    forest_families = [('pine_dense',32),('pine_sparse',32),('deciduous_dense',32),('deciduous_sparse',32),('forest_edge',16)]
    forest_layouts = [
        'a broad shallow crescent with an open inward-facing notch',
        'an asymmetric tapering wedge with its tallest canopy off-center',
        'a compact kidney-shaped grove with two unequal canopy lobes',
        'a loose winding S-shaped grove, a clear shallow opening in the middle',
        'an irregular triangle with a broad low foreground and taller rear',
        'a long oval canopy group with an offset gap on the right edge',
        'a diagonal stepped group with three overlapping canopy levels',
        'a compact broken ring whose small opening faces the lower-left',
    ]
    crowns = ['one dominant tall crown and several small companions',
              'two unequal dominant crowns joined by low understory',
              'three descending crown heights that give a strong depth rhythm',
              'a low broad canopy with one slender rear crown rising above it']
    for family, count in forest_families:
        pine = family.startswith('pine')
        dense = 'dense' in family
        for index in range(count):
            detail = ('slender conifer trees with tiered tapering pine crowns' if pine else 'deciduous broadleaf trees with rounded asymmetric clustered crowns')
            if family == 'forest_edge':detail = 'an irregular mixed woodland edge, rounded deciduous crowns with a few restrained conifers; canopy thins naturally toward one side'
            density = 'nine to fourteen overlapping trunks and joined crowns, a connected but layered canopy' if dense else 'four to seven spaced trunks with clear negative spaces between crowns, joined by a thin quiet mossy foot'
            add('scenery', family, index + 1,
                f'One grove of {detail}. {density}. Layout: {forest_layouts[index % 8]}.\nCrown hierarchy: {crowns[index // 8]}. Clearly visible short trunks, canopy shadow and separate light-facing foliage volumes. No river, road, rock, field, flower, snow or building. No enclosing grass platform.',
                gate='source_forest', dimensions=(132,108))

    # 96 foothills, 96 ridges and 48 peak groups; axis is respected by the
    # source-driven crest orientation. Each entry has a distinct silhouette.
    landforms = [
        'one dominant off-center summit with two low rounded shoulders',
        'two unequal summits connected by a deep readable saddle',
        'three descending summits with an interrupted sloping crest',
        'a long asymmetric high shoulder tapering to a low spur',
        'a compact horseshoe crest enclosing a shallow open valley',
        'a bent dog-leg crest with one broad front slope',
        'a pair of broad overlapping masses and a narrow rear peak',
        'a stepped crest with a high back summit and a lower front shelf',
        'a forked Y-shaped crest with one longer tapered branch',
        'a broad central dome with a short rocky lateral spur',
        'a shallow zigzag crest with alternating high and low saddles',
        'a sloping double shoulder with a narrow deep cleft on one side',
    ]
    surfaces = [
        'broad soft grassy slopes with one quiet exposed gray rock band',
        'a smooth long lit face with an offset angular shaded rock face',
        'an irregular rocky crown and softly rounded lower foothill shoulders',
        'two coherent diagonal mineral strata crossing the visible slope',
    ]
    for base, total in [('foothill',96),('ridge',96),('peak',48)]:
        for axis in ['ew','ns']:
            for index in range(total // 2):
                orientation = 'LEFT to RIGHT, broad 1.6:1 visible silhouette' if axis == 'ew' else 'TOP toward BOTTOM in depth, overlapping front-to-back, compact 0.9:1 visible silhouette; do not make a left-right strip'
                height = {'foothill':'Low rolling hill relief, substantial smooth convex volume; avoid tall pointy mountains', 'ridge':'Medium-high rocky mountain ridge, angular crest and broad shaded flanks', 'peak':'High angular mountain group with a clearly dominant summit and deeply shaded flank; absolutely no invented snowcap'}[base]
                add('scenery', f'{base}_{axis}', index + 1,
                    f'{height}. Runs {orientation}.\nSilhouette: {landforms[index % 12]}. Surface organization: {surfaces[index // 12]}. One connected mass with irregular soft grass foot. No trees, snow, roads, rivers, settlements, loose surrounding stones or round ground platform.',
                    axis=axis, gate={'foothill':'source_hill','ridge':'source_mountain','peak':'source_peak'}[base],
                    dimensions=((144,94) if axis=='ew' else (96,116)) if base=='foothill' else ((176,120) if axis=='ew' else (116,146)))

    small_layouts = [
        'a compact shallow crescent, longest side along left-to-right',
        'an irregular diagonal tapered wedge rising toward upper-right',
        'two unequal overlapping lobes with a narrow side notch',
        'a broken shallow S curve with small open negative spaces',
        'an asymmetric broad oval with a narrow tapered end',
        'a compact three-lobed triangle of descending heights',
        'a bent low ridge with one longer lateral extension',
        'a stepped edge, high at the back and low in front',
    ]
    family_subjects = {
        'rocky_outcrop': ['one low exposed weathered rock outcrop with angular gray stone planes', 'one low rounded gray boulder outcrop partly embedded in grassy soil', 'a compact low slab outcrop with two broad visible mineral strata'],
        'wetland_reeds': ['a small joined tuft group of slender muted reeds with tan seedheads', 'a low connected patch of narrow gray-green marsh sedges', 'an uneven reed edge with a few tall stems rising above short grass'],
        'riverbank': ['a very low small tuft group of riparian grass with a few fine reeds', 'a subtle low grassy bank hummock with two short sedge tufts', 'a quiet connected narrow edge of grass and small rounded pebbles'],
        'shore': ['a low small irregular coastal stone cluster with softly weathered gray faces', 'a low muted sandy-gravel shoreline verge with a few small embedded stones', 'a compact low coastal grassy hummock with subdued tiny gray pebbles'],
    }
    for family, subjects in family_subjects.items():
        for index in range(24):
            add('scenery', family, index+1,
                f'{subjects[index // 8]}. Layout: {small_layouts[index % 8]}. Keep it low and subtle, visible detail at 70-100 pixels. No trees, building, river channel, pool, open water, white surf, cliff, bridge, road or invented landmark. All exterior is transparent; no opaque grass floor.',
                gate={'rocky_outcrop':'source_hill_mountain_peak','wetland_reeds':'source_wetland','riverbank':'surveyed_river_landside','shore':'surveyed_coast_landside'}[family], dimensions=(92,64))

    # 66 settlement sources. Culture is bound to a source location, never to
    # the faction currently occupying that city. They are symbols, not surveys.
    settlement_shapes = [
        'an asymmetric L-shaped cluster of uneven roof heights with an open little courtyard',
        'a staggered diagonal cluster around one short narrow lane, one low foreground annex',
    ]
    for role, count_per_region in [('village',2),('market',2),('county',2),('capital',1)]:
        for region in REGIONS:
            for index in range(count_per_region):
                size = {'village':'three to five small houses', 'market':'seven to nine modest houses and two simple awnings', 'county':'eleven to fourteen modest houses grouped around a restrained larger administrative courtyard', 'capital':'a dense group of eighteen to twenty-two roof volumes with two restrained larger civic courtyards'}[role]
                add('building', f'{role}_{region}', index+1,
                    f'A {role} settlement SYMBOL, {size}. {settlement_shapes[index]}. Roof planes and cast shadows must make the settlement feel solid and layered. No walls around the settlement, towers, fortifications, temple or signature monument unless independently authored elsewhere.',
                    role=role, region=region, gate='real_sourced_settlement_only', dimensions=(136,116))
    for index, region in enumerate(['north_china','south_china','japan','korea','north_eurasia','south_asia']):
        add('building', f'station_{region}', 1,
            'One modest late nineteenth/early twentieth-century railway station SYMBOL: low rectangular masonry or timber passenger building, shallow roofed platform canopy, one short freight shed. Asymmetric grouped roof volumes, strong readable depth. No tracks outside the subject, locomotive, train, named station sign or clock-face lettering. Show only the station architecture.',
            role='station', region=region, gate='source_railway_and_station_unlocked', dimensions=(136,100))
    for region in ['north_china','south_china','japan','southeast_asia']:
        add('building', f'dock_{region}', 1,
            'One modest historical port warehouse group SYMBOL: two or three low warehouses, a short simple timber pier finger and a small hand-operated hoist. Readable broad roof planes and depth. No water rectangle, boats, huge modern cranes, ship, flags or invented named port landmark. Transparent exterior.',
            role='dock', region=region, gate='real_source_port_only', dimensions=(136,100))
    assert len(rows) == 666, len(rows)
    assert len({r['id'] for r in rows}) == 666
    assert len({r['prompt'] for r in rows}) == 666
    return rows


def initialize():
    rows = plan()
    payload = dict(format=1, source_route='sub2-image-gen/gpt-image-2.5/high',
                   original_images_modified=False, manually_composited=False,
                   baseline_map_assets=74, additional_independent_sources=666,
                   target_map_assets=740, families={}, assets=rows)
    for row in rows:payload['families'][row['family']]=payload['families'].get(row['family'],0)+1
    if CATALOG.exists():
        if json.loads(CATALOG.read_text(encoding='utf-8')) != payload:
            raise RuntimeError('Immutable production catalog differs; create a revision explicitly')
    else:write_json(CATALOG,payload)
    if not BASELINE.exists():
        manifest=json.loads((P/'assets/manifest.json').read_text(encoding='utf-8'))
        maps=[{key:r.get(key) for key in ['id','category','source_file','source_sha256','engine_path']} for r in manifest['assets'] if r['category'] in ['tile','scenery','building']]
        if len(maps)!=74:raise RuntimeError(f'Expected 74 original map assets before production, got {len(maps)}')
        write_json(BASELINE,dict(created_at_utc=datetime.now(timezone.utc).isoformat(),count=74,assets=maps,
                                 target_count=740,additional_required=666,definition='tile + scenery + building; excludes unit, UI, portraits, FX, copies and tint variants'))
    return rows


def measure(row):
    folder=RAW/row['id']/row['source_revision']
    source=folder/'source.png';prompt_file=folder/'prompt.txt'
    if not source.exists():return None
    with Image.open(source) as im:
        im.verify()
    with Image.open(source) as im:
        dimensions=list(im.size)
        alpha=im.getchannel('A') if im.mode=='RGBA' else None
        extrema=alpha.getextrema() if alpha is not None else (255,255)
        bounds=alpha.point(lambda a:255 if a>16 else 0).getbbox() if alpha is not None else (0,0,*im.size)
        if bounds is None:raise RuntimeError('Empty alpha image: '+row['id'])
        alpha_coverage=(ImageStat.Stat(alpha).mean[0]/255) if alpha is not None else 1.0
        # Hashing is an analysis-only duplicate check, not an image transform
        # written back to disk. Alpha silhouette is included for future QA.
        thumb=im.convert('RGBA').resize((24,24))
        fingerprint=hashlib.sha256(thumb.tobytes()).hexdigest()
    if row['category']!='tile' and extrema[0]!=0:
        raise RuntimeError('Transparent exterior missing: '+row['id'])
    return {**{k:v for k,v in row.items() if k!='prompt'},
            'state':'generated_pending_visual_review','game_ready':False,
            'source_kind':'sub2_image_gen','model':'gpt-image-2.5','quality':'high',
            'style_version':'warlord_ew6_v025_map_bank_v0212',
            'era':'pre_1940_representative_symbol_not_exact_historical_reconstruction' if row['category']=='building' else 'terrain_symbol_not_historical_landcover',
            'source_file':source.relative_to(ROOT).as_posix(),'source_sha256':sha(source),
            'prompt_file':prompt_file.relative_to(ROOT).as_posix(),'prompt_sha256':sha(prompt_file),
            'actual_dimensions':dimensions,'planned_source_request':[1024,1024],
            'engine_path':f'res://assets/{row["category"]}/{row["id"]}.png',
            'planned_engine_path':f'res://assets/{row["category"]}/{row["id"]}.png',
            'background':'opaque_seamless' if row['category']=='tile' else 'transparent',
            'alpha_min':extrema[0],'alpha_coverage_mean':round(alpha_coverage,6),
            'alpha_bounds':list(bounds),'analysis_fingerprint_rgba_24':fingerprint,
            'revision':'map_bank_v0212_r001','image_modified':False,'manual_compositing':False,
            'visual_review':'pending; automated alpha/format/provenance checks are not formal art approval'}


def generate(row):
    folder=RAW/row['id']/row['source_revision'];folder.mkdir(parents=True,exist_ok=True)
    source=folder/'source.png';prompt=folder/'prompt.txt'
    if prompt.exists() and prompt.read_text(encoding='utf-8')!=row['prompt']:
        raise RuntimeError('Immutable prompt mismatch: '+row['id'])
    if not prompt.exists():prompt.write_text(row['prompt'],encoding='utf-8')
    if not source.exists():
        for retry in range(8):
            attempt=1;log=folder/'generation.log'
            while log.exists():
                attempt+=1;log=folder/f'generation_attempt_{attempt:02d}.log'
            with log.open('w',encoding='utf-8') as stream:
                result=subprocess.run([sys.executable,str(CLI),'generate','--model','gpt-image-2.5',
                    '--quality','high','--size','1024x1024','--background',
                    'opaque' if row['category']=='tile' else 'transparent','--prompt-file',str(prompt),'--out',str(source)],
                    stdout=stream,stderr=subprocess.STDOUT,timeout=1200)
            if not result.returncode and source.exists():break
            diagnostic=log.read_text(encoding='utf-8',errors='replace')
            transient=any(marker in diagnostic for marker in ['HTTP 429','HTTP 502','HTTP 503','HTTP 504','timed out'])
            if not transient or retry==7:
                raise RuntimeError('Sub2 generation failed: '+row['id']+'; local log '+log.relative_to(ROOT).as_posix())
            # Native worker backoff leaves the foreground agent responsive.
            # The exact same prompt/model is retained, with every attempt logged.
            time.sleep(min(60,12*(retry+1)))
    return measure(row)


def report(rows, complete, failures, *, running, requested, started):
    result=dict(created_at_utc=datetime.now(timezone.utc).isoformat(),
                passed=len(complete)==666 and not failures,running=running,
                catalog_file=CATALOG.relative_to(P).as_posix(),catalog_sha256=sha(CATALOG),
                baseline_file=BASELINE.relative_to(P).as_posix(),baseline_count=74,
                target_map_assets=740,target_additional=666,requested_this_run=requested,
                completed=len(complete),elapsed_this_run_seconds=round(time.monotonic()-started,1),
                source_route='sub2-image-gen/gpt-image-2.5/high',
                original_images_modified=False,manual_compositing=False,
                formal_art_approval=False,failures=failures,
                assets=sorted(complete.values(),key=lambda r:r['id']))
    write_json(REPORT,result)


def install(rows):
    if (P/'presentation/data/map_settlement_extension_plan.json').exists():
        raise RuntimeError('The explicit settlement extension is planned; install both complete catalogs with generate_settlement_bank.py --install')
    measured=[measure(row) for row in rows]
    if any(row is None for row in measured):raise RuntimeError('All 666 original sources are required before installation')
    hashes=[row['source_sha256'] for row in measured]
    if len(set(hashes))!=666:raise RuntimeError('Duplicate source bytes found; no duplicate is counted')
    manifest_path=P/'assets/manifest.json';manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    current={row['id']:row for row in manifest['assets']}
    visuals=dict(format=1,baseline_count=74,additional_count=666,total_map_assets=740,
                 original_images_modified=False,full_texture_draw=True,families={},records={})
    for row in measured:
        target=P/row['engine_path'].removeprefix('res://')
        if target.exists() and sha(target)!=row['source_sha256']:raise RuntimeError('Refuse to replace existing source: '+row['id'])
        if not target.exists():shutil.copyfile(ROOT/row['source_file'],target)
        current[row['id']]=row
        visuals['families'].setdefault(row['family'],[]).append(row['id'])
        visuals['records'][row['id']]={key:row[key] for key in ['category','family','variant','axis','region','role','gate','visible_bounds','actual_dimensions','alpha_bounds','source_sha256']}
        visuals['records'][row['id']]['dimensions']=visuals['records'][row['id']].pop('actual_dimensions')
    manifest['assets']=sorted(current.values(),key=lambda row:row['id']);write_json(manifest_path,manifest)
    write_json(P/'presentation/data/map_bank_visuals.json',visuals)
    write_json(P/'reports/map_bank_installation.json',dict(passed=True,installed=666,baseline=74,
        total_map_assets=sum(r['category'] in ['tile','scenery','building'] for r in current.values()),
        unique_new_original_hashes=666,source_pngs_modified=False,formal_art_approval=False,
        source_catalog_sha256=sha(CATALOG),runtime_visuals_sha256=sha(P/'presentation/data/map_bank_visuals.json')))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--workers',type=int,default=3)
    parser.add_argument('--only',default='')
    parser.add_argument('--prepare-only',action='store_true')
    parser.add_argument('--install',action='store_true')
    args=parser.parse_args();started=time.monotonic();rows=initialize()
    if args.prepare_only:
        print('Immutable catalog ready: 74 baseline + 666 independent sources = 740 map assets',flush=True);return
    if args.install:
        install(rows);print('666 unchanged Sub2 originals installed; formal visual review remains separate',flush=True);return
    selected=[row for row in rows if not args.only or row['id'] in args.only.split(',')]
    complete={};failures=[]
    for row in rows:
        existing=measure(row)
        if existing is not None:complete[row['id']]=existing
    by_family=defaultdict(deque)
    for row in selected:
        if row['id'] not in complete:by_family[row['family']].append(row)
    # Interleave families so alpha, silhouette and regional consistency can be
    # reviewed early, before hundreds of one category have been generated.
    missing=[]
    while any(by_family.values()):
        for family in by_family:
            if by_family[family]:missing.append(by_family[family].popleft())
    report(rows,complete,failures,running=bool(missing),requested=len(missing),started=started)
    print(f'Sub2 production: {len(complete)}/666 existing; {len(missing)} scheduled, {args.workers} native workers',flush=True)
    with ThreadPoolExecutor(max_workers=max(1,args.workers)) as pool:
        pending={pool.submit(generate,row):row['id'] for row in missing}
        for future in as_completed(pending):
            aid=pending[future]
            try:complete[aid]=future.result()
            except Exception as error:failures.append(dict(id=aid,reason=str(error)))
            report(rows,complete,failures,running=True,requested=len(missing),started=started)
            print(f'{len(complete)}/666 ready; {len(failures)} failed; {aid}',flush=True)
    report(rows,complete,failures,running=False,requested=len(missing),started=started)
    raise SystemExit(bool(failures))


if __name__=='__main__':main()
