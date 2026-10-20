"""Author start-date snapshots. These lists are not a continuous service history.

Unknown names are left out rather than manufacturing an officer to fill a quota.
Scenario formations are gameplay stacks, never literal historical battalions.
"""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[2];P=ROOT/'game/railway_warlords'
def read(p):return json.loads(p.read_text('utf-8'))
def write(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
people=read(P/'content/definitions/generals.json');by_name={r['name']:r['id'] for r in people}
service=read(P/'content/definitions/commander_service.json');by_id={r['id']:r for r in service}
sources=read(P/'content/definitions/commander_sources.json');source_index={r['id']:r for r in sources}
boorman={r['slug']:r for r in read(ROOT/'output/commander_expansion/research/boorman/index.json')['rows'] if r['passed']}
for slug,r in boorman.items():
 sid='boorman_'+slug.replace('-','_')
 if sid not in source_index:
  record=dict(id=sid,url=r['url'],sha256=r['sha256'],publisher='ENP-China / X-Boorman academic digital edition',title='Biographical Dictionary of Republican China')
  sources.append(record);source_index[sid]=record
for name,slug,title,year,level in [
 ('吴佩孚','wu-peifu','北洋陆军第3师师长',1918,'division'),
 ('张作霖','zhang-zuolin','奉军统帅、东三省巡阅使',1919,'army_or_higher'),
 ('张学良','zhang-xueliang','奉军第3混成旅旅长',1920,'brigade'),
 ('冯玉祥','feng-yuxiang','陆军第16混成旅旅长',1917,'brigade'),
 ('孙传芳','sun-chuanfang','北洋陆军第18师师长',1921,'division'),
 ('齐燮元','qi-xieyuan','陆军第6师师长',1916,'division'),
 ('阎锡山','yan-xishan','第2战区司令长官',1937,'army_or_higher'),
 ('唐继尧','tang-jiyao','川滇黔联军总司令',1924,'army_or_higher'),
 ('陈炯明','chen-jiongming','粤军总司令兼第1军军长',1918,'army_or_higher'),
 ('许崇智','xu-chongzhi','粤军第2军军长',1918,'army_or_higher'),
 ('段祺瑞','duan-qirui','北洋陆军第6镇统制',1905,'division'),
 ('李宗仁','li-zongren','国民革命军第7军军长',1926,'army_or_higher'),
 ('白崇禧','bai-chongxi','国民革命军第7军参谋长兼第2旅旅长',1926,'brigade')]:
 if slug not in boorman:continue
 r=by_id[by_name[name]];sid='boorman_'+slug.replace('-','_')
 r.update(documented_title=title,documented_year=year,command_level=level,source_ids=[sid],reference_urls=list(dict.fromkeys(r.get('reference_urls',[])+[boorman[slug]['url']])),appointment_date_status='dated_office_reference; full_tenure_requires_review')
 # The dictionary's life-year conventions do not overwrite the independently
 # registered dates. Several early biographies contain acknowledged year errors.
for r in service:
 life=read(P/'presentation/data/general_lifespans.json')['generals'].get(r['id'],{})
 for key in ['birth_date','death_date']:
  if key in life:r[key]=life[key]

def E(name,title='',formation='',reserve=False,refs=None,note=''):
 id=by_name[name];r=by_id[id]
 return dict(general_id=id,title_at_start=title or r.get('documented_title',''),formation=formation,
  deployment_role='strategic_reserve' if reserve else 'field_command',auto_assign=not reserve,
  source_ids=refs if refs is not None else r.get('source_ids',[]),reference_urls=r.get('reference_urls',[]),
  historical_note=note,placement_status='authored_gameplay_stack_not_literal_historical_location')
def warlord(year,campaign=False):
 z=[E('吴佩孚','直军前线指挥',note='所部属于直军；编队格位为战术抽象。'),E('曹锟','直系军政统帅',reserve=True)]
 if year>=1922:z.append(E('冯玉祥','直军将领',note='1924年10月23日前仍列直军；政变按既有事件另行处理。'))
 f=[E('张作霖','奉军统帅',reserve=campaign),E('张学良','奉军前线将领')]
 if year>=1922:f.append(E('郭松龄','奉军前线将领',note='详细军职及战斗序列仍待单独复核。'))
 if year>=1924:f.append(E('张宗昌','奉军后援指挥',note='不把其1926年的直鲁联军职务前移至1924年。'))
 result={'zhili':z,'fengtian':f}
 if year==1920:result['anhui']=[E('段祺瑞','定国军统帅',reserve=True),E('徐树铮','皖军东路指挥',note='1920年7月直皖冲突中的东路作战，非以军官生卒年推定。')]
 if not campaign:
  # Free-world political/military reserves may be appointed by the player;
  # they are not asserted to be present at an authored local engagement.
  if year==1920:result['zhili'].append(E('冯玉祥','第16混成旅旅长'))
  result['zhili'].append(E('孙传芳','直系军官',note='驻防及具体部队需按地区另查；不自动推演为北方局部战役参战者。'))
  for side,name,title in [('shanxi','阎锡山','山西军政首领'),('jiangsu','齐燮元','江苏军政将领'),('zhejiang','卢永祥','浙江督军'),('yunnan','唐继尧','云南军政首领')]:
   result[side]=[E(name,title)]
  if year>=1922:result['guangdong']=[E('许崇智','粤军统帅')]
  if year>=1924:result['dongjiang']=[E('陈炯明','东江粤军统帅')]
 return result

out=[]
for sid in read(P/'content/scenarios/catalog.json')['scenarios']:
 recipe=read(P/'content/scenarios'/(sid+'.json'));date=recipe['anchor_date'];year=int(date[:4]);factions={f:[] for f in recipe['faction_roster']}
 authored={}
 if recipe['mode']=='legion':
  note='Military training uses the separately budgeted reference-era selection; not a historical battle.'
 elif sid.startswith(('campaign_1920_','campaign_1922_','campaign_1924_')) or sid.startswith('conq_'):
  authored=warlord(year,recipe['mode']=='campaign');note='军政统帅与前线将领分开；未强制统一每方人数。1924年政变由既有事件处理。'
 elif sid in ['asia_1840','campaign_1840_01']:
  authored={'qing':[E('裕谦','浙江巡抚',refs=['eccp_volume_2'],note='1840年出任浙江巡抚；钦差大臣职务为1841年，不前移。')]}
  if sid=='asia_1840':authored['qing'].append(E('林则徐','钦差大臣、广东防务主持者',reserve=True))
  note='尚未核实的英方将领留空，不把广东将领自动放在浙江战场。'
 elif sid=='asia_1860' or sid=='campaign_1860_03':
  authored={'taiping':[E('洪秀全','太平天国天王',reserve=True),E('陈玉成','英王、前军主将'),E('李秀成','忠王、后军主将')],
   'qing':[E('曾国藩','湘军统帅',reserve=True),E('曾国荃','湘军统帅'),E('彭玉麟','湘军水师统帅',refs=['eccp_volume_2']),E('杨岳斌','湘军水师统帅',refs=['eccp_volume_2'])]}
  note='湘军水师自1853年形成；1862/1863年的后续官衔不作1860年开局官职。无1862年才成立的淮军。'
 elif sid=='asia_1890':
  authored={'qing':[E('李鸿章','直隶总督、北洋军政主持者',reserve=True),E('刘铭传','台湾巡抚',reserve=True),E('宋庆','毅军统帅'),E('冯子材','清军将领',reserve=True)]}
  note='仅编列本批可证实的清方在世军政统帅；不以1894年日本联军职务代替1890年任职。'
 elif sid in ['campaign_1890_02','campaign_1890_03']:
  authored={'qing':[E('李鸿章','北洋军政统筹',reserve=True),E('宋庆','清军统帅')],
    'japan':[E('伊東祐亨','连合舰队司令长官'),E('大山巌','第2军司令官'),E('山縣有朋' if '山縣有朋' in by_name else '山县有朋','日本陆军统帅',reserve=True)]}
  if sid.endswith('_03'):authored['japan'].extend([E('野津道貫','日本陆军统帅'),E('乃木希典','日本陆军旅团长')])
  note='黄海海战、辽东战事与讲和日期是不同事件；本目录是战区名单，非宣称每人同日同格参战。后续逐战还原单独审核。'
 elif sid=='asia_1900' or sid.startswith('campaign_1900_'):
  authored={'qing':[E('荣禄','武卫军军政统筹',reserve=True),E('董福祥','甘军统帅'),E('宋庆','毅军统帅')],
   'eight_nation':[E('福島安正','日本派遣军指挥',note='日方派遣军将领；不以其代表其他七国。')]}
  note='不在1900年6—8月部署9月才抵华的瓦德西；未核实义和团军职不虚造师旅。'
 elif sid=='asia_1917':
  authored={'beiyang_gov':[E('段祺瑞','北洋军政人物',reserve=True),E('冯国璋','江苏督军',reserve=True),E('冯玉祥','第16混成旅将领'),E('曹锟','直隶督军')],
   'guangzhou_government':[E('孙中山','南方政治军事领袖',reserve=True)],
   'russian_empire':[E('卡列金','顿河军政首领',reserve=True)]}
  note='广州军政府1917年9月成立，现有6月锚点存在既有历史审核项；将领名单不把其称为6月已经成立的政府。'
 elif sid in ['campaign_1917_01','campaign_1917_02']:
  authored={'beiyang_gov':[E('段祺瑞','北洋军政人物',reserve=True)],'guangzhou_government':[E('孙中山','护法政治领袖',reserve=True)]}
  note='现有剧本锚点先于广州军政府成立，保留明确审核项；不虚构随军编制。不把卡列金放入彼得格勒。'
 elif sid=='asia_1927' or sid.startswith('campaign_1927_'):
  authored={'kmt':[E('蒋介石','国民革命军总司令',reserve=True),E('李宗仁','国民革命军第7军军长'),E('白崇禧','北伐军前线指挥')],
   'zhili':[E('吴佩孚','北方军阀将领',reserve=True),E('孙传芳','五省联军统帅')],
   'fengtian':[E('张作霖','安国军统帅',reserve=True),E('张学良','安国军将领'),E('张宗昌','直鲁联军总司令')],
   'shanxi':[E('阎锡山','山西军政首领')],'guominjun':[E('冯玉祥','国民联军总司令')],'yunnan':[E('唐继尧','云南军政人物',reserve=True)]}
  if sid=='campaign_1927_03':
   authored={'ccp':[E('贺龙','起义军总指挥兼第20军军长'),E('叶挺','第11军副军长兼第24师师长')],'kmt':[]}
   note='1927年8月1日南昌起义军事指挥；周士第所部8月2日加入，不前移。贺龙的归属指起义军合作方，不倒推入党日期。'
  else:note='不在1927年4月为李德胜、彭德怀安排尚未取得的师旅军职；北伐阶段另行核对。'
 elif sid in ['asia_1940','campaign_1940_01','campaign_1940_02']:
  authored={'kmt':[E('蒋介石','军事委员会委员长',reserve=True),E('李宗仁','第5战区司令长官',reserve=True),E('张自忠','第33集团军总司令')],
   'ccp':[E('朱德','第18集团军总司令',reserve=True),E('彭德怀','第18集团军副总司令'),E('刘伯承','第129师师长'),E('贺龙','第120师师长'),E('聂荣臻','晋察冀军区司令员'),E('陈赓','第386旅旅长')],
   'japan':[E('山本五十六','连合舰队司令长官')]}
  if sid=='campaign_1940_01':authored={'kmt':authored['kmt'],'japanese_occupied':[]}
  if sid=='campaign_1940_02':
   authored={'ccp':authored['ccp'],'japanese_occupied':[]}
   authored['ccp'].append(E('范子侠','第129师新编第10旅旅长',note='1940年百团大战中的旅级指挥；另据中国军网战史核对。'))
  note='中国战区按部队与日期分别编列；不把赴苏养伤的林彪、1940年病休的徐海东部署到百团大战。日方师团级具体任职本批尚待补齐，空缺不伪造。'
 else:note='未完成军职与参战事实核对的阵营名单留空；不使用人物在世年龄自动补齐。'
 for owner,entries in authored.items():
  if owner not in factions:continue
  seen=set()
  for entry in entries:
   assert entry['general_id'] not in seen,(sid,owner,entry['general_id']);seen.add(entry['general_id'])
   r=by_id[entry['general_id']]
   assert r['birth_year']+16<=year<=r['death_year'],(sid,r['name'])
   entry.update(eligible_from=date,eligible_through=date,date_scope='scenario_start_snapshot_only_not_full_service_tenure')
  factions[owner]=entries
 out.append(dict(id=sid,anchor_date=date,factions=factions,uniform_side_limit=None,roster_policy='explicit_dated_sides',
  historical_oob_complete=False,source_review_status='curated_partial_roster_with_explicit_gaps',historical_note=note))
write(P/'content/definitions/commander_service.json',service)
write(P/'content/definitions/commander_sources.json',sources)
write(P/'content/definitions/commander_deployments.json',out)
print(json.dumps(dict(scenarios=len(out),military_people=len(people),dated_entries=sum(len(e) for d in out for e in d['factions'].values()),empty_sides=sum(not e for d in out if not d['id'].startswith('legion_') for e in d['factions'].values()),all_asia_oob_complete=False)))
