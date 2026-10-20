"""Continue the same authorized Sub2 route after the first coordinator ends."""
from pathlib import Path
import json,subprocess,sys,time
BASE=Path(__file__).resolve().parent
while True:
    try:state=json.loads((BASE/'portrait_cohort_progress.json').read_text('utf-8'))
    except (ValueError,PermissionError,FileNotFoundError):time.sleep(10);continue
    if str(state.get('status','')).startswith('failed'):raise SystemExit('Previous cohort failed; no concurrent fallback is started.')
    if state.get('status')=='generation_complete_not_manual_or_likeness_approval':break
    time.sleep(10)
with (BASE/'boorman_commanders_coordinator.log').open('a',encoding='utf-8') as log:
    result=subprocess.run([sys.executable,'-X','utf8',str(BASE/'generate_expansion_portraits.py'),
        '--roster',str(BASE/'boorman_commanders.json'),'--workers','3'],stdout=log,stderr=subprocess.STDOUT)
raise SystemExit(result.returncode)
