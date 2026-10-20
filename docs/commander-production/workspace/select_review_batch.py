"""List complete four-stage sets still awaiting individual source inspection."""
from pathlib import Path
import argparse,json
BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[1]
args=argparse.ArgumentParser();args.add_argument('--people',type=int,default=1);options=args.parse_args()
known={r['id']:r['sha256'] for r in json.loads((BASE/'source_portrait_review.json').read_text('utf-8'))['viewed_originals']}
by={}
for file in sorted((ROOT/'output/imagegen/warlord/commander_expansion_v0228').glob('*_generation.json')):
 for r in json.loads(file.read_text('utf-8'))['records']:
  if known.get(r['id'])!=r['source_sha256']:by.setdefault(r['general_id'],[]).append(r)
groups=[sorted(rows,key=lambda r:r['reference_year']) for rows in by.values() if len(rows)==4][:options.people]
print(json.dumps([{k:r[k] for k in ['id','general_id','subject','reference_year','approximate_age','source_file']} for group in groups for r in group],ensure_ascii=False))
