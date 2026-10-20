"""New complete Sub2 revisions for eight rejected identities; retain every r001 byte."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import importlib.util, json, shutil

BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[1]
spec=importlib.util.spec_from_file_location('expansion',BASE/'generate_expansion_portraits.py')
expansion=importlib.util.module_from_spec(spec);spec.loader.exec_module(expansion)
raw=expansion.RAW;path=raw/'eccp_commanders_generation.json'
proof=json.loads(path.read_text('utf-8'))
ids={'cn_534e5c14','cn_767d9f506587'}
people=[r for r in json.loads((BASE/'eccp_commanders.json').read_text('utf-8'))['people'] if r['id'] in ids]
briefs={
 'cn_534e5c14':('Frederick Townsend Ward, the American adventurer born in Salem, Massachusetts in 1831. He is the real historical commander called Hua Er in Chinese. A white American man of European ancestry with wavy medium-brown hair, a long narrow oval face, prominent straight nose, deep-set eyes, restrained narrow moustache and small pointed chin beard. Keep this SAME underlying face at all four living ages. Do not interpret his Chinese transliterated name as a Chinese ethnicity or use a generic Chinese officer face.'),
 'cn_767d9f506587':('Henry Andres Burgevine, the American soldier born in 1836, the real historical commander called Bai Qiwen in Chinese. A white American man of European ancestry, short side-parted dark-brown hair, a broad angular face, strong straight nose, deep-set eyes, firm square chin and a neat narrow moustache with short side-whiskers. Keep this SAME underlying face at all four living ages. Do not interpret his Chinese transliterated name as a Chinese ethnicity or use a generic Chinese officer face.')}
jobs=[]
for person in people:
 for row in expansion.jobs(person):
  row['revision']='r002'
  row['prompt']=expansion.generator.STYLE.replace('post-1949 uniforms, ','')+f'\nSUBJECT IDENTITY: {briefs[person["id"]]}\nILLUSTRATION DATE: {row["reference_year"]}, approximately {row["approximate_age"]} years old. This man died young; do not depict an elderly person.\nCLOTHING: Sober 1850s-style dark wool civilian frock coat, plain waistcoat, white shirt and dark neckcloth; no military rank or medals. This production has not verified his uniform at this particular age.\nCOMPOSITION: One compact complete bust, all hair and both shoulders, generous transparent space around the head and sides. Clean natural alpha edges without a colored fringe. No text, no panels, no collage.\n'
  jobs.append(row)
plan=BASE/'foreign_identity_revision_plan.json'
value=dict(reason='Eight whole originals rejected for identity or cross-age inconsistency',jobs=jobs,originals_modified=False)
if plan.exists():assert json.loads(plan.read_text('utf-8'))==value
else:plan.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
records=[]
with ThreadPoolExecutor(max_workers=2) as pool:
 futures=[pool.submit(expansion.generator.generate,row) for row in jobs]
 for future in as_completed(futures):
  records.append(future.result());print(f'{len(records)}/8 new complete revision ready',flush=True)
assert len(records)==8
old=[r for r in proof['records'] if r['general_id'] in ids]
receipt=dict(superseded_originals=old,replacements=records,source_rasters_modified=False,
 formal_art_approval=False,historical_likeness_approval=False,review_required=True,
 updated_at_utc=datetime.now(timezone.utc).isoformat())
(BASE/'foreign_identity_revision_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
snapshot=raw/'eccp_commanders_before_foreign_identity_revision.json'
if not snapshot.exists():shutil.copyfile(path,snapshot)
replacement={r['id']:r for r in records}
proof['records']=[replacement.get(r['id'],r) for r in proof['records']]
proof['revised_identities']=8;proof['manual_art_review_complete']=False;proof['installed']=False
path.write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Eight revisions generated; none automatically reviewed or installed',flush=True)
