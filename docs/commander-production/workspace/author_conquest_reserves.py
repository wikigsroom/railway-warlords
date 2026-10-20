"""Publish optional free-world reserves from sourced, earlier military offices.

These officers are gameplay appointment options, never a reconstructed opening
order of battle. No local campaign receives this supplementary pool. A whole
uncertain appointment year must have passed before it grants a reserve option.
"""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[2];P=ROOT/'game/railway_warlords'
def read(p):return json.loads(p.read_text('utf-8'))
def write(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
services=read(P/'content/definitions/commander_service.json')
existing=read(P/'content/definitions/commander_deployments.json');initial={r['id']:r for r in existing}
unavailable={
 '林彪':[dict(from_date='1938-01-01',through_date='1941-12-31',reason='赴苏治疗期间不列为可即时任命的后备人员；准确往返日另待审核。')],
 '徐海东':[dict(from_date='1940-01-01',through_date='1970-03-25',reason='1940年起长期病休，不作为即时战场任命人选。')],
 '张勋':[dict(from_date='1917-07-13',through_date='1923-12-31',reason='复辟失败后退居天津，不按1911年提督履历自动加入北洋政府战场后备。')],
}
for service in services:
 if service['name'] in unavailable:service['gameplay_unavailable_intervals']=unavailable[service['name']]
 # Their documented early NRA office predates the later allegiance used in
 # this archive. Do not backdate that allegiance into an April 1927 opening.
 if service['name'] in ['叶剑英','叶挺']:service['recall_allegiance_first_documented_year']=1927 if service['name']=='叶剑英' else 1937
 if service['name']=='张宗昌':service['recall_allegiance_first_documented_year']=1922
out=[]
for sid in read(P/'content/scenarios/catalog.json')['scenarios']:
 recipe=read(P/'content/scenarios'/(sid+'.json'))
 if recipe['mode']!='conquest':continue
 date=recipe['anchor_date'];year=int(date[:4]);factions={f:[] for f in recipe['faction_roster']}
 placed={r['general_id'] for rows in initial[sid]['factions'].values() for r in rows}
 for r in services:
  owner=r.get('historical_side','');first=r.get('documented_year')
  # Original commanders already have hand-authored dated scenario rosters.
  # Do not reuse their old 1924 faction fallback as a recall affiliation.
  if r.get('cohort')=='legacy_29':continue
  if owner not in factions or r['id'] in placed or first is None or int(first)>=year:continue
  if int(r.get('recall_allegiance_first_documented_year',0))>=year:continue
  if year<int(r['birth_year'])+16 or year>int(r['death_year']):continue
  if r.get('death_date') and date>r['death_date']:continue
  if any(v['from_date']<=date<=v['through_date'] for v in r.get('gameplay_unavailable_intervals',[])):continue
  if not r.get('source_ids') or not r.get('documented_title'):continue
  factions[owner].append(dict(general_id=r['id'],title_at_start='曾任：'+r['documented_title'],
   formation='',deployment_role='conquest_optional_reserve',auto_assign=False,
   source_ids=r['source_ids'],reference_urls=r['reference_urls'],
   eligible_from=date,eligible_through=date,
   historical_note='自由征服可任命的后备人选；军职见载年份早于开局。不是历史开局任职、现役状态或战场位置的认定。',
   placement_status='gameplay_recall_option_not_historical_opening_oob'))
 out.append(dict(id=sid,anchor_date=date,factions=factions,
  policy='Conquest-only optional reserve; an earlier documented office plus the registered historical allegiance. Never auto-assigned or used in local historical battles.',
  exhaustive=False))
write(P/'content/definitions/commander_recall_pools.json',out)
write(P/'content/definitions/commander_service.json',services)
print(json.dumps(dict(conquests=len(out),optional_reserve_entries=sum(len(rows) for r in out for rows in r['factions'].values()),historical_campaigns_modified=False,counts={r['id']:{f:len(rows) for f,rows in r['factions'].items() if rows} for r in out})))
