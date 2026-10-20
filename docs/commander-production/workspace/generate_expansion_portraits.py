"""Generate independently dated originals only; never installs unreviewed art."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
import argparse
import importlib.util
import json
import shutil
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
P=ROOT/'game/railway_warlords'
spec=importlib.util.spec_from_file_location('portrait_generator',P/'tools/generate_general_portraits.py')
generator=importlib.util.module_from_spec(spec);spec.loader.exec_module(generator)
RAW=ROOT/'output/imagegen/warlord/commander_expansion_v0228'
generator.RAW=RAW

def living_stages(born,died):
    last=died-born-1
    if last>=60:ages=[25,38,50,last]
    elif last>=45:ages=[22,32,41,last]
    elif last>=30:ages=[20,round(20+(last-20)/3),round(20+2*(last-20)/3),last]
    else:ages=[max(15,last-9),max(16,last-6),max(17,last-3),last]
    if ages!=sorted(set(ages)):raise ValueError('Four distinct living stages needed')
    return [dict(id=s,label=label,reference_year=born+age,approximate_age=age) for s,label,age in zip(['young','prime','middle','late'],['青年','壮年','中年','暮年'],ages)]

def jobs(person):
    stages=living_stages(person['birth_year'],person['death_year'])
    for stage in stages:
        age=stage['approximate_age'];year=stage['reference_year']
        # Office is a fact at its documented year. Never project it back onto
        # a youth portrait before military service is separately established.
        uniform_after=person.get('portrait_uniform_not_before',person.get('documented_year'))
        if uniform_after is None:uniform_after=9999
        if year<uniform_after:
            clothing=person.get('youth_clothing','Plain dark Chinese civilian long gown with a modest upright cloth collar, bareheaded. No military rank, medals or insignia.')
        else:clothing=person.get('adult_clothing','Plain muted khaki or gray Chinese period officer cotton high-collar tunic, bareheaded. No invented medals, service insignia, modern camouflage, post-1949 rank boards or costume.')
        face=person.get('portrait_face_brief','Use any reliably documented likeness of this named real person if known. No authenticated likeness has been verified in this production brief. Do not claim an exact archival reconstruction. Give this person an individual, natural face; do not reuse another general\'s face.')
        age_note='This person died young. The fourth stage means the final living phase, NOT an elderly appearance. No gray-haired old man, deep elderly wrinkles or impossible 60-year-old face.' if person['death_year']-person['birth_year']<60 else 'Natural aging at the stated approximate age, with a consistent facial structure across the separately generated variants.'
        documented_year=person.get('documented_year')
        if documented_year is None:documented_year='an institutional biography with appointment year not established'
        prompt=generator.STYLE.replace('post-1949 uniforms, ','')+f'\nSUBJECT: {person["name"]} ({person["id"]}), approximately {age} years old around {year}.\nPerson context: {person["documented_title"]}, documented in {documented_year}; this title must not be projected to the earlier portrait year.\nIdentity: {face}\nAGE: {age_note}\nCLOTHING for THIS year: {clothing}\nOne complete compact bust, entire head and both shoulders visible with 12 percent transparent margin above all hair or headwear and 10 percent at both sides. Fully transparent background. No text, no panel, no frame, no collage.\n'
        yield dict(id=f'portrait_{person["id"]}_{year}',general_id=person['id'],subject=person['name'],reference_year=year,
            age_stage=stage['id'],approximate_age=age,prompt=prompt,revision='r001',reference_urls=person.get('reference_urls',[]),
            reference_scope='Life-year and command-office facts; interpretive illustration, not an authenticated same-year likeness.',
            likeness_approval=False)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--roster',required=True);parser.add_argument('--workers',type=int,default=3);parser.add_argument('--limit-people',type=int);args=parser.parse_args()
    people=json.loads(Path(args.roster).read_text(encoding='utf-8'))['people']
    if args.limit_people:people=people[:args.limit_people]
    all_jobs=[job for person in people for job in jobs(person)]
    RAW.mkdir(parents=True,exist_ok=True)
    # Immutable request manifest; later cohorts use a distinct plan file.
    plan_id=Path(args.roster).stem
    plan=RAW/(plan_id+'_plan.json')
    plan_value={'requested_people':len(people),'requested_originals':len(all_jobs),'jobs':all_jobs,'originals_modified':False}
    if plan.exists() and json.loads(plan.read_text(encoding='utf-8'))!=plan_value:raise ValueError('Immutable plan conflict')
    if not plan.exists():plan.write_text(json.dumps(plan_value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    report=RAW/(plan_id+'_generation.json');records=[];failures=[]
    if report.exists():
        prior=RAW/(plan_id+'_interrupted_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')+'.json')
        shutil.copyfile(report,prior)
    def generate_with_retries(row):
        folder=RAW/row['id']/row['revision']
        for attempt in range(1,5):
            existing_log=folder/'generation.log'
            if existing_log.exists() and not (folder/'source.png').exists():
                archived=folder/('generation_attempt_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')+'.log')
                shutil.copyfile(existing_log,archived)
            try:return generator.generate(row)
            except Exception:
                if attempt==4:raise
                # Same immutable request, same provider and model. No image edits.
                # Backoff stays below a minute and does not block user updates.
                time.sleep(min(45,8*attempt))
    def save(terminal=False):
        value={'requested_people':len(people),'requested_originals':len(all_jobs),'generated':len(records),'failed':len(failures),
            'terminal':terminal,'passed':terminal and not failures,'records':records,'failures':failures,
            'updated_at_utc':datetime.now(timezone.utc).isoformat(),'manual_art_review_complete':False,
            'installed':False,'source_rasters_modified':False,'route':'sub2-image-gen/gpt-image-2.5/high'}
        report.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    save()
    with ThreadPoolExecutor(max_workers=max(1,args.workers)) as pool:
        tasks={pool.submit(generate_with_retries,row):row['id'] for row in all_jobs}
        for future in as_completed(tasks):
            aid=tasks[future]
            try:records.append(future.result());print(f'{len(records)}/{len(all_jobs)} {aid}: whole original ready',flush=True)
            except Exception as e:failures.append({'id':aid,'error':str(e)});print(aid+': FAILED '+str(e),flush=True)
            save()
    save(True)
    raise SystemExit(1 if failures else 0)

if __name__=='__main__':main()
