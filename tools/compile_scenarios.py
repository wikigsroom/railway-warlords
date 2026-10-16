"""Author explicit playable deployments on compiled real-geography maps."""
from pathlib import Path
import json
P=Path(__file__).resolve().parents[1]
def read(n):return json.loads((P/'content/definitions'/f'{n}.json').read_text(encoding='utf-8'))
def write(n,obj):(P/'content/scenarios'/f'{n}.json').write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
def beijing_coup(campaign=False):
    event=dict(id='beijing_coup',date='1924-10-23',type='coup',new_owner='guominjun',source_owner='zhili',actor_id='feng_yuxiang',city_id='beijing',designation_date='1924-10-25',designation_source_ids=['nxtzb_guominjun_1924'],forecast_date='1924-10-09',name='北京政变',description='史实：1924年10月23日冯玉祥发动北京政变；25日议决改组国民军。局内按人物、编队和北京控制权检查事件条件，不生成或传送部队恢复历史结果。',source_ids=['coup_1924','ruc_1924','gz_beijing_coup_1924'],new_faction_resources=dict(cash=400,food=300,arms=160),resource_basis='沿用初版事件的游戏军需配置，不声称史实库存。',trigger_policy='fixed_campaign_calendar' if campaign else 'conditional_conquest_calendar')
    if campaign:event.update(round=5,forecast_round=3,forecast_date='1924-10-21')
    return event
campaign_targets=[['zhuozhou','zhuozhou','langfang','yangcun','nanyuan','tianjin'],['changxindian','guan','machang','tianjin','shanhaiguan','luanzhou'],['tangshan','jiumenkou','shanhaiguan','luanzhou','beijing','tianjin']]
allids=[]
for m in read('missions'):
    year=m['year'];number=int(m['id'][-2:]);target=campaign_targets[[1920,1922,1924].index(year)][number-1]
    map_id='jingfeng' if target in ['jiumenkou','shanhaiguan','luanzhou','tangshan'] else 'jingjin'
    objective=m['primary_objective']['type']
    defender='anhui' if year==1920 else 'fengtian'
    player='zhili'
    # Shanhaiguan withdrawal is played from the historically retreating Fengtian side.
    if year==1922 and number==5:player,defender='fengtian','zhili'
    if year==1924 and number==2:player,defender='fengtian','zhili'
    scenario=dict(id=m['id'],name=m['title'],mode='campaign',map_id=map_id,anchor_date={1920:'1920-07-14',1922:'1922-04-29',1924:'1924-09-15'}[year],days_per_round=1,round_limit=m['round_limit'],player_default=player,faction_roster=[player,defender],target_city_id=target,objective_type=objective,objective_count=m['primary_objective']['count'],general_slots=m['general_slots'],starting_resources=m['starting_resource_budget'],player_formations=min(m['unit_budget']['player_formations'],14),enemy_formations=min(m['unit_budget']['enemy_formations'],16),full_visibility=False,unlock_after=m['unlock_after'],stars=m['stars'],historical_status='historical_theater_with_authored_tactical_deployment',source_ids=m['source_ids'],deployment_note='城市、地形和铁路依现实地理抽象；编队数量、交战位置和关卡目标为游戏设计，不宣称复原战斗序列。',events=[])
    scenario['calendar_status']='simulation_calendar_not_daily_battle_reconstruction'
    if year==1924 and number==2:
        scenario['anchor_date']='1924-10-06'
        scenario['source_ids']=list(dict.fromkeys(scenario['source_ids']+['bkzx_shanhaiguan_1924']))
        scenario['historical_date_basis']='以1924年10月6日奉军攻击九门口的记载作为本关时间起点；不把游戏回合解释成逐日战斗记录。'
        scenario['base_city_id']='jinzhou'
        scenario['friend_start_offset']={'q':4,'r':-3}
        scenario['enemy_start_offset']={'q':-2,'r':1}
        scenario['deployment_note']='九门口、山海关起局由直军防守；奉军从关外东侧进入，锦州作后方，不将秦皇岛配置为奉军基地。编队数量与具体格位为游戏战术抽象，不宣称复原实际战斗序列。'
    if year==1924 and number==3:
        scenario.update(anchor_date='1924-10-06', objective_type='hold', objective_count=3,
                        base_city_id='qinhuangdao', enemy_base_city_id='jinzhou',
                        initial_city_owners={'qinhuangdao':'zhili','shanhaiguan':'zhili','jinzhou':'fengtian'},
                        friend_start_offset={'q':-4,'r':2}, enemy_start_offset={'q':4,'r':-3})
        scenario['source_ids']=list(dict.fromkeys(scenario['source_ids']+['bkzx_shanhaiguan_1924']))
        scenario['historical_date_basis']='与九门口攻击关共用有记载的1924年10月6日窗口；山海关由直军防御，奉军从关外进攻。三阶段坚守是关卡目标，不声称实际坚守天数。'
        scenario['deployment_note']='直军控制山海关、秦皇岛，奉军以后方锦州为基地从关外进攻。原“直军夺取奉军山海关”目标已纠正为防守；具体编队和格位为战术抽象。'
    if year==1924 and number==5:
        scenario['anchor_date']='1924-10-19'
        scenario['events']=[beijing_coup(True)]
    write(m['id'],scenario);allids.append(m['id'])
