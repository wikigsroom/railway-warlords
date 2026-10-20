"""Append independently sourced start-date deployments, preserving earlier audits."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[2];P=ROOT/'game/railway_warlords'
def read(p):return json.loads(p.read_text('utf-8'))
def write(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
services={r['id']:r for r in read(P/'content/definitions/commander_service.json')}
rows=read(P/'content/definitions/commander_deployments.json');index={r['id']:r for r in rows}
def add(sid,side,gid,title=None,reserve=False,note=''):
 r=index[sid];s=services[gid];date=r['anchor_date'];assert side in r['factions']
 assert s['birth_year']+16<=int(date[:4])<=s['death_year'],(sid,gid)
 e=dict(general_id=gid,title_at_start=title or s['documented_title'],formation='',
  deployment_role='strategic_reserve' if reserve else 'field_command',auto_assign=not reserve,
  source_ids=s['source_ids'],reference_urls=s['reference_urls'],historical_note=note,
  placement_status='authored_gameplay_stack_not_literal_historical_location',
  eligible_from=date,eligible_through=date,date_scope='scenario_start_snapshot_only_not_full_service_tenure')
 r['factions'][side]=[old for old in r['factions'][side] if old['general_id']!=gid]+[e]

# The three-party expedition was British/French, not the 1900 Eight-Nation force.
timeline_path=P/'content/history/asia_timeline.json';timeline=read(timeline_path)
if not any(s['id']=='nam_second_china_war' for s in timeline['sources']):
 timeline['sources'].append(dict(id='nam_second_china_war',title='National Army Museum: Second China War',url='https://www.nam.ac.uk/explore/second-china-war',use='1860年英法联军统帅、大沽及八里桥战事；不用作精确地格驻地依据。',source_status='secondary_institutional_summary'))
for t in timeline['timelines']:
 for c in t.get('conflicts',[]):
  if c['id']=='second_opium_war_1860':c['source_ids']=['nam_second_china_war','state_china_milestone']
write(timeline_path,timeline)
for sid in ['campaign_1860_01','campaign_1860_02']:
 path=P/'content/scenarios'/(sid+'.json');recipe=read(path)
 recipe['faction_roster']=['qing','british_empire','french_empire']
 recipe['initial_wars']=[['qing','british_empire'],['qing','french_empire']]
 recipe['starting_formations_by_faction']={'qing':8,'british_empire':5,'french_empire':3}
 recipe['initial_relations']=[dict(faction_a='british_empire',faction_b='french_empire',state='ALLIANCE')]
 # These are authored playable stack counts, never literal historical strengths.
 recipe['formation_count_status']='gameplay_stack_counts_not_historical_troop_numbers'
 recipe['objective_type']='hold';recipe['objective_count']=5
 recipe['objective_by_faction']={'qing':{'type':'hold','count':5},'british_empire':{'type':'capture','count':1,'accept_allied_control':True},'french_empire':{'type':'capture','count':1,'accept_allied_control':True}}
 recipe['source_ids']=['asia_timeline','nam_second_china_war']
 if sid.endswith('_01'):recipe['initial_city_owners']={'tianjin':'qing','beijing':'qing'}
 write(path,recipe)
 index[sid]['factions']={f:index[sid]['factions'].get(f,[]) for f in recipe['faction_roster']}

for sid in ['asia_1840','campaign_1840_01']:
 add(sid,'british_empire','gordon_bremer',note='1840年7月5日定海远征的海军指挥；舰队格位是游戏抽象。')
 if sid=='asia_1840':add(sid,'qing','guan_tianpei',reserve=True,note='广东防务统帅作为自由世界战略后备；不放入浙江局部战场。')
 index[sid]['historical_note']='英方海军指挥据NAM远征记述；葛云飞当时丁忧，不以1841年定海防务倒推1840年7月到场。'
add('campaign_1840_02','qing','guan_tianpei',reserve=True,note='1841年1月7日虎门外围炮台战事的广东水师统筹；不把其2月26日殉职前移。')
add('campaign_1840_02','british_empire','gordon_bremer',note='1841年1月海军远征；不部署3月才来华的高夫或8月才接掌海军的帕克。')
for gid in ['hugh_gough','william_parker']:
 add('campaign_1840_03','british_empire',gid,note='1842年长江进军及南京议和战区指挥，非宣称条约签订日仍有同一场强攻。')

for sid in ['asia_1860','campaign_1860_01','campaign_1860_02']:
 add(sid,'qing','sengge_rinchen',note='北方战区指挥。8月大沽与9月张家湾/八里桥是分别发生的战事；部队格位为抽象。')
 add(sid,'british_empire','hope_grant')
 add(sid,'french_empire','cousin_montauban')
 if sid!='campaign_1860_02':add(sid,'british_empire','robert_napier',title='英军师级指挥官',note='据NAM，1860年8月21日所部师进攻大沽北炮台。')
 index[sid]['historical_note']+='；1860年北线仅登记有来源的清军和英法联军，不使用1900年八国联军标签。'

for sid in ['asia_1890','campaign_1890_02']:
 add(sid,'qing','ding_ruchang')
 add(sid,'qing','liu_buchan')
# Both naval officers had died by the April 1895 scenario; no age-year shortcut.
for sid in ['asia_1900','campaign_1900_01']:
 add(sid,'qing','luo_rongguang',reserve=sid=='asia_1900',note='1900年6月17日大沽守将；不延用到7月14日天津战役。')
add('campaign_1900_03','eight_nation','alfred_gaselee',title='英属印度远征军指挥官',note='1900年8月北京救援的英方指挥；不把尚未抵华的瓦德西置于开局。')
for sid in ['asia_1927','campaign_1927_01','campaign_1927_02']:
 add(sid,'kmt','he_yingqin',reserve=True,note='国民革命军第1军军政统筹后备；不宣称其到达该城市的某一具体地格。')
 add(sid,'kmt','tang_shengzhi',reserve=True,note='武汉国民政府北伐战区指挥；城市战斗和日期的既有审核项另列。')
 add(sid,'kmt','zhang_fakui',title='国民革命军第4军军长',reserve=True,note='1927年扩编后的第4军指挥；原12师履历仅作档案参照。')
add('campaign_1927_03','kmt','zhang_fakui',title='国民革命军第2方面军前敌总指挥',reserve=True,note='起义前后方面军统筹人物，当日在庐山；列战区战略后备，非南昌城内守军或即时在场将领。')
write(P/'content/definitions/commander_deployments.json',rows)
print(json.dumps(dict(scenarios=len(rows),entries=sum(len(v) for r in rows for v in r['factions'].values()),local_1860_factions_corrected=True,historical_orders_of_battle_complete=False)))
