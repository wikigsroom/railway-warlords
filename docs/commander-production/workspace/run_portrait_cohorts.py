"""One gateway batch at a time, three jobs total; preserve every original."""
from pathlib import Path
from datetime import datetime,timezone
import json,subprocess,sys,time

BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[1]
RAW=ROOT/'output/imagegen/warlord/commander_expansion_v0228'
cohorts=['martyr_commanders','ndl_commanders','deputy_commanders','cpc_commanders','eccp_commanders']
state=BASE/'portrait_cohort_progress.json'
def save(current,status,completed):
    state.write_text(json.dumps(dict(current=current,status=status,completed=completed,cohorts=cohorts,
        maximum_gateway_concurrency=3,updated_at_utc=datetime.now(timezone.utc).isoformat(),installed=False,
        all_originals_manually_reviewed=False),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

completed=[]
save(cohorts[0],'waiting_for_existing_generator',completed)
while True:
    first=RAW/(cohorts[0]+'_generation.json')
    if first.exists():
        try:report=json.loads(first.read_text(encoding='utf-8'))
        except (ValueError,PermissionError):time.sleep(10);continue
        if report.get('terminal'):
            if not report.get('passed'):
                save(cohorts[0],'failed_requires_same_route_retry',completed);raise SystemExit(1)
            completed.append(cohorts[0]);break
    time.sleep(10)
for cohort in cohorts[1:]:
    save(cohort,'generating_four_independent_living_stages',completed)
    args=[sys.executable,'-X','utf8',str(BASE/'generate_expansion_portraits.py'),'--roster',str(BASE/(cohort+'.json')),'--workers','3']
    with (BASE/(cohort+'_coordinator.log')).open('a',encoding='utf-8') as log:
        result=subprocess.run(args,stdout=log,stderr=subprocess.STDOUT)
    if result.returncode:
        save(cohort,'failed_requires_same_route_retry',completed);raise SystemExit(result.returncode)
    completed.append(cohort)
save('', 'generation_complete_not_manual_or_likeness_approval',completed)
print(json.dumps(dict(generation_complete=True,cohorts=completed)),flush=True)
