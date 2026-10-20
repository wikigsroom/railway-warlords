"""Bind only explicitly inspected images to human-readable inspection decisions."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[1]
f=BASE/'source_portrait_review.json';review=json.loads(f.read_text('utf-8'))
records={r['id']:r for p in (ROOT/'output/imagegen/warlord/commander_expansion_v0228').glob('*_generation.json') for r in json.loads(p.read_text('utf-8'))['records']}
known={r['id']:r for r in review['viewed_originals']}
decisions={}
for decision_file in sorted(BASE.glob('source_review_decisions*.json')):
 decisions.update(json.loads(decision_file.read_text('utf-8')))
for id,decision in decisions.items():
 r=records[id];p=ROOT/r['source_file'];previous=known.get(id,{})
 # A review of r001 must never silently approve a newly generated r002.
 expected=decision.get('expected_source_sha256')
 if expected and expected!=r['source_sha256']:continue
 if previous and previous.get('sha256')!=r['source_sha256'] and not expected:continue
 if (previous.get('sha256')==r['source_sha256'] and previous.get('path')==str(p)
     and previous.get('notes')==decision['notes']
     and previous.get('usable_for_in_engine_review')==decision['usable_for_in_engine_review']):
  continue
 digest=hashlib.sha256(p.read_bytes()).hexdigest();assert digest==r['source_sha256'],id
 known[id]=dict(id=id,path=str(p),sha256=digest,viewed_complete_original=True,
   notes=decision['notes'],usable_for_in_engine_review=decision['usable_for_in_engine_review'],
   formal_art_approval=False,historical_likeness_approval=False,accepted=False)
review.update(viewed_originals=list(known.values()),reviewed_at_utc=datetime.now(timezone.utc).isoformat(),
 all_generated_originals_reviewed=len(known)==len(records),source_rasters_modified=False,
 inspection_scope='Complete originals displayed individually; runtime usability is not historical likeness or formal art approval.')
f.write_text(json.dumps(review,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(whole_sources_viewed=len(known),generated=len(records),formal_art_approval=False)))
