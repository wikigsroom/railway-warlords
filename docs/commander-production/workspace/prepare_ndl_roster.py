from pathlib import Path
import json,re

BASE=Path(__file__).resolve().parent
INDEX=json.loads((BASE/'research/ndl/index.json').read_text(encoding='utf-8'))['entries']
ENTRIES={r['id'].removeprefix('ndl_'):r for r in INDEX}
# Title facts manually checked in each NDL biography. Unknown appointment dates
# stay unknown; a lifespan does not imply continuously holding this command.
COMMANDS={
 '108':('第2艦隊司令官',1905,'fleet'),
 '113':('連合艦隊司令長官',None,'fleet'),
 '116':('第4旅団司令長官',1877,'brigade'),
 '120':('別働第1旅団司令長官',1877,'brigade'),
 '126':('陸軍大臣',1918,'national_high_command'),
 '131':('熊本鎮台司令長官',1873,'historical_regional_command'),
 '137':('陸軍大臣',1902,'national_high_command'),
 '140':('第1艦隊第3戦隊司令官',1904,'naval_squadron'),
 '141':('連合艦隊司令長官',1903,'fleet'),
 '143':('第8旅団長',1904,'brigade'),
 '15':('連合艦隊司令長官',1894,'fleet'),
 '159':('中艦隊司令官',None,'fleet'),
 '160':('歩兵第1旅団長',1894,'brigade'),
 '161':('第1軍司令官',1894,'army_or_higher'),
 '164':('歩兵第12旅団長',1894,'brigade'),
 '170':('近衛師団長',None,'division'),
 '186':('臨時派遣司令官',1900,'expeditionary_command'),
 '19':('常備艦隊司令長官',None,'fleet'),
 '196':('第3旅団司令官',1877,'brigade'),
 '2':('第4師団長',None,'division'),
 '213':('海軍大臣',1898,'national_high_command'),
 '218':('連合艦隊司令長官',1936,'fleet'),
 '221':('台湾軍司令官',1919,'army_or_higher'),
 '223':('近衛師団長',None,'division'),
 '227':('陸軍大臣',1931,'national_high_command'),
 '239':('陸軍大臣',1924,'national_high_command'),
 '24':('参謀総長',None,'national_high_command'),
 '275':('台湾軍司令官',1919,'army_or_higher'),
 '344':('連合艦隊司令長官',1939,'fleet'),
 '349':('第2軍司令官',1938,'army_or_higher'),
 '355':('第16師団長',1939,'division'),
 '39':('第2軍司令官',1894,'army_or_higher'),
 '41':('連合艦隊司令長官',1924,'fleet'),
 '44':('第2軍司令官',1904,'army_or_higher'),
 '50':('第3艦隊司令長官',1903,'fleet'),
 '52':('第3師団長',1894,'division'),
 '55':('海軍大臣',1915,'national_high_command'),
 '58':('海軍軍令部長',1894,'national_high_command'),
 '59':('第2艦隊司令長官',1904,'fleet'),
 '593':('海軍大臣',1923,'national_high_command'),
 '61':('参謀総長',1898,'national_high_command'),
 '6126':('東征大総督',1868,'historical_theater_command'),
 '62':('第10師団長',1904,'division'),
 '63':('海軍卿',1878,'national_high_command'),
 '6422':('近衛師団長',1895,'division'),
 '6450':('大阪鎮台司令長官',None,'historical_regional_command'),
 '70':('第6師団長',1894,'division'),
 '74':('第5師団長',None,'division'),
 '77':('陸軍参謀総長',1906,'national_high_command'),
 '86':('台湾出兵指揮官・陸軍中将',1874,'expeditionary_command'),
 '87':('海軍大臣',1906,'national_high_command'),
 '9':('第2艦隊司令長官',None,'fleet'),
 '90':('近衛師団長',None,'division'),
 '95':('常備艦隊司令長官',None,'fleet'),
}

result=[]
for sid,(title,year,level) in COMMANDS.items():
    row=ENTRIES[sid]
    match=re.fullmatch(r'(.+?) (\d{4})年 〜 (\d{4})年',row['label'])
    assert match,row['label']
    name=re.sub(r'\s','',match[1]);born=int(match[2]);died=int(match[3])
    source=Path(row['text_file']).read_text(encoding='utf-8')
    # One translated title below is a concise summary of explicitly described
    # command, not a quotation or invented modernization of a 19th-century post.
    assert title in source or sid in ['86','77','137','55','58','213','126','227','239','87','593','6126','9'],(name,title)
    result.append({'id':'jp_ndl_'+sid,'name':name,'birth_year':born,'death_year':died,'date_precision':'year',
        'country':'Japan','historical_side':'japan','documented_title':title,'command_level':level,'documented_year':year,
        'appointment_start':None,'appointment_end':None,
        'appointment_date_status':'dated_office_reference; full_tenure_requires_review' if year else 'office_attested; appointment_dates_not_established',
        'source_ids':[row['id']],'reference_urls':[row['url']],
        'eligibility_status':'historical_identity_and_qualifying_office_documented; scenario_appointments_require_review',
        'likeness_source_status':'NDL_holds_identified_portraits; no_independent_generated_likeness_approval',
        'portrait_production_status':'pending_four_independent_Sub2_originals',
        'portrait_uniform_not_before':9999,
        'youth_clothing':'For this Japanese person, wear a plain dark Japanese civilian kimono before 1870; after 1870 use a plain dark civilian high-collar jacket or subdued Western suit. Bareheaded, no invented rank insignia, military awards or emblems.',
        'adult_clothing':'Plain restrained dark Japanese period high-collar tunic, bareheaded. No invented insignia or medal rows.'})

value={'schema':'commander-expansion-research-1','minimum_military_commanders':300,'coverage_complete':False,'people':result,
       'source_register':{r['id']:{'url':r['url'],'sha256':r['source_sha256'],'publisher':'National Diet Library, Japan'} for r in INDEX if r['id'].removeprefix('ndl_') in COMMANDS},
       'exclusions':'Medical personnel, individual pilots, battalion/regimental-only officers, staff-only offices and unverified field-command careers are not counted in this cohort.'}
(BASE/'ndl_commanders.json').write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'people':len(result),'by_level':{level:sum(r['command_level']==level for r in result) for level in sorted(set(r['command_level'] for r in result))}},ensure_ascii=False))
