from pathlib import Path
import hashlib
import json
import re
import unicodedata
import argparse

parser=argparse.ArgumentParser()
parser.add_argument('--deputies',action='store_true')
args=parser.parse_args()

ROOT=Path(__file__).resolve().parents[2]
RESEARCH=Path(__file__).resolve().parent/'research'
download={r['id']:r for r in json.loads((RESEARCH/'source_downloads.json').read_text(encoding='utf-8'))}
rx=re.compile(r'^(.+?)[（(]\s*(\d{4}|[?？])\s*[—－-]\s*(\d{4})[^）)]*[）)]\s*(.+)$')
qualification=re.compile(r'(师师长|旅旅长|军军长|路军司令(?:员)?|总司令(?:员)?|军总指挥|军司令(?:员)?)(?:兼|、|$)')
if args.deputies:
    qualification=re.compile(r'(师副师长|军副军长|军副总指挥|路军副总司令|路军副总指挥|军副司令(?:员)?)(?:兼|、|$)')
already={r['name'] for r in json.loads((RESEARCH.parent/'martyr_commanders.json').read_text(encoding='utf-8'))['people']} if args.deputies else set()
rows={}
for f in sorted(RESEARCH.glob('martyrs_*.txt')):
    for line in f.read_text(encoding='utf-8').splitlines():
        match=rx.match(unicodedata.normalize('NFKC',line))
        if not match or not match[2].isdigit():continue
        name=re.sub(r'\s','',match[1]);title=match[4]
        if name in already:continue
        q=qualification.search(title)
        if not q:continue
        sid=f.stem
        if sid not in download:raise ValueError(sid)
        born=int(match[2]);died=int(match[3]);level='brigade' if '旅旅长' in q[1] else 'division' if '师师长' in q[1] else 'army_or_higher'
        if args.deputies:level='deputy_division' if '师副师长' in q[1] else 'deputy_army_or_higher'
        # An army prefix is not a command appointment. Require the qualifying
        # office itself to end the phrase, or to be followed by a second office.
        if name in rows:
            if [born,died] != [rows[name]['birth_year'],rows[name]['death_year']]:raise ValueError('Life conflict '+name)
            rows[name]['source_ids'].append(sid)
            continue
        gid='cn_'+''.join(format(ord(c),'x') for c in name)
        side='ccp' if any(s in title for s in ['八路军','新四军','红军','人民革命军','东北抗日联军','东北抗日同盟军']) else 'northeast_volunteers' if any(s in title for s in ['义勇军','救国军','民众','少年铁血','吉林人民']) else 'kmt'
        rows[name]={'id':gid,'name':name,'birth_year':born,'death_year':died,'date_precision':'year',
            'country':'China','historical_side':side,'documented_title':title,'command_level':level,
            'documented_year':died,'appointment_start':None,'appointment_end':None,
            'appointment_date_status':'death_year_office_attested; appointment_start_unknown',
            'source_ids':[sid],'reference_urls':[download[sid]['url']],
            'eligibility_status':'historical_identity_and_qualifying_office_documented; scenario_appointments_require_review',
            'likeness_source_status':'no_authenticated_portrait_reviewed_yet',
            'portrait_production_status':'pending_four_independent_Sub2_originals'}

result={'schema':'commander-expansion-research-1','minimum_military_commanders':300,
 'coverage_complete':False,'people':list(rows.values()),
 'source_register':{sid:{k:v for k,v in r.items() if k not in ['file']} for sid,r in download.items() if sid.startswith('martyrs_')},
 'notes':['Source lists attest names, life years and offices. They do not establish appointment start dates.',
          'Brigade/division/corps commanders only. Civilian officials, unit collectives, staff-only appointments, battalion/regimental/squad commanders are excluded from this cohort.',
          'The roster is a researched cohort, not a claim to cover all Asian commanders or a shipped playability certificate.']}
if args.deputies:
    result['notes'][1]='Documented deputy division/corps commanders, including concurrent field commands. Original deputy titles are retained; no promotion to full commander is implied. Staff-only appointments are excluded.'
(RESEARCH.parent/('deputy_commanders.json' if args.deputies else 'martyr_commanders.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'people':len(rows),'levels':{level:sum(r['command_level']==level for r in rows.values()) for level in ['brigade','division','army_or_higher']}},ensure_ascii=False))
for row in rows.values():print(row['name']+' | '+row['documented_title'])
