"""Five independent Sub2 originals for the officer UI; immutable, reviewed separately."""
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
import argparse,hashlib,json,shutil,subprocess,sys
from PIL import Image

P=Path(__file__).resolve().parents[1];ROOT=P.parents[1]
RAW=ROOT/'output/imagegen/warlord/officer_ui_v0223'
CLI=Path('C:/Users/carzy/.codex/skills/sub2-image-gen/scripts/sub2_image_gen.py')

MATERIAL='''ONE original front-facing flat square interface material for a premium historical military strategy game. Very restrained, coherent silver and gunmetal language. No lettering, symbol, logo, ornament, screw, rust, object, illustration, pattern, sheet, mockup, nested panel or collage. The entire canvas is one opaque material plate with a perfectly straight outer edge. Only the outermost 0.6 percent of the canvas has one extremely thin bevel; 98.8 percent is quiet usable material. Barely perceptible fine brush grain, low contrast, even illumination. No broad border, corner decoration, gold frame, directional spotlight or black vignette. Native Godot controls will provide all readable text and controls. Never copy an existing game asset.\n'''
ICON='''ONE original small gameplay progression emblem for a historical military strategy game, painted with coherent muted brass and blue-gray enamel, soft upper-left light, clear dimensional silhouette, sparse well-defined contours. This is an abstract GAMEPLAY emblem, not an awarded historical decoration and not a reproduction of a real military order. No national flag, ruler, coat of arms, rank, lettering, number, inscription, watermark or invented historical claim. Complete object centered within the middle 76 percent of a square canvas, generous margins, transparent alpha outside, no pedestal, background, ground disc, sheet, views or collage. Readable at 64 pixels.\n'''

SPECS=[
 ('ui','ui_officer_sheet_v023',MATERIAL+'Cool silver-gray #cbd0cd painted matte metal. A subtle pale edge, absolutely quiet low-contrast cool-gray center. Opaque full canvas.',False),
 ('ui','ui_command_plate_v023',MATERIAL+'Dark blue-gray steel #40515a. One hairline silver highlight around the outermost edge, no bronze inner border. Opaque full canvas.',False),
 ('icon','icon_medal_marksmanship_v023',ICON+'One brass circular target emblem with a restrained crossed pair of period bolt-action rifle silhouettes, small dark blue cloth ribbon, compact and uncluttered.',True),
 ('icon','icon_medal_steadfast_v023',ICON+'One simple slate-blue shield with one brass crenellated defense motif, small dark blue cloth ribbon, compact and uncluttered. No crown, eagle or real coat of arms.',True),
 ('icon','icon_medal_logistics_v023',ICON+'One brass supply-wheel and simple wheat-ear emblem, small dark blue cloth ribbon, compact and uncluttered. No national emblems, gear text or real military order.',True),
]

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def generate(spec):
 category,aid,prompt,alpha=spec;folder=RAW/aid/'r001';folder.mkdir(parents=True,exist_ok=True)
 prompt_file=folder/'prompt.txt';source=folder/'source.png'
 if prompt_file.exists() and prompt_file.read_text(encoding='utf-8')!=prompt:raise ValueError('Immutable prompt conflict: '+aid)
 if not prompt_file.exists():prompt_file.write_text(prompt,encoding='utf-8')
 if not source.exists():
  log=folder/'generation.log';attempt=2
  while log.exists():log=folder/f'generation_attempt_{attempt:02d}.log';attempt+=1
  with log.open('w',encoding='utf-8') as out:
   result=subprocess.run([sys.executable,str(CLI),'generate','--model','gpt-image-2.5','--quality','high','--size','1024x1024','--background','transparent' if alpha else 'opaque','--prompt-file',str(prompt_file),'--out',str(source)],stdout=out,stderr=subprocess.STDOUT,timeout=900)
  if result.returncode or not source.exists():raise ValueError('Sub2 generation failed: '+aid)
 with Image.open(source) as im:
  dimensions=list(im.size);alpha_min=im.getchannel('A').getextrema()[0] if im.mode=='RGBA' else 255
  if alpha and alpha_min!=0:raise ValueError('Transparent complete original required: '+aid)
 return dict(id=aid,category=category,subject=aid,view='front',era='game_ui',source_file=source.relative_to(ROOT).as_posix(),source_sha256=sha(source),prompt_file=prompt_file.relative_to(ROOT).as_posix(),prompt_sha256=sha(prompt_file),actual_dimensions=dimensions,source_kind='sub2_image_gen',model='gpt-image-2.5',quality='high',image_modified=False,manual_compositing=False,style_version='officer_ui_v0223',planned_source_request=[1024,1024],runtime_import_max_dimension=1024 if category=='ui' else 256,background='transparent' if alpha else 'opaque',alpha_min=alpha_min,revision='officer_ui_v0223_r001',state='source_reviewed_runtime_pending',game_ready=False,reference_scope='Abstract native UI material or gameplay progression symbol, not a historical award.')

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--install-reviewed',action='store_true');args=parser.parse_args()
 if args.install_reviewed:
  review=json.loads((RAW/'review.json').read_text(encoding='utf-8'));accepted={r['id']:r for r in review['originals']}
  manifest_path=P/'assets/manifest.json';manifest=json.loads(manifest_path.read_text(encoding='utf-8'));known={r['id']:r for r in manifest['assets']}
  for spec in SPECS:
   row=generate(spec);r=accepted[row['id']]
   if not r['accepted'] or not r['viewed_complete_original'] or r['sha256']!=row['source_sha256']:raise ValueError('Whole original source review missing')
   target=P/'assets'/row['category']/(row['id']+'.png')
   if target.exists() and sha(target)!=row['source_sha256']:raise ValueError('Installed original conflict')
   if not target.exists():shutil.copyfile(ROOT/row['source_file'],target)
   known[row['id']]=row|dict(engine_path='res://'+target.relative_to(P).as_posix())
  manifest['assets']=list(known.values());manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
  shutil.copyfile(RAW/'review.json',P/'reports/ui_refinement_source_review.json');print(json.dumps({'installed':len(SPECS),'total':len(known)}));return
 records=[];failures=[]
 with ThreadPoolExecutor(max_workers=2) as pool:
  tasks={pool.submit(generate,s):s[1] for s in SPECS}
  for future in as_completed(tasks):
   try:row=future.result();records.append(row);print(row['id']+': independent original ready',flush=True)
   except Exception as error:failures.append({'id':tasks[future],'error':str(error)});print(tasks[future]+': FAILED',flush=True)
 RAW.mkdir(parents=True,exist_ok=True)
 (RAW/'generation.json').write_text(json.dumps({'passed':not failures,'records':records,'failures':failures,'source_route':'sub2-image-gen/gpt-image-2.5/high','source_images_modified':False},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 raise SystemExit(1 if failures else 0)

if __name__=='__main__':main()
