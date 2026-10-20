"""Install immutable Sub2 originals after complete-source visual inspection.

Runtime review is provisional. It does not assert documentary likeness or formal
art acceptance. No raster is resized, cropped, composited, mirrored or repainted.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,shutil
from PIL import Image

P=Path(__file__).resolve().parents[1];ROOT=P.parents[1]
RAW=ROOT/'output/imagegen/warlord/commander_expansion_v0228'
REVIEW=ROOT/'output/commander_expansion/source_portrait_review.json'
def read(p):return json.loads(p.read_text('utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--only',nargs='*');args=ap.parse_args()
 inspected={r['id']:r for r in read(REVIEW)['viewed_originals']}
 mpath=P/'assets/manifest.json';manifest=read(mpath);known={r['id']:r for r in manifest['assets']}
 records={}
 for report in sorted(RAW.glob('*_generation.json')):
  for row in read(report)['records']:
   if row['id'] in records and records[row['id']]!=row:raise ValueError('Conflicting generated original '+row['id'])
   records[row['id']]=row
 selected=[r for r in records.values() if (not args.only or r['id'] in args.only) and r['id'] in inspected]
 installed=[]
 for row in selected:
  evidence=inspected[row['id']]
  if not evidence.get('viewed_complete_original') or not evidence.get('usable_for_in_engine_review'):continue
  src=ROOT/row['source_file'];prompt=ROOT/row['prompt_file']
  assert evidence['sha256']==row['source_sha256']==sha(src),row['id']
  assert sha(prompt)==row['prompt_sha256'],row['id']
  with Image.open(src) as im:
   assert im.mode=='RGBA' and im.getchannel('A').getextrema()[0]==0 and list(im.size)==row['actual_dimensions'],row['id']
  target=P/'assets/portrait'/(row['id']+'.png');tp=P/'docs/asset-prompts'/(row['id']+'.txt')
  if row['id'] in known:assert known[row['id']]['source_sha256']==row['source_sha256'],row['id']
  if target.exists():assert sha(target)==row['source_sha256'],row['id']
  else:shutil.copyfile(src,target)
  if tp.exists():assert sha(tp)==row['prompt_sha256'],row['id']
  else:shutil.copyfile(prompt,tp)
  known[row['id']]=row|dict(category='portrait',view='three_quarter',era=str(row['reference_year']),
   state='whole_source_viewed_runtime_review_pending',game_ready=False,
   style_version='warlord_commanders_v0228',planned_source_request=[1024,1024],
   runtime_import_max_dimension=512,background='transparent',alpha_min=0,
   engine_path='res://'+target.relative_to(P).as_posix(),reviewed=True,
   formal_art_approval=False,historical_likeness_approval=False)
  # Only importer configuration is authored; original PNG bytes are untouched.
  imp=target.with_suffix('.png.import')
  if not imp.exists():
   digest=hashlib.md5(('res://'+target.relative_to(P).as_posix()).encode()).hexdigest()
   ctex=f'res://.godot/imported/{target.name}-{digest}.ctex'
   template=(P/'assets/portrait/portrait_wu_peifu_1914.png.import').read_text('utf-8')
   import re
   template=re.sub(r'^uid=.*\n','',template,flags=re.M)
   template=re.sub(r'^path=.*$',f'path="{ctex}"',template,flags=re.M)
   template=re.sub(r'^source_file=.*$',f'source_file="res://{target.relative_to(P).as_posix()}"',template,flags=re.M)
   template=re.sub(r'^dest_files=.*$',f'dest_files=["{ctex}"]',template,flags=re.M)
   imp.write_text(template,encoding='utf-8')
  installed.append(row['id'])
 manifest['assets']=list(known.values());write(mpath,manifest)
 provenance=[];total=0
 for row in manifest['assets']:
  file=P/row['engine_path'].removeprefix('res://');total+=file.stat().st_size
  prompt_path='docs/asset-prompts/'+row['id']+'.txt'
  assert (P/prompt_path).is_file(),row['id']
  provenance.append(dict(id=row['id'],category=row['category'],image=file.relative_to(P).as_posix(),
   image_sha256=row['source_sha256'],prompt=prompt_path,prompt_sha256=sha(P/prompt_path),
   source_kind=row['source_kind'],model=row['model'],quality=row['quality'],
   original_workspace_source=row['source_file'],image_modified=False,formal_art_approval=False))
 write(P/'docs/asset-provenance/index.json',dict(version='0.2.28',count=len(provenance),image_bytes=total,assets=provenance))
 report=dict(version='0.2.28',generated_originals=len(records),whole_sources_viewed=len(inspected),
  installed_expansion_originals=sum(r.get('style_version')=='warlord_commanders_v0228' for r in known.values()),
  eligible_this_run=len(installed),source_rasters_modified=False,manual_compositing=False,
  formal_art_approval=False,historical_likeness_approval=False,updated_at_utc=datetime.now(timezone.utc).isoformat())
 write(P/'reports/commander_portrait_installation.json',report)
 write(P/'reports/commander_portrait_source_review.json',read(REVIEW))
 print(json.dumps(report))
if __name__=='__main__':main()
