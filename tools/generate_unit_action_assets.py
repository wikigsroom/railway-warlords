"""Immutable, independent action key poses via the user's Sub2 route only."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import argparse, hashlib, json, shutil, subprocess, sys
from PIL import Image
from generate_unit_direction_assets import STYLE, DIRECTIONS, PROJECT, ROOT, SKILL

RAW=ROOT/'output/imagegen/warlord/ew6_v025/actions'

def plan():
    for direction, phrase in DIRECTIONS.items():
        view={'n':'Strict rear view: ONLY backs of caps, jackets and shoulders; no faces, noses, chest buttons or front of tunics visible.',
              's':'Strict front view: faces and fronts of jackets visible; not backs.',
              'e':'Right-facing side view: faces, toes and rifles point to the RIGHT edge.',
              'w':'Left-facing side view: faces, toes and rifles point to the LEFT edge.'}[direction]
        for pose in ['march_a','march_b','fire','hit']:
            action={'march_a':'Marching contact pose: the LEFT foot is forward and planted, RIGHT foot behind with heel lifted. Rifles held safely across the chest or right shoulder; relaxed marching elbows. All three infantrymen use the same clear left-forward stride.',
                    'march_b':'Marching opposite contact pose: the RIGHT foot is forward and planted, LEFT foot behind with heel lifted. Rifles held safely across the chest or right shoulder; relaxed marching elbows. All three infantrymen use the same clear right-forward stride.',
                    'fire':'Braced standing shooting pose: feet apart, knees slightly flexed, rifle butt pressed into right shoulder, right hand on trigger, left hand supports wooden fore-end, cheek at stock. All THREE bolt-action rifles aim parallel to the stated map heading. No muzzle flash or smoke; the game animates those separately.',
                    'hit':'Brief NON-GRAPHIC hit-reaction pose: shoulders recoil backward slightly, knees bend, weight shifts to the rear foot, one elbow lifts in reflex while both hands retain the rifle. Still upright and still facing the stated direction. Rifles lowered slightly, no muzzle flash. Same three men and same formation. NO blood, injuries, bandages, gore, fallen men or dramatic flying bodies.'}[pose]
            prompt=STYLE+f'''
ONE complete independent transparent game formation: exactly THREE Chinese regular
rifle infantrymen of 1920-1924, wearing matching muted KHAKI high-collar tunics,
plain unmarked khaki peaked caps, dark brown leather belt and simple brown rectangular
backpack, puttees and black ankle boots. Full-length early bolt-action wooden-stock
rifles. All three face {phrase}. {view}
ACTION: {action}
The camera is the SAME fixed elevated orthographic strategy-map camera for every
direction. Upright bodies on a horizontal ground plane; feet toward the canvas bottom.
Compact triangular formation, three men with visible separation, equal scale,
low-wide silhouette and upper-left sunlight, soft darker right planes. Quiet broad
hand-painted volumes, clean edges, restrained olive-khaki palette, premium 2.5D map art.
Only the subject, centered in the middle 78 percent of a square canvas. Complete boots,
heads and weapons inside generous transparent margins. Fully transparent alpha exterior
and gaps. No floor, terrain, ground slab, circular disc, shadow, haze, glow, gradient,
text, insignia, logo, flags, helmets, modern camouflage or automatic weapons. NOT a
sprite sheet, animation strip, collage or multiple panels. One single formation only.
'''
            yield f'unit_rifle_{direction}_{pose}',direction,pose,prompt

def generate(job):
    aid,direction,pose,prompt=job;folder=RAW/aid/'r001';folder.mkdir(parents=True,exist_ok=True)
    text=folder/'prompt.txt';source=folder/'source.png'
    if text.exists() and text.read_text(encoding='utf-8')!=prompt:raise RuntimeError('immutable prompt conflict: '+aid)
    if not text.exists():text.write_text(prompt,encoding='utf-8')
    if not source.exists():
        with (folder/'generation.log').open('w',encoding='utf-8') as log:
            result=subprocess.run([sys.executable,str(SKILL),'generate','--model','gpt-image-2.5','--size','1024x1024','--quality','high','--background','transparent','--prompt-file',str(text),'--out',str(source)],stdout=log,stderr=subprocess.STDOUT,timeout=900)
        if result.returncode or not source.exists():raise RuntimeError('Sub2 generation failed: '+aid)
    with Image.open(source) as image:
        if image.mode!='RGBA' or image.getchannel('A').getextrema()[0]!=0:raise RuntimeError('missing transparent exterior: '+aid)
        dimensions=list(image.size);bounds=list(image.getchannel('A').point(lambda value:255 if value>32 else 0).getbbox())
    destination=PROJECT/'assets/unit'/f'{aid}.png'
    if destination.exists() and destination.read_bytes()!=source.read_bytes():raise RuntimeError('immutable runtime source conflict: '+aid)
    shutil.copyfile(source,destination)
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    return dict(id=aid,category='unit',subject='rifle',view=direction,action_pose=pose,
        state='generated_pending_visual_review',game_ready=False,source_kind='sub2_image_gen',model='gpt-image-2.5',quality='high',
        style_version='warlord_ew6_v025_action_r001',era='1920-1924',source_file=source.relative_to(ROOT).as_posix(),source_sha256=sha(source),
        prompt_file=text.relative_to(ROOT).as_posix(),prompt_sha256=sha(text),actual_dimensions=dimensions,planned_source_request=[1024,1024],
        engine_path='res://'+destination.relative_to(PROJECT).as_posix(),planned_engine_path='res://'+destination.relative_to(PROJECT).as_posix(),
        runtime_import_max_dimension=512,background='transparent',alpha_min=0,alpha_bounds=bounds,revision='action_r001',image_modified=False,manual_compositing=False)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--workers',type=int,default=2);args=parser.parse_args()
    records=[];failed=[]
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures={pool.submit(generate,job):job[0] for job in plan()}
        for future in as_completed(futures):
            aid=futures[future]
            try:records.append(future.result());print(aid+': source ready',flush=True)
            except Exception as error:failed.append(dict(id=aid,error=str(error)));print(aid+': failed',flush=True)
    manifest_path=PROJECT/'assets/manifest.json';manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    existing={row['id']:row for row in manifest['assets']}
    for row in records:
        if row['id'] in existing and existing[row['id']]['source_sha256']!=row['source_sha256']:raise RuntimeError('manifest conflict: '+row['id'])
        existing.setdefault(row['id'],row)
    manifest['assets']=list(existing.values());manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (PROJECT/'reports/unit_action_generation.json').write_text(json.dumps(dict(passed=not failed,requested=16,generated=len(records),failures=failed,ids=[row['id'] for row in records],manual_image_compositing=False),ensure_ascii=False,indent=2),encoding='utf-8')
    raise SystemExit(1 if failed else 0)

if __name__=='__main__':main()
