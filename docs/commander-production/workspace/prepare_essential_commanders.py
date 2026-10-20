"""Append sourced commanding officers without rebuilding earlier reviewed records."""
from pathlib import Path
import importlib.util,json
BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[1];P=ROOT/'game/railway_warlords'
def read(p):return json.loads(p.read_text('utf-8-sig'))
def write(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
spec=importlib.util.spec_from_file_location('living',BASE/'generate_expansion_portraits.py');living=importlib.util.module_from_spec(spec);spec.loader.exec_module(living)
S={r['id']:r for r in read(BASE/'research/essential/index.json')}
for r in S.values():
 if not r.get('locally_cached_original'):r['retrieval_status']='web_tool_verified_native_download_unavailable'
PEOPLE=[
 ('guan_tianpei','关天培',1781,1841,'China','qing','广东水师提督',1834,'fleet',['gdws_guan'],'High forehead, broad cheekbones, lean oval face; thin long moustache and short pointed beard only at mature ages.'),
 ('sengge_rinchen','僧格林沁',1811,1865,'China','qing','清军参赞大臣、北方军事统帅',1853,'historical_theater_command',['dpm_sengge','nam_second_china'],'Mongolian officer with broad round face, small eyes, robust neck and thick moustache at mature ages.'),
 ('ding_ruchang','丁汝昌',1836,1895,'China','qing','北洋海军提督',1888,'fleet',['weihai_ding'],'Broad square face, strong cheekbones, distinct heavy moustache and short rounded chin beard at mature ages.'),
 ('luo_rongguang','罗荣光',1833,1900,'China','qing','天津镇总兵、大沽口守将',None,'historical_field_command',['hunan_luo'],'Long narrow angular face, receding hairline and a long tapered gray beard only in the late living stage.'),
 ('liu_buchan','刘步蟾',1852,1895,'China','qing','北洋海军右翼总兵兼定远舰管带',1888,'naval_squadron',['weihai_liu'],'Oval face with wide forehead, closely set eyes and a neat dark moustache in mature ages. Avoid the elderly Qing minister archetype.'),
 ('yang_fang','杨芳',1770,1846,'China','qing','湖南提督、赴粤参赞大臣',1841,'historical_theater_command',['cppcc_yang_fang'],'Lean weathered angular face, high cheekbones, downturned eyes and long sparse beard at advanced ages.'),
 ('ge_yunfei','葛云飞',1789,1841,'China','qing','定海镇总兵',1838,'historical_field_command',['ge_yunfei_memorial'],'Long broad forehead, upright serious brows, medium cheekbones and short pointed dark beard after middle age.'),
 ('zhang_xun','张勋',1854,1923,'China','beiyang_gov','江南提督',1911,'historical_regional_command',['boorman_zhang_xun'],'High shoulders, thick neck, sloping forehead, bushy eyebrows and pale skin, as described by the cited 1917 contemporary character sketch. A thin Qing queue remains even after 1912.'),
 ('zhang_fakui','张发奎',1896,1980,'China','kmt','国民革命军第12师师长',1926,'division',['boorman_zhang_fakui','shanghai_zhang_fakui'],'Long broad face, thick straight brows, close cropped black hair, small moustache when mature, firm wide jaw.'),
 ('tang_shengzhi','唐生智',1890,1970,'China','kmt','国民革命军第8军军长',1926,'army_or_higher',['boorman_tang_shengzhi','nlpi_tang_shengzhi'],'Long narrow face, high hairline, rounded ears, thin straight moustache at middle age, slender neck.'),
 ('he_yingqin','何应钦',1890,1987,'China','kmt','国民革命军第1军军长',1926,'army_or_higher',['he_yingqin_office','he_yingqin_life'],'Round narrow-chinned face, swept short hair, arched brows and distinct neat small moustache at middle age.'),
 ('gordon_bremer','伯麦',1786,1850,'Britain','british_empire','英国赴华海军指挥官',1840,'fleet',['anu_bremer','nam_first_china'],'British naval officer, wide forehead, short receding light-brown hair, strong aquiline nose, full sideburns at mature ages; distinct face, not a generic Victorian portrait.'),
 ('hugh_gough','休·高夫',1779,1869,'Britain','british_empire','英国驻华陆军统帅',1841,'expeditionary_command',['nam_gough_life','nam_first_china'],'Irish officer with high broad forehead, receding hair, narrow lower face and long white side whiskers at elderly ages, clean upper lip.'),
 ('william_parker','威廉·帕克',1781,1866,'Britain','british_empire','英国驻华海军统帅',1841,'fleet',['rmg_parker','nam_first_china'],'British naval officer with broad rounded face, short wavy hair, heavy brows, long nose, prominent full sideburns and clean-shaven chin at mature ages.'),
 ('hope_grant','霍普·格兰特',1808,1875,'Britain','british_empire','英国赴华远征军司令',1860,'expeditionary_command',['nam_grant','nam_second_china'],'Scottish officer, long narrow face, deep-set eyes, tall forehead, close hair and pronounced side whiskers at mature ages, clean upper lip.'),
 ('cousin_montauban','库赞·蒙托邦',1796,1878,'France','french_empire','法国赴华远征军统帅',1859,'expeditionary_command',['napoleon_montauban','bnf_montauban','nam_second_china'],'French officer with round broad forehead, receding wavy hair, broad nose and thick curved moustache at mature ages, defined broad cheeks.'),
 ('robert_napier','罗伯特·纳皮尔',1810,1890,'Britain','british_empire','赴华英军师级指挥官',1860,'division',['npg_napier','nam_second_china'],'British Indian Army engineer officer with high forehead, deep-set eyes, aquiline nose, angular jaw, thick mutton-chop side whiskers at mature ages.'),
 ('alfred_gaselee','阿尔弗雷德·盖斯利',1844,1918,'Britain','british_empire','英属印度军旅指挥官',1897,'brigade',['bl_gaselee','dnb_gaselee'],'British Indian Army officer with long lean oval face, receding short hair, deep-set eyes and a substantial curved moustache at mature ages.'),
]
people=[]
for gid,name,born,died,country,side,title,year,level,refs,face in PEOPLE:
 qing=side=='qing';british=country=='Britain';french=country=='France'
 youth=('Plain Qing-period dark robe with upright collar, shaved front scalp and a subtle queue falling behind, no military insignia.' if qing or gid=='zhang_xun' else 'Plain nineteenth-century civilian coat and high shirt collar, bareheaded, no medals or military insignia.' if british or french else 'Plain dark Chinese early twentieth-century civilian long gown, upright collar, bareheaded; no rank or insignia.')
 adult=('Plain muted dark Qing robe and historically shaped Qing official winter cap with an undecorated rounded crown. No invented rank badge, fantasy armor or modern tunic.' if qing else 'Dark late-Qing military robe with a restrained dark round cap and a thin queue; no modern Republican rank boards.' if gid=='zhang_xun' else 'Plain dark navy nineteenth-century British naval officers coat, restrained high collar, no invented medal ribbons or modern service insignia.' if level=='fleet' and british else 'Plain dark nineteenth-century French officers coat with upright collar, no medals or invented rank insignia.' if french else 'Plain muted nineteenth-century British officers coat with high collar, no camouflage, no modern rank boards and no invented medals.' if british else 'Plain muted khaki or gray early Republican Chinese officer high-collar tunic, bareheaded, no invented medals or post-1949 rank insignia.')
 people.append(dict(id=gid,name=name,birth_year=born,death_year=died,date_precision='year',country=country,historical_side=side,documented_title=title,documented_year=year,command_level=level,appointment_start=None,appointment_end=None,appointment_date_status='dated_office_reference; full_tenure_requires_review',source_ids=refs,reference_urls=[S[s]['url'] for s in refs],eligibility_status='historical_identity_and_qualifying_office_documented; scenario_appointments_require_review',likeness_source_status='interpretive_features_not_authenticated_likeness',portrait_production_status='pending_four_independent_Sub2_originals',portrait_face_brief=face+' Preserve recognizable structure across age stages; these are interpretive illustrations, not authenticated archival copies.',youth_clothing=youth,adult_clothing=adult))
for p in people:
 if p['id']=='tang_shengzhi':p['life_year_note']='Boorman gives 1890 with a question mark; NLPI registers 1890–1970. Approximate ages use 1890; uncertainty is retained.'
 if p['id']=='gordon_bremer':p['source_name_variants']=['James John Gordon Bremer','戈登·伯麦']
 if p['id']=='william_parker':p['source_name_variants']=['Sir William Parker','巴加']
 if p['id']=='hugh_gough':p['source_name_variants']=['Hugh Gough','郭富']
 if p['id']=='alfred_gaselee':p['historical_note']='DNB is used for life years and the 1897 brigade command only; its 1900 Waldersee and entry-day claims are not adopted. British Library records support the Beijing relief context.'
cohort=dict(schema='commander-expansion-research-1',coverage_complete=False,people=people,source_register=S)
path=BASE/'essential_commanders.json'
if path.exists():assert read(path)==cohort,'Immutable essential cohort differs'
else:write(path,cohort)
if __name__=='__main__':
 generals=read(P/'content/definitions/generals.json');service=read(P/'content/definitions/commander_service.json');sources=read(P/'content/definitions/commander_sources.json');life=read(P/'presentation/data/general_lifespans.json')
 existing={r['id'] for r in generals};source_ids={r['id'] for r in sources}
 roles={'land':dict(stars=dict(infantry=3,artillery=2,cavalry=1,navy=0,aviation=0,logistics=2),passive_skill='inf_focus',active_skill='assault_order'),'naval':dict(stars=dict(infantry=1,artillery=2,cavalry=0,navy=3,aviation=0,logistics=2),passive_skill='defense',active_skill='coordinated_fire'),'command':dict(stars=dict(infantry=3,artillery=2,cavalry=1,navy=0,aviation=0,logistics=3),passive_skill='staff_morale',active_skill='ration_order')}
 for p in people:
  if p['id'] in existing:continue
  role='naval' if p['command_level'] in ['fleet','naval_squadron'] else 'land' if p['command_level'] in ['division','brigade'] else 'command'
  generals.append(dict(id=p['id'],name=p['name'],reference_faction_1924_before_coup='',reference_faction_by_scenario={},**roles[role],max_rank=6,max_skill_rank=3,deployment_rule='dated_scenario_explicit_roster',initial_position='authored_in_scenario_not_general_definition',active_year_min=p['birth_year']+16,active_year_max=p['death_year'],historical_note='史实履历与来源见人物档案；星级、战法及成长为游戏平衡参数。',balance_profile='unrated_command_role_baseline_v1'))
  service.append({k:v for k,v in p.items() if k not in ['portrait_face_brief','youth_clothing','adult_clothing']}|dict(cohort='essential_v0228'))
  stages=living.living_stages(p['birth_year'],p['death_year'])
  for s in stages:
   if s['id']=='late' and s['approximate_age']<60:s['label']='生前晚期'
   if s['id']=='middle' and s['approximate_age']<40:s['label']='生前中期'
  life['generals'][p['id']]=dict(name=p['name'],birth_year=p['birth_year'],death_year=p['death_year'],date_precision='year',stages=stages,late_stage_is_last_living_period=stages[-1]['approximate_age']<60,reference_urls=p['reference_urls'],source_type='institutional_biography_or_scholarly_reference',source_review_date='2026-10-20',likeness_approval=False,precision_note=p.get('life_year_note','有来源的生卒年，未知生日保持年精度。'),military_deployable=True,person_role='military_commander')
 for sid,row in S.items():
  if sid not in source_ids:sources.append(row)
 write(P/'content/definitions/generals.json',generals);write(P/'content/definitions/commander_service.json',service);write(P/'content/definitions/commander_sources.json',sources);write(P/'presentation/data/general_lifespans.json',life)
 print(json.dumps(dict(added_cohort=len(people),military_commanders=len(generals),new_originals_requested=len(people)*4,all_historical_officers_covered=False)))
