"""Sub2-only source revisions. Generate, visually review, then install unchanged PNGs."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from PIL import Image
from generate_assets import EQUIPMENT

P = Path(__file__).resolve().parents[1]
ROOT = P.parents[1]
CLI = Path('C:/Users/carzy/.codex/skills/sub2-image-gen/scripts/sub2_image_gen.py')
RAW = ROOT / 'output/imagegen/warlord/ew6_v025/refinement_r002'
REGENERATED = {'scenery_forest_mixed', 'unit_rifle_n', 'unit_armored_car_n', 'unit_river_gunboat_n', 'unit_transport_ship_n'}
STYLE = '''Original premium 2.5D historical strategy game map miniature. Clean hand-painted
volumes with broad clearly lit planes, restrained dark contours, soft blue-green shadows,
upper-left sunlight. Natural medium sage and olive greens, warm neutral highlights,
no brown parchment, engraving, noisy hatching, photorealism, shiny plastic, anime or fantasy.
Fixed elevated orthographic camera looking down at 55 degrees, north is the TOP of image.
One coherent subject only, transparent alpha outside, subject fills central 80 percent,
complete silhouette with generous empty margins. No text, grid, logo, UI, collage or sheet.
'''

def plan():
    forest = {
        'scenery_forest_pine': 'one asymmetric dense grove of FIVE tall northern Chinese pine trees, strong pointed irregular green crowns, small visible dark trunks, different crown heights; oblique overhead so crown tops dominate',
        'scenery_forest_mixed': 'one asymmetric dense grove of FIVE northern Chinese deciduous trees, rounded billowing medium sage green crowns, a few small visible dark trunks, different canopy heights; oblique overhead so crown tops dominate',
        'scenery_forest_pine_sparse': 'one small loose grove of THREE tall conifer trees, separate irregular pointed fresh muted green crowns, lower trunks visible, airy transparent gaps between trees',
        'scenery_forest_mixed_sparse': 'one small loose grove of THREE deciduous trees with rounded medium green crowns, trunks visible, airy transparent gaps between crowns',
    }
    jobs = []
    for aid, subject in forest.items():
        jobs.append(('scenery', aid, STYLE + f'''ONE forest cell object: {subject}.
Designed to read at 70 display pixels: large simple light-facing crown masses, rich darker
right sides and convincing canopy volume. Low wide compact group, not a giant single tree.
Only a faint soft translucent contact shadow below trunks. NO terrain floor, soil rectangle,
grass island, rock, hill, border, colored halo, circular disc or background. Full alpha exterior.
''', 'terrain_r002'))
    for family in ['militia', 'rifle', 'assault', 'engineer', 'elite_assault']:
        base = 'assault' if family == 'elite_assault' else family
        subject = EQUIPMENT[base]
        jobs.append(('unit', f'unit_{family}_n', STYLE + f'''STRICT REAR VIEW of {subject}.
All soldiers walk AWAY FROM THE CAMERA, heading toward the TOP EDGE (north).
Show ONLY BACKS of jackets, rear collars, back of caps, backpacks, rear of shoulders and
heels. We see the back of each soldier's head. NO FACES, eyes, noses, chest buttons or
front of tunics visible. Rifles and carried equipment point toward the TOP of the image,
parallel to direction of movement. Three-quarter overhead REAR angle, NEVER frontal.
At most three small complete soldiers standing on a horizontal ground plane in compact
formation, all face exactly north. Early 1920s Chinese plain unmarked peaked caps, khaki
high-collar jackets, leather belts and puttees. No flags, emblems, badges, WWII helmet,
modern assault rifle, terrain, pedestal or ground disc. No bodily raster rotation.
''', 'directional_r002'))
    for family in ['armored_car','river_gunboat','transport_ship','coastal_gunship','armored_train']:
        vehicle_heading = '''The narrow engine bonnet and FRONT of the car point toward
the TOP edge. Rear doors, back panel and the back of the vehicle face the BOTTOM edge.
Gun barrel aims toward the TOP. Show the BACKS of any crew, NO faces, no front radiator
or headlights at bottom.''' if family=='armored_car' else '''The pointed BOW of the ship is at
the TOP edge, and the broad STERN with rear railing is at the BOTTOM edge. We view from
behind the STERN looking forward along the deck. Ship travels AWAY toward TOP. Bow and
deck guns point TOP. Any sailors show their BACKS. Do not put the pointed bow at bottom.'''
        jobs.append(('unit', f'unit_{family}_n', STYLE+f'''One {EQUIPMENT[family]}.
STRICT elevated REAR VIEW oriented toward the TOP edge of the map (north).
{vehicle_heading}
One compact complete period vehicle, isolated cutout on full transparent alpha exterior.
No backdrop, water, terrain, cloud, halo, glow, atmosphere, shadow disc or lettering.
''', 'directional_r002'))
    return jobs

def generate(job):
    category, aid, prompt, revision = job
    source_revision = 'r003' if aid in {'unit_rifle_n','unit_river_gunboat_n','unit_transport_ship_n'} else ('r002' if aid in REGENERATED else 'r001')
    if aid in REGENERATED:
        prompt = '''CRISP ISOLATED TRANSPARENT SPRITE. Absolutely no glow, aura, fog,
atmosphere, haze, dust cloud, blurred halo, vignette or colored backdrop around the subject.
Every pixel outside the object silhouette must be fully transparent alpha zero. Only
the solid object and a tiny contact shadow immediately beneath its feet/trunks.
''' + prompt + '\nNo atmosphere around the subject. Empty transparent exterior, sharp object edges.\n'
    if aid=='unit_rifle_n':
        prompt='''Transparent PNG game sprite of THREE Republican Chinese rifle infantrymen,
viewed from BEHIND and ABOVE, walking AWAY toward the TOP of the image. See only backs
of jackets, backpacks, back of caps, back of heads, heels and shouldered bolt-action
rifles. Khaki plain high collar uniforms, unmarked peaked caps, puttees. Compact complete
three-man formation with clear separated silhouettes. Clean hand-painted strategy-game
miniature, broad shaded volumes, muted khaki colors, sharp contours, elevated orthographic
view. All faces invisible because this is strictly a REAR VIEW. Isolated cutout ONLY.
Fully transparent alpha zero background, empty transparent gaps between soldiers.
NO background, glow, halo, dust, gradient, atmosphere, ground, shadow, border, grid or text.
Complete feet and rifles inside generous margins. One formation only, not a sheet.'''
    if aid in {'unit_armored_car_n','unit_river_gunboat_n','unit_transport_ship_n'}:
        prompt='''PLAIN UNMARKED VEHICLE. No flagpoles, no flags, no pennants,
no national emblem, star, sun symbol, writing or badge anywhere. Crew wear plain
cloth peaked caps, NEVER metal helmets. Transparent isolated cutout only.\n'''+prompt
    if aid in {'unit_river_gunboat_n','unit_transport_ship_n'}:
        boat='small early twentieth century Chinese river gunboat with one funnel and period deck gun' if aid=='unit_river_gunboat_n' else 'modest early twentieth century coastal cargo transport steamer with one funnel and cargo crates'
        prompt=f'''Transparent PNG sprite of ONE {boat}. Elevated orthographic REAR VIEW:
we look down from BEHIND the STERN. The pointed BOW is at the TOP of the image. The broad
STERN, rear railing and rudder are at the BOTTOM of the image. Ship travels away toward
the TOP edge, north. All deck crew face away showing only their backs, plain navy cloth
caps and dark blue uniforms. Clean hand-painted 2.5D strategy-game miniature, broad shaded
solid volumes, sharp contours, muted gray steel and brown wooden deck, isolated cutout.
Truly empty transparent alpha zero background. NO flags, flagpoles, symbols, text, badges,
water, backdrop, glow, halo, mist, atmosphere, gradient, ground shadow or vignette. Complete
hull and mast with generous empty margins, one ship only, not a sheet.'''
    if aid=='unit_armored_train_n':
        prompt='''Transparent PNG game miniature of ONE compact 1920s armored steam
locomotive, seen from BEHIND and ABOVE, strictly a REAR VIEW. The locomotive travels
AWAY toward the TOP edge, north. Its steam chimney and boiler FRONT are at the TOP;
its closed riveted armored cab BACK WALL and rear coupling are at the BOTTOM. We see
the rear cab wall, NEVER the front radiator, headlamp or smokebox at the bottom.
One coherent short continuous vehicle with attached wheels and simple turret pointing
TOP. NO separate cannon, detached carriage, soldiers, rails, flags, national symbols
or text. Hand-painted 2.5D historical strategy-game style, muted olive steel, broad lit
volumes, clear silhouette, elevated orthographic rear camera. Fully transparent alpha
zero exterior, empty generous margins, no glow, halo, smoke, background or ground.'''
    folder = RAW / aid / source_revision
    folder.mkdir(parents=True, exist_ok=True)
    prompt_path, source = folder/'prompt.txt', folder/'source.png'
    if prompt_path.exists() and prompt_path.read_text(encoding='utf-8') != prompt:
        raise RuntimeError('immutable prompt mismatch: ' + aid)
    if not prompt_path.exists():
        prompt_path.write_text(prompt, encoding='utf-8')
    if not source.exists():
        log_path = folder/'generation.log'
        attempt = 2
        while log_path.exists():
            log_path = folder/f'generation_attempt_{attempt:02}.log'
            attempt += 1
        with log_path.open('w', encoding='utf-8') as log:
            run = subprocess.run([sys.executable, str(CLI), 'generate', '--model', 'gpt-image-2.5',
                '--quality', 'high', '--size', '1024x1024', '--background', 'transparent',
                '--prompt-file', str(prompt_path), '--out', str(source)], stdout=log,
                stderr=subprocess.STDOUT, timeout=900)
        if run.returncode or not source.exists():
            raise RuntimeError('Sub2 generation failed: ' + aid + '; see ' + str(log_path))
    with Image.open(source) as im:
        dimensions = list(im.size)
        alpha = im.getchannel('A').getextrema()[0] if im.mode == 'RGBA' else 255
    if alpha != 0:
        raise RuntimeError('transparent exterior missing: ' + aid)
    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    return dict(id=aid, category=category, subject=aid, view='n' if category=='unit' else 'elevated',
        state='generated_pending_visual_review', game_ready=False, source_kind='sub2_image_gen',
        model='gpt-image-2.5', quality='high', style_version='warlord_ew6_v025_'+revision,
        era='1920-1924', source_file=source.relative_to(ROOT).as_posix(), source_sha256=digest(source),
        prompt_file=prompt_path.relative_to(ROOT).as_posix(), prompt_sha256=digest(prompt_path),
        actual_dimensions=dimensions, planned_source_request=[1024,1024],
        engine_path=f'res://assets/{category}/{aid}.png', planned_engine_path=f'res://assets/{category}/{aid}.png',
        runtime_import_max_dimension=512, background='transparent', alpha_min=alpha,
        revision=revision, image_modified=False, manual_compositing=False)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--only', default='')
    ap.add_argument('--workers', type=int, default=2)
    ap.add_argument('--install-reviewed', action='store_true')
    args=ap.parse_args()
    selected=[job for job in plan() if not args.only or job[1] in args.only.split(',')]
    rows=[]; failures=[]
    if args.install_reviewed:
        # This mode only installs existing originals after the agent has viewed them.
        for job in selected:
            rev='r003' if job[1] in {'unit_rifle_n','unit_river_gunboat_n','unit_transport_ship_n'} else ('r002' if job[1] in REGENERATED else 'r001')
            if not (RAW/job[1]/rev/'source.png').exists():raise SystemExit('generate first: '+job[1])
            rows.append(generate(job))
        path=P/'assets/manifest.json'; data=json.loads(path.read_text(encoding='utf-8'))
        current={row['id']:row for row in data['assets']}
        for row in rows:
            previous=current.get(row['id'])
            if previous and previous['source_sha256']!=row['source_sha256']:
                row['revision_history']=previous.get('revision_history',[])+[{key:previous.get(key) for key in ('revision','source_file','source_sha256','prompt_file','prompt_sha256')}]
            elif previous:
                row['revision_history']=previous.get('revision_history',[])
            row['visual_review']='source orientation and silhouette inspected in native image viewer; historical/formal art approval pending'
            shutil.copyfile(ROOT/row['source_file'], P/row['engine_path'].removeprefix('res://'))
            current[row['id']]=row
        data['assets']=sorted(current.values(),key=lambda row:row['id'])
        path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    else:
        with ThreadPoolExecutor(max_workers=max(1,args.workers)) as pool:
            pending={pool.submit(generate,job):job[1] for job in selected}
            for future in as_completed(pending):
                try:rows.append(future.result()); print(pending[future]+': source generated',flush=True)
                except Exception as error:failures.append(dict(id=pending[future],reason=str(error)));print(str(error),flush=True)
    report=dict(route='sub2-image-gen/gpt-image-2.5',passed=not failures,installed=args.install_reviewed,
        requested=len(selected),completed=[row['id'] for row in rows],failures=failures,
        manual_compositing=False,source_images_modified=False,assets=rows)
    report_path=P/'reports/terrain_direction_refinement.json'
    report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    raise SystemExit(bool(failures))

if __name__=='__main__':main()
