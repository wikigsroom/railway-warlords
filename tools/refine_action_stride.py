"""Generate a replacement whole PNG; never edit, flip or crop any raster."""
from pathlib import Path
import argparse, hashlib, json, shutil, subprocess, sys
from PIL import Image
from generate_unit_action_assets import RAW, PROJECT, ROOT, SKILL

AID='unit_rifle_n_march_b'
PROMPT='''One isolated transparent 2.5D strategy-game sprite of exactly THREE early
1920s Republican Chinese rifle soldiers walking NORTH, away toward the TOP edge.
Strict elevated REAR view: only backs, backpacks and back of peaked caps; no faces.
This is the RIGHT FOOT BACK keyframe of a walking cycle. For EACH of the three men,
the RIGHT leg extends backward toward the BOTTOM-RIGHT, with the RIGHT boot heel and
sole plainly visible at the LOWEST point. The LEFT foot is planted forward, farther
away near the UPPER-LEFT. Both LEFT and RIGHT feet clearly separate. Do not put the
left boot behind. All three men keep an upright back and a level ground plane.
Every man carries his wood-stock bolt-action rifle on his RIGHT shoulder: the rifle
barrel is on the RIGHT-HAND side of each head as seen in this rear view. Hold the
rifle with the right hand near the stock. Never swap the rifle onto the left side.
Muted khaki high-collar tunics and trousers, plain UNMARKED khaki peaked caps, brown
leather belts, simple brown square backpacks, puttees, black ankle boots. Compact
triangular formation, one man rear center/top and two side men slightly nearer the
camera/bottom, equal figure scale and clear separation. Fixed elevated orthographic
camera, broad shaded hand-painted volumes, warm upper-left sunlight, restrained dark
contours, premium historical map miniature. Complete figures, boots and rifles inside
generous transparent margins. ONLY solid subjects and fully transparent alpha zero
exterior and gaps. No floor, background, shadow, haze, glow, terrain, text, logos,
insignia, flags, helmets, modern weapons, panels, sheets, collage or overlays.
'''

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--install-reviewed',action='store_true');args=parser.parse_args()
    folder=RAW/AID/'r002';folder.mkdir(parents=True,exist_ok=True);prompt=folder/'prompt.txt';source=folder/'source.png'
    if prompt.exists() and prompt.read_text(encoding='utf-8')!=PROMPT:raise RuntimeError('immutable prompt mismatch')
    if not prompt.exists():prompt.write_text(PROMPT,encoding='utf-8')
    if not source.exists():
        with (folder/'generation.log').open('w',encoding='utf-8') as log:
            result=subprocess.run([sys.executable,str(SKILL),'generate','--model','gpt-image-2.5','--size','1024x1024','--quality','high','--background','transparent','--prompt-file',str(prompt),'--out',str(source)],stdout=log,stderr=subprocess.STDOUT,timeout=900)
        if result.returncode or not source.exists():raise RuntimeError('Sub2 stride generation failed')
    if not args.install_reviewed:print('Whole source ready for review: '+str(source));return
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    path=PROJECT/'assets/manifest.json';manifest=json.loads(path.read_text(encoding='utf-8'))
    row=next(row for row in manifest['assets'] if row['id']==AID)
    if row['source_sha256']!=sha(source):row['revision_history']=row.get('revision_history',[])+[{key:row.get(key) for key in ['revision','source_file','source_sha256','prompt_file','prompt_sha256']}]
    with Image.open(source) as image:
        if image.mode!='RGBA' or image.getchannel('A').getextrema()[0]!=0:raise RuntimeError('transparent exterior missing')
        row['actual_dimensions']=list(image.size);row['alpha_bounds']=list(image.getchannel('A').point(lambda v:255 if v>32 else 0).getbbox())
    row.update(source_file=source.relative_to(ROOT).as_posix(),source_sha256=sha(source),prompt_file=prompt.relative_to(ROOT).as_posix(),prompt_sha256=sha(prompt),revision='action_r002')
    shutil.copyfile(source,PROJECT/row['engine_path'].removeprefix('res://'))
    path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(AID+': reviewed whole source installed')

if __name__=='__main__':main()
