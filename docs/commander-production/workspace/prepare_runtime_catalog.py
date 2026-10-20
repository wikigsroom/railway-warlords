"""Stage the expanded catalog without touching the frozen preceding release."""
from pathlib import Path
import importlib.util,json
from datetime import datetime,timezone

BASE=Path(__file__).resolve().parent;P=BASE.parents[1]/'game/railway_warlords'
spec=importlib.util.spec_from_file_location('living',BASE/'generate_expansion_portraits.py');living=importlib.util.module_from_spec(spec);spec.loader.exec_module(living)
OUT=BASE/'runtime_data';OUT.mkdir(exist_ok=True)
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def write(name,obj):(OUT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

old=read(BASE/'baseline_generals_v0227.json');lifes=read(BASE/'baseline_lifespans_v0227.json')
people=[];sources={}
for cohort in ['martyr','ndl','deputy','cpc','eccp','boorman']:
    d=read(BASE/(cohort+'_commanders.json'));people+=d['people']
    for key,row in d['source_register'].items():
        if key in sources and sources[key]!=row:raise ValueError('Source conflict '+key)
        sources[key]=row
assert len(people)+len(old)>=300
assert len({p['id'] for p in people+old})==len(people)+len(old)
assert len({p['name'] for p in people+old})==len(people)+len(old)
service=[]
for d in old:
    life=lifes['generals'][d['id']]
    service.append(dict(id=d['id'],name=d['name'],birth_year=life['birth_year'],death_year=life['death_year'],
        date_precision=life.get('date_precision','year'),country='China',historical_side=d.get('reference_faction_1924_before_coup',''),
        documented_title='',command_level='legacy_pending_office_audit',documented_year=None,
        reference_urls=life['reference_urls'],source_ids=[],cohort='legacy_29',
        appointment_date_status='legacy_general; military_office_and_full_tenure_audit_pending',
        life_year_note=life.get('precision_note',''),historical_note=d.get('historical_note','')))
    if d['id'] in ['yamagata_aritomo','tojo_hideki','yamashita_tomoyuki']:service[-1]['country']='Japan'
    if d['id'] in ['kuropatkin','alexei_kaledin']:service[-1]['country']='Russia'
    if d['id']=='waldersee':service[-1]['country']='Germany'

roles={
 'land':dict(stars=dict(infantry=3,artillery=2,cavalry=1,navy=0,aviation=0,logistics=2),passive_skill='inf_focus',active_skill='assault_order'),
 'naval':dict(stars=dict(infantry=1,artillery=2,cavalry=0,navy=3,aviation=0,logistics=2),passive_skill='defense',active_skill='coordinated_fire'),
 'command':dict(stars=dict(infantry=3,artillery=2,cavalry=1,navy=0,aviation=0,logistics=3),passive_skill='staff_morale',active_skill='ration_order'),
}
for person in people:
    gd=dict(id=person['id'],name=person['name'],reference_faction_1924_before_coup='',reference_faction_by_scenario={},
        **roles['naval' if person['command_level'] in ['fleet','naval_squadron'] else 'command' if person['command_level'] in ['army_or_higher','deputy_army_or_higher','national_high_command','historical_theater_command','historical_regional_command'] else 'land'],
        max_rank=6,max_skill_rank=3,deployment_rule='dated_scenario_explicit_roster',
        initial_position='authored_in_scenario_not_general_definition',
        active_year_min=person['birth_year']+16,active_year_max=person['death_year'],
        historical_note='原始军职与来源见人物履历。星级、战法与成长费用属于游戏平衡参数，不是史实数值。',
        balance_profile='unrated_command_role_baseline_v1')
    old.append(gd)
    record={k:v for k,v in person.items() if k not in ['adult_clothing','youth_clothing','portrait_face_brief','portrait_uniform_not_before']}
    record['cohort']='expanded_v0228';service.append(record)
    stages=living.living_stages(person['birth_year'],person['death_year'])
    for stage in stages:
        age=stage['approximate_age']
        if stage['id']=='late' and age<60:stage['label']='生前晚期'
        elif stage['id']=='middle' and age<40:stage['label']='生前中期'
        elif stage['id']=='prime' and age<25:stage['label']='青年后期'
    lifes['generals'][person['id']]=dict(name=person['name'],birth_year=person['birth_year'],death_year=person['death_year'],
        date_precision='year',stages=stages,late_stage_is_last_living_period=stages[-1]['approximate_age']<60,
        reference_urls=person['reference_urls'],source_type='institutional_biography_or_scholarly_reference',source_review_date='2026-10-20',
        likeness_approval=False,precision_note=person.get('life_year_note','仅登记有来源的生卒年；显示约岁，未知生日不设为1月1日。'),
        military_deployable=True,person_role='military_commander')

lifes['production_version']='0.2.28'
write('generals.json',old);write('commander_service.json',service)
write('commander_sources.json',[dict(id=key,**{k:v for k,v in value.items() if k!='id'}) for key,value in sorted(sources.items())])
write('general_lifespans.json',lifes)
write('catalog_scope.json',dict(planned_version='0.2.28',military_commanders=len(old),new_people=len(people),political_only=4,
    all_asian_brigade_and_division_commands_covered=False,
    important_limit='A documented commander cohort is not an exhaustive census of every Asian brigade/division appointment. Scenario participation and field placement remain separately authored.',
    assets_generated=False,release_complete=False))
print(json.dumps(dict(staged_military_commanders=len(old),new_people=len(people),sources=len(sources),runtime_modified=False)))
