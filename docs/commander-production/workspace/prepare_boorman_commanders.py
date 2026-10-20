from pathlib import Path
import json

BASE=Path(__file__).resolve().parent
index={r['slug']:r for r in json.loads((BASE/'research/boorman/index.json').read_text('utf-8'))['rows'] if r['passed']}
facts=[('cao-kun','曹锟',1862,1938,'北洋陆军第3镇统制',1906,'division','zhili'),
       ('xu-shuzheng','徐树铮',1880,1925,'西北边防军总司令',1919,'army_or_higher','anhui'),
       ('zhang-zongchang','张宗昌',1881,1932,'第6混成旅旅长',1918,'brigade','fengtian')]
people=[];sources={}
for slug,name,born,died,title,year,level,side in facts:
    row=index[slug];sid='boorman_'+slug.replace('-','_')
    sources[sid]=dict(id=sid,url=row['url'],sha256=row['sha256'],
        publisher='ENP-China / X-Boorman academic digital edition',
        title='Biographical Dictionary of Republican China: '+name)
    record=dict(id=slug.replace('-','_'),name=name,birth_year=born,death_year=died,date_precision='year',
        country='China',historical_side=side,documented_title=title,documented_year=year,
        command_level=level,appointment_start=None,appointment_end=None,
        appointment_date_status='dated_office_reference; full_tenure_requires_review',
        source_ids=[sid],reference_urls=[row['url']],
        eligibility_status='historical_identity_and_qualifying_office_documented; scenario_appointments_require_review',
        likeness_source_status='no_independent_generated_likeness_approval',
        portrait_production_status='pending_four_independent_Sub2_originals')
    if slug=='zhang-zongchang':record['life_year_note']='The cited academic biography gives 1881; other biographical accounts give 1882. Approximate ages use 1881, and the discrepancy remains explicit.'
    people.append(record)
(BASE/'boorman_commanders.json').write_text(json.dumps(dict(schema='commander-expansion-research-1',coverage_complete=False,
    people=people,source_register=sources),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(new_people=len(people),sources=len(sources))))