for s in read('scenarios'):
    roster=['zhili','fengtian','anhui','shanxi','jiangsu','zhejiang','yunnan']
    if s['anchor_date']>='1921-01-01':roster.append('guangdong')
    if s['anchor_date']>='1923-01-01':roster.append('dongjiang')
    s.update(map_id='conquest_china',player_default='zhili',faction_roster=roster,general_slots=5,starting_resources=dict(cash=650,food=520,arms=360),full_visibility=False,objective_type='unify',objective_count=1,player_formations=0,enemy_formations=0,target_city_id='beijing',historical_status='historical_theater_with_authored_tactical_deployment',deployment_note='战略归属按历史阵营作粗略抽象；城外编队与能力白名单为平衡配置。租界不作为独立可占领城市。',events=[])
    s['weak_faction_ids']=[f for f in roster if f in ['anhui','shanxi','zhejiang','yunnan','dongjiang']]
    s['weak_faction_tag_basis']='游戏挑战标签，用于成就计数，不是对各时期实际军力的历史判断。'
    if s['id']=='conq_1924':
        s['events']=[beijing_coup()]
    write(s['id'],s);allids.append(s['id'])
focus_targets=['zhuozhou','jiumenkou','tianjin','luanzhou','shanhaiguan','tangshan','yangcun','machang','tianjin','guan','nanyuan','shanhaiguan']
for i,c in enumerate(read('challenges')):
    target=focus_targets[i];m='jingfeng' if target in ['jiumenkou','luanzhou','shanhaiguan','tangshan'] else 'jingjin'
    if c['focus']=='navy':target='hanyang';m='hankou'
    if c['focus']=='embark':target='nanjing';m='ningpu'
    objective='repair' if c['focus']=='repair_rail' else ('escort' if c['focus']=='navy' else ('disembark' if c['focus']=='embark' else 'capture'))
    c.update(mode='legion',map_id=m,anchor_date='1924-09-15',days_per_round=1,player_default='zhili',faction_roster=['zhili','fengtian'],target_city_id=target,objective_type=objective,objective_count=1,starting_resources=dict(cash=c['deployment_cash_budget'],food=360,arms=220),player_formations=10+i//4,enemy_formations=11+i//4,full_visibility=False,events=[],historical_status='declared_military_training_on_real_geography',deployment_note='军团训练题，不对应史实战役。',unlock_after=[])
    write(c['id'],c);allids.append(c['id'])
write('catalog',{'scenarios':allids})
print(f'Authored {len(allids)} scenario recipes (18 campaign / 3 conquest / 12 legion).')
