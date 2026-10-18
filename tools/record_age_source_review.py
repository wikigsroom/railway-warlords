"""Seal only images actually inspected individually, without touching source bytes."""
import json
from expand_general_age_portraits import RAW,rows,generator

def main():
 notes=json.loads((RAW/'review_notes.json').read_text(encoding='utf-8'));records=[]
 selected=list(rows())
 if (RAW/'review.json').exists():
  selected_ids={r['id'] for r in selected}
  records=[r for r in json.loads((RAW/'review.json').read_text(encoding='utf-8'))['originals'] if r['id'] not in selected_ids]
 for row in selected:
  key=row['id']+('@'+row['revision'] if row['revision']!='r001' else '')
  note=notes.get(key,{})
  if note.get('accepted') is not True:raise ValueError('Unreviewed/rejected original: '+key)
  source=RAW/row['id']/row['revision']/'source.png'
  records.append(dict(id=row['id'],revision=row['revision'],source_file=source.relative_to(generator.ROOT).as_posix(),sha256=generator.sha(source),accepted=True,viewed_complete_original=True,note=note['note']))
 rejected=[]
 for key,note in notes.items():
  if note['accepted']:continue
  source=RAW/key/'r001/source.png';prompt=source.with_name('prompt.txt')
  if source.exists():rejected.append(dict(id=key,revision='r001',source_file=source.relative_to(generator.ROOT).as_posix(),sha256=generator.sha(source),prompt_sha256=generator.sha(prompt),accepted=False,note=note['note']))
 report=dict(version='0.2.22',originals=records,rejected_originals=rejected,individual_whole_originals_viewed=len(records),review_notes=notes,source_images_modified=False,manual_compositing=False,formal_art_approval=False,historical_likeness_approval=False)
 (RAW/'review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({'reviewed':len(records),'rejected_earlier_originals':sum(not n['accepted'] for n in notes.values())}))

if __name__=='__main__':main()
